"""Core ingest pipeline — ties together extraction, AI, and storage."""

from __future__ import annotations
from datetime import datetime, timezone
from linkwiki.core import database as db
from linkwiki.core import ai
from linkwiki import extractors
from linkwiki.core import vectors, linker


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
    # ── Duplicate check ────────────────────────────────────────────────────
    existing_id = db.url_exists(url)
    if existing_id:
        return {"status": "duplicate", "id": existing_id, "entry": db.get_entry(existing_id)}

    # ── Extract content ────────────────────────────────────────────────────
    result = extractors.extract(url)

    if dry_run:
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

    # Apply label override from file parser
    if label and not result.title:
        result.title = label

    # ── AI processing ──────────────────────────────────────────────────────
    ai_result: dict = {"summary": None, "tags": [], "entities": [], "suggested_groups": []}

    if result.raw_content:
        try:
            ai_result = ai.summarise_and_tag(
                result.url_type,
                result.title,
                result.author,
                result.raw_content,
            )
        except Exception as exc:
            db.update_entry(entry_id,
                            title=result.title,
                            author=result.author,
                            status="error",
                            error_msg=str(exc),
                            processed_at=_now())
            return {"status": "error", "id": entry_id, "error": str(exc)}

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

    # ── Embed + auto-link ──────────────────────────────────────────────────
    try:
        vectors.embed_entry(entry_id, result.title, ai_result.get("summary"),
                            result.url_type, all_tags)
        linker.link_entry(entry_id)
    except Exception:
        pass  # vector/link failures never block the ingest

    # ── Group assignment ───────────────────────────────────────────────────
    if group_name:
        gid = db.get_or_create_group(group_name, "manual")
        db.assign_to_group(entry_id, gid, "user")

    for suggested in ai_result.get("suggested_groups", []):
        # Only auto-assign to groups that already exist
        existing_group = db.get_group_by_name(suggested)
        if existing_group:
            db.assign_to_group(entry_id, existing_group["id"], "auto")

    return {
        "status": result.status,
        "id": entry_id,
        "entry": db.get_entry(entry_id),
    }
