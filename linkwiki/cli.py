"""LinkWiki CLI — all commands."""

from __future__ import annotations
import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console

# Force UTF-8 output on Windows to support Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from linkwiki.core import database as db
from linkwiki.core import pipeline, file_parser, vectors, linker
from linkwiki.core.logging_config import setup_logging
from linkwiki.core.config import LOG_DIR, LOG_LEVEL

console = Console()
err = Console(stderr=True, style="bold red")


# ── Helpers ────────────────────────────────────────────────────────────────

def _require_db() -> None:
    db.init_db()


def _status_style(status: str) -> str:
    return {"done": "green", "partial": "yellow", "error": "red", "pending": "dim"}.get(status, "white")


def _print_entry_row(entry: dict) -> None:
    tags = ", ".join(entry["tags"][:5])
    if len(entry["tags"]) > 5:
        tags += f" +{len(entry['tags']) - 5}"
    console.print(
        f"  [bold cyan]{entry['id']}[/]  "
        f"[dim]{entry['url_type']:8}[/]  "
        f"{entry.get('title') or entry['url'][:60]}  "
        f"[dim]{tags}[/]"
    )


def _print_entry_detail(entry: dict) -> None:
    groups = db.get_entry_groups(entry["id"])

    title = entry.get("title") or entry["url"]
    header = Text(title, style="bold white")

    lines: list[str] = [
        f"[dim]ID[/]        {entry['id']}",
        f"[dim]URL[/]       {entry['url']}",
        f"[dim]Type[/]      {entry['url_type']}",
    ]
    if entry.get("author"):
        lines.append(f"[dim]Author[/]    {entry['author']}")
    lines.append(f"[dim]Status[/]    [{_status_style(entry['status'])}]{entry['status']}[/]")
    lines.append(f"[dim]Added[/]     {entry.get('created_at', '')[:10]}")

    if entry.get("summary"):
        lines += ["", "[bold]Summary[/]", f"  {entry['summary']}"]

    if entry["tags"]:
        lines += ["", "[bold]Tags[/]", "  " + "  ".join(f"[cyan]{t}[/]" for t in entry["tags"])]

    if entry["entities"]:
        lines += ["", "[bold]Entities[/]"]
        for e in entry["entities"]:
            lines.append(f"  [yellow]{e['name']}[/] [dim]({e.get('type', '')})[/]  {e.get('description', '')}")

    if groups:
        lines += ["", "[bold]Groups[/]", "  " + "  ".join(f"[magenta]{g}[/]" for g in groups)]

    if entry["discovered_links"]:
        lines += ["", f"[bold]Discovered links[/]  [dim]({len(entry['discovered_links'])} found)[/]"]
        for lnk in entry["discovered_links"][:5]:
            label = f"  {lnk.get('label') or ''}"
            lines.append(f"  [blue]{lnk['url']}[/]{label}")
        if len(entry["discovered_links"]) > 5:
            lines.append(f"  [dim]… and {len(entry['discovered_links']) - 5} more[/]")

    if entry.get("error_msg"):
        lines += ["", f"[red]Error: {entry['error_msg']}[/]"]

    console.print(Panel("\n".join(lines), title=header, border_style="cyan", padding=(1, 2)))


# ── CLI root ───────────────────────────────────────────────────────────────

@click.group()
@click.version_option("0.1.0", prog_name="linkwiki")
def cli() -> None:
    """LinkWiki — personal knowledge graph for URLs."""
    setup_logging(LOG_DIR, LOG_LEVEL)


