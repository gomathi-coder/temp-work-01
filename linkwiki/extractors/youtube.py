"""YouTube extractor — transcript via youtube-transcript-api, metadata via oEmbed + pytubefix."""

from __future__ import annotations
import logging
import re
import time
import requests
from linkwiki.extractors.result import ExtractionResult
from linkwiki.core.config import MAX_CONTENT_CHARS

log = logging.getLogger(__name__)

_URL_RE = re.compile(r'https?://[^\s\)\]\'">,]+')
_VIDEO_ID_RE = re.compile(r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})')


def _video_id(url: str) -> str | None:
    m = _VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def _oembed_meta(url: str) -> tuple[str | None, str | None]:
    """Fetch title and author via YouTube oEmbed (no API key needed)."""
    t0 = time.monotonic()
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=10,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        if r.status_code == 200:
            data = r.json()
            title, author = data.get("title"), data.get("author_name")
            log.debug(
                "oEmbed metadata fetched",
                extra={"url": url, "title": title, "author": author, "duration_ms": duration_ms},
            )
            return title, author
        log.warning(
            "oEmbed returned non-200 status",
            extra={"url": url, "status_code": r.status_code, "duration_ms": duration_ms},
        )
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        log.warning(
            "oEmbed fetch failed",
            extra={"url": url, "error": str(e), "duration_ms": duration_ms},
        )
    return None, None


def _pytube_description(url: str) -> str:
    """Try to get description from pytubefix; returns empty string on any failure."""
    t0 = time.monotonic()
    try:
        from pytubefix import YouTube  # type: ignore
        desc = YouTube(url).description or ""
        duration_ms = int((time.monotonic() - t0) * 1000)
        if desc:
            log.debug(
                "description fetched via pytubefix",
                extra={"url": url, "description_chars": len(desc), "duration_ms": duration_ms},
            )
        else:
            log.debug("pytubefix returned empty description", extra={"url": url, "duration_ms": duration_ms})
        return desc
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        log.warning(
            "pytubefix description fetch failed",
            extra={"url": url, "error": str(e), "duration_ms": duration_ms},
        )
        return ""


def _transcript(video_id: str) -> str:
    t0 = time.monotonic()
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        ytt_api = YouTubeTranscriptApi()
        fetched = ytt_api.fetch(video_id)
        transcript = " ".join([snippet.text for snippet in fetched.snippets])
        duration_ms = int((time.monotonic() - t0) * 1000)
        log.info(
            "transcript fetched",
            extra={
                "video_id": video_id,
                "transcript_chars": len(transcript),
                "snippet_count": len(fetched.snippets),
                "duration_ms": duration_ms,
            },
        )
        return transcript
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        log.warning(
            "transcript unavailable",
            extra={"video_id": video_id, "error": str(e), "duration_ms": duration_ms},
        )
        return ""


def _find_urls(text: str) -> list[dict]:
    return [
        {"url": u, "label": "", "context": "in YouTube description"}
        for u in _URL_RE.findall(text)
        if not u.startswith("https://www.youtube.com")
    ]


def extract(url: str) -> ExtractionResult:
    t0 = time.monotonic()
    log.info("extraction started", extra={"url": url, "extractor": "youtube"})

    vid = _video_id(url)
    if not vid:
        log.error("could not parse video ID from URL", extra={"url": url})
        return ExtractionResult(url=url, url_type="youtube",
                                status="error", error_msg="Could not parse video ID")

    log.debug("video ID parsed", extra={"url": url, "video_id": vid})

    title, author = _oembed_meta(url)
    description = _pytube_description(url)
    transcript = _transcript(vid)

    parts: list[str] = []
    if description:
        parts.append(f"Description:\n{description}")
    if transcript:
        parts.append(f"Transcript:\n{transcript}")

    raw_content = "\n\n".join(parts)
    total_ms = int((time.monotonic() - t0) * 1000)

    if not raw_content:
        log.warning(
            "extraction yielded no content",
            extra={"url": url, "video_id": vid, "has_transcript": False,
                   "has_description": False, "duration_ms": total_ms},
        )
        return ExtractionResult(url=url, url_type="youtube", title=title,
                                author=author, status="partial",
                                error_msg="No transcript or description available")

    log.info(
        "extraction complete",
        extra={
            "url": url,
            "video_id": vid,
            "status": "done",
            "has_transcript": bool(transcript),
            "has_description": bool(description),
            "content_chars": len(raw_content),
            "discovered_count": len(_find_urls(description)),
            "duration_ms": total_ms,
        },
    )
    return ExtractionResult(
        url=url,
        url_type="youtube",
        title=title,
        author=author,
        raw_content=raw_content[:MAX_CONTENT_CHARS],
        discovered_links=_find_urls(description)[:40],
        status="done",
    )
