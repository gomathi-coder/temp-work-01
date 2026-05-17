"""Admin routes: entry grid with inline add form."""

from __future__ import annotations

import math
import threading
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from linkwiki.api.deps import _LoginRedirect, get_current_user
from linkwiki.core import database as db
from linkwiki.core.pipeline import process_entry

router = APIRouter(prefix="/admin")
_tpl = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_PAGE_SIZE = 24


def _detect_url_type(url: str) -> str:
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "github.com" in u:
        return "github"
    if "arxiv.org" in u:
        return "arxiv"
    return "web"


@router.get("")
async def admin_page(
    request: Request,
    q: str = "",
    page: int = 1,
    adding: str = "",
    msg: str = "",
):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    page = max(1, page)
    offset = (page - 1) * _PAGE_SIZE

    entries, total = db.list_entries_for_admin(
        user_id=user["id"],
        q=q.strip() or None,
        limit=_PAGE_SIZE,
        offset=offset,
    )

    total_pages = max(1, math.ceil(total / _PAGE_SIZE))

    return _tpl.TemplateResponse(request, "admin/list.html", {
        "user": user,
        "entries": entries,
        "q": q,
        "page": page,
        "total": total,
        "total_pages": total_pages,
        "adding": bool(adding),
        "msg": msg,
    })


@router.post("/entries")
async def admin_add_entry(request: Request, url: str = Form(...)):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    url = url.strip()
    if not url:
        return RedirectResponse(url="/admin", status_code=302)

    existing_id = db.url_exists(url)
    if existing_id:
        return RedirectResponse(url="/admin?msg=duplicate", status_code=302)

    url_type = _detect_url_type(url)
    entry_id = db.create_pending_entry(url, url_type, source_type="ui", user_id=user["id"])

    def _bg():
        process_entry(entry_id, url)

    threading.Thread(target=_bg, daemon=True).start()

    return RedirectResponse(url="/admin?msg=added", status_code=302)