# ── add ────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("url")
@click.option("--group", default=None, help="Assign to a named group (created if needed).")
@click.option("--tag", "tags", multiple=True, help="Extra tag(s) to add (repeatable).")
@click.option("--dry-run", is_flag=True, help="Preview extraction without saving.")
def add(url: str, group: str | None, tags: tuple, dry_run: bool) -> None:
    """Ingest a single URL into the knowledge base."""
    _require_db()

    with console.status(f"[cyan]Processing {url[:60]}…[/]"):
        result = pipeline.ingest(
            url,
            source_type="cli",
            extra_tags=list(tags),
            group_name=group,
            dry_run=dry_run,
        )

    status = result["status"]

    if status == "duplicate":
        console.print(f"[yellow]⚠  Already in DB[/]  [dim]{result['id']}[/]  {url}")
        return

    if status == "dry_run":
        console.print(Panel(
            f"[bold]URL[/]         {url}\n"
            f"[bold]Detected type[/] {result['url_type']}\n"
            f"[bold]Title[/]       {result.get('title') or '(none)'}\n"
            f"[bold]Author[/]      {result.get('author') or '(none)'}\n"
            f"[bold]Content[/]     {result['content_length']:,} chars\n"
            f"[bold]Links found[/] {result['discovered_links']}\n"
            f"[bold]Extraction[/]  {result['extraction_status']}",
            title="[bold]Dry run — nothing saved[/]",
            border_style="yellow",
        ))
        return

    if status == "error":
        err.print(f"✘  Error processing {url}: {result.get('error')}")
        sys.exit(1)

    entry = result["entry"]
    groups_assigned = db.get_entry_groups(entry["id"])

    icon = "✔" if status == "done" else "⚠"
    color = "green" if status == "done" else "yellow"
    console.print(f"\n[{color}]{icon}  Added[/]  [bold cyan]{entry['id']}[/]")
    console.print(f"  [dim]Title[/]    {entry.get('title') or '(no title)'}")
    console.print(f"  [dim]Type[/]     {entry['url_type']}")
    if entry["tags"]:
        console.print(f"  [dim]Tags[/]     {', '.join(entry['tags'])}")
    if entry["entities"]:
        ents = ", ".join(f"{e['name']} ({e.get('type','')})" for e in entry["entities"][:4])
        console.print(f"  [dim]Entities[/] {ents}")
    if entry.get("summary"):
        summary = entry["summary"]
        short = summary[:200] + "…" if len(summary) > 200 else summary
        console.print(f"  [dim]Summary[/]  {short}")
    if groups_assigned:
        console.print(f"  [dim]Groups[/]   {', '.join(groups_assigned)}")
    if entry["discovered_links"]:
        console.print(f"  [dim]Found[/]    {len(entry['discovered_links'])} links in content")
    console.print()


# ── process ────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("file", default="links.txt", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Preview without saving.")
@click.option("--fail-fast", is_flag=True, help="Stop on first error.")
def process(file: str, dry_run: bool, fail_fast: bool) -> None:
    """Batch-ingest URLs from a links file (default: links.txt)."""
    _require_db()

    file_path = str(Path(file).resolve())
    records = file_parser.parse(file_path)

    if not records:
        console.print("[yellow]No URLs found in file.[/]")
        return

    console.print(f"\nProcessing [bold]{file}[/]  ({len(records)} URLs)\n")

    if not dry_run:
        db.register_input_file(file_path)

    counts = {"done": 0, "partial": 0, "duplicate": 0, "error": 0}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Ingesting…", total=len(records))

        for rec in records:
            url = rec["url"]
            progress.update(task, description=f"[cyan]{url[:55]}[/]")

            result = pipeline.ingest(
                url,
                source_type="file",
                source_ref=file_path,
                extra_tags=rec["tags"],
                group_name=rec["group"],
                label=rec["label"],
                dry_run=dry_run,
            )

            status = result["status"]
            if status == "dry_run":
                status = result["extraction_status"]

            counts[status if status in counts else "done"] += 1

            icon = {"done": "[green]✔[/]", "partial": "[yellow]⚠[/]",
                    "duplicate": "[dim]–[/]", "error": "[red]✘[/]"}.get(status, "·")
            entry_id = result.get("id", "")
            title = (result.get("entry") or {}).get("title") or url[:55]
            console.print(f"  {icon} [dim]{entry_id}[/]  {title[:55]}")

            if status == "error" and fail_fast:
                console.print(f"\n[red]Stopped: {result.get('error')}[/]")
                break

            progress.advance(task)

    if not dry_run:
        db.update_input_file(
            file_path,
            total_lines=len(records),
            processed=counts["done"] + counts["partial"],
            skipped=counts["duplicate"],
            errored=counts["error"],
        )

    total = sum(counts.values())
    console.print(
        f"\n[bold]Done[/]  {counts['done'] + counts['partial']} / {total}"
        f"  |  Skipped {counts['duplicate']}"
        f"  |  Errors {counts['error']}\n"
    )


# ── list ───────────────────────────────────────────────────────────────────

