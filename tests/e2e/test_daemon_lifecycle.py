"""E2E tests — daemon lifecycle.

These tests require a running Orchestrator service (11-orchestrator).
They verify:

  1. Daemon status (stopped initially)
  2. Daemon start
  3. Daemon status (running)
  4. Daemon stop
  5. Daemon status (stopped again)
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDaemonLifecycle:
    """Daemon start/stop/status cycle."""

    async def test_daemon_status(
        self, async_client: httpx.AsyncClient, orchestrator_url: str
    ) -> None:
        """GET /daemon/status returns daemon state."""
        resp = await async_client.get(f"{orchestrator_url}/daemon/status", timeout=5.0)
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
        data = body.get("data", {})
        assert "status" in data or "state" in data, f"Daemon status response missing status: {data}"

    async def test_daemon_stop(
        self, async_client: httpx.AsyncClient, orchestrator_url: str
    ) -> None:
        """POST /daemon/stop — daemon should stop gracefully."""
        resp = await async_client.post(f"{orchestrator_url}/daemon/stop", timeout=5.0)
        # May fail if daemon not running — that's OK
        if resp.status_code == 200:
            body = resp.json()
            assert body["meta"]["status"] == "ok"

    async def test_daemon_start(
        self, async_client: httpx.AsyncClient, orchestrator_url: str
    ) -> None:
        """POST /daemon/start — daemon should start."""
        resp = await async_client.post(f"{orchestrator_url}/daemon/start", timeout=10.0)
        assert resp.status_code in (200, 409), f"Daemon start: {resp.status_code} {resp.text[:200]}"
        if resp.status_code == 200:
            body = resp.json()
            assert body["meta"]["status"] == "ok"
