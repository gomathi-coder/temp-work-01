# Design: Admin Tab

## Overview

Add a new **Admin** tab to the navigation. It hosts the "Add" form and a full grid view of all entries (for the current user). Processing happens in the background — the POST responds immediately with a success message while the pipeline runs asynchronously. The **Entries** tab is left unchanged.

---

## 1. Navigation Changes

**Current nav:** Entries | Groups | Stats | [+ Add button in top-right user section]

**New nav:** Entries | Groups | Stats | **Admin** | [+ Add button removed from top-right]

- The `+ Add` button is removed from the user section of `base.html`
- It lives exclusively on the Admin tab page
- Active state detection follows the same pattern: `request.url.path.startswith("/admin")`

---

## 2. Admin Tab: Page Layout

**Route:** `GET /admin`

```
┌─────────────────────────────────────────────────────┐
│  Admin                              [+ Add Link]     │
│                                                      │
│  [_____ Filter by title or URL ___________________]  │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ YOUTUBE  │ │  GITHUB  │ │   WEB    │ │  WEB   │ │
│  │ [done]   │ │[pending] │ │ [error]  │ │[done]  │ │
│  │ Title    │ │ Title    │ │ Title    │ │ Title  │ │
│  │ url...   │ │ url...   │ │ url...   │ │ url... │ │
│  │ 2026-05  │ │ 2026-05  │ │ 2026-05  │ │2026-05 │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│  ...                                                  │
│                                                      │
│        [← Prev]  Page 2 of 5  [Next →]              │
└─────────────────────────────────────────────────────┘
```

### Grid Card Fields
Each card shows:
- **url_type badge** (youtube / github / arxiv / web) — color-coded
- **status badge** (done=green / pending=gray / partial=orange / error=red)
- **Title** (or URL if title not yet resolved)
- **URL** (truncated, links to the entry detail page)
- **created_at** date

Cards are clickable — link to `/entries/{entry_id}`.

### Text Filter
- Single text input: filters on `title` and `url` (case-insensitive, server-side)
- Submitted as a query param: `GET /admin?q=something&page=1`
- Pagination resets to page 1 when filter changes
- No JavaScript required — plain form submit

### Pagination
- 24 entries per page (fits 4-column grid cleanly at standard widths)
- Shows: `[← Prev]  Page N of M  [Next →]`
- Disabled state on first/last page
- Pagination links preserve the `q` filter param

---

## 3. Add Link Flow (Background Processing)

### 3a. Add Form

**Route:** `GET /admin/new` (or a modal on the admin page — see Option note below)

Simple form:
```
URL: [_______________________________]
              [Add Link]  [Cancel]
```

On submit → `POST /admin/entries`

> **Option:** The form can live inline at the top of the Admin page (collapsed/expanded) rather than a separate page, to keep the flow in one place. Recommend: a small inline form that appears when `+ Add Link` is clicked (no JS required — use a query param `?adding=1` to show/hide). Default to this unless you prefer a separate page.

### 3b. POST Handler — Immediate Response

**Route:** `POST /admin/entries`

```
1. Validate URL (non-empty, valid format)
2. Duplicate check — if URL exists, flash "Already exists" and redirect to /admin
3. Create entry in DB immediately:
     status = "pending"
     source_type = "ui"
     created_at = now()
     user_id = current user
4. Dispatch background thread to run full ingest pipeline
5. Flash success message: "Link added — processing in background"
6. Redirect to GET /admin (302)
```

The response is instant (< 100ms). The user sees the new entry in the grid immediately with `status=pending`.

### 3c. Background Processing

Use Python's `threading.Thread` (no new dependencies required).

```python
import threading

def _run_ingest_background(entry_id: str, url: str):
    try:
        _process_existing_entry(entry_id, url)   # new internal function
    except Exception:
        db.set_entry_status(entry_id, "error", error_msg=traceback.format_exc())

thread = threading.Thread(target=_run_ingest_background, args=(entry_id, url), daemon=True)
thread.start()
```

### 3d. Pipeline Split

The current `ingest()` does everything atomically. We split it:

| Phase | Where | Timing |
|-------|-------|--------|
| Duplicate check | POST handler | Immediate |
| Create pending entry in DB | POST handler | Immediate |
| Content extraction | Background thread | Async |
| AI processing (Claude) | Background thread | Async |
| Embedding + linking | Background thread | Async |
| Group assignment | Background thread | Async |
| Update entry status to done/partial/error | Background thread | Async |

**New internal function** in `pipeline.py`:
```python
def process_entry(entry_id: str, url: str, source_type: str = "ui") -> None:
    """Run extraction, AI, embedding, and linking for an already-created pending entry."""
    ...
```

The existing `ingest()` function is **not removed** — the CLI still uses it and it works synchronously end-to-end. The new `process_entry()` is the background-safe version used by the admin POST handler.

### 3e. Status Lifecycle

```
[created]
    ↓
 pending   ← entry visible in Admin grid immediately
    ↓
 done / partial / error   ← after background pipeline finishes
```

User refreshes the Admin page to see the updated status. No polling, no WebSockets.

---

## 4. Files to Create / Modify

### New Files
| File | Purpose |
|------|---------|
| `linkwiki/api/routers/admin.py` | Admin tab routes: GET /admin, GET /admin/new, POST /admin/entries |
| `linkwiki/api/templates/admin/list.html` | Admin grid page template |

### Modified Files
| File | Change |
|------|--------|
| `linkwiki/api/app.py` | Register admin router |
| `linkwiki/api/templates/base.html` | Add Admin nav link; remove `+ Add` from user section |
| `linkwiki/core/pipeline.py` | Add `process_entry()` function (background-safe, non-duplicating logic) |
| `linkwiki/core/database.py` | Add `create_pending_entry()` and `set_entry_status()` helpers |

---

## 5. Database Helper Functions

Two new helpers in `database.py`:

```python
def create_pending_entry(url: str, url_type: str, source_type: str, user_id: str) -> str:
    """Insert a new entry with status='pending'. Returns entry_id."""

def set_entry_status(entry_id: str, status: str, error_msg: str | None = None) -> None:
    """Update status (and optionally error_msg) on an existing entry."""
```

The existing `create_entry()` / `update_entry()` functions are reused inside `process_entry()`.

---

## 6. No Changes to Entries Tab

- `GET /entries`, `GET /entries/{id}`, `POST /entries/{id}/delete` — untouched
- `GET /entries/new` and `POST /entries` — untouched (kept for backward compatibility / CLI parity)
- The `+ Add` button disappears from the navbar user section only

---

## 7. Out of Scope (Not in This Change)

- Real-time status updates (WebSocket / SSE / polling)
- Admin-only access control (all authenticated users can access Admin)
- Bulk delete / bulk reprocess actions
- Column sorting on the Admin grid
- Edit entry from Admin grid

---

## 8. Confirmed Decisions

| Question | Decision |
|----------|----------|
| Add form placement | Inline on Admin page via `?adding=1` query param |
| Grid columns | Responsive: 1 col mobile, 2 col tablet, 4 col desktop |
| Page size | 24 per page |
| Who sees Admin | All authenticated users |
| Old `+ Add` button | Keep as shortcut — links to `/admin?adding=1` |