@cli.command(name="list")
@click.option("--tag", default=None, help="Filter by tag.")
@click.option("--group", default=None, help="Filter by group name.")
@click.option("--type", "url_type", default=None, help="Filter by type (youtube|github|web|arxiv).")
@click.option("--status", default=None, help="Filter by status (done|partial|error|pending).")
@click.option("--limit", default=20, show_default=True, help="Max results.")
@click.option("--offset", default=0, help="Pagination offset.")
def list_cmd(tag, group, url_type, status, limit, offset) -> None:
    """List entries with optional filters."""
    _require_db()

    entries = db.list_entries(tag=tag, group=group, url_type=url_type,
                               status=status, limit=limit, offset=offset)
    if not entries:
        console.print("[dim]No entries found.[/]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="dim", width=9)
    table.add_column("Title", max_width=50)
    table.add_column("Tags", style="dim", max_width=30)
    table.add_column("St", width=3)

    for e in entries:
        tags_str = ", ".join(e["tags"][:4])
        if len(e["tags"]) > 4:
            tags_str += f" +{len(e['tags'])-4}"
        status_icon = {"done": "✔", "partial": "⚠", "error": "✘", "pending": "…"}.get(e["status"], "?")
        table.add_row(
            e["id"],
            e["url_type"],
            e.get("title") or e["url"][:50],
            tags_str,
            status_icon,
        )

    console.print(table)
    console.print(f"[dim]Showing {len(entries)} result(s)[/]")


# ── show ───────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("id_or_url")
def show(id_or_url: str) -> None:
    """Show full detail for an entry (accepts ID or URL)."""
    _require_db()

    entry = db.get_entry(id_or_url)
    if not entry:
        err.print(f"Entry not found: {id_or_url}")
        sys.exit(1)

    _print_entry_detail(entry)


# ── search ─────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option("--limit", default=10, show_default=True)
def search(query: str, limit: int) -> None:
    """Search entries by keyword (title, summary, tags)."""
    _require_db()

    entries = db.search_entries(query, limit=limit)
    if not entries:
        console.print(f"[dim]No results for '{query}'[/]")
        return

    console.print(f"\n[bold]Results for '[cyan]{query}[/]'[/]\n")
    for e in entries:
        _print_entry_row(e)
    console.print()


# ── stats ──────────────────────────────────────────────────────────────────

@cli.command()
def stats() -> None:
    """Show knowledge base summary statistics."""
    _require_db()

    s = db.get_stats()
    e = s["entries"]

    by_type = "  ".join(f"{k}: {v}" for k, v in sorted(e.get("by_type", {}).items()))
    by_status = "  ".join(f"{k}: {v}" for k, v in sorted(e.get("by_status", {}).items()))
    by_source = "  ".join(f"{k}: {v}" for k, v in sorted(e.get("by_source", {}).items()))

    console.print(Panel(
        f"[bold]Entries[/]           {e['total']}\n"
        f"  by type   {by_type}\n"
        f"  by status {by_status}\n"
        f"  by source {by_source}\n\n"
        f"[bold]Tags[/]              {s['tags']['unique']} unique\n"
        f"[bold]Entities[/]          {s['entities']['unique']} unique\n"
        f"[bold]Groups[/]            {s['groups']['total']}\n"
        f"[bold]Graph edges[/]       {s['links']['total']}\n"
        f"[bold]Discovered (queue)[/] {s['discovered_pending']}",
        title="[bold]LinkWiki Stats[/]",
        border_style="cyan",
    ))


# ── groups ─────────────────────────────────────────────────────────────────

@cli.group(name="group")
def group_cmd() -> None:
    """Manage groups."""


@group_cmd.command(name="list")
def groups_list() -> None:
    """List all groups."""
    _require_db()
    groups = db.list_groups()
    if not groups:
        console.print("[dim]No groups yet.[/]")
        return
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Name", style="magenta")
    table.add_column("Type", style="dim")
    table.add_column("Entries", justify="right")
    for g in groups:
        table.add_row(g["name"], g["group_type"], str(g["entry_count"]))
    console.print(table)


@group_cmd.command(name="create")
@click.argument("name")
@click.option("--description", default=None)
def group_create(name: str, description: str | None) -> None:
    """Create a manual group."""
    _require_db()
    gid = db.get_or_create_group(name, "manual")
    if description:
        with db._conn() as conn:
            conn.execute("UPDATE groups SET description = ? WHERE id = ?", (description, gid))
    console.print(f"[green]✔[/] Group '[magenta]{name}[/]' ready  [dim]{gid}[/]")


@group_cmd.command(name="add")
@click.argument("entry_id")
@click.argument("group_name")
def group_add(entry_id: str, group_name: str) -> None:
    """Add an entry to a group."""
    _require_db()
    entry = db.get_entry(entry_id)
    if not entry:
        err.print(f"Entry not found: {entry_id}")
        sys.exit(1)
    gid = db.get_or_create_group(group_name, "manual")
    db.assign_to_group(entry["id"], gid, "user")
    console.print(f"[green]✔[/] [cyan]{entry['id']}[/] → [magenta]{group_name}[/]")


@group_cmd.command(name="remove")
@click.argument("entry_id")
@click.argument("group_name")
def group_remove(entry_id: str, group_name: str) -> None:
    """Remove an entry from a group."""
    _require_db()
    g = db.get_group_by_name(group_name)
    if not g:
        err.print(f"Group not found: {group_name}")
        sys.exit(1)
    db.remove_from_group(entry_id, g["id"])
    console.print(f"[yellow]–[/] [cyan]{entry_id}[/] removed from [magenta]{group_name}[/]")


@group_cmd.command(name="show")
@click.argument("group_name")
def group_show(group_name: str) -> None:
    """Show all entries in a group."""
    _require_db()
    g = db.get_group_by_name(group_name)
    if not g:
        err.print(f"Group not found: {group_name}")
        sys.exit(1)
    entries = db.list_entries(group=group_name, limit=100)
    console.print(f"\n[magenta bold]{group_name}[/]  [dim]{g['group_type']} · {g['entry_count']} entries[/]\n")
    for e in entries:
        _print_entry_row(e)
    console.print()


@group_cmd.command(name="delete")
@click.argument("group_name")
@click.confirmation_option(prompt="Delete this group?")
def group_delete(group_name: str) -> None:
    """Delete a group (entries are not deleted)."""
    _require_db()
    if db.delete_group(group_name):
        console.print(f"[yellow]–[/] Group '[magenta]{group_name}[/]' deleted")
    else:
        err.print(f"Group not found: {group_name}")


# ── related ────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("id_or_url")
@click.option("--type", "link_type", default=None,
              help="Filter by edge type (semantic|shared_tag|shared_entity|discovered|manual).")
@click.option("--limit", default=10, show_default=True)
def related(id_or_url: str, link_type: str | None, limit: int) -> None:
    """Show entries linked to a given entry."""
    _require_db()
    entry = db.get_entry(id_or_url)
    if not entry:
        err.print(f"Entry not found: {id_or_url}")
        sys.exit(1)

    related_entries = db.get_related(entry["id"], link_type=link_type, limit=limit)
    if not related_entries:
        console.print("[dim]No related entries found.[/]")
        return

    console.print(f"\n[bold]Related to[/] [cyan]{entry['id']}[/]  {entry.get('title') or ''}\n")
    for r in related_entries:
        strength = f"[dim]{r['strength']:.2f}[/]" if r.get("strength") else ""
        ltype = f"[dim]{r.get('link_type', '')}[/]"
        console.print(f"  {strength}  {ltype:20}  [cyan]{r['id']}[/]  {r.get('title') or r['url'][:55]}")
    console.print()


# ── add-discovered ─────────────────────────────────────────────────────────

@cli.command("add-discovered")
@click.argument("id_or_url")
@click.option("--all", "ingest_all", is_flag=True, help="Ingest all without prompting.")
@click.option("--filter", "url_filter", default=None, help="Only ingest URLs containing this substring.")
def add_discovered(id_or_url: str, ingest_all: bool, url_filter: str | None) -> None:
    """Ingest links discovered inside an entry's content."""
    _require_db()
    entry = db.get_entry(id_or_url)
    if not entry:
        err.print(f"Entry not found: {id_or_url}")
        sys.exit(1)

    links = entry.get("discovered_links", [])
    if url_filter:
        links = [l for l in links if url_filter in l["url"]]
    if not links:
        console.print("[dim]No discovered links found.[/]")
        return

    console.print(f"\n[bold]Discovered links in[/] [cyan]{entry['id']}[/]\n")
    for i, lnk in enumerate(links, 1):
        label = f"  {lnk.get('label')}" if lnk.get("label") else ""
        console.print(f"  [{i:2}] {lnk['url'][:70]}{label}")

    if not ingest_all:
        choice = click.prompt(
            "\nEnter numbers to ingest (comma-separated), 'all', or 'none'",
            default="none",
        )
        if choice.lower() == "none":
            return
        if choice.lower() == "all":
            to_ingest = links
        else:
            indices = []
            for part in choice.split(","):
                part = part.strip()
                if part.isdigit() and 1 <= int(part) <= len(links):
                    indices.append(int(part) - 1)
            to_ingest = [links[i] for i in indices]
    else:
        to_ingest = links

    console.print()
    for lnk in to_ingest:
        url = lnk["url"]
        with console.status(f"[cyan]{url[:60]}…[/]"):
            result = pipeline.ingest(url, source_type="discovered", source_ref=entry["id"])
        status = result["status"]
        icon = {"done": "[green]✔[/]", "partial": "[yellow]⚠[/]",
                "duplicate": "[dim]–[/]", "error": "[red]✘[/]"}.get(status, "·")
        title = (result.get("entry") or {}).get("title") or url[:55]
        console.print(f"  {icon} {title[:60]}")
    console.print()


# ── reindex ────────────────────────────────────────────────────────────────

@cli.command()
def reindex() -> None:
    """Rebuild the ChromaDB vector index from SQLite."""
    _require_db()
    entries = db.list_entries(status="done", limit=10_000)
    entries += db.list_entries(status="partial", limit=10_000)

    console.print(f"Re-embedding [bold]{len(entries)}[/] entries…\n")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  BarColumn(), TaskProgressColumn(), console=console) as progress:
        task = progress.add_task("Embedding…", total=len(entries))
        for e in entries:
            vectors.embed_entry(e["id"], e.get("title"), e.get("summary"),
                                e["url_type"], e["tags"])
            progress.advance(task)

    console.print(f"[green]✔[/] Index rebuilt — {vectors.count()} vectors stored\n")


