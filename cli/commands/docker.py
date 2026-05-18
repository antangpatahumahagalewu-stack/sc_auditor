"""Docker Compose lifecycle commands: up, down, logs, ps, restart.

These commands manage the Vyper microservice stack via docker compose.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cli.config import get_config

console = Console()
err_console = Console(stderr=True)


# ── Helpers ──────────────────────────────────────────────────────

def _docker_compose(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run docker-compose command with the given args."""
    cmd = ["docker", "compose"] + args
    console.print(f"[dim]Running: {' '.join(cmd)}[/]")
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=False,
        text=True,
    )


def _compose_path() -> Path:
    """Get the docker-compose project directory."""
    cfg = get_config()
    return cfg.project_dir


# ── Commands ─────────────────────────────────────────────────────

def up(
    build: bool = typer.Option(False, "--build", "-b", help="Rebuild images before starting"),
    detach: bool = typer.Option(True, "--detach", "-d", help="Run in background"),
    scale: Optional[str] = typer.Option(None, "--scale", help="Scale a service, e.g. scanner=3"),
    services: Optional[list[str]] = typer.Argument(None, help="Services to start (default: all)"),
) -> None:
    """Start all Vyper microservices."""
    project_dir = _compose_path()
    if not (project_dir / "docker-compose.yml").exists():
        err_console.print(
            f"[red]docker-compose.yml not found in {project_dir}[/]\n"
            "Run from the vyper project directory or set project_dir in config."
        )
        raise typer.Exit(1)

    args = ["up"]
    if detach:
        args.append("-d")
    if build:
        args.append("--build")
    if scale:
        args.extend(["--scale", scale])
    if services:
        args.extend(services)

    console.print(f"[bold cyan]Starting Vyper services...[/]")
    result = _docker_compose(args, project_dir)

    if result.returncode != 0:
        err_console.print("[red]Failed to start services.[/]")
        raise typer.Exit(result.returncode)

    console.print("[bold green]✅ Vyper services started![/]")
    console.print("  Dashboard: [link=http://localhost:8000]http://localhost:8000[/]")
    console.print("  API:       http://localhost:8009")


def down(
    volumes: bool = typer.Option(False, "--volumes", "-v", help="Remove persisted data volumes"),
    remove_orphans: bool = typer.Option(True, "--remove-orphans", help="Remove orphaned containers"),
) -> None:
    """Stop all Vyper microservices."""
    project_dir = _compose_path()

    args = ["down"]
    if volumes:
        args.append("-v")
    if remove_orphans:
        args.append("--remove-orphans")

    console.print("[bold yellow]Stopping Vyper services...[/]")
    result = _docker_compose(args, project_dir)

    if result.returncode != 0:
        err_console.print("[red]Failed to stop services.[/]")
        raise typer.Exit(result.returncode)

    console.print("[bold green]✅ Vyper services stopped.[/]")


def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    tail: int = typer.Option(50, "--tail", "-n", help="Number of lines to show"),
    service: Optional[str] = typer.Argument(None, help="Service name (default: all)"),
) -> None:
    """Show logs from Vyper services."""
    project_dir = _compose_path()

    args = ["logs"]
    if follow:
        args.append("-f")
    args.extend(["--tail", str(tail)])
    if service:
        args.append(service)

    result = _docker_compose(args, project_dir)

    if result.returncode != 0:
        err_console.print("[red]Failed to get logs.[/]")
        raise typer.Exit(result.returncode)


def ps() -> None:
    """List running Vyper services."""
    project_dir = _compose_path()

    args = ["ps", "--format", "json"]
    result = subprocess.run(
        ["docker", "compose"] + args,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        err_console.print("[red]Failed to list services.[/]")
        raise typer.Exit(result.returncode)

    # Parse JSON output
    import json
    try:
        services = json.loads(result.stdout)
        if not services:
            console.print("[yellow]No services running.[/]")
            return

        if isinstance(services, dict):
            services = [services]

        table = Table(title="Running Services", box=None, header_style="bold cyan")
        table.add_column("Name", width=30)
        table.add_column("Status", width=12)
        table.add_column("Ports", width=30)

        for svc in services:
            name = svc.get("Name", svc.get("Service", "?"))
            state = svc.get("State", svc.get("Status", "?"))
            ports = svc.get("Ports", "")

            sc = "green" if state == "running" else "red"
            table.add_row(name, f"[{sc}]{state}[/]", str(ports)[:30])

        console.print(table)

    except (json.JSONDecodeError, KeyError) as exc:
        # Fallback: print raw output
        print(result.stdout)


def restart(
    service: Optional[str] = typer.Argument(None, help="Service to restart (default: all)"),
    timeout: int = typer.Option(10, "--timeout", "-t", help="Stop timeout in seconds"),
) -> None:
    """Restart Vyper services."""
    project_dir = _compose_path()

    args = ["restart", "-t", str(timeout)]
    if service:
        args.append(service)

    console.print(f"[bold yellow]Restarting services...[/]")
    result = _docker_compose(args, project_dir)

    if result.returncode != 0:
        err_console.print("[red]Failed to restart services.[/]")
        raise typer.Exit(result.returncode)

    console.print("[bold green]✅ Services restarted.[/]")
