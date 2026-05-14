"""Static HTML export — self-contained wiki with search and group navigation."""

from __future__ import annotations
import re
import html as html_lib
from pathlib import Path
from linkwiki.core import database as db

# ── Shared assets ──────────────────────────────────────────────────────────

_CSS = """
:root {
  --bg:         #0d1117;
  --surface:    #161b22;
  --surface2:   #21262d;
  --border:     #30363d;
  --text:       #c9d1d9;
  --text-muted: #8b949e;
  --heading:    #f0f6fc;
  --link:       #58a6ff;
  --link-hover: #79c0ff;
  --tag-bg:     #1f3855;
  --tag-text:   #79c0ff;
  --ent-bg:     #2d1f4e;
  --ent-text:   #c4b5fd;
  --green:      #3fb950;
  --yellow:     #d29922;
  --red:        #f85149;
  --orange:     #e3b341;
  --purple:     #bc8cff;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--text);
  line-height: 1.6; font-size: 15px;
}
a { color: var(--link); text-decoration: none; }
a:hover { color: var(--link-hover); text-decoration: underline; }

/* Layout */
.container { max-width: 1100px; margin: 0 auto; padding: 0 20px; }
.layout { display: grid; grid-template-columns: 220px 1fr; gap: 24px;
          align-items: start; margin-top: 24px; }
@media (max-width: 720px) { .layout { grid-template-columns: 1fr; } }

/* Header */
header {
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: 14px 0; position: sticky; top: 0; z-index: 100;
}
.header-inner {
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
}
.site-title { color: var(--heading); font-weight: 700; font-size: 1.1rem; }
.site-title span { color: var(--link); }
.header-search {
  flex: 1; min-width: 200px; max-width: 420px;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 6px; padding: 6px 12px; color: var(--text);
  font-size: 14px;
}
.header-search:focus { outline: none; border-color: var(--link); }
.header-meta { margin-left: auto; color: var(--text-muted); font-size: 13px; }

/* Sidebar */
.sidebar { position: sticky; top: 72px; }
.sidebar-section { margin-bottom: 20px; }
.sidebar-title {
  font-size: 11px; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px;
}
.group-btn {
  display: block; width: 100%; text-align: left;
  background: none; border: none; cursor: pointer;
  color: var(--text); padding: 5px 10px; border-radius: 5px;
  font-size: 13px; margin-bottom: 2px;
}
.group-btn:hover { background: var(--surface2); color: var(--heading); }
.group-btn.active { background: var(--tag-bg); color: var(--tag-text); }
.group-btn .count {
  float: right; color: var(--text-muted); font-size: 12px;
}
.filter-link {
  display: block; padding: 5px 10px; border-radius: 5px;
  font-size: 13px; margin-bottom: 2px; color: var(--text);
}
.filter-link:hover { background: var(--surface2); text-decoration: none; }

/* Entry grid */
#entries-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
  padding-bottom: 40px;
}
.entry-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px;
  transition: border-color .15s;
}
.entry-card:hover { border-color: var(--link); }
.card-header { display: flex; align-items: flex-start;
               justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.card-title {
  font-weight: 600; color: var(--heading); font-size: 14px; line-height: 1.4;
}
.card-title a { color: var(--heading); }
.card-title a:hover { color: var(--link-hover); }
.card-summary { font-size: 13px; color: var(--text-muted);
                margin-bottom: 10px; line-height: 1.5;
                display: -webkit-box; -webkit-line-clamp: 3;
                -webkit-box-orient: vertical; overflow: hidden; }
.card-tags { display: flex; flex-wrap: wrap; gap: 5px; }

/* Badges & tags */
.badge {
  display: inline-block; padding: 2px 7px; border-radius: 4px;
  font-size: 11px; font-weight: 600; letter-spacing: .03em;
  white-space: nowrap; flex-shrink: 0;
}
.badge-youtube { background: #3d1a1a; color: #f97583; }
.badge-github  { background: #1a2d1a; color: var(--green); }
.badge-web     { background: #1a2840; color: var(--link); }
.badge-arxiv   { background: #3d2e00; color: var(--orange); }
.badge-default { background: var(--surface2); color: var(--text-muted); }
.badge-done    { background: #1a2d1a; color: var(--green); }
.badge-partial { background: #3d2e00; color: var(--yellow); }
.badge-error   { background: #3d1a1a; color: var(--red); }

.tag {
  background: var(--tag-bg); color: var(--tag-text);
  padding: 2px 8px; border-radius: 12px; font-size: 12px;
  cursor: pointer; border: none;
}
.tag:hover { background: #2a4e75; text-decoration: none; }
.entity-tag {
  background: var(--ent-bg); color: var(--ent-text);
  padding: 2px 8px; border-radius: 12px; font-size: 12px;
}

/* Entry detail page */
.entry-page { max-width: 800px; margin: 32px auto; padding: 0 20px 60px; }
.entry-page h1 { color: var(--heading); font-size: 1.5rem;
                  line-height: 1.4; margin-bottom: 12px; }
.entry-meta { display: flex; flex-wrap: wrap; gap: 8px;
              align-items: center; margin-bottom: 20px; }
.entry-url { color: var(--text-muted); font-size: 13px;
             word-break: break-all; margin-bottom: 16px; }
.section { margin-bottom: 24px; }
.section-title {
  font-size: 12px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .06em; color: var(--text-muted);
  margin-bottom: 10px; padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}
.summary-text { color: var(--text); line-height: 1.7; font-size: 15px; }
.related-list { list-style: none; }
.related-list li {
  padding: 8px 0; border-bottom: 1px solid var(--border);
  display: flex; align-items: baseline; gap: 10px;
}
.related-list li:last-child { border-bottom: none; }
.link-type-badge {
  font-size: 11px; padding: 1px 6px; border-radius: 3px; white-space: nowrap;
}
.lt-semantic    { background: #2d1f4e; color: var(--purple); }
.lt-shared_tag  { background: var(--tag-bg); color: var(--tag-text); }
.lt-shared_entity { background: var(--ent-bg); color: var(--ent-text); }
.lt-discovered  { background: #1a2d1a; color: var(--green); }
.strength { color: var(--text-muted); font-size: 12px; }
.disc-list { list-style: none; }
.disc-list li { padding: 5px 0; border-bottom: 1px solid var(--border);
                font-size: 13px; }
.disc-list li:last-child { border-bottom: none; }

/* Group page */
.group-page { max-width: 900px; margin: 32px auto; padding: 0 20px 60px; }
.group-page h1 { color: var(--heading); font-size: 1.4rem; margin-bottom: 8px; }
.entry-table { width: 100%; border-collapse: collapse; margin-top: 16px; }
.entry-table th {
  text-align: left; padding: 8px 12px; font-size: 12px;
  text-transform: uppercase; letter-spacing: .05em;
  color: var(--text-muted); border-bottom: 1px solid var(--border);
}
.entry-table td { padding: 10px 12px; border-bottom: 1px solid var(--border);
                  font-size: 14px; vertical-align: top; }
.entry-table tr:hover td { background: var(--surface2); }

/* Misc */
.back-link { display: inline-flex; align-items: center; gap: 5px;
             color: var(--text-muted); font-size: 13px; margin-bottom: 20px; }
.back-link:hover { color: var(--link); text-decoration: none; }
.no-results { text-align: center; color: var(--text-muted);
              padding: 60px 0; display: none; }
"""

