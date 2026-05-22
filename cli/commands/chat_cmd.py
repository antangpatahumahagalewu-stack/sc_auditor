"""Vyper Chat command — open AI chatbot terminal interface."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def chat() -> None:
    """Open Vyper AI Chat — pipeline-aware AI assistant.

    Interactive chatbot that answers questions about pipeline status,
    audit history, service health, findings, and configurations.
    Uses live data from all 19 Vyper microservices + AI.
    """
    try:
        from cli.chat.app import ChatApp
        ChatApp().run()
    except ImportError as exc:
        console.print(f"[red]Error: Missing dependency — {exc}[/red]")
        console.print("[yellow]Run: pip install textual[/yellow]")
        raise typer.Exit(1) from exc
