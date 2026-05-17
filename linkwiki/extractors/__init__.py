"""URL router — delegates to the right extractor based on the URL."""

from __future__ import annotations
from urllib.parse import urlparse
from linkwiki.extractors.result import ExtractionResult


def extract(url: str) -> ExtractionResult:
    host = urlparse(url).netloc.lower()

    if "youtube.com" in host or "youtu.be" in host:
        from linkwiki.extractors.youtube import extract as _extract
    elif "github.com" in host:
        from linkwiki.extractors.github import extract as _extract
    elif "arxiv.org" in host:
        from linkwiki.extractors.arxiv import extract as _extract
    else:
        from linkwiki.extractors.web import extract as _extract

    return _extract(url)
