# LinkWiki — REST API Specification

## Overview

The REST API (Phase 3) wraps the same core library used by the CLI.
It enables the web UI, mobile app, browser extensions, and third-party
integrations (Zapier, n8n, iOS Shortcuts, etc.).

**Stack:** FastAPI + Uvicorn  
**Base URL:** `http://localhost:8000/api/v1`  
**Auth:** API key via `X-API-Key` header (single-user; key stored in config)  
**Format:** JSON request/response throughout

---

## Authentication

All endpoints require the header:
```
X-API-Key: <your-api-key>
```

The key is set once in `.env` as `LINKWIKI_API_KEY`. No user accounts — this
is a personal tool.

---

## Endpoints

### Entries

#### `POST /entries` — Add a single URL
```
Request body:
{
  "url": "https://youtube.com/watch?v=...",
  "tags": ["optional", "extra-tags"],       // merged with LLM tags
  "group": "LLM Papers",                    // optional, created if not exists
  "label": "My title override"              // optional
}

Response 201:
{
  "id": "abc12345-...",
  "url": "https://...",
  "status": "pending",                      // processing is async
  "message": "Queued for processing"
}

Response 409 (already exists):
{
  "error": "duplicate",
  "existing_id": "abc12345-..."
}
```

> Processing happens asynchronously. Poll `GET /entries/{id}` or use the
> WebSocket stream (`/ws/events`) to receive the `entry.processed` event.

---

#### `POST /entries/batch` — Add multiple URLs (mirrors file input)
```
Request body:
{
  "urls": [
    { "url": "https://...", "tags": [], "group": null },
    { "url": "https://...", "tags": ["llm"] }
  ],
  "source_ref": "my-batch-import"           // label stored in source_ref
}

Response 202:
{
  "queued": 12,
  "duplicate": 3,
  "invalid": 0,
  "job_id": "job-xyz"                       // poll GET /jobs/{job_id}
}
```

---

#### `GET /entries` — List / search entries
```
Query params:
  q         string   Semantic search query
  tag       string   Filter by tag  (repeatable: ?tag=llm&tag=paper)
  group     string   Filter by group name
  type      string   youtube | github | web | …
  source    string   file | cli | api | ui | discovered
  status    string   pending | done | error | partial
  sort      string   created | title | type  [default: created]
  order     string   asc | desc  [default: desc]
  limit     int      [default: 20, max: 100]
  offset    int      [default: 0]

Response 200:
{
  "total": 142,
  "offset": 0,
  "limit": 20,
  "items": [
    {
      "id": "abc123",
      "url": "https://...",
      "url_type": "youtube",
      "title": "Let's build GPT",
      "author": "Andrej Karpathy",
      "summary": "...",
      "tags": ["llm", "pytorch"],
      "status": "done",
      "source_type": "file",
      "source_ref": "links.txt",
      "created_at": "2026-05-14T10:00:00Z"
    },
    ...
  ]
}
```

---

#### `GET /entries/{id}` — Get a single entry (full detail)
```
Response 200:
{
  "id": "abc123",
  "url": "...",
  "url_type": "youtube",
  "title": "...",
  "author": "...",
  "summary": "...",
  "tags": [...],
  "entities": [
    { "name": "Andrej Karpathy", "type": "person", "description": "..." }
  ],
  "discovered_links": [
    { "url": "https://...", "label": "...", "context": "in description" }
  ],
  "groups": ["LLM Education", "Transformers"],
  "related": [
    { "id": "def456", "title": "...", "link_type": "semantic", "strength": 0.91 }
  ],
  "source_type": "file",
  "source_ref": "links.txt",
  "status": "done",
  "created_at": "...",
  "processed_at": "..."
}
```

---

#### `PATCH /entries/{id}` — Update tags, group, or label
```
Request body (all fields optional):
{
  "tags": ["new-tag"],       // replaces existing tags
  "label": "New title"
}

Response 200: updated entry object
```

---

#### `DELETE /entries/{id}` — Remove an entry
```
Response 204: no body
```

---

### Groups

#### `GET /groups` — List all groups
```
Query params:
  type    manual | auto-semantic | auto-tag | auto-entity
  
Response 200:
{
  "items": [
    {
      "id": "grp123",
      "name": "LLM Papers",
      "description": "...",
      "group_type": "manual",
      "entry_count": 14,
      "parent_id": null
    },
    ...
  ]
}
```

