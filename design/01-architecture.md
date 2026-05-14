# LinkWiki — System Architecture

## Overview

LinkWiki is a personal knowledge graph that ingests URLs (YouTube, GitHub, websites),
extracts their content, summarises it with an LLM, tags and links entries to each
other, and lets you browse the result as a wiki.

---

## Phased Delivery

| Phase | Scope |
|-------|-------|
| 1 | CLI tool — `process` (file input), `add`, `list`, `show`, `search` |
| 2 | Grouping, linking, wiki graph view, `sync` |
| 3 | REST API (FastAPI) — enables web UI and mobile |
| 4 | Web UI (React/Next.js) |
| 5 | Mobile (React Native or PWA) |

The core library (extraction, AI, storage) is designed once and wrapped by the
CLI in Phase 1, then exposed as HTTP endpoints in Phase 3, then consumed by
the UI in Phase 4.

---

## High-Level Component Map

```
  Link inputs
  ┌─────────────────────────────────────────────────────────────┐
  │  links.txt (file)    CLI add     REST API     Web / Mobile  │
  └────────┬─────────────────┬──────────┬───────────────┬───────┘
           │                 │          │               │
           └─────────────────▼──────────▼───────────────┘
                        Core Library
          ┌───────────────────────────────────────────┐
          │                                           │
          ▼                                           ▼
   ┌─────────────┐                         ┌──────────────────┐
   │  Extractors │                         │   AI Processor   │
   │  (content)  │                         │   (Claude API)   │
   └──────┬──────┘                         └────────┬─────────┘
          │                                         │
          └──────────────────┬──────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │  Storage Layer  │
                    │  SQLite + Chroma│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Linker / Graph │
                    │  (grouping &    │
                    │   linking)      │
                    └─────────────────┘
```

---

## Component Responsibilities

### 1. Extractors
Responsible for fetching raw content from a URL and discovering related links
embedded in that content.

| Source | Content extracted | Related links discovered |
|--------|-------------------|--------------------------|
| YouTube | Full transcript (via API), video title, channel, description | Links in description, chapter markers |
| GitHub | README, repo description, topics, language stats | Referenced repos, docs links |
| Web (generic) | Main article text via trafilatura, page title, author | `<a>` hrefs in body, Open Graph links |
| HuggingFace | Model card / dataset card text | Linked papers, demos, spaces |
| Medium / Substack | Article body (behind paywall: best-effort) | Related articles suggested |

### 2. AI Processor (Claude API)
All language tasks are handled by Claude. Prompt caching is used on the shared
system prompt to reduce cost.

Tasks per ingested link:
- **Summarise** — 3–5 sentence summary of the content
- **Tag** — 5–15 keyword tags (technology, domain, format, maturity)
- **Extract entities** — named people, tools, papers, organisations, concepts
- **Discover thematic group** — suggest which existing groups this belongs to
  (or propose a new group name)

Batch tasks (run on demand via `sync` command):
- **Semantic grouping** — compare all entry summaries to identify clusters
- **Link strength** — score pairwise similarity for entries that share tags or entities

### 3. Storage Layer

Two stores, both local:

| Store | What lives there |
|-------|-----------------|
| SQLite | Entries, tags, entities, discovered links, groups, link edges, full raw content |
| ChromaDB (local) | Embedding vectors of entry summaries for semantic search and similarity |

SQLite is the source of truth. ChromaDB is a search index that can be rebuilt at any time.

### 4. Linker / Graph
Builds and maintains the knowledge graph.

Edge types between entries:

| Edge type | How created | Strength |
|-----------|-------------|----------|
| `discovered` | URL found in source content | 0.6 |
| `shared_tag` | N tags in common (N ≥ 2) | 0.4 × N |
| `shared_entity` | Named entity appears in both | 0.5 per entity |
| `semantic` | Cosine similarity of embeddings | actual score |
| `manual` | User explicitly linked | 1.0 |
| `group_member` | Both belong to same group | implicit |

An entry can belong to many groups. Groups can be nested (sub-topics).

---

## Data Flow — Adding a Link

```
linkwiki add <url>

        │
        ▼
  1. Route URL → correct extractor
        │
        ▼
  2. Extract raw content + discovered_links
        │
        ▼
  3. Claude: summarise + tag + entities + group hints
        │
        ▼
  4. Store entry in SQLite
        │
        ▼
  5. Embed summary → store in ChromaDB
        │
        ▼
  6. Auto-link: tag overlap + entity overlap with existing entries
        │
        ▼
  7. Queue discovered_links (shown to user; added with `add` or `auto-add`)
        │
        ▼
  8. Display result summary to user
```

---

## Technology Choices

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11+ | Best ecosystem for scraping, AI SDKs |
| CLI | `click` + `rich` | Pleasant output, easy to extend |
| Web scraping | `trafilatura` | Best-in-class article extraction |
| YouTube | `youtube-transcript-api` + `pytube` | Transcript + metadata |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) | Long-context, instruction-following |
| Structured DB | SQLite via `sqlite3` | Zero-ops, single-file, easily portable |
| Vector DB | ChromaDB (local) | Zero-ops, on-disk, good Python API |
| Embeddings | `sentence-transformers` `all-MiniLM-L6-v2` | Free, local, fast |
| Web server (Phase 3) | FastAPI | Async, auto-docs, same Python codebase |
| Web frontend (Phase 3) | Next.js + Tailwind | SSR, fast, graph viz via `react-force-graph` |

---

## Future Extension Points

- **Plugin extractors** — drop a new `extractor_for_arxiv.py` to handle arXiv links
- **Export adapters** — Obsidian Markdown, Notion API, Roam JSON
- **Multi-user** — swap SQLite for Postgres, add auth layer
- **Public wiki** — render static HTML from the graph for sharing
