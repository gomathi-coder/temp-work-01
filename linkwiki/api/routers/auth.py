"""Auth routes: login, register, logout, profile, change password."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from linkwiki.api.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from linkwiki.api.deps import _LoginRedirect, get_current_user
from linkwiki.core.database import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    update_user_last_login,
    update_user_password,
    init_db,
)

router = APIRouter()
_tpl = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def _set_auth_cookie(response: RedirectResponse, user_id: str) -> RedirectResponse:
    response.set_cookie(
        key="access_token",
        value=create_access_token(user_id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
    )
    return response


# ── Register ───────────────────────────────────────────────────────────────

@router.get("/register")
async def register_page(request: Request):
    return _tpl.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    def _err(msg: str):
        return _tpl.TemplateResponse(request, "register.html", {"error": msg, "username": username})

    username = username.strip()
    if not username or len(username) < 3:
        return _err("Username must be at least 3 characters.")
    if len(password) < 8:
        return _err("Password must be at least 8 characters.")
    if password != confirm_password:
        return _err("Passwords do not match.")
    if get_user_by_username(username):
        return _err("Username already taken.")

    init_db()
    user_id = create_user(username, hash_password(password))
    return _set_auth_cookie(RedirectResponse(url="/entries", status_code=302), user_id)


# ── Login ──────────────────────────────────────────────────────────────────

@router.get("/login")
async def login_page(request: Request):
    return _tpl.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    def _err(msg: str):
        return _tpl.TemplateResponse(request, "login.html", {"error": msg, "username": username})

    user = get_user_by_username(username.strip())
    if not user or not verify_password(password, user["password_hash"]):
        return _err("Invalid username or password.")

    update_user_last_login(user["id"])
    return _set_auth_cookie(RedirectResponse(url="/entries", status_code=302), user["id"])


# ── Logout ─────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp


# ── Profile ────────────────────────────────────────────────────────────────

@router.get("/profile")
async def profile_page(request: Request):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response
    return _tpl.TemplateResponse(request, "profile.html", {"user": user, "error": None, "success": None})


@router.post("/profile/password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    try:
        user = get_current_user(request)
    except _LoginRedirect as e:
        return e.response

    def _err(msg: str):
        return _tpl.TemplateResponse(request, "profile.html", {"user": user, "error": msg, "success": None})

    if not verify_password(current_password, user["password_hash"]):
        return _err("Current password is incorrect.")
    if len(new_password) < 8:
        return _err("New password must be at least 8 characters.")
    if new_password != confirm_password:
        return _err("New passwords do not match.")

    update_user_password(user["id"], hash_password(new_password))
    updated_user = get_user_by_id(user["id"])
    return _tpl.TemplateResponse(
        request, "profile.html",
        {"user": updated_user, "error": None, "success": "Password updated successfully."},
    )
