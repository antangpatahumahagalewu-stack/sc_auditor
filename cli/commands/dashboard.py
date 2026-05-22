"""Dashboard command — web dashboard has been removed, redirect to monitor."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def dashboard(
    url: str = typer.Option("", "--url", "-u", help="Dashboard URL override (ignored)"),
) -> None:
    """The Vyper web dashboard has been removed.

    Use ``vyper monitor`` instead for the live terminal dashboard, or
    ``vyper health`` for a quick service status overview.
    """
    console.print(
        "[yellow]⚠ Web dashboard (15-dashboard) has been removed.[/]\n\n"
        "Use [bold cyan]vyper monitor[/] for a live terminal dashboard, or\n"
        "[bold cyan]vyper health[/] for a quick service status overview.\n\n"
        "To re-enable the dashboard, add the 15-dashboard service back to\n"
        "docker-compose.yml and rebuild:  docker compose build 15-dashboard"
    )