_SEARCH_JS = """
const cards = document.querySelectorAll('.entry-card');
const noResults = document.getElementById('no-results');
let activeGroup = null;

function applyFilters() {
  const q = (document.getElementById('search-input')?.value || '').toLowerCase();
  let shown = 0;
  cards.forEach(card => {
    const matchQ = !q || card.dataset.search.includes(q);
    const matchG = !activeGroup || card.dataset.groups.includes(activeGroup);
    const show = matchQ && matchG;
    card.style.display = show ? '' : 'none';
    if (show) shown++;
  });
  if (noResults) noResults.style.display = shown === 0 ? 'block' : 'none';
}

document.getElementById('search-input')?.addEventListener('input', applyFilters);

document.querySelectorAll('.group-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const g = btn.dataset.group;
    activeGroup = (activeGroup === g) ? null : g;
    document.querySelectorAll('.group-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.group === activeGroup));
    applyFilters();
  });
});

document.querySelectorAll('.tag-filter').forEach(t => {
  t.addEventListener('click', e => {
    e.preventDefault();
    const q = t.dataset.tag;
    const inp = document.getElementById('search-input');
    if (inp) { inp.value = q; applyFilters(); }
  });
});
"""


# ── Public entry point ─────────────────────────────────────────────────────

def export_html(entries: list[dict], output_dir: str) -> int:
    out = Path(output_dir)
    (out / "entries").mkdir(parents=True, exist_ok=True)
    (out / "groups").mkdir(parents=True, exist_ok=True)

    # Enrich each entry with groups and related
    enriched = []
    for e in entries:
        ec = dict(e)
        ec["groups"] = db.get_entry_groups(e["id"])
        ec["related"] = db.get_related(e["id"], limit=8)
        enriched.append(ec)

    groups = db.list_groups()

    # Write files
    _write_index(enriched, groups, out)
    for e in enriched:
        _write_entry_page(e, out)
    for g in groups:
        g_entries = [e for e in enriched if g["name"] in e["groups"]]
        _write_group_page(g, g_entries, out)

    return 1 + len(enriched) + len(groups)