# ── sync ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--tags/--no-tags", default=True, show_default=True)
@click.option("--entities/--no-entities", default=True, show_default=True)
@click.option("--semantic/--no-semantic", default=True, show_default=True)
def sync(tags: bool, entities: bool, semantic: bool) -> None:
    """Re-run auto-linking and auto-grouping across all entries."""
    _require_db()

    with console.status("[cyan]Syncing knowledge graph…[/]"):
        results = linker.sync_all(run_tags=tags, run_entities=entities, run_semantic=semantic)

    console.print(Panel(
        f"[bold]Tag links[/]       {results.get('tag_links', 0):>6} edges\n"
        f"[bold]Tag groups[/]      {results.get('tag_groups', 0):>6} groups updated\n"
        f"[bold]Entity links[/]    {results.get('entity_links', 0):>6} edges\n"
        f"[bold]Entity groups[/]   {results.get('entity_groups', 0):>6} groups updated\n"
        f"[bold]Semantic links[/]  {results.get('semantic_links', 0):>6} edges\n"
        f"[bold]Semantic groups[/] {results.get('semantic_groups', 0):>6} clusters named\n"
        f"[bold]Discovered[/]      {results.get('discovered_links', 0):>6} cross-links",
        title="[bold]Sync complete[/]",
        border_style="green",
    ))


