"""Tests for Upkeep Service (13-upkeep).

Endpoints:
  GET /health
  GET /status
  GET /logs
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestUpkeepHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, upkeep_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{upkeep_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"


@pytest.mark.integration
class TestUpkeepEndpoints:
    """Scheduler status and logs."""

    @pytest.mark.asyncio
    async def test_status(self, async_client: httpx.AsyncClient, upkeep_url: str) -> None:
        """GET /status returns scheduler state."""
        resp = await async_client.get(f"{upkeep_url}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_logs(self, async_client: httpx.AsyncClient, upkeep_url: str) -> None:
        """GET /logs returns job history."""
        resp = await async_client.get(f"{upkeep_url}/logs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
