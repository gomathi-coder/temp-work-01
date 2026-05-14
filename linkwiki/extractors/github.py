"""GitHub extractor — repo metadata + README via GitHub REST API."""

from __future__ import annotations
import base64
import re
import requests
from linkwiki.extractors.result import ExtractionResult
from linkwiki.core.config import GITHUB_TOKEN, MAX_CONTENT_CHARS

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
    m = _REPO_RE.search(url)
    if not m:
        return ExtractionResult(url=url, url_type="github",
                                status="error", error_msg="Could not parse owner/repo from URL")

    owner, repo = m.group(1), m.group(2).rstrip(".git")
    headers = _headers()

    try:
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers, timeout=10,
        )
        if resp.status_code == 404:
            return ExtractionResult(url=url, url_type="github",
                                    status="error", error_msg="Repository not found")
        resp.raise_for_status()
    except requests.RequestException as e:
        return ExtractionResult(url=url, url_type="github",
                                status="error", error_msg=str(e))

    meta = resp.json()
    title = meta.get("full_name", f"{owner}/{repo}")
    description = meta.get("description") or ""
    topics = ", ".join(meta.get("topics", []))
    stars = meta.get("stargazers_count", 0)
    language = meta.get("language") or ""

    readme = ""
    try:
        r = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            headers=headers, timeout=10,
        )
        if r.status_code == 200:
            readme = base64.b64decode(r.json()["content"]).decode("utf-8", errors="replace")
    except Exception:
        pass

    raw_content = (
        f"Repository: {title}\n"
        f"Description: {description}\n"
        f"Language: {language}\n"
        f"Stars: {stars}\n"
        f"Topics: {topics}\n\n"
        f"README:\n{readme}"
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
