"""FastAPI application — Jinja2 server-rendered web UI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from linkwiki.api.routers import auth as auth_router
from linkwiki.api.routers import entries as entries_router
from linkwiki.api.routers import groups as groups_router
from linkwiki.api.routers import stats as stats_router
from linkwiki.core.database import init_db

_HERE = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="LinkWiki", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=_HERE / "static"), name="static")

app.include_router(auth_router.router, tags=["auth"])
app.include_router(entries_router.router, tags=["entries"])
app.include_router(groups_router.router, tags=["groups"])
app.include_router(stats_router.router, tags=["stats"])

from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    return RedirectResponse(url="/entries", status_code=302)
