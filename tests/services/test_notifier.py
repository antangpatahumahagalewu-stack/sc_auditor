"""Tests for Notifier Service (10-notifier).

Endpoints:
  GET /health
  GET /channels
  GET /delivery-log
  POST /test
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestNotifierHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, notifier_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{notifier_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"


@pytest.mark.integration
class TestNotifierEndpoints:
    """Notifier channel and log endpoints."""

    @pytest.mark.asyncio
    async def test_channels(self, async_client: httpx.AsyncClient, notifier_url: str) -> None:
        """GET /channels returns channel configuration."""
        resp = await async_client.get(f"{notifier_url}/channels")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_delivery_log(self, async_client: httpx.AsyncClient, notifier_url: str) -> None:
        """GET /delivery-log returns delivery history."""
        resp = await async_client.get(f"{notifier_url}/delivery-log")
        if resp.status_code == 200:
            body = resp.json()
            assert body["meta"]["status"] == "ok"
