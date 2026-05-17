"""Parse a links.txt file into a list of URL records."""

from __future__ import annotations
from pathlib import Path


def parse(file_path: str | Path) -> list[dict]:
    """
    Parse a links file. Each non-blank, non-comment line has the form:

        <url>  [| tags: t1, t2]  [| group: Name]  [| label: Title]

    Returns a list of dicts: {url, tags, group, label, line_num}.
    """
    results: list[dict] = []
    with open(file_path, encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            url = parts[0].strip()
            if not url.startswith("http"):
                continue

            tags: list[str] = []
            group: str | None = None
            label: str | None = None

            for part in parts[1:]:
                if part.startswith("tags:"):
                    tags = [t.strip() for t in part[5:].split(",") if t.strip()]
                elif part.startswith("group:"):
                    group = part[6:].strip() or None
                elif part.startswith("label:"):
                    label = part[6:].strip() or None

            results.append({
                "url": url,
                "tags": tags,
                "group": group,
                "label": label,
                "line_num": line_num,
            })

    return results
