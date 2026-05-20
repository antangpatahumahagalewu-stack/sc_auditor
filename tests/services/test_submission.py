"""Tests for Submission Service (16-submission).

Endpoints:
  GET /health
  POST /submit
  GET /status/{submission_id}
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
class TestSubmissionHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, async_client: httpx.AsyncClient, submission_url: str) -> None:
        """GET /health returns 200."""
        resp = await async_client.get(f"{submission_url}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["status"] == "ok"
