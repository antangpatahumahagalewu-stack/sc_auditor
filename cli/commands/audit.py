"""Audit command — run the full Vyper audit pipeline.

Usage:
    vyper audit 0xdead... --chain ethereum --program ethena
    vyper audit 0xdead... --priority 10
"""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm

from cli.client import VyperClient
from cli.output import (
    get_progress,
    show_audit_started,
    show_audit_status,
    show_error,
    show_success,
)

console = Console()
err_console = Console(stderr=True)


def audit(
    address: str = typer.Argument(..., help="Contract address (0x-prefixed)"),
    chain: str = typer.Option("ethereum", "--chain", "-c", help="Blockchain name"),
    program: str = typer.Option("", "--program", "-p", help="Immunefi program slug"),
    priority: int = typer.Option(5, "--priority", min=0, max=10, help="Audit priority (0-10)"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for pipeline to complete"),
    timeout: int = typer.Option(600, "--timeout", help="Max wait time in seconds"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Run the full audit pipeline for a smart contract."""
    if not address.startswith("0x"):
        show_error("Address must be 0x-prefixed")
        raise typer.Exit(1)

    async def _run() -> None:
        async with VyperClient() as client:
            # Start the audit
            try:
                result = await client.start_audit(
                    address=address,
                    chain=chain,
                    program=program,
                    priority=priority,
                )
            except Exception as exc:
                show_error(f"Failed to start audit: {exc}")
                raise typer.Exit(1)

            audit_id = result.get("audit_id", "")
            show_audit_started(result)

            if not wait:
                show_success(f"Audit {audit_id[:8]} started in background")
                return

            # Poll for completion
            import time
            start_time = time.monotonic()

            with get_progress() as progress:
                task = progress.add_task(
                    f"[cyan]Audit {audit_id[:8]}...[/]",
                    total=None,
                )

                while True:
                    elapsed = time.monotonic() - start_time
                    if elapsed > timeout:
                        progress.stop()
                        show_error(f"Audit did not complete within {timeout}s timeout")
                        show_success(f"Check status later: vyper status {audit_id}")
                        raise typer.Exit(1)

                    try:
                        status = await client.get_audit(audit_id)
                    except Exception:
                        await asyncio.sleep(2)
                        continue

                    state = status.get("state", "")
                    progress.update(
                        task,
                        description=f"[cyan]{state.upper()}[/]",
                    )

                    if state in ("completed",) or "failed" in state or state in ("timeout", "aborted"):
                        progress.stop()
                        console.print()
                        show_audit_status(status)

                        if state == "completed":
                            show_success(f"Audit completed in {status.get('duration_seconds', 0):.1f}s")
                        else:
                            show_error(f"Audit finished with state: {state}")
                        return

                    await asyncio.sleep(2)

    asyncio.run(_run())