# ── Index page ─────────────────────────────────────────────────────────────

def _write_index(entries: list[dict], groups: list[dict], out: Path) -> None:
    total = len(entries)
    by_type: dict[str, int] = {}
    for e in entries:
        by_type[e["url_type"]] = by_type.get(e["url_type"], 0) + 1

    type_summary = " · ".join(f"{k} {v}" for k, v in sorted(by_type.items()))

    sidebar_groups = "\n".join(
        f'<button class="group-btn" data-group="{_esc(g["name"])}">'
        f'{_esc(g["name"])} <span class="count">{g["entry_count"]}</span></button>'
        for g in groups
    )

    cards_html = "\n".join(_entry_card(e) for e in entries)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LinkWiki</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <div class="container">
    <div class="header-inner">
      <div class="site-title">Link<span>Wiki</span></div>
      <input id="search-input" class="header-search"
             placeholder="Search title, summary, tags…" autocomplete="off">
      <div class="header-meta">{total} entries · {type_summary}</div>
    </div>
  </div>
</header>

<div class="container">
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-section">
        <div class="sidebar-title">Groups</div>
        <button class="group-btn" data-group="">All</button>
        {sidebar_groups}
      </div>
      <div class="sidebar-section">
        <div class="sidebar-title">Type</div>
        {"".join(
            f'<a class="filter-link" href="#" onclick="filterType(\'{k}\');return false">'
            f'{k} <span style="float:right;color:var(--text-muted)">{v}</span></a>'
            for k, v in sorted(by_type.items())
        )}
      </div>
    </aside>

    <main>
      <div id="entries-grid">{cards_html}</div>
      <div id="no-results" class="no-results">No entries match your search.</div>
    </main>
  </div>
</div>

<script>
{_SEARCH_JS}
function filterType(t) {{
  const inp = document.getElementById('search-input');
  if (inp) {{ inp.value = t; applyFilters(); }}
}}
</script>
</body>
</html>"""

    (out / "index.html").write_text(html, encoding="utf-8")


def _entry_card(e: dict) -> str:
    title = _esc(e.get("title") or e["url"])
    summary = _esc((e.get("summary") or "")[:200])
    tags_html = " ".join(
        f'<button class="tag tag-filter" data-tag="{_esc(t)}">{_esc(t)}</button>'
        for t in e["tags"][:6]
    )
    type_badge = _type_badge(e["url_type"])
    search_data = " ".join(filter(None, [
        (e.get("title") or "").lower(),
        (e.get("summary") or "").lower(),
        " ".join(e["tags"]),
        " ".join(ent.get("name", "") for ent in e.get("entities", [])),
    ]))
    groups_data = "|".join(e.get("groups", []))
    entry_url = f"entries/{e['id']}.html"

    return f"""<div class="entry-card"
     data-search="{_esc(search_data)}"
     data-groups="{_esc(groups_data)}">
  <div class="card-header">
    <div class="card-title"><a href="{entry_url}">{title}</a></div>
    {type_badge}
  </div>
  <div class="card-summary">{summary}</div>
  <div class="card-tags">{tags_html}</div>
</div>"""


# ── Entry detail page ──────────────────────────────────────────────────────

def _write_entry_page(e: dict, out: Path) -> None:
    title = _esc(e.get("title") or e["url"])
    meta_badges = _type_badge(e["url_type"])
    if e.get("author"):
        meta_badges += f' <span class="badge badge-default">{_esc(e["author"])}</span>'
    meta_badges += f' <span class="badge badge-{e["status"]}">{e["status"]}</span>'
    created = (e.get("created_at") or "")[:10]
    if created:
        meta_badges += f' <span style="color:var(--text-muted);font-size:13px">{created}</span>'

    summary_section = ""
    if e.get("summary"):
        summary_section = f"""<div class="section">
  <div class="section-title">Summary</div>
  <p class="summary-text">{_esc(e["summary"])}</p>
</div>"""

    tags_section = ""
    if e["tags"]:
        tags_html = " ".join(
            f'<a href="../index.html" class="tag">{_esc(t)}</a>'
            for t in e["tags"]
        )
        tags_section = f"""<div class="section">
  <div class="section-title">Tags</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px">{tags_html}</div>
</div>"""

    entities_section = ""
    if e.get("entities"):
        ents_html = "".join(
            f'<span class="entity-tag" title="{_esc(ent.get("description",""))}">'
            f'{_esc(ent["name"])} <span style="opacity:.6;font-size:11px">({_esc(ent.get("type",""))})</span>'
            f'</span> '
            for ent in e["entities"]
        )
        entities_section = f"""<div class="section">
  <div class="section-title">Entities</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px">{ents_html}</div>
