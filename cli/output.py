"""Output formatters — Rich console helpers for beautiful CLI output.

Supports:
  - Rich tables (default)
  - JSON output (for piping)
  - Plain text (minimal)
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from cli.config import get_config

# ── Console ──────────────────────────────────────────────────────

console = Console()
err_console = Console(stderr=True)


# ── Progress ─────────────────────────────────────────────────────

def get_progress() -> Progress:
    """Return a configured Progress instance for pipeline tracking."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


# ── Severity helpers ─────────────────────────────────────────────

SEVERITY_COLORS = {
    "critical": "red bold",
    "high": "orange_red1",
    "medium": "yellow",
    "low": "blue",
    "informational": "grey70",
    "unknown": "white",
}

SEVERITY_ICONS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "informational": "⚪",
    "unknown": "❓",
}


def severity_tag(severity: str) -> Text:
    """Return a colored severity label."""
    sev = (severity or "unknown").lower()
    color = SEVERITY_COLORS.get(sev, "white")
    icon = SEVERITY_ICONS.get(sev, "❓")
    return Text(f"{icon} {sev.upper():14}", style=color)


# ── Audit display ────────────────────────────────────────────────

def show_audit_started(result: dict) -> None:
    """Show the result of starting an audit."""
    audit_id = result.get("audit_id", "?")
    address = result.get("address", "?")
    chain = result.get("chain", "?")
    state = result.get("state", "pending")

    panel = Panel(
        f"[bold cyan]Audit ID:[/] {audit_id}\n"
        f"[bold]Contract:[/] {address}\n"
        f"[bold]Chain:[/]    {chain}\n"
        f"[bold]State:[/]    [green]{state}[/]",
        title="[bold green]🚀 Audit Started[/]",
        border_style="green",
    )
    console.print(panel)


def show_audit_status(record: dict) -> None:
    """Display a single audit record in detail."""
    if not record:
        err_console.print("[red]No audit record found.[/]")
        return

    aid = record.get("audit_id", "?")
    state = record.get("state", "unknown")
    chain = record.get("chain", "?")
    address = record.get("address", "?")
    program = record.get("program") or "(none)"
    created = record.get("created_at", "")
    duration = record.get("duration_seconds")
    error = record.get("error")
    steps = record.get("steps") or []
    findings = record.get("findings")
    report_path = record.get("report_path")

    # State color
    state_colors = {
        "completed": "green",
        "pending": "yellow",
        "fetching_program": "cyan",
        "fetching_source": "cyan",
        "scanning": "cyan",
        "ai_analysis": "cyan",
        "classifying": "cyan",
        "exploiting": "cyan",
        "reporting": "cyan",
        "notifying": "cyan",
        "fetch_failed": "red",
        "scan_failed": "red",
        "ai_failed": "red",
        "classify_failed": "red",
        "exploit_failed": "red",
        "report_failed": "red",
        "notify_failed": "red",
        "timeout": "red",
        "aborted": "red",
    }
    sc = state_colors.get(state, "white")

    # Finding counts
    finding_count = 0
    critical_count = 0
    high_count = 0
    if findings:
        if isinstance(findings, list):
            finding_count = len(findings)
            for f in findings:
                sev = (f.get("severity") or "").lower()
                if sev == "critical":
                    critical_count += 1
                elif sev == "high":
                    high_count += 1
        elif isinstance(findings, dict):
            fl = findings.get("findings", findings.get("classified_findings", []))
            finding_count = len(fl)
            for f in fl:
                sev = (f.get("severity") or f.get("ai_severity") or "").lower()
                if sev == "critical":
                    critical_count += 1
                elif sev == "high":
                    high_count += 1

    # Build info panel
    info = (
        f"[bold]Audit ID:[/]     {aid}\n"
        f"[bold]State:[/]        [{sc}]{state.upper()}[/]\n"
        f"[bold]Contract:[/]     {address}\n"
        f"[bold]Chain:[/]        {chain}\n"
        f"[bold]Program:[/]      {program}\n"
        f"[bold]Created:[/]      {_fmt_time(created)}\n"
    )
    if duration is not None:
        info += f"[bold]Duration:[/]     {duration:.1f}s\n"
    info += f"[bold]Findings:[/]     {finding_count} total"
    if critical_count:
        info += f"  [red bold]{critical_count} critical[/]"
    if high_count:
        info += f"  [orange_red1]{high_count} high[/]"
    info += "\n"
    if report_path:
        info += f"[bold]Report:[/]       {report_path}\n"
    if error:
        info += f"[bold red]Error:[/]        {error}\n"

    panel = Panel(info, title=f"📋 Audit {aid[:8]}", border_style=sc)
    console.print(panel)

    # Steps table
    if steps:
        step_table = Table(title="Pipeline Steps", box=None)
        step_table.add_column("Step", style="cyan")
        step_table.add_column("Status", width=12)
        step_table.add_column("Duration", width=10)
        step_table.add_column("Result")

        for step in steps:
            s_name = step.get("name", "?")
            s_state = step.get("state", "")
            s_dur = step.get("duration_seconds")
            s_error = step.get("error")
            s_result = step.get("result")

            dur_str = f"{s_dur:.1f}s" if s_dur else "-"
            if s_state in ("completed",):
                status = "[green]✅ OK[/]"
            elif s_state and "failed" in str(s_state):
                status = "[red]❌ FAIL[/]"
            elif s_error:
                status = "[red]❌ ERROR[/]"
            else:
                status = "[yellow]⏳ ...[/]"

            result_str = ""
            if s_result:
                if isinstance(s_result, dict):
                    if s_result.get("status") == "skipped":
                        result_str = f"[dim]skipped: {s_result.get('reason', '')}[/]"
                    else:
                        k = list(s_result.keys())[:2]
                        result_str = ", ".join(k)
                else:
                    result_str = str(s_result)[:60]

            step_table.add_row(s_name, status, dur_str, result_str)

        console.print(step_table)


