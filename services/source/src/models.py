"""Pydantic models for the Vyper Source Service.

All request/response models follow the Vyper standard format:
  {"data": ..., "meta": {"status": "ok", "timestamp": "..."}}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Source ─────────────────────────────────────────────────


class SourceFile(BaseModel):
    """A single source file from a verified contract.

    Attributes:
        name: Relative file path (e.g. "contracts/Token.sol").
        content: Full source code of the file.
    """

    name: str
    content: str


class SourceResult(BaseModel):
    """The result of a successful source fetch.

    Attributes:
        sources: Dictionary mapping file names to their source content.
        compiler_version: Solidity compiler version (e.g. "0.8.20").
        license: SPDX license identifier, if detected.
        provider: Name of the provider that returned this result.
        constructor_args: Constructor arguments ABI-encoded hex string, if available.
    """

    sources: dict[str, str]
    compiler_version: str
    license: str | None = None
    provider: str
    constructor_args: str | None = None


# ── Requests ───────────────────────────────────────────────


class FetchRequest(BaseModel):
    """Request body for POST /fetch.

    Attributes:
        chain: Blockchain name (e.g. "ethereum", "polygon").
        address: Contract address (checksummed or lowercase).
        providers: Optional ordered list of providers to try.
                   Defaults to all available providers.
    """

    chain: str
    address: str
    providers: list[str] | None = None


# ── Providers ──────────────────────────────────────────────


class Provider(BaseModel):
    """Descriptor for a source provider.

    Attributes:
        name: Provider identifier (e.g. "etherscan").
        available: Whether the provider responded to connectivity check.
        priority: Default priority order (lower = tried first).
    """

    name: str
    available: bool
    priority: int


# ── API Response Envelope ──────────────────────────────────


class Meta(BaseModel):
    """Standard response metadata.

    Attributes:
        status: Response status indicator ("ok" or "error").
        timestamp: ISO-8601 timestamp of the response.
    """

    status: Literal["ok", "error"] = "ok"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ApiResponse(BaseModel):
    """Standard Vyper API response envelope.

    Attributes:
        data: The response payload.
        meta: Response metadata including status and timestamp.
    """

    data: Any = None
    meta: Meta = Field(default_factory=Meta)


# ── Health ─────────────────────────────────────────────────


class HealthData(BaseModel):
    """Health check response data."""

    status: str = "ok"
    service: str = "source"
    version: str = "0.1.0"
    sources_cached: int = 0
    providers_available: int = 0
