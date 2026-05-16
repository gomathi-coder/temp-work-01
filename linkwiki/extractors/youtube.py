"""YouTube extractor — transcript via youtube-transcript-api, metadata via oEmbed + pytubefix."""

from __future__ import annotations
import re
import requests
from linkwiki.extractors.result import ExtractionResult
from linkwiki.core.config import MAX_CONTENT_CHARS

_URL_RE = re.compile(r'https?://[^\s\)\]\'">,]+')
_VIDEO_ID_RE = re.compile(r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})')


def _video_id(url: str) -> str | None:
    m = _VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def _oembed_meta(url: str) -> tuple[str | None, str | None]:
    """Fetch title and author via YouTube oEmbed (no API key needed)."""
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("title"), data.get("author_name")
    except Exception:
        pass
    return None, None


def _pytube_description(url: str) -> str:
    """Try to get description from pytubefix; returns empty string on any failure."""
    try:
        from pytubefix import YouTube  # type: ignore
        return YouTube(url).description or ""
    except Exception:
        return ""


def _transcript(video_id: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        ytt_api = YouTubeTranscriptApi()
        fetched = ytt_api.fetch(video_id)
        return " ".join([snippet.text for snippet in fetched.snippets])
    except Exception:
        return ""


def _find_urls(text: str) -> list[dict]:
    return [
        {"url": u, "label": "", "context": "in YouTube description"}
        for u in _URL_RE.findall(text)
        if not u.startswith("https://www.youtube.com")
    ]


def extract(url: str) -> ExtractionResult:
    vid = _video_id(url)
    if not vid:
        return ExtractionResult(url=url, url_type="youtube",
                                status="error", error_msg="Could not parse video ID")

    title, author = _oembed_meta(url)
    description = _pytube_description(url)
    transcript = _transcript(vid)

    parts: list[str] = []
    if description:
        parts.append(f"Description:\n{description}")
    if transcript:
        parts.append(f"Transcript:\n{transcript}")

    raw_content = "\n\n".join(parts)
    if not raw_content:
        return ExtractionResult(url=url, url_type="youtube", title=title,
                                author=author, status="partial",
                                error_msg="No transcript or description available")

    return ExtractionResult(
        url=url,
        url_type="youtube",
        title=title,
        author=author,
        raw_content=raw_content[:MAX_CONTENT_CHARS],
        discovered_links=_find_urls(description)[:40],
        status="done",
    )
