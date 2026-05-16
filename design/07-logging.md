# Logging Design

## Overview

LinkWiki uses Python's standard `logging` module with a structured **JSON Lines (JSONL)** output format. Every log record is a single JSON object on one line, written to rotating files in the `logs/` directory. This makes logs both human-readable and trivially parseable by tools like `jq`, pandas, or any log aggregation platform.

Logging is initialised once at CLI startup (`cli()` in `cli.py`) and propagates through a named logger hierarchy rooted at `linkwiki`.

---

## Log Files

| File | Level filter | Max size | Retained copies |
|---|---|---|---|
| `logs/linkwiki.jsonl` | Configurable (default INFO) | 10 MB | 5 |
| `logs/errors.jsonl` | ERROR and above only | 5 MB | 3 |

Both files rotate automatically via `RotatingFileHandler`. Old rotations are suffixed `.1`, `.2`, etc.

`logs/errors.jsonl` is a focused view for quick failure triage — it receives the same records as the main log but filtered to ERROR/CRITICAL only.

---

## Record Format

Each record is a JSON object on a single line (no pretty-printing):

```json
{
  "ts": "2026-05-16T10:23:45.123456+00:00",
  "level": "INFO",
  "logger": "linkwiki.extractors.web",
  "msg": "HTTP response received",
  "url": "https://example.com/article",
  "status_code": 200,
  "content_bytes": 52480,
  "duration_ms": 312
}
```

### Fixed fields (always present)

| Field | Type | Description |
|---|---|---|
| `ts` | ISO 8601 string | UTC timestamp with microsecond precision |
| `level` | string | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `logger` | string | Dotted logger name (e.g. `linkwiki.extractors.youtube`) |
| `msg` | string | Human-readable description of the event |

### Context fields (caller-supplied via `extra=`)

Context fields are merged into the top-level JSON object alongside the fixed fields. Each module adds the fields that are relevant to the event — see the per-module tables below.

If an exception is attached (`exc_info=True`), a formatted `exc` string field is appended.

---

## Logger Hierarchy

```
linkwiki                          ← root; both file handlers live here
├── linkwiki.extractors.web       ← generic web scraping
├── linkwiki.extractors.youtube   ← YouTube transcript + metadata
├── linkwiki.extractors.github    ← GitHub repo via REST API
├── linkwiki.extractors.arxiv     ← arXiv paper via Atom API
├── linkwiki.core.pipeline        ← ingest orchestration
└── linkwiki.core.ai              ← Claude API calls
```

Child loggers inherit handlers from the root (`linkwiki`) and do not add handlers of their own.

---

## Log Level Semantics

| Level | Used for |
|---|---|
| `DEBUG` | Internal step details — parsed IDs, per-field metadata, intermediate states. Useful during development; disabled in production by default. |
| `INFO` | Key milestones — extraction started/complete, HTTP responses, AI call success, ingest complete with timing. Normal operational visibility. |
| `WARNING` | Degraded but recoverable situations — paywall/JS page (fell back to description), missing transcript, rate-limit backoff, README unavailable, embedding failure (non-blocking). |
| `ERROR` | Failures that stop processing a URL — HTTP errors, unparseable IDs, AI exhausted all retries, repository not found. Written to both `linkwiki.jsonl` and `errors.jsonl`. |

---

## Per-Module Events

### `linkwiki.extractors.web`

| Event | Level | Key extra fields |
|---|---|---|
| `extraction started` | INFO | `url`, `extractor` |
| `HTTP response received` | INFO | `url`, `status_code`, `duration_ms`, `content_bytes` |
| `HTTP error response` | ERROR | `url`, `status_code`, `error`, `duration_ms` |
| `HTTP request failed` | ERROR | `url`, `error`, `duration_ms` |
| `metadata extracted` | DEBUG | `url`, `title`, `author`, `discovered_count` |
| `content extraction failed, possible paywall or JS-rendered page` | WARNING | `url`, `fallback` |
| `extraction complete` | INFO | `url`, `status`, `content_chars`, `discovered_count`, `duration_ms` |

