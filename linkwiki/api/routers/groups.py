"""Group routes: list and detail."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from linkwiki.api.deps import _LoginRedirect, get_current_user
from linkwiki.core import database as db

router = APIRouter(prefix="/groups")
_tpl = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("")
async def group_list(request: Request):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    groups = db.list_groups(user_id=user["id"])
    return _tpl.TemplateResponse(request, "groups/list.html", {
        "user": user,
        "groups": groups,
    })


@router.get("/{group_id}")
async def group_detail(request: Request, group_id: str):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    with db._conn() as conn:
        row = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
    if not row:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/groups", status_code=302)

    group = dict(row)
    entries = db.list_entries(group=group["name"], user_id=user["id"], limit=100)

    return _tpl.TemplateResponse(request, "groups/detail.html", {
        "user": user,
        "group": group,
        "entries": entries,
    })
