"""Custom Textual widgets for Vyper Monitor."""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from typing import Any

from rich.text import Text
from rich.panel import Panel
from textual.reactive import reactive
from textual.widgets import Static, RichLog

# ── Clipboard helper (cross-platform) ─────────────────────────

_RICH_TAG_RE = re.compile(r"\[/?\w+(?:[^\]]*)?\]")


def strip_rich_markup(text: str) -> str:
    """Remove Rich markup tags like [bold], [dim], [green], [/], etc."""
    return _RICH_TAG_RE.sub("", text)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    if not text.strip():
        return False
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
        return True
    except ImportError:
        pass
    except Exception:
        pass
    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(
                ["clip"], stdin=subprocess.PIPE, shell=True,
                text=True, encoding="utf-8", errors="replace",
            )
            proc.communicate(input=text)
            return proc.returncode == 0
        elif sys.platform == "darwin":
            proc = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
            )
            proc.communicate(input=text)
            return proc.returncode == 0
        else:
            for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "-i", "-b"]):
                try:
                    proc = subprocess.Popen(
                        cmd, stdin=subprocess.PIPE,
                        text=True, encoding="utf-8", errors="replace",
                    )
                    proc.communicate(input=text)
                    if proc.returncode == 0:
                        return True
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return False


class StatusBar(Static):
    """Top status bar: service health count, pipeline status, queue size."""

    health_data: reactive[list[dict]] = reactive([])
    queue_size: reactive[int] = reactive(0)
    pipeline_active: reactive[int] = reactive(0)

    def render(self) -> Panel:
        total = 19
        alive = sum(
            1 for s in self.health_data
            if isinstance(s, dict) and s.get("status") == "healthy"
        )
        color = "green" if alive == total else "yellow" if alive >= total // 2 else "red"
        alive_icon = "✅" if alive == total else "⚠️" if alive > total // 2 else "❌"

        text = Text.assemble(
            (" ◆ ", "bold cyan"),
            ("VYPER Monitor", "bold white"),
            (" — ", "dim"),
            (f"{alive}/{total}", f"bold {color}"),
            (f" {alive_icon}  ", "bold"),
            ("Pipeline: ", "dim"),
            (f"{self.pipeline_active}", "bold green"),
            (" active  ", "dim"),
            ("Queue: ", "dim"),
            (f"{self.queue_size}", "bold yellow" if self.queue_size > 0 else "green"),
        )
        return Panel(text, border_style="cyan", padding=(0, 1))


