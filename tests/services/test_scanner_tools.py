"""Tests for Scanner Tool Services (04a-04d, 05).

These services are the individual scanner tool microservices:
  04a-scanner-slither  — Slither (static analysis)
  04b-scanner-echidna  — Echidna (fuzzing)
  04c-scanner-forge    — Forge (build verification)
  04d-scanner-halmos   — Halmos (formal verification)
  05-scanner-mythril   — Mythril (symbolic execution)
"""

from __future__ import annotations

import httpx
import pytest


SCANNER_TOOL_URLS = [
    ("04a-scanner-slither", "scanner_slither_url"),
    ("04b-scanner-echidna", "scanner_echidna_url"),
    ("04c-scanner-forge", "scanner_forge_url"),
    ("04d-scanner-halmos", "scanner_halmos_url"),
    ("05-scanner-mythril", "scanner_mythril_url"),
]


class TestScannerToolHealth:
    """All 5 scanner tool health endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name,fixture_name", SCANNER_TOOL_URLS)
    async def test_health(self, async_client: httpx.AsyncClient, name: str, fixture_name: str, request) -> None:
        """GET /health returns 200 for each scanner tool."""
        url = request.getfixturevalue(fixture_name)
        resp = await async_client.get(f"{url}/health", timeout=10.0)
        assert resp.status_code == 200, f"{name}: expected 200, got {resp.status_code}"
        body = resp.json()
        # May be flat or wrapped
        if "meta" in body:
            assert body["meta"]["status"] == "ok"
        elif "status" in body:
            assert body["status"] == "ok"
