"""Tests for AI Service (06-ai).

Endpoints:
  GET /health
  POST /analyze
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestAIHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, ai_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{ai_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
        assert "data" in body
