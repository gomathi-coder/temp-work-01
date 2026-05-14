# LinkWiki — CLI Interface Design

## Invocation

```
linkwiki <command> [options]
# or
python main.py <command> [options]
```

---

## Commands

### `add` — Ingest a URL

```
linkwiki add <url> [options]

Options:
  --group TEXT       Assign immediately to a named group
  --tag TEXT         Add extra tag(s)  (repeatable)
  --no-related       Skip auto-linking to similar existing entries
  --dry-run          Show what would be extracted; don't save

Examples:
  linkwiki add "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  linkwiki add "https://arxiv.org/abs/2307.09288" --group "LLM Papers"
  linkwiki add "https://github.com/karpathy/nanoGPT" --tag pytorch --tag education
```

**Output (on success):**
```
✔ Added  [abc12345]
  Title   : Let's build GPT: from scratch, in code, spelled out.
  Type    : youtube
  Tags    : llm, transformer, education, pytorch, from-scratch (5)
  Entities: Andrej Karpathy (person), GPT-2 (model), PyTorch (tool)
  Summary : Karpathy walks through building a character-level GPT from
            scratch in PyTorch, covering attention, positional encoding,
            and training loops …
  Found   : 3 related entries  |  6 links discovered in description
```

---

### `list` — Browse entries

```
linkwiki list [options]

Options:
  --tag TEXT         Filter by tag (repeatable, AND logic)
  --group TEXT       Filter by group name
  --type TEXT        Filter by url_type (youtube|github|web)
  --limit INT        Max results  [default: 20]
  --sort TEXT        created|title|type  [default: created]
  --json             Output raw JSON

Examples:
  linkwiki list
  linkwiki list --tag llm --tag fine-tuning
  linkwiki list --group "LLM Papers" --limit 50
```

**Output:**
```
 ID       Type     Title                                       Tags
─────────────────────────────────────────────────────────────────────
 abc123   youtube  Let's build GPT (Karpathy)                 llm, pytorch …
 def456   web      The Illustrated Transformer (Jay Alammar)  transformer, attention …
 ghi789   github   karpathy/nanoGPT                           llm, pytorch, gpt …
```

---

### `show` — View a single entry

```
linkwiki show <id-or-url>

Options:
  --json             Output raw JSON

Examples:
  linkwiki show abc123
  linkwiki show "https://github.com/karpathy/nanoGPT"
```

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Let's build GPT: from scratch, in code, spelled out.
 ID: abc12345  |  Type: youtube  |  Added: 2026-05-14
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 URL      https://www.youtube.com/watch?v=kCc8FmEb1nY
 Author   Andrej Karpathy

 Summary
   Karpathy walks through building a character-level GPT from
   scratch in PyTorch, covering tokenisation, the attention
   mechanism, positional encoding, and the training loop.

 Tags
   llm  transformer  education  pytorch  from-scratch  gpt  beginner-friendly

 Entities
   Andrej Karpathy (person)   GPT-2 (model)   PyTorch (tool)
   Attention Is All You Need (paper)

 Groups
   → LLM Education   → Transformer Architecture

 Related entries  (top 5 by strength)
   0.91  def456  The Illustrated Transformer
   0.88  ghi789  karpathy/nanoGPT
   0.72  jkl012  GPT in 60 lines of NumPy (Jay Mody)

 Discovered links  (found in description)
   https://arxiv.org/abs/1706.03762   Attention Is All You Need
   https://github.com/karpathy/nanoGPT
   …  (6 total — run `linkwiki add-discovered abc123` to ingest them)
```

---

### `search` — Semantic + keyword search

```
linkwiki search <query> [options]

Options:
  --limit INT        Max results  [default: 10]
  --type TEXT        Filter by url_type
  --tag TEXT         Filter by tag

Examples:
  linkwiki search "how does attention work"
  linkwiki search "LoRA fine-tuning" --type github
```

**Search strategy:** vector similarity (ChromaDB) → re-ranked by tag overlap.

---

### `related` — Find entries similar to a given one

```
linkwiki related <id-or-url> [options]

Options:
  --limit INT        [default: 10]
  --type TEXT        discovered | shared_tag | shared_entity | semantic | all

Examples:
  linkwiki related abc123
  linkwiki related abc123 --type semantic
```

---

### `add-discovered` — Ingest links found inside an entry

```
linkwiki add-discovered <id> [options]

Options:
  --all              Ingest all discovered links without prompting
  --filter TEXT      Only ingest URLs matching this substring

Examples:
  linkwiki add-discovered abc123
  linkwiki add-discovered abc123 --filter arxiv.org
```

Without `--all`, shows a numbered list and prompts which to add.

---

### `groups` — List all groups

```
linkwiki groups [options]

Options:
  --type TEXT        manual | auto-semantic | auto-tag | auto-entity

Output:
  Name                  Type         Entries
  ─────────────────────────────────────────
  LLM Papers            manual       14
  Transformer Arch.     auto-tag     9
  Karpathy Content      auto-entity  6
  Fine-Tuning Methods   auto-semantic 11
```

---

### `group` subcommands

```
linkwiki group create <name> [--description TEXT]
linkwiki group add    <entry-id> <group-name>
linkwiki group remove <entry-id> <group-name>
linkwiki group show   <group-name>
linkwiki group delete <group-name>
```

---

### `sync` — Re-run auto-grouping and linking

```
linkwiki sync [options]

Options:
  --tags             Re-run tag-based linking only
  --entities         Re-run entity-based linking only
  --semantic         Re-run semantic clustering only (slow, calls ChromaDB)
  --all              Run all  [default]
```

Prints a summary: `+N links added, -M links removed, K groups updated`.

---

### `export` — Export the knowledge graph

```
linkwiki export [options]

Options:
  --format TEXT      obsidian | json | csv  [default: json]
  --output TEXT      Output directory or file  [default: ./linkwiki-export]
  --group TEXT       Export only entries in this group

Examples:
  linkwiki export --format obsidian --output ~/ObsidianVault/LinkWiki
  linkwiki export --format json --output dump.json
```

**Obsidian export:** one `.md` file per entry, `[[wikilinks]]` for related entries,
YAML frontmatter with tags and entities.

---

### `stats` — Overview of the knowledge base

```
linkwiki stats

Output:
  Entries    : 142  (youtube: 54  |  web: 67  |  github: 21)
  Tags       : 89 unique tags
  Entities   : 213 unique entities
  Links      : 1 204 edges  (semantic: 780 | shared_tag: 310 | …)
  Groups     : 18  (manual: 5  |  auto: 13)
  Discovered : 47 links waiting to be added
```

---

## Global Options

```
linkwiki --data-dir PATH   Override default ~/.linkwiki data directory
linkwiki --quiet           Suppress decorative output, just emit results
linkwiki --version         Show version
```

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Claude API key (required) | — |
| `GITHUB_TOKEN` | For higher GitHub API rate limits (optional) | — |
| `LINKWIKI_DATA_DIR` | Override data directory | `~/.linkwiki` |

---

## Error Handling

| Situation | Behaviour |
|-----------|-----------|
| URL already exists | Warn and skip (or `--force` to re-process) |
| YouTube has no transcript | Fall back to title + description only; note in entry |
| Paywall / 403 | Store URL + title from Open Graph; mark status `partial` |
| Claude API error | Retry ×3 with backoff; if still failing, store raw content without LLM fields |
| ChromaDB unavailable | Disable semantic search; warn user; all other commands still work |
