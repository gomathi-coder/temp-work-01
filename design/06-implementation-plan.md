# LinkWiki — Phase-wise Implementation Plan

---

## Phase 1 — CLI Core (File Input + Add + Process)

**Goal:** Working CLI that can ingest URLs from a file or directly, extract
content, summarise with Claude, store in SQLite, and display results.

### Milestone 1.1 — Project Scaffold
| Task | Files |
|------|-------|
| Create directory structure | `linkwiki/`, `linkwiki/core/`, `linkwiki/extractors/` |
| Add dependencies | `requirements.txt` |
| Config and env loading | `linkwiki/core/config.py`, `.env.example` |
| Entry point | `main.py` |

```
requirements.txt includes:
  anthropic, click, rich, python-dotenv,
  youtube-transcript-api, pytube, trafilatura,
  beautifulsoup4, requests
```

**Commit:** `scaffold: project structure, config, and dependencies`

---

### Milestone 1.2 — Database Layer
| Task | Files |
|------|-------|
| SQLite schema (entries, groups, entry_groups, links, input_files) | `linkwiki/core/database.py` |
| CRUD: create, get, list, update, delete entry | `linkwiki/core/database.py` |
| CRUD: input_files table (register file, update counts) | `linkwiki/core/database.py` |
| DB initialisation on first run | `linkwiki/core/database.py` |

**Commit:** `feat: SQLite schema and database CRUD layer`

---

### Milestone 1.3 — Content Extractors
| Task | Files |
|------|-------|
| URL router (detect youtube / github / web / arxiv) | `linkwiki/extractors/__init__.py` |
| YouTube extractor (transcript + metadata + description links) | `linkwiki/extractors/youtube.py` |
| Web extractor (trafilatura + OG fallback + link discovery) | `linkwiki/extractors/web.py` |
| GitHub extractor (API + README + topics) | `linkwiki/extractors/github.py` |
| arXiv extractor (abstract + authors via arXiv API) | `linkwiki/extractors/arxiv.py` |

**Commit:** `feat: content extractors for YouTube, web, GitHub, arXiv`

---

### Milestone 1.4 — Claude AI Module
| Task | Files |
|------|-------|
| Anthropic client setup with prompt caching | `linkwiki/core/ai.py` |
| `summarise_and_tag(content)` → summary, tags, entities, group hints | `linkwiki/core/ai.py` |
| Content truncation utility (keep head + tail within token limit) | `linkwiki/core/ai.py` |
| Retry logic with exponential backoff on API errors | `linkwiki/core/ai.py` |

**Commit:** `feat: Claude AI module for summarisation, tagging, entity extraction`

---

### Milestone 1.5 — CLI Commands (add + process)
| Task | Files |
|------|-------|
| `linkwiki add <url>` — single URL ingest | `linkwiki/cli.py` |
| `linkwiki process [file]` — batch file ingest with progress bar | `linkwiki/cli.py` |
| Input file parser (URL + inline tags/group/label) | `linkwiki/core/file_parser.py` |
| Duplicate detection and skip logic | `linkwiki/core/file_parser.py` |
| Rich terminal output (progress, summary table) | `linkwiki/cli.py` |

**Commit:** `feat: CLI add and process commands with rich output`

---

### Milestone 1.6 — CLI Read Commands
| Task | Files |
|------|-------|
| `linkwiki list` — table view with filters | `linkwiki/cli.py` |
| `linkwiki show <id>` — full entry detail | `linkwiki/cli.py` |
| `linkwiki stats` — knowledge base summary | `linkwiki/cli.py` |

**Commit:** `feat: CLI list, show, stats commands`

**Phase 1 Done:** You can drop URLs into `links.txt`, run `linkwiki process`,
and browse summarised, tagged results in the terminal.

---

## Phase 2 — Knowledge Graph (Linking + Grouping + Search)

**Goal:** Entries are automatically linked to each other and grouped by topic.
Semantic search works. Discovered links can be ingested.

### Milestone 2.1 — Vector Store
| Task | Files |
|------|-------|
| ChromaDB setup (local, on-disk) | `linkwiki/core/vectors.py` |
| Embed entry summary on `add`/`process` | `linkwiki/core/vectors.py` |
| `search_similar(query, n)` — return top-N matching entries | `linkwiki/core/vectors.py` |
| Rebuild index command (`linkwiki reindex`) | `linkwiki/cli.py` |

**Commit:** `feat: ChromaDB vector store and semantic search`

---