---

#### `POST /groups` — Create a group
```
Request body:
{
  "name": "Fine-Tuning Methods",
  "description": "Optional description",
  "parent_id": null
}

Response 201: group object
```

---

#### `POST /groups/{group_id}/entries/{entry_id}` — Add entry to group
```
Response 200: { "ok": true }
```

#### `DELETE /groups/{group_id}/entries/{entry_id}` — Remove entry from group
```
Response 204
```

---

### File Processing

#### `POST /process` — Process a links file (server-side path)
```
Request body:
{
  "file_path": "/home/user/links.txt",
  "dry_run": false
}

Response 202:
{
  "job_id": "job-abc",
  "total_lines": 23
}
```

#### `GET /files` — List registered input files and their stats
```
Response 200:
{
  "items": [
    {
      "id": "...",
      "file_path": "links.txt",
      "last_read_at": "2026-05-14T09:00:00Z",
      "total_lines": 23,
      "processed": 20,
      "skipped": 2,
      "errored": 1
    }
  ]
}
```

---

### Jobs (Async Operations)

#### `GET /jobs/{job_id}` — Poll batch job status
```
Response 200:
{
  "job_id": "job-abc",
  "status": "running",           // queued | running | done | failed
  "total": 23,
  "processed": 11,
  "errored": 0,
  "started_at": "...",
  "finished_at": null
}
```

---

### Sync / Graph

#### `POST /sync` — Trigger re-linking and auto-grouping
```
Request body:
{
  "tags": true,
  "entities": true,
  "semantic": true
}

Response 202:
{
  "job_id": "job-sync-xyz"
}
```

---

### Stats

#### `GET /stats` — Knowledge base summary
```
Response 200:
{
  "entries": {
    "total": 142,
    "by_type": { "youtube": 54, "web": 67, "github": 21 },
    "by_status": { "done": 138, "error": 4 },
    "by_source": { "file": 110, "cli": 20, "api": 12 }
  },
  "tags": { "unique": 89 },
  "entities": { "unique": 213 },
  "links": { "total": 1204, "by_type": { "semantic": 780, "shared_tag": 310 } },
  "groups": { "total": 18, "manual": 5, "auto": 13 },
  "discovered_pending": 47
}
```

---

### Real-time Events (WebSocket)

#### `WS /ws/events` — Stream processing events
```
Client connects with header: X-API-Key: <key>

Server pushes JSON messages:
{ "event": "entry.queued",     "entry_id": "abc123", "url": "https://..." }
{ "event": "entry.processing", "entry_id": "abc123" }
{ "event": "entry.done",       "entry_id": "abc123", "title": "...", "tags": [...] }
{ "event": "entry.error",      "entry_id": "abc123", "error": "connection timeout" }
{ "event": "job.done",         "job_id": "job-xyz",  "processed": 20, "errored": 1 }
```

Used by the web UI to show live progress when processing a batch file.

---

## Error Response Format

All errors follow the same shape:
```json
{
  "error": "not_found",
  "message": "Entry abc123 does not exist",
  "detail": null
}
```

| HTTP status | `error` value | Meaning |
|-------------|--------------|---------|
| 400 | `invalid_request` | Bad input (missing field, wrong type) |
| 401 | `unauthorized` | Missing or wrong API key |
| 404 | `not_found` | Entry / group does not exist |
| 409 | `duplicate` | URL already in the database |
| 422 | `validation_error` | Pydantic validation failed |
| 429 | `rate_limited` | Too many requests (Claude API upstream) |
| 500 | `internal_error` | Unexpected server error |

---

## Integration Examples

### Browser extension (POST on click)
```js
fetch("http://localhost:8000/api/v1/entries", {
  method: "POST",
  headers: { "X-API-Key": KEY, "Content-Type": "application/json" },
  body: JSON.stringify({ url: window.location.href })
})
```

### iOS Shortcut / Zapier
`POST /entries` with `{ "url": "<shared URL>", "source_ref": "ios-share-sheet" }`

### Obsidian plugin
`GET /entries?q=attention+mechanism&limit=5` → insert links as suggestions
