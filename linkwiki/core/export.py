"""Export adapters — JSON, CSV, Obsidian Markdown, static HTML."""

from __future__ import annotations
import csv
import json
import re
from pathlib import Path
from linkwiki.core import database as db


def export_html(entries: list[dict], output_dir: str) -> int:
    from linkwiki.core.html_export import export_html as _export_html
    return _export_html(entries, output_dir)


def export_json(entries: list[dict], output_path: str) -> None:
    enriched = [_enrich(e) for e in entries]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"entries": enriched, "total": len(enriched)}, f, indent=2, ensure_ascii=False)


def export_csv(entries: list[dict], output_path: str) -> None:
    fields = ["id", "url", "url_type", "title", "author", "summary",
              "tags", "groups", "source_type", "status", "created_at"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for e in entries:
            row = dict(e)
            row["tags"] = ", ".join(e.get("tags", []))
            row["groups"] = ", ".join(db.get_entry_groups(e["id"]))
            writer.writerow(row)


def export_obsidian(entries: list[dict], output_dir: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Build a title → filename map for wikilinks
    title_map: dict[str, str] = {}
    for e in entries:
        title_map[e["id"]] = _safe_filename(e.get("title") or e["id"])

    for e in entries:
        enriched = _enrich(e)
        content = _to_obsidian_md(enriched, title_map)
        filename = title_map[e["id"]] + ".md"
        (out / filename).write_text(content, encoding="utf-8")


# ── Helpers ────────────────────────────────────────────────────────────────

def _enrich(entry: dict) -> dict:
    e = dict(entry)
    e["groups"] = db.get_entry_groups(entry["id"])
    related = db.get_related(entry["id"], limit=10)
    e["related"] = [{"id": r["id"], "title": r.get("title") or r["url"],
                     "link_type": r.get("link_type"), "strength": r.get("strength")}
                    for r in related]
    return e


def _safe_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip()[:80] or "untitled"


def _to_obsidian_md(entry: dict, title_map: dict[str, str]) -> str:
    tags_yaml = "\n".join(f"  - {t}" for t in entry.get("tags", []))
    entities_yaml = "\n".join(
        f'  - "{e["name"]}"' for e in entry.get("entities", [])
    )
    groups_yaml = "\n".join(f"  - {g}" for g in entry.get("groups", []))

    frontmatter = (
        "---\n"
        f"url: {entry['url']}\n"
        f"type: {entry['url_type']}\n"
        f"author: {entry.get('author') or ''}\n"
        f"status: {entry['status']}\n"
        f"created: {(entry.get('created_at') or '')[:10]}\n"
    )
    if tags_yaml:
        frontmatter += f"tags:\n{tags_yaml}\n"
    if entities_yaml:
        frontmatter += f"entities:\n{entities_yaml}\n"
    if groups_yaml:
        frontmatter += f"groups:\n{groups_yaml}\n"
    frontmatter += "---\n\n"

    title = entry.get("title") or entry["url"]
    body = f"# {title}\n\n[Source]({entry['url']})\n\n"

    if entry.get("summary"):
        body += f"## Summary\n\n{entry['summary']}\n\n"

    if entry.get("related"):
        body += "## Related\n\n"
        for r in entry["related"]:
            linked_title = title_map.get(r["id"], r["title"])
            body += f"- [[{linked_title}]]  _{r.get('link_type', '')} · {r.get('strength', 0):.2f}_\n"
        body += "\n"

    if entry.get("discovered_links"):
        body += "## Discovered Links\n\n"
        for lnk in entry["discovered_links"][:20]:
            label = lnk.get("label") or lnk["url"]
            body += f"- [{label}]({lnk['url']})\n"
        body += "\n"

    return frontmatter + body
