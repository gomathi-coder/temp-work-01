"""Core ingest pipeline — ties together extraction, AI, and storage."""

from __future__ import annotations
import logging
import traceback
import time
from datetime import datetime, timezone
from linkwiki.core import database as db
from linkwiki.core import ai
from linkwiki import extractors
from linkwiki.core import vectors, linker

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ingest(
    url: str,
    source_type: str = "cli",
    source_ref: str | None = None,
    extra_tags: list[str] | None = None,
    group_name: str | None = None,
    label: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Full ingest for a single URL.

    Returns a result dict with keys:
      status  : "duplicate" | "done" | "partial" | "error" | "dry_run"
      id      : entry ID (when saved)
      entry   : full entry dict (when saved)
      error   : error message (when status == "error")
    """
    t0 = time.monotonic()
    log.info(
        "ingest started",
        extra={"url": url, "source_type": source_type, "source_ref": source_ref,
               "dry_run": dry_run, "group": group_name},
    )

    # ── Duplicate check ────────────────────────────────────────────────────
    existing_id = db.url_exists(url)
    if existing_id:
        log.info(
            "duplicate detected, skipping",
            extra={"url": url, "existing_id": existing_id},
        )
        return {"status": "duplicate", "id": existing_id, "entry": db.get_entry(existing_id)}

    # ── Extract content ────────────────────────────────────────────────────
    log.debug("dispatching to extractor", extra={"url": url})
    result = extractors.extract(url)
    log.info(
        "extraction finished",
        extra={
            "url": url,
            "url_type": result.url_type,
            "extraction_status": result.status,
            "content_chars": len(result.raw_content or ""),
            "discovered_links": len(result.discovered_links),
        },
    )

    if dry_run:
        log.info("dry run complete, not persisting", extra={"url": url})
        return {
            "status": "dry_run",
            "url_type": result.url_type,
            "title": result.title,
            "author": result.author,
            "content_length": len(result.raw_content or ""),
            "discovered_links": len(result.discovered_links),
            "extraction_status": result.status,
        }

    # ── Persist entry (status=pending) ─────────────────────────────────────
    entry_id = db.create_entry(url, result.url_type, source_type, source_ref)
    log.debug("entry created in database", extra={"url": url, "entry_id": entry_id})

    # Apply label override from file parser
    if label and not result.title:
        result.title = label

    # ── AI processing ──────────────────────────────────────────────────────
    ai_result: dict = {"summary": None, "tags": [], "entities": [], "suggested_groups": []}

    if result.raw_content:
        log.info(
            "AI processing started",
            extra={"entry_id": entry_id, "url": url, "content_chars": len(result.raw_content)},
        )
        try:
            ai_result = ai.summarise_and_tag(
                result.url_type,
                result.title,
                result.author,
                result.raw_content,
            )
            log.info(
                "AI processing complete",
                extra={
                    "entry_id": entry_id,
                    "tags_count": len(ai_result.get("tags", [])),
                    "entities_count": len(ai_result.get("entities", [])),
                    "suggested_groups": ai_result.get("suggested_groups", []),
                },
            )
        except Exception as exc:
            log.error(
                "AI processing failed",
                extra={"entry_id": entry_id, "url": url, "error": str(exc)},
            )
            db.update_entry(entry_id,
                            title=result.title,
                            author=result.author,
                            status="error",
                            error_msg=str(exc),
                            processed_at=_now())
            return {"status": "error", "id": entry_id, "error": str(exc)}
    else:
        log.debug(
            "skipping AI processing, no content available",
            extra={"entry_id": entry_id, "url": url, "extraction_status": result.status},
        )

    # ── Merge tags ─────────────────────────────────────────────────────────
    all_tags = list(dict.fromkeys(ai_result.get("tags", []) + (extra_tags or [])))

    # ── Persist full entry ─────────────────────────────────────────────────
    db.update_entry(
        entry_id,
        title=result.title,
        author=result.author,
        raw_content=result.raw_content,
        summary=ai_result.get("summary"),
        tags=all_tags,
        entities=ai_result.get("entities", []),
        discovered_links=result.discovered_links,
        status=result.status,
        processed_at=_now(),
    )
    log.debug(
        "entry persisted",
        extra={"entry_id": entry_id, "status": result.status, "tags": all_tags},
    )

    # ── Embed + auto-link ──────────────────────────────────────────────────
    try:
        vectors.embed_entry(entry_id, result.title, ai_result.get("summary"),
                            result.url_type, all_tags)
        linker.link_entry(entry_id)
        log.debug("embedding and linking complete", extra={"entry_id": entry_id})
    except Exception as exc:
        log.warning(
            "embedding/linking failed (non-blocking)",
            extra={"entry_id": entry_id, "error": str(exc)},
        )

    # ── Group assignment ───────────────────────────────────────────────────
    if group_name:
        gid = db.get_or_create_group(group_name, "manual")
        db.assign_to_group(entry_id, gid, "user")
        log.debug(
            "manual group assigned",
            extra={"entry_id": entry_id, "group": group_name, "group_id": gid},
        )

    for suggested in ai_result.get("suggested_groups", []):
        existing_group = db.get_group_by_name(suggested)
        if existing_group:
            db.assign_to_group(entry_id, existing_group["id"], "auto")
            log.debug(
                "auto group assigned",
                extra={"entry_id": entry_id, "group": suggested, "group_id": existing_group["id"]},
            )

    duration_ms = int((time.monotonic() - t0) * 1000)
    log.info(
        "ingest complete",
        extra={
            "url": url,
            "entry_id": entry_id,
            "status": result.status,
            "url_type": result.url_type,
            "duration_ms": duration_ms,
        },
    )
    return {
        "status": result.status,
        "id": entry_id,
        "entry": db.get_entry(entry_id),
    }


def process_entry(entry_id: str, url: str) -> None:
    """
    Run extraction, AI, embedding, and linking for an already-created pending entry.
    Designed to be called from a background thread — updates DB status when done.
    """
    t0 = time.monotonic()
    log.info("background process started", extra={"entry_id": entry_id, "url": url})

    try:
        result = extractors.extract(url)
        log.info(
            "background extraction finished",
            extra={"entry_id": entry_id, "url_type": result.url_type,
                   "content_chars": len(result.raw_content or "")},
        )

        ai_result: dict = {"summary": None, "tags": [], "entities": [], "suggested_groups": []}
        if result.raw_content:
            try:
                ai_result = ai.summarise_and_tag(
                    result.url_type, result.title, result.author, result.raw_content
                )
            except Exception as exc:
                log.error("AI failed in background", extra={"entry_id": entry_id, "error": str(exc)})
                db.update_entry(
                    entry_id,
                    url_type=result.url_type,
                    title=result.title,
                    author=result.author,
                    status="error",
                    error_msg=str(exc),
                    processed_at=_now(),
                )
                return

        all_tags = list(dict.fromkeys(ai_result.get("tags", [])))

        db.update_entry(
            entry_id,
            url_type=result.url_type,
            title=result.title,
            author=result.author,
            raw_content=result.raw_content,
            summary=ai_result.get("summary"),
            tags=all_tags,
            entities=ai_result.get("entities", []),
            discovered_links=result.discovered_links,
            status=result.status,
            processed_at=_now(),
        )

        try:
            vectors.embed_entry(entry_id, result.title, ai_result.get("summary"),
                                result.url_type, all_tags)
            linker.link_entry(entry_id)
        except Exception as exc:
            log.warning("embedding/linking failed (non-blocking)",
                        extra={"entry_id": entry_id, "error": str(exc)})

        for suggested in ai_result.get("suggested_groups", []):
            existing_group = db.get_group_by_name(suggested)
            if existing_group:
                db.assign_to_group(entry_id, existing_group["id"], "auto")

        duration_ms = int((time.monotonic() - t0) * 1000)
        log.info("background process complete",
                 extra={"entry_id": entry_id, "status": result.status, "duration_ms": duration_ms})

    except Exception as exc:
        log.error("background process failed",
                  extra={"entry_id": entry_id, "error": str(exc), "tb": traceback.format_exc()})
        db.update_entry(entry_id, status="error", error_msg=str(exc), processed_at=_now())
