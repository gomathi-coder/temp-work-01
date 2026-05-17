"""Stats route."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from linkwiki.api.deps import _LoginRedirect, get_current_user
from linkwiki.core.database import get_stats

router = APIRouter()
_tpl = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/stats")
async def stats_page(request: Request):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    stats = get_stats(user_id=user["id"])
    return _tpl.TemplateResponse(request, "stats.html", {
        "user": user,
        "stats": stats,
    })
