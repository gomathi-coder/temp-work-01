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
    status        TEXT NOT NULL DEFAULT 'pending',-- pending | processing | done | error
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
-- Index hints
-- ─────────────────────────────────────────
CREATE INDEX idx_entries_url_type ON entries(url_type);
CREATE INDEX idx_entries_status   ON entries(status);
CREATE INDEX idx_links_from       ON links(from_id);
CREATE INDEX idx_links_to         ON links(to_id);
CREATE INDEX idx_links_type       ON links(link_type);
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
  status: EntryStatus        # enum
  created_at: datetime
  processed_at: datetime | None

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
entries ──< entry_groups >── groups
   │                              │
   └──────────< links >───────────┘
   (from_id)         (to_id)

groups ──< groups (self-ref, parent_id)
```

One entry → many groups.
One group → many entries.
One entry → many outgoing/incoming links.
Groups can be nested one level deep (parent_id).
