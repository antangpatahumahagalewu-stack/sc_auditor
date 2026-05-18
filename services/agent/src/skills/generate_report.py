"""Skill: Generate audit reports in Immunefi-ready format."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from src.skills.base import BaseSkill

log = structlog.get_logger()

REPORTER_URL = "http://reporter:8007"


class GenerateReportSkill(BaseSkill):
    """Menghasilkan laporan audit — format Immunefi-ready dan full internal."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @property
    def name(self) -> str:
        return "generate_report"

    @property
    def description(self) -> str:
        return (
            "Menghasilkan laporan audit smart contract. Dua format: "
            "'immunefi' untuk laporan siap-submit ke Immunefi (hanya TP), "
            "dan 'full' untuk laporan lengkap dengan semua temuan, metrik, dan analisis. "
            "Output dalam format Markdown."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "audit_id": {
                "type": "string",
                "description": "Audit session ID. Required.",
                "required": True,
            },
            "format": {
                "type": "string",
                "description": "'immunefi' untuk submit-ready, 'full' untuk laporan lengkap",
                "required": False,
            },
            "findings": {
                "type": "array",
                "description": "List of analyzed findings with AI verdicts",
                "required": False,
            },
            "contract_name": {
                "type": "string",
                "description": "Nama kontrak yang diaudit",
                "required": False,
            },
            "program_name": {
                "type": "string",
                "description": "Nama program Immunefi",
                "required": False,
            },
        }

    async def run(self, **kwargs: Any) -> Any:
        audit_id = kwargs.get("audit_id", "")
        if not audit_id:
            return {"error": "audit_id required"}

        body = {
            "audit_id": audit_id,
            "format": kwargs.get("format", "immunefi"),
        }

        resp = await self._client.post(f"{REPORTER_URL}/generate", json=body)
        resp.raise_for_status()
        data = resp.json()

        report_data = data.get("data", {})
        return {
            "report_id": report_data.get("report_id"),
            "format": report_data.get("format"),
            "content": report_data.get("content", ""),
            "summary": {
                "total_findings": report_data.get("total_findings", 0),
                "critical": report_data.get("critical_count", 0),
                "high": report_data.get("high_count", 0),
                "medium": report_data.get("medium_count", 0),
                "low": report_data.get("low_count", 0),
                "overall_score": report_data.get("overall_score"),
            },
        }
