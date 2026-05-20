"""Tests for Orchestrator Service (11-orchestrator).

Endpoints:
  GET /health
  GET /audits
  GET /audit/{id}
  POST /audit
  GET /queue
  GET /daemon/status
  POST /daemon/start
  POST /daemon/stop
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestOrchestratorHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, orchestrator_url: str) -> None:
        """GET /health returns 200 with rich data."""
        resp = await async_client.get(f"{orchestrator_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
        data = body.get("data")
        if data:
            for field in ("daemon", "pipeline", "queue_size"):
                assert field in data, f"orchestrator health missing {field}"


@pytest.mark.integration
class TestOrchestratorEndpoints:
    """Audit and management endpoints."""

    @pytest.mark.asyncio
    async def test_list_audits(self, async_client: httpx.AsyncClient, orchestrator_url: str) -> None:
        """GET /audits returns audit list."""
        resp = await async_client.get(f"{orchestrator_url}/audits")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
        assert "data" in body

    @pytest.mark.asyncio
    async def test_get_audit_missing(self, async_client: httpx.AsyncClient, orchestrator_url: str) -> None:
        """GET /audit/{id} with nonexistent ID returns 404."""
        resp = await async_client.get(f"{orchestrator_url}/audit/__nonexistent__")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_queue(self, async_client: httpx.AsyncClient, orchestrator_url: str) -> None:
        """GET /queue returns the current queue."""
        resp = await async_client.get(f"{orchestrator_url}/queue")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_daemon_status(self, async_client: httpx.AsyncClient, orchestrator_url: str) -> None:
        """GET /daemon/status returns daemon state."""
        resp = await async_client.get(f"{orchestrator_url}/daemon/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
