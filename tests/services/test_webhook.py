"""Tests for Webhook Service (12-webhook).

Endpoints:
  GET /health
  GET /logs
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestWebhookHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, webhook_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{webhook_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"


@pytest.mark.integration
class TestWebhookEndpoints:
    """Webhook log endpoints."""

    @pytest.mark.asyncio
    async def test_logs(self, async_client: httpx.AsyncClient, webhook_url: str) -> None:
        """GET /logs returns delivery log."""
        resp = await async_client.get(f"{webhook_url}/logs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