### Milestone 2.2 — Auto-Linker
| Task | Files |
|------|-------|
| Tag-based linking (shared ≥ 2 tags → edge) | `linkwiki/core/linker.py` |
| Entity-based linking (shared entity names → edge) | `linkwiki/core/linker.py` |
| Semantic linking (cosine similarity ≥ 0.70 → edge) | `linkwiki/core/linker.py` |
| Discovered-link edges (URL found inside another entry) | `linkwiki/core/linker.py` |
| Run linker automatically after each `add`/`process` | `linkwiki/core/linker.py` |

**Commit:** `feat: auto-linker for tag, entity, semantic, and discovered edges`

---

### Milestone 2.3 — Auto-Grouping
| Task | Files |
|------|-------|
| Tag-based groups (entries sharing dominant tag) | `linkwiki/core/linker.py` |
| Entity-based groups (entries sharing key entity) | `linkwiki/core/linker.py` |
| Semantic cluster detection (HDBSCAN on embeddings) | `linkwiki/core/linker.py` |
| Claude names each new cluster | `linkwiki/core/ai.py` |
| `linkwiki sync` CLI command | `linkwiki/cli.py` |

**Commit:** `feat: auto-grouping by tags, entities, and semantic clusters`

---

### Milestone 2.4 — Group + Related CLI Commands
| Task | Files |
|------|-------|
| `linkwiki groups` — list all groups | `linkwiki/cli.py` |
| `linkwiki group create/add/remove/show` | `linkwiki/cli.py` |
| `linkwiki related <id>` — show linked entries | `linkwiki/cli.py` |
| `linkwiki search <query>` — semantic + tag search | `linkwiki/cli.py` |
| `linkwiki add-discovered <id>` — ingest links found in an entry | `linkwiki/cli.py` |

**Commit:** `feat: CLI groups, related, search, add-discovered commands`

---

### Milestone 2.5 — Export
| Task | Files |
|------|-------|
| JSON export (full dump) | `linkwiki/core/export.py` |
| CSV export (flat table) | `linkwiki/core/export.py` |
| Obsidian Markdown export (one .md per entry, wikilinks, YAML frontmatter) | `linkwiki/core/export.py` |
| `linkwiki export` CLI command | `linkwiki/cli.py` |

**Commit:** `feat: export to JSON, CSV, and Obsidian Markdown`

**Phase 2 Done:** The knowledge graph is live. Entries link to each other
automatically, groups form by topic, and you can search, browse, and export.

---

## Phase 3 — REST API

**Goal:** Expose all core functionality over HTTP so the web UI and mobile app
can consume it. Also enables browser extensions and automation.

### Milestone 3.1 — FastAPI Scaffold
| Task | Files |
|------|-------|
| FastAPI app setup, CORS, API key auth middleware | `server/main.py`, `server/auth.py` |
| Shared core library import (reuses Phase 1+2 code) | `server/main.py` |
| Health check endpoint (`GET /health`) | `server/routers/health.py` |
| Uvicorn entry point | `server/main.py` |

**Commit:** `feat: FastAPI server scaffold with auth middleware`

---

### Milestone 3.2 — Entry Endpoints
| Task | Files |
|------|-------|
| `POST /api/v1/entries` (single add, async) | `server/routers/entries.py` |
| `POST /api/v1/entries/batch` (bulk add, returns job ID) | `server/routers/entries.py` |
| `GET /api/v1/entries` (list + filter + search) | `server/routers/entries.py` |
| `GET /api/v1/entries/{id}` (full detail) | `server/routers/entries.py` |
| `PATCH /api/v1/entries/{id}` (update tags/label) | `server/routers/entries.py` |
| `DELETE /api/v1/entries/{id}` | `server/routers/entries.py` |
| Pydantic request/response models | `server/schemas.py` |

**Commit:** `feat: entries CRUD endpoints`

---

### Milestone 3.3 — Groups + Files + Jobs Endpoints
| Task | Files |
|------|-------|
| `GET/POST /api/v1/groups` | `server/routers/groups.py` |
| `POST/DELETE /api/v1/groups/{id}/entries/{id}` | `server/routers/groups.py` |
| `POST /api/v1/process` (server-side file ingest) | `server/routers/files.py` |
| `GET /api/v1/files` (input file registry) | `server/routers/files.py` |
| `GET /api/v1/jobs/{id}` (async job polling) | `server/routers/jobs.py` |
| `POST /api/v1/sync` | `server/routers/sync.py` |
| `GET /api/v1/stats` | `server/routers/stats.py` |

