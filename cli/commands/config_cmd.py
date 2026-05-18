"""Config command — view and manage Vyper CLI configuration.

Usage:
    vyper config [show|set|init|path]
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cli.config import DEFAULT_CONFIG_PATH, get_config

console = Console()
err_console = Console(stderr=True)


def config_cmd(
    action: str = typer.Argument("show", help="show | set <key> <value> | init | path"),
    key: Optional[str] = typer.Argument(None, help="Config key to set"),
    value: Optional[str] = typer.Argument(None, help="Config value to set"),
) -> None:
    """View and manage Vyper CLI configuration."""
    cfg = get_config()

    if action == "show":
        table = Table(title="Vyper CLI Configuration", box=None, header_style="bold cyan")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        for k, v in cfg.as_table():
            table.add_row(k, v)
        console.print(table)
        console.print(f"\nConfig file: [dim]{DEFAULT_CONFIG_PATH}[/]")

    elif action == "set":
        if not key or value is None:
            err_console.print("Usage: vyper config set <key> <value>")
            raise typer.Exit(1)
        cfg.set(key, value)
        cfg.save()
        console.print(f"[green]✅ Set {key} = {value}[/]")

    elif action == "init":
        cfg.save()
        console.print(f"[green]✅ Config initialized at {DEFAULT_CONFIG_PATH}[/]")

    elif action == "path":
        console.print(str(DEFAULT_CONFIG_PATH))

    else:
        err_console.print(f"Unknown action: {action}. Try: show, set, init, path")
        raise typer.Exit(1)
