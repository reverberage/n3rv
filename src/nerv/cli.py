from __future__ import annotations

from pathlib import Path

import typer

from nerv.a2a.hub import main as hub_main
from nerv.init import run_init
from nerv.cli_memory import memory_app

app = typer.Typer(
    name="nerv", help="Invisible engineering infrastructure for opencode agents"
)
hub_app = typer.Typer(help="A2A Hub commands")
app.add_typer(hub_app, name="hub")
app.add_typer(memory_app, name="memory")


@hub_app.command("start")
def hub_start() -> None:
    """Start the A2A hub server."""
    hub_main()


@app.command("init")
def init(
    root: Path = typer.Option(
        Path.cwd(),
        "--root",
        help="Project root directory",
    ),
    project_name: str | None = typer.Option(
        None,
        "--project-name",
        help="Project name (overrides auto-detection)",
    ),
    stack: str | None = typer.Option(
        None,
        "--stack",
        help="Stack type: python, node, go, generic",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing files without prompting",
    ),
) -> None:
    """Initialize agent-native integration files."""
    exit_code = run_init(
        root=root,
        project_name=project_name,
        stack_override=stack,
        force=force,
    )
    raise typer.Exit(code=exit_code)


@app.command("update")
def update_command(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview changes without writing"
    ),
    force_commands: bool = typer.Option(
        False, "--force-commands", help="Overwrite command files"
    ),
    only: str | None = typer.Option(
        None,
        "--only",
        help="Only update one category: marker-merge, json-merge, overwrite, skip-default",
    ),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root directory"),
) -> None:
    """Update agent-native integration files in an existing project."""
    from nerv.init.update import run_update

    raise typer.Exit(
        code=run_update(root, dry_run=dry_run, force_commands=force_commands, only=only)
    )


def main() -> None:
    """Entry point for CLI."""
    app()
