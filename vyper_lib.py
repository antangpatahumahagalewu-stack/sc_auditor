"""Vyper Shared Library — Common utilities for all 12 services."""

import json
import os
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field

# ── Constants ──────────────────────────────────────────────

DATA_DIR = Path("/data")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CONFIG_URL = os.getenv("CONFIG_URL", "http://config:8000")

# ── Logging ────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger()


# ── Pydantic Models ────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = ""
    version: str = "0.1.0"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: str = "internal_error"


# ── JSON File Helpers ──────────────────────────────────────

def read_json(path: Path) -> Any:
    """Read JSON file, return None if not exists or invalid."""
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, PermissionError) as e:
        log.error("json_read_error", path=str(path), error=str(e))
        return None


def write_json(path: Path, data: Any) -> bool:
    """Write JSON file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        tmp.replace(path)
        return True
    except Exception as e:
        log.error("json_write_error", path=str(path), error=str(e))
        if tmp.exists():
            tmp.unlink()
        return False


# ── Config Client ──────────────────────────────────────────

import httpx


# ── Shared HTTP Client (connection pooling) ────────────────

_SHARED_CLIENT: httpx.AsyncClient | None = None


def _get_shared_client() -> httpx.AsyncClient:
    """Return a shared httpx client with connection pooling."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None:
        _SHARED_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
        )
    return _SHARED_CLIENT


# ── Config Client ──────────────────────────────────────────


class ConfigClient:
    """HTTP client to fetch config from Config Service.

    Uses a shared httpx.AsyncClient for connection pooling.
    """

    def __init__(self, base_url: str = CONFIG_URL):
        self.base_url = base_url

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        client = _get_shared_client()
        try:
            resp = await client.get(f"{self.base_url}/config/{key}")
            if resp.status_code == 200:
                return resp.json().get("value", default)
        except httpx.RequestError as e:
            log.warning("config_unreachable", key=key, error=str(e))
        return default

    async def get_all(self) -> dict:
        """Get all config."""
        client = _get_shared_client()
        try:
            resp = await client.get(f"{self.base_url}/config/")
            if resp.status_code == 200:
                return resp.json()
        except httpx.RequestError:
            pass
        return {}


# ── JSON Standard-Input Parser ─────────────────────────────


def parse_standard_input_json(raw: str) -> dict[str, str] | None:
    """Parse Etherscan/Blockscout standard JSON input format.

    Handles both {{...}} (double-braced) and {...} (single) wrapping.
    Returns dict of source path → source code, or None if not parseable.
    """
    if not raw.startswith("{"):
        return None
    cleaned = raw
    if cleaned.startswith("{{") and cleaned.endswith("}}"):
        cleaned = cleaned[1:-1]
    try:
        parsed = json.loads(cleaned)
        std_sources = parsed.get("sources", {})
        if not std_sources:
            return None
        sources: dict[str, str] = {}
        for path, info in std_sources.items():
            content = ""
            if isinstance(info, str):
                content = info
            elif isinstance(info, dict):
                content = info.get("content", "")
            if content:
                sources[path] = content
        return sources
    except (json.JSONDecodeError, TypeError):
        return None
