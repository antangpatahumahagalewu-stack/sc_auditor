"""Skill: Run static analysis on smart contracts (Slither, Mythril, Echidna)."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from src.skills.base import BaseSkill

log = structlog.get_logger()

SCANNER_URL = "http://scanner:8000"


class ScanContractSkill(BaseSkill):
    """Menjalankan static analysis tools pada smart contract."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @property
    def name(self) -> str:
        return "scan_contract"

    @property
    def description(self) -> str:
        return (
            "Menjalankan static analysis tools (Slither, Mythril, Echidna) "
            "pada smart contract source code. Mengembalikan daftar findings "
            "dengan severity, lokasi, dan deskripsi."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "sources": {
                "type": "object",
                "description": "Dictionary: filename → source code. Required.",
                "required": True,
            },
            "tools": {
                "type": "array",
                "description": "Tools to run: ['slither'], ['mythril'], ['echidna'], or all",
                "required": False,
            },
            "contract_name": {
                "type": "string",
                "description": "Nama kontrak utama (untuk Echidna)",
                "required": False,
            },
            "compiler": {
                "type": "string",
                "description": "Solidity compiler version (e.g. 0.8.20)",
                "required": False,
            },
        }

    async def run(self, **kwargs: Any) -> Any:
        sources = kwargs.get("sources", {})
        if not sources:
            return {"error": "sources required"}

        tools = kwargs.get("tools", ["slither", "mythril", "echidna"])

        body = {
            "sources": sources,
            "tools": tools,
            "contract_name": kwargs.get("contract_name", ""),
            "compiler": kwargs.get("compiler", ""),
        }

        resp = await self._client.post(f"{SCANNER_URL}/scan", json=body)
        resp.raise_for_status()
        data = resp.json()

        scan_data = data.get("data", {})

        findings = scan_data.get("findings", [])
        summary = {
            "total": len(findings),
            "critical": sum(1 for f in findings if f.get("severity") == "critical"),
            "high": sum(1 for f in findings if f.get("severity") == "high"),
            "medium": sum(1 for f in findings if f.get("severity") == "medium"),
            "low": sum(1 for f in findings if f.get("severity") == "low"),
            "tools_run": scan_data.get("tools_run", tools),
        }

        return {
            "findings": findings,
            "summary": summary,
            "audit_id": scan_data.get("audit_id"),
            "tool_results": scan_data.get("tool_results", {}),
        }
