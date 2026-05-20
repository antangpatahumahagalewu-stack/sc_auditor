"""Tests for Config Service (01-config).

Endpoints:
  GET  /health
  GET  /config/{key}
  PUT  /config/{key}
  DELETE /config/{key}
  PUT  /config/bulk
  GET  /config/
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestConfigHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, config_url: str) -> None:
        """GET /health returns 200 with flat HealthResponse (Type A)."""
        resp = await async_client.get(f"{config_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "config"
        assert "version" in body
        assert "timestamp" in body


@pytest.mark.integration
class TestConfigCRUD:
    """Config CRUD operations."""

    TEST_KEY = "vyper_test_key"
    TEST_VALUE = {"test": True, "purpose": "integration"}

    @pytest.mark.asyncio
    async def test_upsert(self, async_client: httpx.AsyncClient, config_url: str) -> None:
        """PUT /config/{key} creates or updates a value."""
        resp = await async_client.put(f"{config_url}/config/{self.TEST_KEY}", json={"value": self.TEST_VALUE})
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_get(self, async_client: httpx.AsyncClient, config_url: str) -> None:
        """GET /config/{key} retrieves stored value."""
        await async_client.put(f"{config_url}/config/{self.TEST_KEY}", json={"value": self.TEST_VALUE})
        resp = await async_client.get(f"{config_url}/config/{self.TEST_KEY}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
        data = body.get("data", {})
        assert self.TEST_KEY in data

    @pytest.mark.asyncio
    async def test_get_missing_returns_404(self, async_client: httpx.AsyncClient, config_url: str) -> None:
        """GET /config/{key} with nonexistent key returns 404."""
        resp = await async_client.get(f"{config_url}/config/__nonexistent_key__")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete(self, async_client: httpx.AsyncClient, config_url: str) -> None:
        """DELETE /config/{key} removes a key."""
        await async_client.put(f"{config_url}/config/{self.TEST_KEY}", json={"value": self.TEST_VALUE})
        resp = await async_client.delete(f"{config_url}/config/{self.TEST_KEY}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list(self, async_client: httpx.AsyncClient, config_url: str) -> None:
        """GET /config/ returns all keys."""
        resp = await async_client.get(f"{config_url}/config/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
        assert isinstance(body.get("data"), dict)
