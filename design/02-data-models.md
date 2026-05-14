# LinkWiki — Data Models

## SQLite Schema

```sql
-- ─────────────────────────────────────────
-- Core entry: one row per ingested URL
-- ─────────────────────────────────────────
CREATE TABLE entries (
    id            TEXT PRIMARY KEY,          -- UUID v4
    url           TEXT UNIQUE NOT NULL,
    url_type      TEXT NOT NULL,             -- youtube | github | web | huggingface | arxiv
    title         TEXT,
    author        TEXT,                      -- channel name, GitHub owner, article author
    raw_content   TEXT,                      -- full transcript / article text (truncated at 80k chars)
    summary       TEXT,                      -- 3–5 sentence LLM summary
    tags          TEXT NOT NULL DEFAULT '[]',     -- JSON array of strings
    entities      TEXT NOT NULL DEFAULT '[]',     -- JSON array of Entity objects (see below)
    discovered_links TEXT NOT NULL DEFAULT '[]',  -- JSON array of URLs found inside content
    source_type   TEXT NOT NULL DEFAULT 'cli',    -- file | cli | api | ui | discovered
    source_ref    TEXT,                           -- filename, API key label, parent entry ID, etc.
    status        TEXT NOT NULL DEFAULT 'pending',-- pending | processing | done | error | partial
    error_msg     TEXT,
    created_at    TEXT NOT NULL,             -- ISO-8601
    processed_at  TEXT
);

-- ─────────────────────────────────────────
-- Groups / collections
-- ─────────────────────────────────────────
CREATE TABLE groups (
    id            TEXT PRIMARY KEY,          -- UUID v4
    name          TEXT NOT NULL UNIQUE,
    description   TEXT,
    group_type    TEXT NOT NULL,             -- manual | auto-semantic | auto-tag | auto-entity
    parent_id     TEXT REFERENCES groups(id),-- optional nesting
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- ─────────────────────────────────────────
-- Many-to-many: entries ↔ groups
-- ─────────────────────────────────────────
CREATE TABLE entry_groups (
    entry_id      TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    group_id      TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    added_by      TEXT NOT NULL DEFAULT 'auto',  -- auto | user
    added_at      TEXT NOT NULL,
    PRIMARY KEY (entry_id, group_id)
);

-- ─────────────────────────────────────────
-- Directed edges in the knowledge graph
-- ─────────────────────────────────────────
CREATE TABLE links (
    id            TEXT PRIMARY KEY,          -- UUID v4
    from_id       TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    to_id         TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    link_type     TEXT NOT NULL,             -- discovered | shared_tag | shared_entity | semantic | manual
    strength      REAL NOT NULL DEFAULT 1.0, -- 0.0–1.0
    metadata      TEXT NOT NULL DEFAULT '{}',-- JSON: which tags/entities caused the link
    created_at    TEXT NOT NULL,
    UNIQUE (from_id, to_id, link_type)
);

-- ─────────────────────────────────────────
-- Input file registry
-- Tracks which batch files have been processed
-- ─────────────────────────────────────────
CREATE TABLE input_files (
    id            TEXT PRIMARY KEY,          -- UUID v4
    file_path     TEXT NOT NULL UNIQUE,      -- absolute or relative path to links.txt
    last_read_at  TEXT,                      -- ISO-8601, NULL = never processed
    total_lines   INTEGER DEFAULT 0,
    processed     INTEGER DEFAULT 0,         -- lines successfully ingested
    skipped       INTEGER DEFAULT 0,         -- duplicates / blank lines
    errored       INTEGER DEFAULT 0
);

-- ─────────────────────────────────────────
-- Index hints
-- ─────────────────────────────────────────
CREATE INDEX idx_entries_url_type    ON entries(url_type);
CREATE INDEX idx_entries_status      ON entries(status);
CREATE INDEX idx_entries_source_type ON entries(source_type);
CREATE INDEX idx_links_from          ON links(from_id);
CREATE INDEX idx_links_to            ON links(to_id);
CREATE INDEX idx_links_type          ON links(link_type);
```

---

## JSON Sub-object Shapes

### Entity (stored in `entries.entities`)
```json
{
  "name": "Andrej Karpathy",
  "type": "person",
  "description": "Former Tesla AI director, now independent educator"
}
```

Entity types: `person`, `tool`, `paper`, `organisation`, `concept`, `dataset`, `model`

### Discovered link (stored in `entries.discovered_links`)
```json
{
  "url": "https://arxiv.org/abs/2307.09288",
  "label": "LLaMA 2 paper",
  "context": "mentioned in YouTube description"
}
```

### Link metadata (stored in `links.metadata`)
```json
{
  "shared_tags": ["llm", "fine-tuning"],
  "shared_entities": ["LoRA"],
  "similarity_score": 0.87
}
```

---

## ChromaDB Collection

**Collection name:** `entry_summaries`

| Field | Value |
|-------|-------|
| `id` | Same UUID as `entries.id` |
| `document` | `title + "\n\n" + summary` (≤ 2 000 chars) |
| `embedding` | 384-dim float vector from `all-MiniLM-L6-v2` |
| `metadata.url_type` | youtube / github / web / … |
| `metadata.tags` | comma-separated tag string (for metadata filtering) |

Querying: `collection.query(query_texts=["attention mechanism"], n_results=10)`

---

## Domain Object Model (Python)

```
Entry
  id: str
  url: str
  url_type: UrlType          # enum
  title: str | None
  author: str | None
  raw_content: str | None
  summary: str | None
  tags: list[str]
  entities: list[Entity]
  discovered_links: list[DiscoveredLink]
  source_type: SourceType    # enum: file, cli, api, ui, discovered
  source_ref: str | None     # filename | API key label | parent entry ID
  status: EntryStatus        # enum: pending, processing, done, error, partial
  created_at: datetime
  processed_at: datetime | None

InputFile
  id: str
  file_path: str
  last_read_at: datetime | None
  total_lines: int
  processed: int
  skipped: int
  errored: int

Entity
  name: str
  type: EntityType           # enum: person, tool, paper, ...
  description: str

DiscoveredLink
  url: str
  label: str
  context: str

Group
  id: str
  name: str
  description: str | None
  group_type: GroupType      # enum: manual, auto-semantic, auto-tag, auto-entity
  parent_id: str | None
  entry_count: int           # computed

GraphLink
  id: str
  from_id: str
  to_id: str
  link_type: LinkType        # enum: discovered, shared_tag, shared_entity, semantic, manual
  strength: float
  metadata: dict
```

---

## Entity Relationship Diagram

```
input_files ──< entries (source_ref = file_path, source_type = 'file')
                   │
                   ├──< entry_groups >── groups
                   │                       │
                   └──────< links >─────────┘
                   (from_id)    (to_id)

groups ──< groups (self-ref, parent_id)
```

One entry → many groups.
One group → many entries.
One entry → many outgoing/incoming links.
Groups can be nested one level deep (parent_id).
One input file → many entries (linked via `source_ref`).

## Source Tracking Reference

| source_type | source_ref value | How entry was created |
|-------------|------------------|-----------------------|
| `file` | `links.txt` (filename) | Batch file processed via `linkwiki process` |
| `cli` | `NULL` | `linkwiki add <url>` directly in terminal |
| `api` | API key label or client name | POST `/entries` via REST API |
| `ui` | `NULL` | Added through the web or mobile UI |
| `discovered` | Parent entry UUID | URL found inside another entry's content |
