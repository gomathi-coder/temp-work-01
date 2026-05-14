"""LinkWiki CLI — all commands."""

from __future__ import annotations
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from linkwiki.core import database as db
from linkwiki.core import pipeline, file_parser

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
