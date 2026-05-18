"""Dashboard command — open the Vyper web dashboard in a browser."""

from __future__ import annotations

import webbrowser

import typer
from rich.console import Console

from cli.config import get_config

console = Console()
err_console = Console(stderr=True)


def dashboard(
    url: str = typer.Option("", "--url", "-u", help="Dashboard URL override"),
) -> None:
    """Open the Vyper web dashboard in your default browser."""
    cfg = get_config()
    dash_url = url or cfg.get("dashboard_url", "http://localhost:8000")

    console.print(f"[cyan]Opening dashboard:[/] {dash_url}")
    try:
        webbrowser.open(dash_url)
        console.print("[green]✅ Dashboard opened in browser.[/]")
    except Exception as exc:
        err_console.print(f"[red]Failed to open browser:[/] {exc}")
        console.print(f"Visit manually: {dash_url}")
