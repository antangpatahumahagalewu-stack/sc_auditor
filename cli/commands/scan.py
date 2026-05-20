"""Scan command — run analysis tools directly on a Solidity file.

Usage:
    vyper scan contract.sol
    vyper scan contract.sol --tools slither,mythril --compiler 0.8.20
    vyper scan contract.sol --json
    vyper scan contract.sol --halmos
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cli.client import VyperClient
from cli.output import (
    get_progress,
    print_json,
    show_error,
    show_findings,
    show_success,
)

console = Console()
err_console = Console(stderr=True)


def scan(
    file_path: str = typer.Argument(..., help="Solidity file or directory to scan"),
    tools: str = typer.Option("slither,mythril", "--tools", "-t", help="Comma-separated tools"),
    compiler: str = typer.Option("0.8.20", "--compiler", "-c", help="Solidity compiler version"),
    timeout: int = typer.Option(600, "--timeout", help="Scan timeout in seconds"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    halmos: bool = typer.Option(False, "--halmos", help="Enable Halmos formal verification (symbolic execution)"),
) -> None:
    """Run analysis tools directly on a Solidity contract (bypasses pipeline). Supports --halmos flag for symbolic execution."""
    path = Path(file_path)
    if not path.exists():
        show_error(f"File not found: {file_path}")
        raise typer.Exit(1)

    # Read source file(s)
    sources: dict[str, str] = {}
    if path.is_file():
        if path.suffix not in (".sol",):
            show_error(f"Not a Solidity file: {path.suffix}")
            raise typer.Exit(1)
        sources[path.name] = path.read_text("utf-8")
    elif path.is_dir():
        sol_files = list(path.rglob("*.sol"))
        if not sol_files:
            show_error(f"No .sol files found in {file_path}")
            raise typer.Exit(1)
        for sf in sol_files:
            relative = sf.relative_to(path)
            sources[str(relative)] = sf.read_text("utf-8")
        console.print(f"[dim]Found {len(sources)} .sol files[/]")

    tool_list = [t.strip() for t in tools.split(",") if t.strip()]
    if halmos and "halmos" not in tool_list:
        tool_list.append("halmos")

    async def _run() -> None:
        async with VyperClient() as client:
            console.print(f"[bold cyan]Scanning[/] {len(sources)} file(s) with {', '.join(tool_list)}")

            with get_progress() as progress:
                task = progress.add_task("[cyan]Scanning...", total=None)

                try:
                    result = await client.scan_contract(
                        sources=sources,
                        compiler=compiler,
                        tools=tool_list,
                        timeout=float(timeout),
                    )
                except Exception as exc:
                    progress.stop()
                    show_error(f"Scan failed: {exc}")
                    raise typer.Exit(1)

                progress.stop()

            # Extract findings
            findings = []
            if isinstance(result, dict):
                findings = result.get("findings", result.get("all_findings", []))
                if not findings:
                    # Try nested data structure
                    data = result.get("data", result)
                    if isinstance(data, dict):
                        findings = data.get("findings", data.get("all_findings", []))

            if json_output:
                print_json(result)
                return

            console.print()
            if findings:
                show_findings(findings)
                show_success(f"Found {len(findings)} finding(s)")
            else:
                show_success("No findings — contract looks clean!")

            # Show summary
            tool_results = result.get("tool_results", result.get("data", {}))
            if isinstance(tool_results, dict):
                console.print("\n[bold]Tool Results:[/]")
                for tool_name, tool_data in tool_results.items():
                    status = tool_data.get("status", "?")
                    errors = tool_data.get("errors", [])
                    sc = "green" if status == "success" else "red"
                    console.print(f"  {tool_name}: [{sc}]{status}[/]")
                    if errors and verbose:
                        for err in errors[:3]:
                            console.print(f"    [dim]{err}[/]")

    asyncio.run(_run())