**Commit:** `feat: groups, files, jobs, sync, and stats endpoints`

---

### Milestone 3.4 — WebSocket + Background Workers
| Task | Files |
|------|-------|
| `WS /ws/events` event stream (entry.queued, entry.done, job.done) | `server/ws.py` |
| Async background task queue for processing | `server/workers.py` |
| Connect `add`/`process`/`sync` to task queue | `server/workers.py` |

**Commit:** `feat: WebSocket event stream and async background workers`

**Phase 3 Done:** Full REST API running locally. Browser extension, iOS
Shortcuts, and Zapier can send links directly to LinkWiki.

---

## Phase 4 — Web UI

**Goal:** Browser-based interface to add links, browse the wiki, view the graph,
and manage groups.

### Milestone 4.1 — Next.js Scaffold
| Task | Files |
|------|-------|
| Next.js + Tailwind setup | `web/` |
| API client (typed fetch wrapper around REST API) | `web/lib/api.ts` |
| Auth (API key stored in localStorage) | `web/lib/auth.ts` |

**Commit:** `feat: Next.js web UI scaffold with API client`

---

### Milestone 4.2 — Core Pages
| Task | Route |
|------|-------|
| Dashboard / home (stats + recent entries) | `/` |
| Entry list with filter sidebar | `/entries` |
| Entry detail page | `/entries/[id]` |
| Add link form (single + paste bulk) | `/add` |
| Groups list | `/groups` |
| Group detail (entries in group) | `/groups/[name]` |

**Commit:** `feat: core pages — dashboard, entries, add, groups`

---

### Milestone 4.3 — Knowledge Graph View
| Task | Files |
|------|-------|
| Force-directed graph (`react-force-graph`) | `web/components/Graph.tsx` |
| Nodes = entries, edges = links (coloured by type) | `web/components/Graph.tsx` |
| Click node → open entry detail panel | `web/components/Graph.tsx` |
| Filter graph by group or tag | `web/components/Graph.tsx` |

**Commit:** `feat: interactive knowledge graph view`

---

### Milestone 4.4 — Live Processing View
| Task | Files |
|------|-------|
| WebSocket connection for live events | `web/lib/ws.ts` |
| Processing queue panel (shows progress as links are ingested) | `web/components/Queue.tsx` |
| Toast notifications on entry.done / entry.error | `web/components/Toast.tsx` |

**Commit:** `feat: live processing feed via WebSocket`

**Phase 4 Done:** Full web interface for browsing, adding, and visually
exploring the knowledge graph.

---

## Phase 5 — Mobile

**Goal:** Add links from your phone via share sheet; browse your wiki on the go.

### Milestone 5.1 — PWA (Progressive Web App)
| Task | Notes |
|------|-------|
| Add `manifest.json` and service worker to the Next.js web app | Lightest path — works on iOS and Android |
| "Add to Home Screen" prompt | |
| Offline: cached entry list | |

**Commit:** `feat: PWA manifest and service worker for mobile install`

---

### Milestone 5.2 — iOS Share Extension (Optional)
| Task | Notes |
|------|-------|
| iOS Shortcut: share any URL → POST to `/api/v1/entries` | No native app needed |
| Document setup steps in README | |

**Commit:** `docs: iOS Shortcuts integration guide`

---

## Summary Table

| Phase | Key Deliverable | Est. Complexity |
|-------|----------------|-----------------|
| 1 | CLI: `add`, `process`, `list`, `show` | Medium |
| 2 | Knowledge graph: linking, grouping, search, export | High |
| 3 | REST API (FastAPI) | Medium |
| 4 | Web UI: pages + graph view + live feed | High |
| 5 | Mobile: PWA + iOS Shortcuts | Low |

---

## Folder Structure (Final)

```
linkwiki/               ← core library (used by CLI and server)
  core/
    config.py
    database.py
    ai.py
    vectors.py
    linker.py
    export.py
    file_parser.py
  extractors/
    __init__.py         ← URL router
    youtube.py
    web.py
    github.py
    arxiv.py
  cli.py                ← all click commands

server/                 ← FastAPI REST API (Phase 3)
  main.py
  auth.py
  schemas.py
  workers.py
  ws.py
  routers/
    entries.py
    groups.py
    files.py
    jobs.py
    sync.py
    stats.py

web/                    ← Next.js frontend (Phase 4)
  app/
  components/
  lib/

design/                 ← design documents (this folder)

main.py                 ← CLI entry point
requirements.txt
.env.example
README.md
```
