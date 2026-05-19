"""Immunefi Service — FastAPI application.

Fetches bug bounty programs from the Immunefi GitHub mirror,
detects associated GitHub repositories, and serves the data via REST API.

Port: 8001
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.models import (
    ApiResponse,
    HealthData,
    Meta,
    Program,
    ProgramListResponse,
    StatsResponse,
    SyncStatus,
)
from src.sync import SyncManager

# ── Logging ────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger()

# ── Constants ──────────────────────────────────────────────

DATA_DIR = Path("/data/immunefi")
SERVICE_NAME = "immunefi"
SERVICE_VERSION = "0.1.0"

# ── Sync Manager (global singleton) ───────────────────────

sync_manager = SyncManager(DATA_DIR)

# Background sync task tracking
_sync_tasks: dict[str, asyncio.Task] = {}


# ── Lifespan ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load programs on startup, clean up client on shutdown."""
    log.info("app.startup", service=SERVICE_NAME)

    # Load existing programs from disk
    count = len(sync_manager.load_programs())
    log.info("app.programs_loaded", count=count)

    yield

    log.info("app.shutdown", service=SERVICE_NAME)


# ── App Factory ────────────────────────────────────────────

app = FastAPI(
    title="Vyper Immunefi Service",
    description="Fetches bug bounty programs from Immunefi and detects GitHub repos",
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

# CORS — permissive for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helper ─────────────────────────────────────────────────

def ok(data: object = None) -> ApiResponse:
    """Build a standard success response."""
    return ApiResponse(data=data, meta=Meta(status="ok"))


# ── Endpoints ──────────────────────────────────────────────

@app.get("/health")
async def health() -> ApiResponse:
    """Health check endpoint."""
    return ok(
        HealthData(
            status="ok",
            service=SERVICE_NAME,
            version=SERVICE_VERSION,
            programs_cached=len(sync_manager.programs),
            last_synced=sync_manager.last_synced,
        )
    )


@app.get("/programs")
async def list_programs(
    offset: int = Query(0, ge=0, description="Number of programs to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max programs to return"),
    status: str | None = Query(None, description="Filter by status (active, inactive, etc.)"),
    chain: str | None = Query(None, description="Filter by blockchain"),
    search: str | None = Query(None, description="Search by name or slug"),
    sort: str = Query("name", description="Sort field: name, max_bounty, status"),
    order: str = Query("asc", description="Sort order: asc or desc"),
) -> ApiResponse:
    """List all synced programs with optional filtering."""
    programs = list(sync_manager.programs.values())

    # Filter by status
    if status:
        programs = [p for p in programs if p.status.lower() == status.lower()]

    # Filter by chain
    if chain:
        chain_lower = chain.lower()
        programs = [p for p in programs if any(c.lower() == chain_lower for c in p.chains)]

    # Search by name or slug
    if search:
        q = search.lower()
        programs = [
            p for p in programs
            if q in p.name.lower() or q in p.slug.lower()
        ]

    # Sort
    reverse = order.lower() == "desc"
    if sort == "max_bounty":
        programs.sort(key=lambda p: p.max_bounty or 0, reverse=reverse)
    elif sort == "status":
        programs.sort(key=lambda p: p.status, reverse=reverse)
    else:
        programs.sort(key=lambda p: p.name.lower(), reverse=reverse)

    total = len(programs)
    paginated = programs[offset:offset + limit]

    return ok(
        ProgramListResponse(
            data=paginated,
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@app.get("/programs/{slug:path}")
async def get_program(slug: str) -> ApiResponse:
    """Get a single program by slug."""
    program = sync_manager.programs.get(slug)
    if not program:
        raise HTTPException(status_code=404, detail=f"Program '{slug}' not found")
    return ok(program)


@app.post("/sync")
async def trigger_sync() -> ApiResponse:
    """Trigger a full sync from Immunefi GitHub mirror (async).

    Dispatches a background task and returns a sync_id
    that can be polled via GET /sync/{sync_id}.
    """
    sync_id = str(uuid.uuid4())

    async def _run_sync(sid: str) -> None:
        """Background sync task."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                status = await sync_manager.sync_all(client=client)
                sync_manager._syncs[sid] = status
        except Exception as e:
            log.error("sync.background_failed", sync_id=sid, error=str(e))
            if sid in sync_manager._syncs:
                sync_manager._syncs[sid].status = "failed"

    # Track the in-progress sync
    sync_manager._syncs[sync_id] = SyncStatus(
        sync_id=sync_id,
        status="running",
        programs_synced=0,
        total=0,
        started_at=datetime.now(timezone.utc).isoformat(),
        completed_at=None,
    )

    task = asyncio.create_task(_run_sync(sync_id))
    _sync_tasks[sync_id] = task
    # Cleanup old task ref on completion
    task.add_done_callback(lambda _: _sync_tasks.pop(sync_id, None))

    return ok({"sync_id": sync_id, "status": "running"})


@app.post("/sync/run")
async def run_sync() -> ApiResponse:
    """Execute a full sync synchronously (blocking — may take minutes).

    Returns the completed SyncStatus.
    """
    log.info("sync.manual_trigger")
    async with httpx.AsyncClient(timeout=60.0) as client:
        status = await sync_manager.sync_all(client=client)
    return ok(status)


@app.get("/sync/{sync_id}")
async def get_sync(sync_id: str) -> ApiResponse:
    """Check the status of a sync operation."""
    status = sync_manager.get_sync_status(sync_id)
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Sync '{sync_id}' not found. Sync IDs are only valid during a running sync.",
        )
    return ok(status)


@app.get("/sync/status")
async def get_latest_sync_status() -> ApiResponse:
    """Get the latest sync information from the stored data."""
    return ok({
        "last_synced": sync_manager.last_synced,
        "programs_cached": len(sync_manager.programs),
    })


@app.get("/stats")
async def get_stats() -> ApiResponse:
    """Return aggregated program statistics."""
    programs = sync_manager.programs.values()

    by_status: dict[str, int] = {}
    by_chain: dict[str, int] = {}
    bounty_ranges: dict[str, int] = {
        "0-1k": 0,
        "1k-10k": 0,
        "10k-100k": 0,
        "100k-1M": 0,
        "1M+": 0,
        "unknown": 0,
    }
    total_contracts = 0
    total_repos = 0

    for p in programs:
        # Status
        s = p.status or "unknown"
        by_status[s] = by_status.get(s, 0) + 1

        # Chain
        for c in p.chains:
            chain_key = c or "unknown"
            by_chain[chain_key] = by_chain.get(chain_key, 0) + 1

        # Bounty range
        bounty = p.max_bounty
        if bounty is None:
            bounty_ranges["unknown"] += 1
        elif bounty < 1000:
            bounty_ranges["0-1k"] += 1
        elif bounty < 10_000:
            bounty_ranges["1k-10k"] += 1
        elif bounty < 100_000:
            bounty_ranges["10k-100k"] += 1
        elif bounty < 1_000_000:
            bounty_ranges["100k-1M"] += 1
        else:
            bounty_ranges["1M+"] += 1

        # Contracts & repos
        total_contracts += len(p.contracts)
        total_repos += len(p.repos)

    return ok(
        StatsResponse(
            total_programs=len(programs),
            by_status=by_status,
            by_chain=by_chain,
            bounty_ranges=bounty_ranges,
            total_contracts=total_contracts,
            total_repos=total_repos,
        )
    )
