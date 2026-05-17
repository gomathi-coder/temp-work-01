"""FastAPI dependencies shared across routers."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse

from linkwiki.api.auth import decode_access_token
from linkwiki.core.database import get_user_by_id


def get_current_user(request: Request) -> dict:
    """Return the logged-in user dict, or redirect to /login."""
    token = request.cookies.get("access_token")
    if token:
        user_id = decode_access_token(token)
        if user_id:
            user = get_user_by_id(user_id)
            if user:
                return user
    # Returning a RedirectResponse from a dependency is handled in routers
    # by checking the return type; raising it directly works for HTML pages.
    raise _LoginRedirect()


class _LoginRedirect(Exception):
    """Sentinel raised when the user is not authenticated."""
    response = RedirectResponse(url="/login", status_code=302)
