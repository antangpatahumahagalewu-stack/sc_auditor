"""Tests for Scanner Service (04-scanner, legacy monolith).

Endpoints:
  GET  /health
  GET  /scan/{audit_id}
  GET  /status
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestScannerHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, scanner_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{scanner_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"


@pytest.mark.integration
class TestScannerEndpoints:
    """Scanner operation endpoints."""

    @pytest.mark.asyncio
    async def test_status(self, async_client: httpx.AsyncClient, scanner_url: str) -> None:
        """GET /status returns tool statuses."""
        resp = await async_client.get(f"{scanner_url}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_scan_missing(self, async_client: httpx.AsyncClient, scanner_url: str) -> None:
        """GET /scan/{id} with nonexistent audit returns 404."""
        resp = await async_client.get(f"{scanner_url}/scan/__nonexistent__")
        assert resp.status_code == 404
