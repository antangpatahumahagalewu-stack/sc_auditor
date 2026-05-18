"""Status commands — audit status, list, stats, queue, health.

Usage:
    vyper status <audit-id>
    vyper list [--state completed] [--limit 20]
    vyper stats
    vyper queue
    vyper health
    vyper daemon
"""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console

from cli.client import VyperClient
from cli.output import (
    print_json,
    show_audit_status,
    show_audits_table,
    show_error,
    show_health,
    show_queue,
    show_stats,
    show_success,
)

console = Console()
err_console = Console(stderr=True)


# ── Shared async runner ──────────────────────────────────────────

def _async_run(coro):
    """Run an async function synchronously."""
    return asyncio.run(coro)


# ── Commands ─────────────────────────────────────────────────────

def status(
    audit_id: str = typer.Argument(..., help="Audit ID to check"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """Check the status of a specific audit."""
    async def _run() -> None:
        async with VyperClient() as client:
            try:
                record = await client.get_audit(audit_id)
            except Exception as exc:
                show_error(f"Failed to get audit: {exc}")
                raise typer.Exit(1)

            if not record:
                show_error(f"Audit not found: {audit_id}")
                raise typer.Exit(1)

            if json_output:
                print_json(record)
                return

            show_audit_status(record)

    _async_run(_run())


def list_audits(
    state: str = typer.Option("", "--state", "-s", help="Filter by state (completed, failed, pending, etc.)"),
    program: str = typer.Option("", "--program", "-p", help="Filter by program slug"),
    chain: str = typer.Option("", "--chain", "-c", help="Filter by chain"),
    limit: int = typer.Option(100, "--limit", "-n", help="Max results"),
    offset: int = typer.Option(0, "--offset", "-o", help="Pagination offset"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """List all audits with optional filtering."""
    async def _run() -> None:
        async with VyperClient() as client:
            try:
                records = await client.list_audits(
                    state=state,
                    program=program,
                    chain=chain,
                    limit=limit,
                    offset=offset,
                )
            except Exception as exc:
                show_error(f"Failed to list audits: {exc}")
                raise typer.Exit(1)

            total = 0
            if isinstance(records, dict):
                total = records.get("total", len(records.get("data", [])))
                records = records.get("data", [])
            elif isinstance(records, list):
                total = len(records)

            if json_output:
                print_json(records)
                return

            show_audits_table(records, total)

    _async_run(_run())


def stats(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """Show pipeline statistics."""
    async def _run() -> None:
        async with VyperClient() as client:
            try:
                result = await client.get_stats()
            except Exception as exc:
                show_error(f"Failed to get stats: {exc}")
                raise typer.Exit(1)

            if json_output:
                print_json(result)
                return

            show_stats(result)

    _async_run(_run())


def queue(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """View the audit priority queue."""
    async def _run() -> None:
        async with VyperClient() as client:
            try:
                items = await client.get_queue()
            except Exception as exc:
                show_error(f"Failed to get queue: {exc}")
                raise typer.Exit(1)

            if json_output:
                print_json(items)
                return

            show_queue(items)

    _async_run(_run())


def health(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """Check health of all Vyper services."""
    async def _run() -> None:
        async with VyperClient() as client:
            console.print("[bold cyan]Checking all service health...[/]")
            try:
                results = await client.health_all()
            except Exception as exc:
                show_error(f"Health check failed: {exc}")
                raise typer.Exit(1)

            if json_output:
                print_json(results)
                return

            show_health(results)

    _async_run(_run())


def daemon(
    action: str = typer.Argument("status", help="start | stop | status"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """Manage the continuous scanning daemon."""
    if action not in ("start", "stop", "status"):
        show_error("Action must be: start, stop, or status")
        raise typer.Exit(1)

    async def _run() -> None:
        async with VyperClient() as client:
            try:
                if action == "start":
                    result = await client.daemon_start()
                    show_success("Daemon started")
                elif action == "stop":
                    result = await client.daemon_stop()
                    show_success("Daemon stopped")
                else:
                    result = await client.daemon_status()

                if json_output:
                    print_json(result)
                elif result:
                    console.print(f"[bold]Daemon state:[/] {result.get('status', result)}")
            except Exception as exc:
                show_error(f"Daemon {action} failed: {exc}")
                raise typer.Exit(1)

    _async_run(_run())