class EventLog(RichLog):
    """Live event log with auto-scroll and level-based color coding."""

    paused: reactive[bool] = reactive(False)
    filter_level: reactive[str] = reactive("ALL")

    def __init__(self) -> None:
        super().__init__(highlight=True, markup=True, min_width=80, max_lines=500)
        self._event_store: list[dict] = []

    def add_event(self, event: dict) -> None:
        """Append a single event, respecting filter."""
        self._event_store.append(event)
        if len(self._event_store) > 500:
            self._event_store = self._event_store[-500:]

        if self.filter_level != "ALL" and event.get("level") != self.filter_level:
            return
        self.write(self._format(event))

    def get_all_events_text(self) -> str:
        """Return all stored events as plain text (for clipboard copy)."""
        lines: list[str] = []
        for ev in self._event_store:
            ts = ev.get("time", "")
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)[:19]
            level = ev.get("level", "INFO")
            msg = ev.get("message", "")
            lines.append(f"[{ts_str}] {level}: {msg}")
        return "\n".join(lines)

    def get_visible_events_text(self) -> str:
        """Return only events matching current filter as plain text."""
        lines: list[str] = []
        for ev in self._event_store:
            if self.filter_level != "ALL" and ev.get("level") != self.filter_level:
                continue
            ts = ev.get("time", "")
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)[:19]
            level = ev.get("level", "INFO")
            msg = ev.get("message", "")
            lines.append(f"[{ts_str}] {level}: {msg}")
        return "\n".join(lines)

    def copy_events(self, visible_only: bool = False) -> bool:
        """Copy events to clipboard. Returns True on success."""
        if visible_only:
            text = self.get_visible_events_text()
        else:
            text = self.get_all_events_text()
        return copy_to_clipboard(text) if text else False

    def add_events(self, events: list[dict]) -> None:
        """Append multiple events."""
        for ev in events:
            self.add_event(ev)

    def watch_filter_level(self, old: str, new: str) -> None:
        """Rebuild display when filter changes."""
        self.clear()
        for ev in self._event_store[-200:]:
            if new == "ALL" or ev.get("level") == new:
                self.write(self._format(ev))

    @staticmethod
    def _format(event: dict) -> Text:
        ts = event.get("time", datetime.now())
        ts_str = ts.strftime("%H:%M:%S") if isinstance(ts, datetime) else str(ts)[:8]
        level = event.get("level", "INFO")
        msg = event.get("message", "")
        icon = event.get("icon", "▪")

        STYLES = {
            "SUCCESS": ("green", "bold"),
            "INFO": ("green", ""),
            "WARNING": ("yellow", ""),
            "ERROR": ("red", "bold"),
            "CRITICAL": ("bold blue", "bold"),
        }
        style, _ = STYLES.get(level, ("white", ""))

        return Text.assemble(
            (ts_str, "dim"),
            "  ",
            (icon, style),
            "  ",
            (msg, "white" if level not in ("ERROR", "CRITICAL") else "bold red"),
        )


class SummaryBar(Static):
    """Bottom summary: audit stats + service health dots."""

    stats: reactive[dict] = reactive({})
    health_data: reactive[list[dict]] = reactive([])

    def render(self) -> Panel:
        total = self.stats.get("total_audits", 0)
        completed = self.stats.get("completed", 0)
        failed = self.stats.get("failed", 0)
        findings = self.stats.get("total_findings", 0)
        tp = self.stats.get("tp", 0)
        fp = self.stats.get("fp", 0)
        fn = self.stats.get("fn", 0)
        rate = self.stats.get("success_rate", 0)
        rate_str = f"{rate:.0f}%" if isinstance(rate, (int, float)) else "N/A"

        text = Text.assemble(
            (" 📊 ", "dim"),
            (f"{total} audits", "bold"),
            (" · ", "dim"),
            (f"{completed} ✅", "green"),
            (" ", ""),
            (f"{failed} ❌", "red" if failed > 0 else "dim"),
            (" · ", "dim"),
            (f"{findings} findings", "bold"),
            (" · ", "dim"),
            (f"TP {tp}", "green"),
            (" · ", "dim"),
            (f"FP {fp}", "yellow"),
            (" · ", "dim"),
            (f"FN {fn}", "red"),
            (" · ", "dim"),
            (f"{rate_str}", "bold cyan"),
            ("  ", ""),
            ("🖥️ ", "dim"),
        )

        for svc in self.health_data:
            if not isinstance(svc, dict):
                continue
            color = "green" if svc.get("status") == "healthy" else "red"
            text.append_text(Text("●", style=color))
            text.append_text(Text(" ", style="dim"))

        return Panel(text, border_style="dim", padding=(0, 1))


class ShortcutsBar(Static):
    """Bottom bar with keyboard shortcuts."""

    def render(self) -> Panel:
        text = Text.assemble(
            (" [/]", "bold"),
            (" Search  ", "dim"),
            (" [Space]", "bold"),
            (" Pause  ", "dim"),
            (" [1-6]", "bold"),
            (" Filter  ", "dim"),
            (" [↑↓]", "bold"),
            (" Scroll  ", "dim"),
            (" [r]", "bold"),
            (" Refresh  ", "dim"),
            (" [Q]", "bold"),
            (" Exit", "dim"),
        )
        return Panel(text, border_style="dim", padding=(0, 1))
