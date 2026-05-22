"""Vyper Monitor command — open live terminal dashboard + AI Chat."""

from __future__ import annotations

import subprocess
import sys
import typer
from rich.console import Console

app = typer.Typer()
console = Console()


def _launch_chat_window() -> None:
    """Launch AI Chat in a new terminal window."""
    cmd = f"{sys.executable} -m cli chat"

    try:
        if sys.platform == "win32":
            # Windows — open new cmd window via start
            subprocess.Popen(
                f'start "VYPER AI Chat" cmd /c {cmd}',
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True,
            )
        elif sys.platform == "darwin":
            # macOS — open new Terminal window
            subprocess.Popen(
                ["osascript", "-e",
                 f'tell app "Terminal" to do script "{cmd}"'],
                stdin=None, stdout=None, stderr=None, close_fds=True,
            )
        else:
            # Linux — try common terminals
            terminals = ["x-terminal-emulator", "gnome-terminal", "xterm", "konsole"]
            launched = False
            for term in terminals:
                try:
                    subprocess.Popen(
                        [term, "-e", cmd],
                        stdin=None, stdout=None, stderr=None, close_fds=True,
                    )
                    launched = True
                    break
                except FileNotFoundError:
                    continue
            if not launched:
                console.print("[yellow]⚠️ Could not open AI Chat window automatically.[/yellow]")
                console.print(f"[yellow]   Run manually: {cmd}[/yellow]")
    except Exception as exc:
        console.print(f"[dim]Chat window launch: {exc}[/dim]")
        console.print(f"[dim]Run chat manually: {cmd}[/dim]")


@app.callback(invoke_without_command=True)
def monitor(
    ctx: typer.Context,
    poll_interval: int = typer.Option(
        5, "--interval", "-i",
        help="Polling interval in seconds for health checks",
        show_default=True,
    ),
    no_chat: bool = typer.Option(
        False, "--no-chat", "-n",
        help="Do not auto-launch AI Chat window",
        show_default=True,
    ),
) -> None:
    """Open Vyper Monitor — live terminal dashboard + AI Chat.

    Displays real-time event log, service health, and pipeline statistics
    from all 19 Vyper microservices. Auto-polls every 3-10 seconds.

    Also launches AI Chat in a separate terminal window for pipeline Q&A.
    Use --no-chat to disable the chat window.
    """
    if not no_chat:
        _launch_chat_window()
        console.print("[green]✅ AI Chat window launched in separate terminal[/green]")
        console.print("[dim]   Press [Q] in dashboard to quit[/dim]")
        console.print("")

    try:
        from cli.monitor.app import VyperMonitorApp
        VyperMonitorApp(poll_interval=poll_interval).run()
    except ImportError as exc:
        console.print(f"[red]Error: Missing dependency — {exc}[/red]")
        console.print("[yellow]Run: pip install textual[/yellow]")
        raise typer.Exit(1) from exc
