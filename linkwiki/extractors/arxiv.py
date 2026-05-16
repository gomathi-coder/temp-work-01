"""arXiv extractor — abstract + authors via the arXiv Atom API."""

from __future__ import annotations
import logging
import re
import time
import xml.etree.ElementTree as ET
import requests
from linkwiki.extractors.result import ExtractionResult

log = logging.getLogger(__name__)

_ID_RE = re.compile(r'arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+(?:v\d+)?)')
_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _arxiv_id(url: str) -> str | None:
    m = _ID_RE.search(url)
    return m.group(1) if m else None


def extract(url: str) -> ExtractionResult:
    log.info("extraction started", extra={"url": url, "extractor": "arxiv"})
    t0 = time.monotonic()

    arxiv_id = _arxiv_id(url)
    if not arxiv_id:
        log.error("could not parse arXiv ID from URL", extra={"url": url})
        return ExtractionResult(url=url, url_type="arxiv",
                                status="error", error_msg="Could not parse arXiv ID from URL")

    log.debug("arXiv ID parsed", extra={"url": url, "arxiv_id": arxiv_id})

    try:
        resp = requests.get(
            f"http://export.arxiv.org/api/query?id_list={arxiv_id}",
            timeout=10,
        )
        api_ms = int((time.monotonic() - t0) * 1000)
        resp.raise_for_status()
        log.debug(
            "arXiv API response received",
            extra={"url": url, "arxiv_id": arxiv_id,
                   "status_code": resp.status_code, "duration_ms": api_ms},
        )
    except requests.RequestException as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        log.error(
            "arXiv API request failed",
            extra={"url": url, "arxiv_id": arxiv_id,
                   "error": str(e), "duration_ms": duration_ms},
        )
        return ExtractionResult(url=url, url_type="arxiv",
                                status="error", error_msg=str(e))

    root = ET.fromstring(resp.text)
    entry = root.find("atom:entry", _NS)
    if entry is None:
        duration_ms = int((time.monotonic() - t0) * 1000)
        log.error(
            "paper not found on arXiv",
            extra={"url": url, "arxiv_id": arxiv_id, "duration_ms": duration_ms},
        )
        return ExtractionResult(url=url, url_type="arxiv",
                                status="error", error_msg="Paper not found on arXiv")

    title_el = entry.find("atom:title", _NS)
    summary_el = entry.find("atom:summary", _NS)
    title = title_el.text.strip().replace("\n", " ") if title_el is not None else None
    abstract = summary_el.text.strip() if summary_el is not None else ""

    authors = [
        a.find("atom:name", _NS).text
        for a in entry.findall("atom:author", _NS)
        if a.find("atom:name", _NS) is not None
    ]

    raw_content = (
        f"Title: {title}\n"
        f"Authors: {', '.join(authors)}\n\n"
        f"Abstract:\n{abstract}"
    )

    total_ms = int((time.monotonic() - t0) * 1000)
    log.info(
        "extraction complete",
        extra={
            "url": url, "status": "done",
            "arxiv_id": arxiv_id,
            "title": title,
            "author_count": len(authors),
            "abstract_chars": len(abstract),
            "duration_ms": total_ms,
        },
    )
    return ExtractionResult(
        url=url,
        url_type="arxiv",
        title=title,
        author=", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
        raw_content=raw_content,
        discovered_links=[],
        status="done",
    )
