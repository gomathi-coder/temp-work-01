"""Entry routes: list, detail, add, delete."""

from __future__ import annotations

import math
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from linkwiki.api.deps import _LoginRedirect, get_current_user
from linkwiki.core import database as db
from linkwiki.core.pipeline import ingest

router = APIRouter(prefix="/entries")
_tpl = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_PAGE_SIZE = 20


# ── List ───────────────────────────────────────────────────────────────────

@router.get("")
async def entry_list(request: Request, q: str = "", tag: str = "", page: int = 1):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    page = max(1, page)
    offset = (page - 1) * _PAGE_SIZE

    if q.strip():
        entries = db.search_entries(q.strip(), user_id=user["id"], limit=_PAGE_SIZE)
        total = len(entries)
    else:
        entries = db.list_entries(
            tag=tag.strip() or None,
            user_id=user["id"],
            limit=_PAGE_SIZE,
            offset=offset,
        )
        total = db.count_entries(tag=tag.strip() or None, user_id=user["id"])

    all_tags = db.list_all_tags(user["id"])

    total_pages = max(1, math.ceil(total / _PAGE_SIZE))

    return _tpl.TemplateResponse(request, "entries/list.html", {
        "user": user,
        "entries": entries,
        "q": q,
        "tag": tag,
        "page": page,
        "total": total,
        "total_pages": total_pages,
        "all_tags": all_tags,
    })


# ── Add (GET = form page, POST = process) ─────────────────────────────────

@router.get("/new")
async def add_entry_page(request: Request):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response
    return _tpl.TemplateResponse(request, "entries/new.html", {"user": user, "error": None})


@router.post("")
async def add_entry(request: Request, url: str = Form(...)):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    url = url.strip()
    if not url:
        return RedirectResponse(url="/entries", status_code=302)

    result = ingest(url, source_type="ui")

    if result["status"] == "error":
        return _tpl.TemplateResponse(request, "entries/new.html", {
            "user": user,
            "error": f"Failed to process link: {result.get('error', 'unknown error')}",
            "url": url,
        })

    entry_id = result["id"]
    # Tag entry with the logged-in user
    db.update_entry(entry_id, user_id=user["id"])

    return RedirectResponse(url=f"/entries/{entry_id}", status_code=302)


# ── Detail ─────────────────────────────────────────────────────────────────

@router.get("/{entry_id}")
async def entry_detail(request: Request, entry_id: str):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    entry = db.get_entry(entry_id)
    if not entry or entry.get("user_id") != user["id"]:
        return RedirectResponse(url="/entries", status_code=302)

    related = db.get_related(entry_id, limit=8)
    groups = db.get_entry_groups(entry_id)

    # Group entities by type for cleaner display
    entities_by_type: dict[str, list] = {}
    for ent in entry.get("entities") or []:
        kind = ent.get("type", "other")
        entities_by_type.setdefault(kind, []).append(ent)

    return _tpl.TemplateResponse(request, "entries/detail.html", {
        "user": user,
        "entry": entry,
        "related": related,
        "groups": groups,
        "entities_by_type": entities_by_type,
    })


# ── Delete ─────────────────────────────────────────────────────────────────

@router.post("/{entry_id}/delete")
async def delete_entry(request: Request, entry_id: str):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    entry = db.get_entry(entry_id)
    if entry and entry.get("user_id") == user["id"]:
        db.delete_entry(entry_id)

    return RedirectResponse(url="/entries", status_code=302)
