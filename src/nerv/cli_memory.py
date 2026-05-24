from __future__ import annotations

from collections.abc import Iterable

import typer
from rich.columns import Columns
from rich.console import Console
from rich.table import Table

from nerv.config import load_runtime_settings
from nerv.mcp.memory_server import MemoryService
from nerv.util import format_age

memory_app = typer.Typer(name="memory", help="Inspect persistent engineering memories")
console = Console()


def _build_service() -> MemoryService:
    settings = load_runtime_settings()
    return MemoryService(settings)


def _print_memory_error(exc: Exception) -> None:
    console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(1) from exc


def _preview(content: str, limit: int = 60) -> str:
    return content if len(content) <= limit else f"{content[: limit - 3]}..."


def _stats_table(title: str, rows: Iterable[tuple[str, int]], label: str) -> Table:
    table = Table(title=title)
    table.add_column(label, style="cyan")
    table.add_column("Count", justify="right", style="green")
    for key, count in rows:
        table.add_row(key, str(count))
    return table


@memory_app.command("list")
def memory_list(
    type: str | None = typer.Option(None, "--type", help="Filter by memory type"),
    scope: str | None = typer.Option(None, "--scope", help="Filter by memory scope"),
    limit: int = typer.Option(20, "--limit", help="Maximum memories to show"),
) -> None:
    """List recent memories."""
    try:
        memories = _build_service().memory_context(n=limit)["memories"]
    except Exception as exc:
        _print_memory_error(exc)

    filtered = [
        memory
        for memory in memories
        if (type is None or memory["type"] == type) and (scope is None or memory["scope"] == scope)
    ][:limit]

    if not filtered:
        console.print("No memories found.")
        return

    table = Table(title="Memories")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Scope", style="blue")
    table.add_column("Agent", style="yellow")
    table.add_column("Age", style="green")
    table.add_column("Title")

    for memory in filtered:
        table.add_row(
            memory["id"][:8],
            memory["type"],
            memory["scope"],
            memory["agent_source"],
            format_age(memory["timestamp"]),
            memory["title"],
        )

    console.print(table)


@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(..., help="Semantic query"),
    type: str | None = typer.Option(None, "--type", help="Filter by memory type"),
    keyword: str | None = typer.Option(None, "--keyword", help="Add a keyword content filter"),
    limit: int = typer.Option(5, "--limit", help="Maximum results to show"),
) -> None:
    """Search memories."""
    try:
        response = _build_service().memory_search(query=query, type_filter=type, keyword=keyword, limit=limit)
    except Exception as exc:
        _print_memory_error(exc)

    results = response["results"]
    if not results:
        console.print("No memories found.")
        return

    table = Table(title="Memory Search Results")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Type", style="magenta")
    table.add_column("Agent", style="yellow")
    table.add_column("Title")
    table.add_column("Content Preview")

    for result in results:
        table.add_row(
            f"{result['score']:.2f}",
            result["type"],
            result["agent_source"],
            result["title"],
            _preview(result["content"]),
        )

    console.print(table)
    if response.get("nudge"):
        console.print(f"[yellow]{response['nudge']}[/yellow]")


@memory_app.command("prune")
def memory_prune(
    scope: str = typer.Option(..., "--scope", help="Scope to prune: session or personal"),
    older_than: int = typer.Option(30, "--older-than", help="Soft-delete memories older than N days"),
) -> None:
    """Soft-delete old memories of a given scope."""
    try:
        result = _build_service().memory_prune(scope=scope, older_than_days=older_than)
    except Exception as exc:
        _print_memory_error(exc)

    console.print(f"Pruned [green]{result['pruned']}[/green] {scope} memories older than {older_than} days.")


@memory_app.command("stats")
def memory_stats() -> None:
    """Show aggregate memory statistics."""
    try:
        stats = _build_service().memory_stats()
    except Exception as exc:
        _print_memory_error(exc)

    console.print(f"Total memories: {stats['total']}")
    console.print(
        Columns(
            [
                _stats_table("By Type", stats["by_type"].items(), "Type"),
                _stats_table("By Scope", stats["by_scope"].items(), "Scope"),
                _stats_table("By Agent", stats["by_agent"].items(), "Agent"),
            ]
        )
    )
