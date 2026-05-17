"""GitHub extractor — repo metadata + README via GitHub REST API."""

from __future__ import annotations
import base64
import logging
import re
import time
import requests
from linkwiki.extractors.result import ExtractionResult
from linkwiki.core.config import GITHUB_TOKEN, MAX_CONTENT_CHARS

log = logging.getLogger(__name__)

_URL_RE = re.compile(r'https?://[^\s\)\]\'">,]+')
_REPO_RE = re.compile(r'github\.com/([^/\s]+)/([^/\s#?]+)')


def _headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _find_urls(text: str) -> list[dict]:
    return [
        {"url": u, "label": "", "context": "in README"}
        for u in _URL_RE.findall(text)
        if "github.com" not in u
    ][:40]


def extract(url: str) -> ExtractionResult:
    log.info("extraction started", extra={"url": url, "extractor": "github"})
    t0 = time.monotonic()

    m = _REPO_RE.search(url)
    if not m:
        log.error("could not parse owner/repo from URL", extra={"url": url})
        return ExtractionResult(url=url, url_type="github",
                                status="error", error_msg="Could not parse owner/repo from URL")

    owner, repo = m.group(1), m.group(2).rstrip(".git")
    log.debug("parsed repository", extra={"url": url, "owner": owner, "repo": repo,
                                          "authenticated": bool(GITHUB_TOKEN)})
    headers = _headers()

    try:
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers, timeout=10,
        )
        api_ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 404:
            log.error(
                "repository not found",
                extra={"url": url, "owner": owner, "repo": repo,
                       "status_code": 404, "duration_ms": api_ms},
            )
            return ExtractionResult(url=url, url_type="github",
                                    status="error", error_msg="Repository not found")
        resp.raise_for_status()
        log.debug(
            "repository metadata fetched",
            extra={"url": url, "owner": owner, "repo": repo,
                   "status_code": resp.status_code, "duration_ms": api_ms},
        )
    except requests.RequestException as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        log.error(
            "GitHub API request failed",
            extra={"url": url, "owner": owner, "repo": repo,
                   "error": str(e), "duration_ms": duration_ms},
        )
        return ExtractionResult(url=url, url_type="github",
                                status="error", error_msg=str(e))

    meta = resp.json()
    title = meta.get("full_name", f"{owner}/{repo}")
    description = meta.get("description") or ""
    topics = ", ".join(meta.get("topics", []))
    stars = meta.get("stargazers_count", 0)
    language = meta.get("language") or ""

    log.debug(
        "repository details",
        extra={"url": url, "title": title, "language": language,
               "stars": stars, "topics_count": len(meta.get("topics", []))},
    )

    readme = ""
    try:
        t_readme = time.monotonic()
        r = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            headers=headers, timeout=10,
        )
        readme_ms = int((time.monotonic() - t_readme) * 1000)
        if r.status_code == 200:
            readme = base64.b64decode(r.json()["content"]).decode("utf-8", errors="replace")
            log.debug(
                "README fetched",
                extra={"url": url, "readme_chars": len(readme), "duration_ms": readme_ms},
            )
        else:
            log.warning(
                "README not available",
                extra={"url": url, "status_code": r.status_code, "duration_ms": readme_ms},
            )
    except Exception as e:
        log.warning("README fetch failed", extra={"url": url, "error": str(e)})

    raw_content = (
        f"Repository: {title}\n"
        f"Description: {description}\n"
        f"Language: {language}\n"
        f"Stars: {stars}\n"
        f"Topics: {topics}\n\n"
        f"README:\n{readme}"
    )

    total_ms = int((time.monotonic() - t0) * 1000)
    log.info(
        "extraction complete",
        extra={
            "url": url, "status": "done",
            "title": title, "language": language, "stars": stars,
            "content_chars": len(raw_content),
            "discovered_count": len(_find_urls(readme)),
            "duration_ms": total_ms,
        },
    )
    return ExtractionResult(
        url=url,
        url_type="github",
        title=title,
        author=owner,
        raw_content=raw_content[:MAX_CONTENT_CHARS],
        discovered_links=_find_urls(readme),
        status="done",
    )
