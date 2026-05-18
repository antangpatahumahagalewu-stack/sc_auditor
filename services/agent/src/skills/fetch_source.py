"""Skill: Fetch smart contract source code from multiple providers."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from src.skills.base import BaseSkill

log = structlog.get_logger()

SOURCE_URL = "http://source:8002"


class FetchSourceSkill(BaseSkill):
    """Mengambil source code smart contract dari Etherscan, Sourcify, GitHub, dll."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @property
    def name(self) -> str:
        return "fetch_source"

    @property
    def description(self) -> str:
        return (
            "Mengambil source code smart contract dari berbagai provider. "
            "Bisa fetch dari contract address + chain, atau dari URL GitHub. "
            "Hasilnya berupa file-file .sol beserta metadata compiler."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "address": {
                "type": "string",
                "description": "Contract address (0x...) — required jika fetch dari blockchain",
                "required": False,
            },
            "chain": {
                "type": "string",
                "description": "Chain name: ethereum, arbitrum, polygon, etc",
                "required": False,
            },
            "url": {
                "type": "string",
                "description": "URL GitHub atau Sourcify — alternatif dari address+chain",
                "required": False,
            },
            "program_slug": {
                "type": "string",
                "description": "Immunefi program slug — untuk ambil source dari repositori program",
                "required": False,
            },
        }

    async def run(self, **kwargs: Any) -> Any:
        body: dict[str, Any] = {}

        if kwargs.get("address") and kwargs.get("chain"):
            body["address"] = kwargs["address"]
            body["chain"] = kwargs["chain"]
        elif kwargs.get("url"):
            body["url"] = kwargs["url"]
        elif kwargs.get("program_slug"):
            body["program_slug"] = kwargs["program_slug"]
        else:
            return {"error": "Provide address+chain, url, or program_slug"}

        if kwargs.get("contract_name"):
            body["contract_name"] = kwargs["contract_name"]

        resp = await self._client.post(f"{SOURCE_URL}/fetch", json=body)
        resp.raise_for_status()
        data = resp.json()

        result: dict[str, Any] = {
            "files": {},
            "compiler": None,
            "contract_name": None,
        }

        source_data = data.get("data", {})
        if isinstance(source_data, dict):
            result["files"] = source_data.get("files", {})
            result["compiler"] = source_data.get("compiler_version")
            result["contract_name"] = source_data.get("contract_name")
            result["source_path"] = source_data.get("source_path")

        file_count = len(result["files"])
        file_names = list(result["files"].keys())
        result["_summary"] = f"Found {file_count} file(s): {', '.join(file_names[:5])}"

        return result