---

### `linkwiki.extractors.youtube`

| Event | Level | Key extra fields |
|---|---|---|
| `extraction started` | INFO | `url`, `extractor` |
| `could not parse video ID from URL` | ERROR | `url` |
| `video ID parsed` | DEBUG | `url`, `video_id` |
| `oEmbed metadata fetched` | DEBUG | `url`, `title`, `author`, `duration_ms` |
| `oEmbed returned non-200 status` | WARNING | `url`, `status_code`, `duration_ms` |
| `oEmbed fetch failed` | WARNING | `url`, `error`, `duration_ms` |
| `description fetched via pytubefix` | DEBUG | `url`, `description_chars`, `duration_ms` |
| `pytubefix description fetch failed` | WARNING | `url`, `error`, `duration_ms` |
| `transcript fetched` | INFO | `video_id`, `transcript_chars`, `snippet_count`, `duration_ms` |
| `transcript unavailable` | WARNING | `video_id`, `error`, `duration_ms` |
| `extraction yielded no content` | WARNING | `url`, `video_id`, `has_transcript`, `has_description`, `duration_ms` |
| `extraction complete` | INFO | `url`, `video_id`, `status`, `has_transcript`, `has_description`, `content_chars`, `discovered_count`, `duration_ms` |

---

### `linkwiki.extractors.github`

| Event | Level | Key extra fields |
|---|---|---|
| `extraction started` | INFO | `url`, `extractor` |
| `could not parse owner/repo from URL` | ERROR | `url` |
| `parsed repository` | DEBUG | `url`, `owner`, `repo`, `authenticated` |
| `repository metadata fetched` | DEBUG | `url`, `owner`, `repo`, `status_code`, `duration_ms` |
| `repository not found` | ERROR | `url`, `owner`, `repo`, `status_code`, `duration_ms` |
| `GitHub API request failed` | ERROR | `url`, `owner`, `repo`, `error`, `duration_ms` |
| `repository details` | DEBUG | `url`, `title`, `language`, `stars`, `topics_count` |
| `README fetched` | DEBUG | `url`, `readme_chars`, `duration_ms` |
| `README not available` | WARNING | `url`, `status_code`, `duration_ms` |
| `README fetch failed` | WARNING | `url`, `error` |
| `extraction complete` | INFO | `url`, `status`, `title`, `language`, `stars`, `content_chars`, `discovered_count`, `duration_ms` |

---

### `linkwiki.extractors.arxiv`

| Event | Level | Key extra fields |
|---|---|---|
| `extraction started` | INFO | `url`, `extractor` |
| `could not parse arXiv ID from URL` | ERROR | `url` |
| `arXiv ID parsed` | DEBUG | `url`, `arxiv_id` |
| `arXiv API response received` | DEBUG | `url`, `arxiv_id`, `status_code`, `duration_ms` |
| `arXiv API request failed` | ERROR | `url`, `arxiv_id`, `error`, `duration_ms` |
| `paper not found on arXiv` | ERROR | `url`, `arxiv_id`, `duration_ms` |
| `extraction complete` | INFO | `url`, `status`, `arxiv_id`, `title`, `author_count`, `abstract_chars`, `duration_ms` |

---

### `linkwiki.core.pipeline`