def show_audits_table(records: list[dict], total: int) -> None:
    """Display a list of audits as a table."""
    if not records:
        console.print("[dim]No audits found.[/]")
        return

    table = Table(
        title=f"Audits (showing {len(records)} of {total})",
        box=None,
        header_style="bold cyan",
    )
    table.add_column("ID", width=10)
    table.add_column("State", width=14)
    table.add_column("Chain", width=10)
    table.add_column("Program", width=14)
    table.add_column("Findings", width=8)
    table.add_column("Duration", width=8)
    table.add_column("Created")

    for r in records:
        aid = r.get("audit_id", "?")[:8]
        state = r.get("state", "?")
        chain = r.get("chain", "?")
        program = (r.get("program") or "-")[:12]
        dur = r.get("duration_seconds")
        created = _fmt_time(r.get("created_at", ""), short=True)
        findings = r.get("findings")
        fcount = len(findings) if isinstance(findings, list) else 0

        sc = "green" if state == "completed" else "red" if "failed" in state else "yellow"
        table.add_row(
            aid,
            f"[{sc}]{state}[/]",
            chain,
            program,
            str(fcount),
            f"{dur:.1f}s" if dur else "-",
            created,
        )

    console.print(table)


# ── Finding display ──────────────────────────────────────────────

def show_findings(findings: list[dict]) -> None:
    """Display a list of security findings."""
    if not findings:
        console.print("[dim]No findings.[/]")
        return

    table = Table(title="Security Findings", box=None, header_style="bold cyan")
    table.add_column("ID", width=8)
    table.add_column("Severity", width=14)
    table.add_column("Tool", width=10)
    table.add_column("Title")
    table.add_column("Location")

    for f in findings:
        fid = f.get("id", f.get("finding_id", "?"))[:8]
        sev = f.get("severity", f.get("ai_severity", "unknown"))
        tool = f.get("tool", "?")
        title = f.get("title", "?")
        loc = (
            f.get("file") or f.get("contract") or ""
        )
        if f.get("line"):
            loc += f":{f['line']}"

        table.add_row(fid, severity_tag(sev), tool, title, loc)

    console.print(table)


# ── Health display ───────────────────────────────────────────────

def show_health(results: list[dict]) -> None:
    """Display health check results."""
    table = Table(title="Service Health", box=None, header_style="bold cyan")
    table.add_column("Service", width=16)
    table.add_column("Status", width=10)
    table.add_column("Details")

    all_healthy = True
    for r in results:
        name = r.get("name", "?")
        status = r.get("status", "unknown")
        if status != "healthy":
            all_healthy = False

        sc = "green" if status == "healthy" else "red"
        detail = ""
        data = r.get("data")
        if data:
            svc = data.get("service", "")
            detail = f"v{data.get('version', '?')}" if svc else ""
        if r.get("error"):
            detail = r["error"]

        table.add_row(name, f"[{sc}]{status}[/]", detail)

    console.print(table)
    if all_healthy:
        console.print("\n[bold green]✅ All services healthy![/]")
    else:
        console.print("\n[bold red]❌ Some services are down![/]")


# ── Stats display ────────────────────────────────────────────────

def show_stats(stats: dict) -> None:
    """Display pipeline statistics."""
    if not stats:
        err_console.print("[red]No stats available.[/]")
        return

    table = Table(title="Pipeline Statistics", box=None)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value")

    for k, v in sorted(stats.items()):
        if isinstance(v, float):
            val = f"{v:.1f}"
        elif isinstance(v, dict):
            val = json.dumps(v, indent=1)[:100]
        else:
            val = str(v)
        table.add_row(k.replace("_", " ").title(), val)

    console.print(table)


# ── Queue display ────────────────────────────────────────────────

def show_queue(items: list[dict]) -> None:
    """Display the priority queue."""
    if not items:
        console.print("[dim]Queue is empty.[/]")
        return

    table = Table(title="Audit Queue (sorted by priority)", box=None, header_style="bold cyan")
    table.add_column("Priority", width=8)
    table.add_column("Address", width=48)
    table.add_column("Chain")
    table.add_column("Program")

    for item in items:
        prio = item.get("priority_score", item.get("priority", 0))
        addr = item.get("address", item.get("contract_id", "?"))[:48]
        chain = item.get("chain", "?")
        prog = item.get("program", "-")

        table.add_row(str(prio), addr, chain, prog)

    console.print(table)


# ── Helpers ──────────────────────────────────────────────────────

def _fmt_time(iso_str: str, short: bool = False) -> str:
    """Format ISO timestamp to human-readable."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if short:
            return dt.strftime("%H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return iso_str[:19]


def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    console.print(json.dumps(data, indent=2, default=str))


# ── Error display ────────────────────────────────────────────────

def show_error(message: str, detail: str = "") -> None:
    """Display an error message."""
    if detail:
        err_console.print(f"[red]Error:[/] {message}")
        err_console.print(f"[dim]{detail}[/]")
    else:
        err_console.print(f"[red]Error:[/] {message}")


# ── Success display ──────────────────────────────────────────────

def show_success(message: str) -> None:
    """Display a success message."""
    console.print(f"[green]✅ {message}[/]")
