"""Tests for Agent Service (14-agent).

Endpoints:
  GET /health
  GET /team/structure
  GET /team/sessions
  POST /agent/run
  GET /skills
  GET /memory
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestAgentHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, agent_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{agent_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"


@pytest.mark.integration
class TestAgentEndpoints:
    """Agent team and memory endpoints."""

    @pytest.mark.asyncio
    async def test_team_structure(self, async_client: httpx.AsyncClient, agent_url: str) -> None:
        """GET /team/structure returns agent team configuration."""
        resp = await async_client.get(f"{agent_url}/team/structure")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_skills(self, async_client: httpx.AsyncClient, agent_url: str) -> None:
        """GET /skills returns available agent skills."""
        resp = await async_client.get(f"{agent_url}/skills")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_memory(self, async_client: httpx.AsyncClient, agent_url: str) -> None:
        """GET /memory returns agent memory state."""
        resp = await async_client.get(f"{agent_url}/memory")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
