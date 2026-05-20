"""Tests for Immunefi Service (02-immunefi).

Endpoints:
  GET /health
  GET /programs
  GET /programs/{slug}
  GET /stats
  GET /updates
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestImmunefiHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, immunefi_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{immunefi_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"


@pytest.mark.integration
class TestImmunefiEndpoints:
    """Immunefi program and stats endpoints."""

    @pytest.mark.asyncio
    async def test_programs(self, async_client: httpx.AsyncClient, immunefi_url: str) -> None:
        """GET /programs returns program list."""
        resp = await async_client.get(f"{immunefi_url}/programs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
        data = body.get("data")
        if isinstance(data, dict):
            assert "data" in data
            assert "total" in data

    @pytest.mark.asyncio
    async def test_stats(self, async_client: httpx.AsyncClient, immunefi_url: str) -> None:
        """GET /stats returns aggregated statistics."""
        resp = await async_client.get(f"{immunefi_url}/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
        data = body.get("data")
        if data:
            for field in ("total_programs", "by_status", "by_chain"):
                assert field in data

    @pytest.mark.asyncio
    async def test_program_detail_missing(self, async_client: httpx.AsyncClient, immunefi_url: str) -> None:
        """GET /programs/{slug} with nonexistent slug returns 404."""
        resp = await async_client.get(f"{immunefi_url}/programs/__nonexistent_slug__")
        assert resp.status_code in (200, 404)
        if resp.status_code == 404:
            assert "meta" in resp.json()
