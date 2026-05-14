"""Generic web extractor — trafilatura for article text, BeautifulSoup for links."""

from __future__ import annotations
import requests
import trafilatura  # type: ignore
from bs4 import BeautifulSoup
from linkwiki.extractors.result import ExtractionResult
from linkwiki.core.config import MAX_CONTENT_CHARS

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LinkWiki/1.0; +https://github.com/linkwiki)"}


def _og(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", property=f"og:{prop}") or soup.find("meta", attrs={"name": prop})
    return tag.get("content") if tag else None


def _page_title(soup: BeautifulSoup) -> str | None:
    og = _og(soup, "title")
    if og:
        return og
    return soup.title.string.strip() if soup.title and soup.title.string else None


def _page_author(soup: BeautifulSoup) -> str | None:
    for name in ("author", "article:author", "twitter:creator"):
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", property=name)
        if tag and tag.get("content"):
            return tag["content"]
    return None


def _discover_links(soup: BeautifulSoup) -> list[dict]:
    seen: set[str] = set()
    links: list[dict] = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if href.startswith("http") and href not in seen:
            seen.add(href)
            links.append({
                "url": href,
                "label": a.get_text(strip=True)[:100],
                "context": "in page body",
            })
    return links[:60]


def extract(url: str) -> ExtractionResult:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except requests.RequestException as e:
        return ExtractionResult(url=url, url_type="web",
                                status="error", error_msg=str(e))

    soup = BeautifulSoup(html, "html.parser")
    title = _page_title(soup)
    author = _page_author(soup)
    discovered = _discover_links(soup)

    content = trafilatura.extract(html, include_links=False, include_comments=False)

    if not content:
        # Paywall or JS-rendered — store metadata only
        description = _og(soup, "description") or ""
        return ExtractionResult(
            url=url, url_type="web", title=title, author=author,
            raw_content=description or None,
            discovered_links=discovered,
            status="partial",
            error_msg="Main content could not be extracted (possible paywall or JS page)",
        )

    return ExtractionResult(
        url=url,
        url_type="web",
        title=title,
        author=author,
        raw_content=content[:MAX_CONTENT_CHARS],
        discovered_links=discovered,
        status="done",
    )
