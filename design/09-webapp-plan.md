# Web App Plan — LinkWiki

## Decisions Made

### Rendering Strategy
- **FastAPI + Jinja2 templates** (server-rendered HTML)
- No Node.js, no npm, no build step
- Minimal vanilla JS for interactivity (search, add-link dialog)
- Plain CSS for styling

### Auth Strategy
- **JWT stored in httpOnly cookie** (stateless)
- Server issues JWT on login → stored as `httpOnly`, `SameSite=lax` cookie
- Browser auto-sends cookie on every request — no JS token management needed
- Server validates JWT signature on each protected route
- No server-side session storage (no Redis, no DB sessions)

### Groups
- Groups are AI-generated or manually assigned topic clusters
- An entry (link) can belong to multiple groups (many-to-many)
- Groups are a browsing/filtering mechanism — not core to v1
- **v1 scope:** entry list with tag filtering + search; group browsing deferred to v2

---

## Multi-User Database Changes

Add `users` table and `user_id` FK to existing tables:

```sql
CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    last_login    TEXT
);

-- Add user_id to existing tables
ALTER TABLE entries     ADD COLUMN user_id TEXT REFERENCES users(id);
ALTER TABLE groups      ADD COLUMN user_id TEXT REFERENCES users(id);
ALTER TABLE input_files ADD COLUMN user_id TEXT REFERENCES users(id);
```

---

## Folder Structure

```
linkwiki/
  api/
    __init__.py
    app.py            # FastAPI app, Jinja2 setup, route registration
    auth.py           # JWT create/verify, password hashing, current_user dep
    deps.py           # FastAPI dependencies (get_current_user)
    routers/
      auth.py         # POST /login, POST /register, POST /logout, GET /me
      entries.py      # GET /entries, POST /entries, GET /entries/{id}, DELETE /entries/{id}
      groups.py       # GET /groups, GET /groups/{id}
      sync.py         # POST /sync (re-run auto-linking)
      stats.py        # GET /stats
  templates/
    base.html         # layout: navbar, flash messages, CSS link
    login.html
    register.html
    entries/
      list.html       # paginated feed, search bar, tag filter
      detail.html     # full entry: summary, tags, entities, related links
    groups/
      list.html       # group cards with entry count
      detail.html     # entries inside a group
    profile.html      # username display, change password form
    stats.html        # knowledge base stats overview
  static/
    style.css
    app.js            # minimal JS: search debounce, add-link dialog, delete confirm
```

---

## Auth Flow

```
Register:
  POST /register (form: username, password)
  → hash password (bcrypt)
  → insert into users table
  → issue JWT → set httpOnly cookie
  → redirect to /entries

Login:
  POST /login (form: username, password)
  → lookup user → verify password hash
  → issue JWT → set httpOnly cookie
  → redirect to /entries

Logout:
  POST /logout
  → clear cookie
  → redirect to /login

Protected routes:
  request.cookies.get("access_token")
  → verify JWT signature + expiry
  → extract user_id → attach to request
  → 401/redirect to /login if invalid
```

---

## Pages — v1 Scope

| Route | Page | Notes |
|-------|------|-------|
| `GET /login` | Login form | Public |
| `POST /login` | Process login | Public |
| `GET /register` | Register form | Public |
| `POST /register` | Process register | Public |
| `POST /logout` | Clear cookie | Auth required |
| `GET /entries` | Entry list | Auth required; search + tag filter |
| `GET /entries/{id}` | Entry detail | Auth required |
| `POST /entries` | Add new link | Auth required (form submit) |
| `DELETE /entries/{id}` | Delete entry | Auth required |
| `GET /groups` | Group list | Auth required |
| `GET /groups/{id}` | Group detail | Auth required |
| `GET /profile` | User profile | Auth required |
| `POST /profile/password` | Change password | Auth required |
| `GET /stats` | Stats overview | Auth required |

---

## Dependencies to Add

```
python-jose[cryptography]>=3.3.0   # JWT create/verify
passlib[bcrypt]>=1.7.4              # password hashing
python-multipart>=0.0.9             # form submission parsing
jinja2>=3.1.0                       # templating (bundled with fastapi[all])
```

---

## Implementation Order

1. **Multi-user DB migration** — add `users` table, `user_id` columns to existing tables
2. **Auth module** — JWT helpers, password hashing, `get_current_user` dependency
3. **Auth routes + templates** — login, register, logout pages
4. **FastAPI app scaffold** — Jinja2 setup, static files, route registration
5. **Entry list page** — paginated feed, search, tag filter
6. **Entry detail page** — full entry view with related links
7. **Add link flow** — form in navbar/dialog → POST → redirect back
8. **Group list + detail pages**
9. **Profile + change password**
10. **Stats page**

---

## Out of Scope for v1

- WebSocket live feed (processing progress)
- Knowledge graph visualization
- Background job system (sync runs inline for now)
- Mobile / PWA
- REST API for external clients (CLI still works directly via DB)