| Event | Level | Key extra fields |
|---|---|---|
| `ingest started` | INFO | `url`, `source_type`, `source_ref`, `dry_run`, `group` |
| `duplicate detected, skipping` | INFO | `url`, `existing_id` |
| `dispatching to extractor` | DEBUG | `url` |
| `extraction finished` | INFO | `url`, `url_type`, `extraction_status`, `content_chars`, `discovered_links` |
| `dry run complete, not persisting` | INFO | `url` |
| `entry created in database` | DEBUG | `url`, `entry_id` |
| `AI processing started` | INFO | `entry_id`, `url`, `content_chars` |
| `AI processing complete` | INFO | `entry_id`, `tags_count`, `entities_count`, `suggested_groups` |
| `AI processing failed` | ERROR | `entry_id`, `url`, `error` |
| `skipping AI processing, no content available` | DEBUG | `entry_id`, `url`, `extraction_status` |
| `entry persisted` | DEBUG | `entry_id`, `status`, `tags` |
| `embedding and linking complete` | DEBUG | `entry_id` |
| `embedding/linking failed (non-blocking)` | WARNING | `entry_id`, `error` |
| `manual group assigned` | DEBUG | `entry_id`, `group`, `group_id` |
| `auto group assigned` | DEBUG | `entry_id`, `group`, `group_id` |
| `ingest complete` | INFO | `url`, `entry_id`, `status`, `url_type`, `duration_ms` |

---

### `linkwiki.core.ai`

| Event | Level | Key extra fields |
|---|---|---|
| `summarisation started` | INFO | `url_type`, `title`, `content_chars`, `model` |
| `sending request to Claude` | DEBUG | `url_type`, `attempt`, `model` |
| `Claude API call succeeded` | INFO | `url_type`, `attempt`, `duration_ms`, `input_tokens`, `output_tokens`, `tags_returned`, `entities_returned` |
| `JSON decode error, retrying with reminder` | WARNING | `url_type`, `attempt`, `error` |
| `rate limit hit, backing off` | WARNING | `url_type`, `attempt`, `wait_secs`, `error` |
| `API transient error, retrying` | WARNING | `url_type`, `attempt`, `wait_secs`, `error` |
| `Claude API failed after all attempts` | ERROR | `url_type`, `title`, `duration_ms`, `last_error` |
| `cluster naming started` | INFO | `entry_count` |
| `cluster naming complete` | INFO | `entry_count`, `cluster_name`, `attempt`, `duration_ms` |
| `cluster naming attempt failed` | WARNING | `attempt`, `error` |
| `cluster naming exhausted retries, returning fallback` | WARNING | `entry_count` |

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `LINKWIKI_LOG_DIR` | `logs` | Directory where log files are written (relative to working directory or absolute) |
| `LINKWIKI_LOG_LEVEL` | `INFO` | Minimum level for `linkwiki.jsonl` — `DEBUG`, `INFO`, `WARNING`, or `ERROR`. `errors.jsonl` is always ERROR+. |

These are read via `linkwiki/core/config.py` and passed to `setup_logging()` in `linkwiki/core/logging_config.py`.

---

## Implementation Files

| File | Role |
|---|---|
| [`linkwiki/core/logging_config.py`](../linkwiki/core/logging_config.py) | `_JsonFormatter` class and `setup_logging(log_dir, level_str)` function |
| [`linkwiki/core/config.py`](../linkwiki/core/config.py) | `LOG_DIR` and `LOG_LEVEL` constants (read from env vars) |
| [`linkwiki/cli.py`](../linkwiki/cli.py) | Calls `setup_logging(LOG_DIR, LOG_LEVEL)` once at CLI group entry |

---

## Querying the Logs

Because each record is valid JSON, standard tools work directly.

**Count errors by extractor:**
```bash
jq -r 'select(.level=="ERROR") | .logger' logs/errors.jsonl | sort | uniq -c
```

**Find all failed ingests with their durations:**
```bash
jq 'select(.msg=="ingest complete" and .status=="error")' logs/linkwiki.jsonl
```

**Average ingest duration over the last run:**
```bash
jq 'select(.msg=="ingest complete") | .duration_ms' logs/linkwiki.jsonl | awk '{s+=$1;n++} END {print s/n "ms avg"}'
```

**Show all warnings for a specific URL:**
```bash
jq --arg u "https://example.com" 'select(.url==$u and .level=="WARNING")' logs/linkwiki.jsonl
```

**Watch live (follow mode):**
```bash
tail -f logs/linkwiki.jsonl | while read line; do echo "$line" | jq '{ts,level,logger,msg}'; done
```