</div>"""

    groups_section = ""
    if e.get("groups"):
        groups_html = " ".join(
            f'<a href="../groups/{_safe_fname(g)}.html" '
            f'style="background:var(--surface2);padding:3px 10px;border-radius:5px;'
            f'font-size:13px;color:var(--text)">{_esc(g)}</a>'
            for g in e["groups"]
        )
        groups_section = f"""<div class="section">
  <div class="section-title">Groups</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px">{groups_html}</div>
</div>"""

    related_section = ""
    if e.get("related"):
        items = ""
        for r in e["related"]:
            lt = r.get("link_type", "")
            st = r.get("strength", 0)
            r_title = _esc(r.get("title") or r["url"])
            items += (
                f'<li>'
                f'<span class="link-type-badge lt-{lt}">{lt}</span>'
                f'<a href="{r["id"]}.html">{r_title}</a>'
                f'<span class="strength">{st:.2f}</span>'
                f'</li>\n'
            )
        related_section = f"""<div class="section">
  <div class="section-title">Related ({len(e["related"])})</div>
  <ul class="related-list">{items}</ul>
</div>"""

    discovered_section = ""
    disc = e.get("discovered_links", [])
    if disc:
        items = "".join(
            f'<li><a href="{_esc(lnk["url"])}" target="_blank" rel="noopener">'
            f'{_esc(lnk.get("label") or lnk["url"][:80])}</a></li>\n'
            for lnk in disc[:30]
        )
        more = f'<li style="color:var(--text-muted);font-size:13px">… and {len(disc)-30} more</li>' if len(disc) > 30 else ""
        discovered_section = f"""<div class="section">
  <div class="section-title">Links found in content ({len(disc)})</div>
  <ul class="disc-list">{items}{more}</ul>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — LinkWiki</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <div class="container">
    <div class="header-inner">
      <a class="site-title" href="../index.html">Link<span>Wiki</span></a>
    </div>
  </div>
</header>
<div class="entry-page">
  <a class="back-link" href="../index.html">← All entries</a>
  <h1>{title}</h1>
  <div class="entry-meta">{meta_badges}</div>
  <div class="entry-url">
    <a href="{_esc(e['url'])}" target="_blank" rel="noopener">{_esc(e['url'])}</a>
  </div>
  {summary_section}
  {tags_section}
  {entities_section}
  {groups_section}
  {related_section}
  {discovered_section}
</div>
</body>
</html>"""

    (out / "entries" / f"{e['id']}.html").write_text(html, encoding="utf-8")


# ── Group page ─────────────────────────────────────────────────────────────

def _write_group_page(group: dict, entries: list[dict], out: Path) -> None:
    name = _esc(group["name"])
    desc = _esc(group.get("description") or "")
    gtype = _esc(group.get("group_type", ""))

    rows = ""
    for e in entries:
        title = _esc(e.get("title") or e["url"])
        tags = " ".join(
            f'<span class="tag" style="cursor:default">{_esc(t)}</span>'
            for t in e["tags"][:4]
        )
        rows += (
            f'<tr>'
            f'<td>{_type_badge(e["url_type"])}</td>'
            f'<td><a href="../entries/{e["id"]}.html">{title}</a></td>'
            f'<td>{tags}</td>'
            f'<td style="color:var(--text-muted);font-size:12px">'
            f'{(e.get("created_at") or "")[:10]}</td>'
            f'</tr>\n'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — LinkWiki</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <div class="container">
    <div class="header-inner">
      <a class="site-title" href="../index.html">Link<span>Wiki</span></a>
    </div>
  </div>
</header>
<div class="group-page">
  <a class="back-link" href="../index.html">← All entries</a>
  <h1>{name}</h1>
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:16px">
    <span class="badge badge-default">{gtype}</span>
    <span style="color:var(--text-muted);font-size:13px">{len(entries)} entries</span>
  </div>
  {f'<p style="color:var(--text-muted);margin-bottom:16px">{desc}</p>' if desc else ''}
  <table class="entry-table">
    <thead>
      <tr>
        <th>Type</th><th>Title</th><th>Tags</th><th>Added</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</div>
</body>
</html>"""

    fname = _safe_fname(group["name"])
    (out / "groups" / f"{fname}.html").write_text(html, encoding="utf-8")


# ── Utilities ──────────────────────────────────────────────────────────────

def _esc(text: str | None) -> str:
    return html_lib.escape(str(text or ""), quote=True)


def _safe_fname(name: str) -> str:
    return re.sub(r'[^\w\-]', '_', name)[:60]


def _type_badge(url_type: str) -> str:
    cls = f"badge-{url_type}" if url_type in ("youtube", "github", "web", "arxiv") else "badge-default"
    return f'<span class="badge {cls}">{_esc(url_type)}</span>'
