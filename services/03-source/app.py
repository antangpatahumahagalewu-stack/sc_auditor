"""Vyper Source Service — FastAPI microservice for fetching Solidity source code.

Fetches verified source code for smart contracts from multiple providers
(Etherscan, Sourcify, GitHub, Blockscout, manual) and caches results
on disk for fast subsequent access.

Port: 8002
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.detector import SourceDetector
from src.models import ApiResponse, FetchRequest, HealthData, Meta, SourceResult

# ── Logging ────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
        if sys.stdout.isatty()
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger()

# ── Constants ──────────────────────────────────────────────

SERVICE_NAME = "source"
SERVICE_VERSION = "0.1.0"

# ── Global detector singleton ──────────────────────────────

detector = SourceDetector()


# ── Lifespan ───────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: ensure data directories exist. Shutdown: clean log."""
    log.info("source.startup", service=SERVICE_NAME, version=SERVICE_VERSION)
    cached = detector.count_cached()
    log.info("source.cache_stats", cached_contracts=cached)
    yield
    log.info("source.shutdown", service=SERVICE_NAME)


# ── App Factory ────────────────────────────────────────────

app = FastAPI(
    title="Vyper Source Service",
    description=(
        "Fetches verified Solidity source code for smart contracts from "
        "multiple providers (Etherscan, Sourcify, GitHub, Blockscout). "
        "Caches results on disk for speed."
    ),
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

# CORS — permissive for local development / Docker compose
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helper ─────────────────────────────────────────────────


def ok(data: object = None) -> ApiResponse:
    """Build a standard Vyper success response."""
    return ApiResponse(data=data, meta=Meta(status="ok"))


def err(detail: str, status_code: int = 400) -> HTTPException:
    """Build a standard Vyper error response."""
    return HTTPException(
        status_code=status_code,
        detail=detail,
    )


# ── Endpoints ──────────────────────────────────────────────


@app.get("/health")
async def health() -> ApiResponse:
    """Health check endpoint.

    Returns service status, version, and cache statistics.
    """
    return ok(
        HealthData(
            status="ok",
            service=SERVICE_NAME,
            version=SERVICE_VERSION,
            sources_cached=detector.count_cached(),
            providers_available=len(detector.list_providers()),
        )
    )


@app.post("/fetch")
async def fetch_source(body: FetchRequest) -> ApiResponse:
    """Fetch verified source code for a contract.

    Tries providers in order (or the specified list) and returns
    the first successful result. The result is cached on disk.

    **Request body**::

        {
            "chain": "ethereum",
            "address": "0x...",
            "providers": ["etherscan", "sourcify", "github", "blockscout"]
        }

    ``providers`` is optional; defaults to all registered providers
    in priority order.
    """
    if not body.chain:
        raise err("chain is required")
    if not body.address or not body.address.startswith("0x"):
        raise err("address must be a 0x-prefixed hex string")

    log.info(
        "fetch.requested",
        chain=body.chain,
        address=body.address,
        providers=body.providers,
    )

    result = await detector.fetch(body.chain, body.address, body.providers)

    if result is None:
        log.info("fetch.not_found", chain=body.chain, address=body.address)
        raise err(
            f"Contract {body.address} not verified on any provider for chain {body.chain}",
            status_code=404,
        )

    log.info(
        "fetch.success",
        chain=body.chain,
        address=body.address,
        provider=result.provider,
        files=len(result.sources),
    )

    return ok(result)


@app.get("/source/{chain}/{address}")
async def get_cached_source(chain: str, address: str) -> ApiResponse:
    """Get cached source for a contract.

    Returns the cached ``SourceResult`` if available, or 404 if
    the contract has not been fetched yet.
    """
    if not address.startswith("0x"):
        raise err("address must be a 0x-prefixed hex string")

    result = detector.get_cached(chain, address)
    if result is None:
        raise err(
            f"Source for {address} on {chain} not found in cache. "
            f"Use POST /fetch to retrieve it first.",
            status_code=404,
        )

    return ok(result)


@app.delete("/source/{chain}/{address}")
async def clear_source_cache(chain: str, address: str) -> ApiResponse:
    """Remove cached source for a contract.

    Returns a confirmation message, or 404 if nothing was cached.
    """
    if not address.startswith("0x"):
        raise err("address must be a 0x-prefixed hex string")

    removed = detector.clear_cache(chain, address)
    if not removed:
        raise err(
            f"No cached source for {address} on {chain}",
            status_code=404,
        )

    log.info("cache.cleared", chain=chain, address=address)
    return ok({"deleted": True, "chain": chain, "address": address})


@app.get("/providers")
async def list_providers() -> ApiResponse:
    """List all available source providers and their status.

    Returns an ordered list of providers with availability flags.
    """
    providers = detector.list_providers()
    return ok(providers)


# ── Entry Point ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8002,
        log_level="info",
        reload=False,
    )
