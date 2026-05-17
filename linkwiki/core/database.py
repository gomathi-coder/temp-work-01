"""SQLite storage — schema init, all CRUD operations."""

from __future__ import annotations
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from linkwiki.core.config import DATA_DIR, DB_PATH


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_id() -> str:
    return str(uuid.uuid4()).replace("-", "")[:8]


# ── Schema ─────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    last_login    TEXT
);

CREATE TABLE IF NOT EXISTS entries (
    id               TEXT PRIMARY KEY,
    url              TEXT UNIQUE NOT NULL,
    url_type         TEXT NOT NULL,
    title            TEXT,
    author           TEXT,
    raw_content      TEXT,
    summary          TEXT,
    tags             TEXT NOT NULL DEFAULT '[]',
    entities         TEXT NOT NULL DEFAULT '[]',
    discovered_links TEXT NOT NULL DEFAULT '[]',
    source_type      TEXT NOT NULL DEFAULT 'cli',
    source_ref       TEXT,
    status           TEXT NOT NULL DEFAULT 'pending',
    error_msg        TEXT,
    created_at       TEXT NOT NULL,
    processed_at     TEXT
);

CREATE TABLE IF NOT EXISTS groups (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    group_type  TEXT NOT NULL DEFAULT 'manual',
    parent_id   TEXT REFERENCES groups(id),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entry_groups (
    entry_id  TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    group_id  TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    added_by  TEXT NOT NULL DEFAULT 'auto',
    added_at  TEXT NOT NULL,
    PRIMARY KEY (entry_id, group_id)
);

CREATE TABLE IF NOT EXISTS links (
    id         TEXT PRIMARY KEY,
    from_id    TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    to_id      TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    link_type  TEXT NOT NULL,
    strength   REAL NOT NULL DEFAULT 1.0,
    metadata   TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE (from_id, to_id, link_type)
);

CREATE TABLE IF NOT EXISTS input_files (
    id           TEXT PRIMARY KEY,
    file_path    TEXT NOT NULL UNIQUE,
    last_read_at TEXT,
    total_lines  INTEGER DEFAULT 0,
    processed    INTEGER DEFAULT 0,
    skipped      INTEGER DEFAULT 0,
    errored      INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_entries_url_type    ON entries(url_type);
CREATE INDEX IF NOT EXISTS idx_entries_status      ON entries(status);
CREATE INDEX IF NOT EXISTS idx_entries_source_type ON entries(source_type);
CREATE INDEX IF NOT EXISTS idx_links_from          ON links(from_id);
CREATE INDEX IF NOT EXISTS idx_links_to            ON links(to_id);
"""


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.executescript(_SCHEMA)
    _migrate_db()


def _migrate_db() -> None:
    """Idempotent ALTER TABLE migrations for columns added after initial release."""
    with _conn() as conn:
        for table, col, definition in [
            ("entries",     "user_id", "TEXT REFERENCES users(id)"),
            ("groups",      "user_id", "TEXT REFERENCES users(id)"),
            ("input_files", "user_id", "TEXT REFERENCES users(id)"),
        ]:
            existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Helpers ────────────────────────────────────────────────────────────────

def _deserialise(row: sqlite3.Row) -> dict:
    d = dict(row)
    for field in ("tags", "entities", "discovered_links"):
        d[field] = json.loads(d[field]) if d.get(field) else []
    return d


def _serialise_lists(kwargs: dict) -> dict:
    for field in ("tags", "entities", "discovered_links"):
        if field in kwargs and isinstance(kwargs[field], list):
            kwargs[field] = json.dumps(kwargs[field])
    return kwargs


# ── Entry CRUD ─────────────────────────────────────────────────────────────

def url_exists(url: str) -> str | None:
    with _conn() as conn:
        row = conn.execute("SELECT id FROM entries WHERE url = ?", (url,)).fetchone()
    return row["id"] if row else None


def create_entry(url: str, url_type: str, source_type: str = "cli",
                 source_ref: str | None = None) -> str:
    entry_id = _short_id()
    with _conn() as conn:
        conn.execute(
            """INSERT INTO entries (id, url, url_type, source_type, source_ref,
               status, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            (entry_id, url, url_type, source_type, source_ref, _now()),
        )
    return entry_id


def update_entry(entry_id: str, **kwargs) -> None:
    if not kwargs:
        return
    kwargs = _serialise_lists(kwargs)
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    with _conn() as conn:
        conn.execute(
            f"UPDATE entries SET {sets} WHERE id = ?",
            [*kwargs.values(), entry_id],
        )


def get_entry(id_or_url: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM entries WHERE id = ? OR url = ?",
            (id_or_url, id_or_url),
        ).fetchone()
    return _deserialise(row) if row else None


def list_entries(
    tag: str | None = None,
    group: str | None = None,
    url_type: str | None = None,
    source_type: str | None = None,
    status: str | None = None,
    user_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    query = "SELECT DISTINCT e.* FROM entries e"
    conditions: list[str] = []
    params: list = []

    if group:
        query += " JOIN entry_groups eg ON e.id = eg.entry_id JOIN groups g ON eg.group_id = g.id"
        conditions.append("g.name = ?")
        params.append(group)
    if url_type:
        conditions.append("e.url_type = ?")
        params.append(url_type)
    if source_type:
        conditions.append("e.source_type = ?")
        params.append(source_type)
    if status:
        conditions.append("e.status = ?")
        params.append(status)
    if tag:
        conditions.append(
            "EXISTS (SELECT 1 FROM json_each(e.tags) WHERE value = ?)"
        )
        params.append(tag)
    if user_id:
        conditions.append("e.user_id = ?")
        params.append(user_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY e.created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_deserialise(r) for r in rows]


def count_entries(
    tag: str | None = None,
    user_id: str | None = None,
) -> int:
    conditions: list[str] = []
    params: list = []
    if tag:
        conditions.append("EXISTS (SELECT 1 FROM json_each(tags) WHERE value = ?)")
        params.append(tag)
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    with _conn() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM entries {where}", params).fetchone()[0]


def get_all_entries_for_linking() -> list[dict]:
    """Return id, tags, entities for all processable entries."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, tags, entities FROM entries WHERE status IN ('done', 'partial')"
        ).fetchall()
    return [_deserialise(r) for r in rows]


def upsert_link(from_id: str, to_id: str, link_type: str,
                strength: float, metadata: dict | None = None) -> None:
    a, b = (from_id, to_id) if from_id < to_id else (to_id, from_id)
    with _conn() as conn:
        conn.execute(
            """INSERT INTO links (id, from_id, to_id, link_type, strength, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (from_id, to_id, link_type) DO UPDATE SET
                   strength = excluded.strength,
                   metadata = excluded.metadata""",
            (_short_id(), a, b, link_type, strength,
             json.dumps(metadata or {}), _now()),
        )


def get_related(entry_id: str, link_type: str | None = None,
                limit: int = 10) -> list[dict]:
    type_clause = "AND l.link_type = ?" if link_type else ""
    base_params = [entry_id, entry_id]
    if link_type:
        base_params.append(link_type)

    with _conn() as conn:
        rows = conn.execute(
            f"""SELECT e.*, l.link_type as _link_type, l.strength as _strength
                FROM links l
                JOIN entries e ON e.id = CASE
                    WHEN l.from_id = ? THEN l.to_id ELSE l.from_id END
                WHERE (l.from_id = ? OR l.to_id = ?) {type_clause}
                  AND e.id != ?
                ORDER BY l.strength DESC
                LIMIT ?""",
            [entry_id] + base_params + [entry_id, limit],
        ).fetchall()

    result = []
    for r in rows:
        d = _deserialise(r)
        d["link_type"] = d.pop("_link_type", None)
        d["strength"] = d.pop("_strength", None)
        result.append(d)
    return result


def delete_links_for(entry_id: str, link_type: str | None = None) -> None:
    clause = "AND link_type = ?" if link_type else ""
    params = [entry_id, entry_id]
    if link_type:
        params.append(link_type)
    with _conn() as conn:
        conn.execute(
            f"DELETE FROM links WHERE (from_id = ? OR to_id = ?) {clause}",
            params,
        )


def create_pending_entry(url: str, url_type: str, source_type: str, user_id: str) -> str:
    """Insert a new entry with status='pending' and return entry_id."""
    entry_id = _short_id()
    with _conn() as conn:
        conn.execute(
            """INSERT INTO entries (id, url, url_type, source_type, status, user_id, created_at)
               VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
            (entry_id, url, url_type, source_type, user_id, _now()),
        )
    return entry_id


def set_entry_status(entry_id: str, status: str, error_msg: str | None = None) -> None:
    """Update status (and optionally error_msg) on an existing entry."""
    with _conn() as conn:
        if error_msg is not None:
            conn.execute(
                "UPDATE entries SET status = ?, error_msg = ?, processed_at = ? WHERE id = ?",
                (status, error_msg, _now(), entry_id),
            )
        else:
            conn.execute(
                "UPDATE entries SET status = ?, processed_at = ? WHERE id = ?",
                (status, _now(), entry_id),
            )


def list_all_tags(user_id: str) -> list[str]:
    """Return all distinct tag values across a user's entries, sorted alphabetically."""
    with _conn() as conn:
        rows = conn.execute(
            """SELECT DISTINCT value FROM entries, json_each(entries.tags)
               WHERE user_id = ? ORDER BY value""",
            (user_id,),
        ).fetchall()
    return [r[0] for r in rows]


def list_entries_for_admin(
    user_id: str,
    q: str | None = None,
    limit: int = 24,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return (entries, total_count) for the admin grid with optional title/url text filter."""
    conditions = ["e.user_id = ?"]
    params: list = [user_id]

    if q:
        conditions.append("(e.title LIKE ? OR e.url LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])

    where = "WHERE " + " AND ".join(conditions)

    with _conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM entries e {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM entries e {where} ORDER BY e.created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

    return [_deserialise(r) for r in rows], total


def search_entries(query_text: str, user_id: str | None = None, limit: int = 20) -> list[dict]:
    """Simple keyword search over title, summary, and tags (Phase 1)."""
    like = f"%{query_text}%"
    user_clause = "AND user_id = ?" if user_id else ""
    params = [like, like, like]
    if user_id:
        params.append(user_id)
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(
            f"""SELECT * FROM entries
               WHERE (title LIKE ? OR summary LIKE ? OR tags LIKE ?)
               {user_clause}
               ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    return [_deserialise(r) for r in rows]


def delete_entry(id_or_url: str) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM entries WHERE id = ? OR url = ?",
            (id_or_url, id_or_url),
        )
    return cur.rowcount > 0


def get_stats(user_id: str | None = None) -> dict:
    where = "WHERE user_id = ?" if user_id else ""
    p = (user_id,) if user_id else ()
    with _conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM entries {where}", p).fetchone()[0]
        by_type = conn.execute(
            f"SELECT url_type, COUNT(*) FROM entries {where} GROUP BY url_type", p
        ).fetchall()
        by_status = conn.execute(
            f"SELECT status, COUNT(*) FROM entries {where} GROUP BY status", p
        ).fetchall()
        unique_tags = conn.execute(
            f"SELECT COUNT(DISTINCT value) FROM entries {where.replace('WHERE','AND') if where else ''} "
            f", json_each(entries.tags)",
            p,
        ).fetchone()[0]
        unique_entities = conn.execute(
            f"SELECT COUNT(DISTINCT json_extract(value, '$.name')) "
            f"FROM entries {where.replace('WHERE','AND') if where else ''} "
            f", json_each(entries.entities)",
            p,
        ).fetchone()[0]
        # Groups and links are global (not per-user) but scoped by user-owned entries
        if user_id:
            total_groups = conn.execute(
                """SELECT COUNT(DISTINCT g.id) FROM groups g
                   JOIN entry_groups eg ON g.id = eg.group_id
                   JOIN entries e ON eg.entry_id = e.id
                   WHERE e.user_id = ?""",
                (user_id,),
            ).fetchone()[0]
            total_links = conn.execute(
                """SELECT COUNT(DISTINCT l.id) FROM links l
                   JOIN entries e ON (l.from_id = e.id OR l.to_id = e.id)
                   WHERE e.user_id = ?""",
                (user_id,),
            ).fetchone()[0]
        else:
            total_groups = conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
            total_links = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]

        # Top tags for this user
        top_tags = conn.execute(
            f"""SELECT value AS tag, COUNT(*) AS cnt
                FROM entries {where}, json_each(entries.tags)
                GROUP BY value ORDER BY cnt DESC LIMIT 10""",
            p,
        ).fetchall()

    return {
        "entries": {
            "total": total,
            "by_type": dict(by_type),
            "by_status": dict(by_status),
        },
        "tags": {"unique": unique_tags, "top": [dict(r) for r in top_tags]},
        "entities": {"unique": unique_entities},
        "groups": {"total": total_groups},
        "links": {"total": total_links},
    }


# ── Group CRUD ─────────────────────────────────────────────────────────────

def get_or_create_group(name: str, group_type: str = "manual") -> str:
    with _conn() as conn:
        row = conn.execute("SELECT id FROM groups WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        group_id = _short_id()
        conn.execute(
            """INSERT INTO groups (id, name, group_type, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (group_id, name, group_type, _now(), _now()),
        )
    return group_id


def assign_to_group(entry_id: str, group_id: str, added_by: str = "auto") -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO entry_groups
               (entry_id, group_id, added_by, added_at) VALUES (?, ?, ?, ?)""",
            (entry_id, group_id, added_by, _now()),
        )


def remove_from_group(entry_id: str, group_id: str) -> None:
    with _conn() as conn:
        conn.execute(
            "DELETE FROM entry_groups WHERE entry_id = ? AND group_id = ?",
            (entry_id, group_id),
        )


def list_groups(user_id: str | None = None) -> list[dict]:
    if user_id:
        # Only groups that contain at least one entry owned by this user
        with _conn() as conn:
            rows = conn.execute(
                """SELECT g.*, COUNT(eg.entry_id) AS entry_count
                   FROM groups g
                   JOIN entry_groups eg ON g.id = eg.group_id
                   JOIN entries e ON eg.entry_id = e.id
                   WHERE e.user_id = ?
                   GROUP BY g.id ORDER BY g.name""",
                (user_id,),
            ).fetchall()
    else:
        with _conn() as conn:
            rows = conn.execute(
                """SELECT g.*, COUNT(eg.entry_id) AS entry_count
                   FROM groups g
                   LEFT JOIN entry_groups eg ON g.id = eg.group_id
                   GROUP BY g.id ORDER BY g.name""",
            ).fetchall()
    return [dict(r) for r in rows]


def get_entry_groups(entry_id: str) -> list[str]:
    with _conn() as conn:
        rows = conn.execute(
            """SELECT g.name FROM groups g
               JOIN entry_groups eg ON g.id = eg.group_id
               WHERE eg.entry_id = ?""",
            (entry_id,),
        ).fetchall()
    return [r["name"] for r in rows]


def get_group_by_name(name: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            """SELECT g.*, COUNT(eg.entry_id) AS entry_count
               FROM groups g
               LEFT JOIN entry_groups eg ON g.id = eg.group_id
               WHERE g.name = ? GROUP BY g.id""",
            (name,),
        ).fetchone()
    return dict(row) if row else None


def delete_group(name: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM groups WHERE name = ?", (name,))
    return cur.rowcount > 0


# ── Input file registry ────────────────────────────────────────────────────

def register_input_file(file_path: str) -> str:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM input_files WHERE file_path = ?", (file_path,)
        ).fetchone()
        if row:
            return row["id"]
        file_id = _short_id()
        conn.execute(
            "INSERT INTO input_files (id, file_path) VALUES (?, ?)",
            (file_id, file_path),
        )
    return file_id


def update_input_file(file_path: str, **kwargs) -> None:
    kwargs["last_read_at"] = _now()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    with _conn() as conn:
        conn.execute(
            f"UPDATE input_files SET {sets} WHERE file_path = ?",
            [*kwargs.values(), file_path],
        )


def list_input_files() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM input_files ORDER BY last_read_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── User CRUD ──────────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str) -> str:
    user_id = _short_id()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, password_hash, _now()),
        )
    return user_id


def get_user_by_username(username: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def update_user_last_login(user_id: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?", (_now(), user_id)
        )


def update_user_password(user_id: str, password_hash: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
        )