# ── export ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--format", "fmt", default="json",
              type=click.Choice(["json", "csv", "obsidian", "html"]), show_default=True)
@click.option("--output", default=None,
              help="Output file or directory.")
@click.option("--group", default=None, help="Export only entries in this group.")
def export(fmt: str, output: str | None, group: str | None) -> None:
    """Export the knowledge base (json | csv | obsidian | html)."""
    _require_db()
    from linkwiki.core.export import export_json, export_csv, export_obsidian, export_html

    entries = db.list_entries(group=group, limit=100_000)
    if not entries:
        console.print("[dim]No entries to export.[/]")
        return

    if fmt == "json":
        path = output or "linkwiki-export.json"
        export_json(entries, path)
        console.print(f"[green]✔[/] JSON export → [bold]{path}[/]  ({len(entries)} entries)")
    elif fmt == "csv":
        path = output or "linkwiki-export.csv"
        export_csv(entries, path)
        console.print(f"[green]✔[/] CSV export  → [bold]{path}[/]  ({len(entries)} entries)")
    elif fmt == "obsidian":
        path = output or "linkwiki-obsidian"
        export_obsidian(entries, path)
        console.print(f"[green]✔[/] Obsidian    → [bold]{path}/[/]  ({len(entries)} files)")
    elif fmt == "html":
        path = output or "linkwiki-html"
        total_files = export_html(entries, path)
        console.print(
            f"[green]✔[/] HTML export → [bold]{path}/[/]\n"
            f"   [dim]{len(entries)} entry pages · groups · index.html[/]\n"
            f"   Open [bold]{path}/index.html[/] in any browser"
        )


# ── archive ────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--source", default="linkwiki-html",
              help="Folder to archive (default: linkwiki-html).")
@click.option("--dest", default="archive",
              help="Destination archive directory (default: archive).")
def archive(source: str, dest: str) -> None:
    """Move the linkwiki-html export folder into archive/ with a timestamp suffix."""
    source_path = Path(source)
    if not source_path.exists() or not source_path.is_dir():
        console.print(f"[red]✖[/] Source folder not found: [bold]{source}[/]")
        raise SystemExit(1)

    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("archive-%d-%m-%Y-%H-%M-%S")
    target = dest_path / timestamp

    shutil.move(str(source_path), str(target))
    console.print(f"[green]✔[/] Archived → [bold]{target}/[/]")
