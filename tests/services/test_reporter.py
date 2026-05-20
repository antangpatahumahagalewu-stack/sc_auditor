"""Tests for Reporter Service (09-reporter).

Endpoints:
  GET /health
  POST /generate
  GET /reports
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestReporterHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, reporter_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{reporter_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"


@pytest.mark.integration
class TestReporterEndpoints:
    """Report generation and listing."""

    @pytest.mark.asyncio
    async def test_list_reports(self, async_client: httpx.AsyncClient, reporter_url: str) -> None:
        """GET /reports returns a list."""
        resp = await async_client.get(f"{reporter_url}/reports")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
