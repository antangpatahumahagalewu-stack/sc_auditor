"""Local CLI configuration — ~/.vyper/config.yml

Stores:
  - Orchestrator URL
  - Service URLs (override defaults)
  - Output preferences
  - Docker compose project path
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

# ── Defaults ─────────────────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    # Service URLs (Docker Compose host-side ports)
    "orchestrator_url": "http://localhost:8009",
    "scanner_url": "http://localhost:8003",
    "exploit_url": "http://localhost:8006",
    "reporter_url": "http://localhost:8007",
    "dashboard_url": "http://localhost:8000",
    "notifier_url": "http://localhost:8008",
    "source_url": "http://localhost:8002",
    "immunefi_url": "http://localhost:8001",

    # Docker compose project directory
    "project_dir": "",  # auto-detected if empty

    # Output preferences
    "output_format": "rich",  # rich | json | text
    "color": True,
    "show_progress": True,

    # Docker compose config
    "compose_file": "docker-compose.yml",
    "project_name": "sc_auditor",
}

DEFAULT_CONFIG_PATH = Path.home() / ".vyper" / "config.yml"


# ── Config Manager ───────────────────────────────────────────────

class Config:
    """Manages local CLI configuration stored in ~/.vyper/config.yml."""

    def __init__(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        self._path = path
        self._data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self._load()

    # ── Loading ─────────────────────────────────────────────────

    def _load(self) -> None:
        """Load config from YAML file, merging with defaults."""
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text("utf-8")
            parsed = yaml.safe_load(raw)
            if isinstance(parsed, dict):
                # Merge: override defaults with user values
                self._data = {**DEFAULT_CONFIG, **parsed}
        except (yaml.YAMLError, OSError) as exc:
            print(f"[yellow]Warning:[/] Could not load config {self._path}: {exc}")

    def save(self) -> None:
        """Persist current config to YAML file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(yaml.dump(self._data, default_flow_style=False), "utf-8")

    # ── Access ──────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    @property
    def data(self) -> Dict[str, Any]:
        return dict(self._data)

    @property
    def project_dir(self) -> Path:
        """Auto-detect project directory if not configured."""
        pd = self.get("project_dir", "")
        if pd:
            return Path(pd)
        # Walk up from cwd looking for docker-compose.yml
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            compose = parent / "docker-compose.yml"
            if compose.exists():
                return parent
        return cwd

    # ── Display ─────────────────────────────────────────────────

    def as_table(self) -> list[tuple[str, str]]:
        """Return config as list of (key, value) tuples for display."""
        rows = []
        for k, v in sorted(self._data.items()):
            if k == "project_dir" and not v:
                v = str(self.project_dir)
            rows.append((k, str(v)))
        return rows


# ── Singleton ────────────────────────────────────────────────────

_config_instance: Config | None = None


def get_config() -> Config:
    """Return global Config singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
