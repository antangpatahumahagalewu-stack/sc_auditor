"""pytest fixtures for Vyper integration tests.

Service URLs default to ``localhost`` ports matching the Docker Compose
mapping and can be overridden via environment variables, e.g.::

    $env:CONFIG_URL = "http://config:8000"
    pytest
"""

from __future__ import annotations

import os

import httpx
import pytest


# ── Service URL defaults (Docker Compose host ports) ────────────

_SERVICE_URLS: dict[str, str] = {
    "config": "http://localhost:8011",
    "immunefi": "http://localhost:8001",
    "source": "http://localhost:8002",
    "scanner": "http://localhost:8003",
    "ai": "http://localhost:8004",
    "classifier": "http://localhost:8005",
    "exploit": "http://localhost:8006",
    "reporter": "http://localhost:8007",
    "notifier": "http://localhost:8008",
    "orchestrator": "http://localhost:8009",
    "webhook": "http://localhost:8010",
    "upkeep": "http://localhost:8012",
}


def _service_url(name: str) -> str:
    """Return the URL for a service, preferring an env var override."""
    return os.environ.get(f"{name.upper()}_URL", _SERVICE_URLS[name])


# ── pytest-asyncio / anyio ──────────────────────────────────────


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Return the async backend for pytest-asyncio/pytest-anyio."""
    return "asyncio"


# ── HTTP client ─────────────────────────────────────────────────


@pytest.fixture(scope="session")
async def async_client() -> httpx.AsyncClient:
    """Shared HTTP client for all integration tests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


# ── Individual service URL fixtures ─────────────────────────────


@pytest.fixture()
def config_url() -> str:
    """Config Service URL."""
    return _service_url("config")


@pytest.fixture()
def immunefi_url() -> str:
    """Immunefi Service URL."""
    return _service_url("immunefi")


@pytest.fixture()
def source_url() -> str:
    """Source Service URL."""
    return _service_url("source")


@pytest.fixture()
def scanner_url() -> str:
    """Scanner Service URL."""
    return _service_url("scanner")


@pytest.fixture()
def ai_url() -> str:
    """AI Service URL."""
    return _service_url("ai")


@pytest.fixture()
def classifier_url() -> str:
    """Classifier Service URL."""
    return _service_url("classifier")


@pytest.fixture()
def exploit_url() -> str:
    """Exploit Service URL."""
    return _service_url("exploit")


@pytest.fixture()
def reporter_url() -> str:
    """Reporter Service URL."""
    return _service_url("reporter")


@pytest.fixture()
def notifier_url() -> str:
    """Notifier Service URL."""
    return _service_url("notifier")


@pytest.fixture()
def orchestrator_url() -> str:
    """Orchestrator Service URL."""
    return _service_url("orchestrator")


@pytest.fixture()
def webhook_url() -> str:
    """Webhook Service URL."""
    return _service_url("webhook")


@pytest.fixture()
def upkeep_url() -> str:
    """Upkeep Service URL."""
    return _service_url("upkeep")
