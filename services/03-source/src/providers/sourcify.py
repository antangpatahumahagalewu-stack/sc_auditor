"""Sourcify provider — fetches verified source from Sourcify (sourcify.dev).

Sourcify is a community-led service for verifying smart contracts.
It supports all EVM chains and provides full metadata + source files.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import SourceResult

log = structlog.get_logger()

# ── Chain name → chain ID mapping ─────────────────────────

CHAIN_IDS: dict[str, int] = {
    "ethereum": 1,
    "arbitrum": 42161,
    "optimism": 10,
    "polygon": 137,
    "bsc": 56,
    "avalanche": 43114,
    "base": 8453,
    "gnosis": 100,
    "fantom": 250,
    "celo": 42220,
    "linea": 59144,
    "scroll": 534352,
    "polygon_zkevm": 1101,
    "zksync": 324,
    "blast": 81457,
    "mantle": 5000,
    "moonbeam": 1284,
    "cronos": 25,
}

SOURCIFY_BASE = "https://sourcify.dev/server"


class SourcifyProvider:
    """Source provider for Sourcify."""

    name = "sourcify"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def fetch(self, chain: str, address: str) -> SourceResult | None:
        """Fetch verified source code from Sourcify.

        Args:
            chain: Blockchain name. Must be in ``CHAIN_IDS``.
            address: Contract address (0x-prefixed, checksummed or lowercase).

        Returns:
            SourceResult if the contract is fully verified, None otherwise.
        """
        chain_id = CHAIN_IDS.get(chain.lower())
        if not chain_id:
            log.warning("sourcify.unsupported_chain", chain=chain)
            return None

        # Sourcify serves files at: /server/files/{chain_id}/{address}/
        url = f"{SOURCIFY_BASE}/files/{chain_id}/{address}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            log.info("sourcify.fetch", chain=chain, address=address)
            try:
                resp = await client.get(url)
                if resp.status_code == 404:
                    log.info("sourcify.not_verified", chain=chain, address=address)
                    return None
                resp.raise_for_status()
                data: Any = resp.json()
            except httpx.RequestError as exc:
                log.warning("sourcify.request_failed", chain=chain, address=address, error=str(exc))
                return None
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    return None
                log.warning("sourcify.http_error", chain=chain, address=address, status=exc.response.status_code)
                return None

        # Sourcify response is a tree: [{"name": "...", "path": "...", "content": "...", ...}]
        # Flatten into sources dict
        sources: dict[str, str] = {}
        compiler_version: str = ""
        license_: str | None = None

        def _walk(node: Any, prefix: str = "") -> None:
            nonlocal compiler_version, license_
            if isinstance(node, dict):
                name = node.get("name", "")
                path = node.get("path", "")
                content = node.get("content", "")

                # Root metadata node — extract compiler + license
                if path.endswith("metadata.json") and content:
                    try:
                        meta = json.loads(content) if isinstance(content, str) else content
                        if "compiler" in meta:
                            cv = meta["compiler"].get("version", "")
                            compiler_version = cv.lstrip("v")
                        if "sources" in meta:
                            for src_path, src_info in meta["sources"].items():
                                lit = ""
                                if isinstance(src_info, dict):
                                    lit = src_info.get("content", "")
                                elif isinstance(src_info, str):
                                    lit = src_info
                                if lit and src_path not in sources:
                                    sources[src_path] = lit
                        # License from metadata
                        if not license_:
                            license_ = meta.get("license") or None
                    except Exception:
                        pass

                # Actual .sol file
                if name.endswith(".sol") and content:
                    file_path = f"{prefix}/{name}" if prefix else name
                    if path:
                        file_path = path
                    sources[file_path] = content

                # Recurse into children
                children = node.get("children", [])
                base = node.get("path", prefix)
                for child in children:
                    _walk(child, prefix=base)
            elif isinstance(node, list):
                for item in node:
                    _walk(item, prefix=prefix)

        if isinstance(data, list):
            for item in data:
                _walk(item)
        else:
            _walk(data)

        if not sources:
            log.info("sourcify.no_sources_found", chain=chain, address=address)
            return None

        return SourceResult(
            sources=sources,
            compiler_version=compiler_version,
            license=license_,
            provider=self.name,
            constructor_args=None,  # Sourcify does not expose constructor args in API
        )
