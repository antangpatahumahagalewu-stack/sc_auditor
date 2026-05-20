"""Tests for Dashboard Service (15-dashboard).

Endpoints:
  GET /health
  GET /api/cases
  GET /api/cases/stats
  GET /api/cases/{id}
  POST /api/cases
  POST /api/cases/{id}/close
  GET /api/health/graph
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestDashboardHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, dashboard_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{dashboard_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"


@pytest.mark.integration
class TestDashboardEndpoints:
    """Dashboard Case Management endpoints."""

    @pytest.mark.asyncio
    async def test_list_cases(self, async_client: httpx.AsyncClient, dashboard_url: str) -> None:
        """GET /api/cases returns case list."""
        resp = await async_client.get(f"{dashboard_url}/api/cases")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_case_stats(self, async_client: httpx.AsyncClient, dashboard_url: str) -> None:
        """GET /api/cases/stats returns statistics."""
        resp = await async_client.get(f"{dashboard_url}/api/cases/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
