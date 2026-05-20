"""Tests for Source Service (03-source).

Endpoints:
  GET  /health
  GET  /source/{audit_id}
  GET  /source/
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestSourceHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, source_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{source_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
        assert "data" in body


@pytest.mark.integration
class TestSourceEndpoints:
    """Source retrieval endpoints."""

    @pytest.mark.asyncio
    async def test_list_sources(self, async_client: httpx.AsyncClient, source_url: str) -> None:
        """GET /source/ returns a list (possibly empty)."""
        resp = await async_client.get(f"{source_url}/source/")
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            body = resp.json()
            assert body["meta"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_get_source_missing(self, async_client: httpx.AsyncClient, source_url: str) -> None:
        """GET /source/{id} with nonexistent audit returns 404."""
        resp = await async_client.get(f"{source_url}/source/__nonexistent__")
        assert resp.status_code == 404
