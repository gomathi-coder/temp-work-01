# LinkWiki — AI Processing Pipeline

## Overview

All language tasks are handled by Claude (`claude-sonnet-4-6`).
The pipeline runs once per ingested URL, plus on-demand batch jobs (`sync`).

---

## Per-Entry Pipeline (triggered on `add`)

```
Raw content  ──▶  [TRUNCATE]  ──▶  Claude: summarise + tag + entities
                                         │
                              ┌──────────┴──────────┐
                              ▼                     ▼
                         Store result        Suggest group(s)
                              │                     │
                              └──────────┬──────────┘
                                         ▼
                               Auto-link to existing entries
```

### Step 1 — Content Truncation

Before sending to Claude, content is truncated to ≤ 80 000 chars (~20k tokens),
keeping the beginning and end of the document (most useful for web articles and
transcripts that front-load conclusions).

For YouTube transcripts, timestamps are stripped but chapter markers are kept.

### Step 2 — Single Claude call: Summarise + Tag + Entities

One call, structured JSON output. Prompt caching applied to the system prompt.

**System prompt (cached):**
```
You are an expert research assistant processing personal knowledge-base entries.
Always respond with valid JSON matching the schema provided.
Be precise with entities; prefer canonical names (e.g. "GPT-4" not "gpt4").
Tags should be lowercase, hyphen-separated, 1–3 words each.
```

**User prompt template:**
```
URL type: {url_type}
Title: {title}
Author: {author}

Content:
{truncated_content}

Return JSON:
{
  "summary": "3–5 sentence summary",
  "tags": ["tag1", "tag2", ...],        // 5–15 tags
  "entities": [
    {"name": "...", "type": "person|tool|paper|organisation|concept|dataset|model", "description": "..."},
    ...
  ],
  "suggested_groups": ["Group Name 1", "Group Name 2"]   // 0–3 guesses based on content
}
```

### Step 3 — Group Matching

`suggested_groups` from Claude is compared against existing group names (string
similarity + exact match). If a match is found, the entry is assigned to that group.
If no match, the suggestion is stored as a pending group proposal shown in `stats`.

---

## Batch Pipeline (triggered on `sync`)

### Tag-based linking (fast, no LLM)
```
For each pair of entries sharing ≥ 2 tags:
  strength = 0.4 × (shared_tag_count / min(tags_a, tags_b))
  upsert link (shared_tag)
```

### Entity-based linking (fast, no LLM)
```
For each pair of entries sharing ≥ 1 entity (by canonical name):
  strength = 0.5 × (shared_entity_count / min(entities_a, entities_b))
  upsert link (shared_entity)
```

### Semantic clustering (slow, uses ChromaDB + optional Claude)

```
1. Embed all unembedded summaries → ChromaDB
2. For each entry, query top-K nearest neighbours (cosine similarity)
3. If similarity ≥ 0.70 → upsert semantic link with that score
4. Run HDBSCAN-style cluster detection on the embedding matrix
5. Each cluster ≥ 3 entries → propose or update an auto-semantic group
   (Claude names the group given a list of its entry titles/tags)
```

Group naming call (one call per new cluster):
```
Given these entries:
  - "Attention Is All You Need" [tags: transformer, attention, paper]
  - "The Illustrated Transformer" [tags: transformer, attention, tutorial]
  - "Let's build GPT" [tags: llm, transformer, education, pytorch]

Suggest a short (2–5 word) group name and one-sentence description.
Return JSON: {"name": "...", "description": "..."}
```

---

## Prompt Caching Strategy

| Prompt part | Cached? | Rationale |
|-------------|---------|-----------|
| System prompt (per-entry call) | Yes (`cache_control: ephemeral`) | Same for every entry |
| System prompt (group naming) | Yes | Same structure every time |
| Content / user turn | No | Unique per entry |

Expected cache hit rate after warm-up: ~85%.
Estimated cost per entry: ~$0.002–$0.005 (depends on content length).

---

## Token Budget Estimates

| Operation | Input tokens (est.) | Output tokens (est.) |
|-----------|--------------------|--------------------|
| Per-entry summarise/tag | 1 000 – 20 000 | 300 – 600 |
| Group naming (batch) | 200 – 500 | 50 – 100 |
| Semantic group refresh (N=100 entries) | — | — (no LLM, only embeddings) |

---

## Fallback Behaviour

| Failure | Fallback |
|---------|---------|
| Claude API timeout | Retry ×3 with exponential backoff (2s, 4s, 8s) |
| Claude returns invalid JSON | Retry once with stricter prompt; if still invalid, store raw response in `error_msg` and mark status `error` |
| Content too short (< 100 chars) | Skip LLM; store URL with title only, tags = [] |
| Rate limit (429) | Pause and retry after `Retry-After` header duration |

---

## Extractor Design

### YouTube
```
1. pytube: fetch title, author, description, publish_date
2. youtube-transcript-api: fetch transcript (auto-generated or manual)
   - If no transcript available: fall back to description only
3. Parse description for URLs with regex
4. Strip timestamps from transcript text before sending to Claude
```

### Web / Article
```
1. requests: GET page HTML  (User-Agent: Mozilla)
2. trafilatura.extract(): extract main article text, strip nav/ads
3. BeautifulSoup: extract all <a href> from main content area
4. Open Graph / JSON-LD: extract title, author, og:description as fallback
5. If text < 200 chars (paywall): store OG metadata only, status = partial
```

### GitHub Repository
```
1. GitHub API: GET /repos/{owner}/{repo}  (title, description, topics, language, stars)
2. GitHub API: GET /repos/{owner}/{repo}/readme  (decode base64 README)
3. Parse README for external URLs
4. If GITHUB_TOKEN set: use authenticated request (5000 req/hr vs 60 req/hr)
```

### HuggingFace (Model / Dataset page)
```
Treated as web extractor, but with HF-specific parsing:
1. trafilatura handles the model card text well
2. Extra: parse "Tags" and "Tasks" from HF page metadata
3. Extra: extract linked paper(s) from "Paper" section
```

### arXiv
```
1. arXiv API: fetch abstract, authors, categories by paper ID
2. Optionally: fetch full PDF text via arxiv2text (heavyweight, optional dep)
3. Abstract is used as primary content if full text not available
```

---

## Directory Structure (reference for implementation)

```
linkwiki/
├── core/
│   ├── config.py          # env vars, paths, model name
│   ├── database.py        # SQLite schema + all CRUD operations
│   ├── extractors/
│   │   ├── __init__.py    # route_url() dispatcher
│   │   ├── youtube.py
│   │   ├── web.py
│   │   ├── github.py
│   │   └── arxiv.py
│   ├── ai.py              # all Claude API calls (one module, cached system prompt)
│   ├── vectors.py         # ChromaDB wrapper (embed, query, cluster)
│   └── linker.py          # build/refresh edges and groups
├── cli.py                 # all click commands, thin wrappers over core/
└── __init__.py
main.py                    # `python main.py` entry point
requirements.txt
.env.example
```
