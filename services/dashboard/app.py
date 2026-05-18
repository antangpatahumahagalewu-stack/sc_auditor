"""Vyper Dashboard Service — FastAPI entry point.

API Gateway + Web UI for the Vyper smart contract bug hunting platform.
Serves Jinja2 HTML templates with Tailwind CSS (CDN), SSE real-time updates,
and REST API proxy/aggregation to internal backend services.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.models import (
    ApiResponse,
    HealthData,
    Meta,
)
from src.proxy import proxy, ServiceProxy
from src.sse import sse_manager

# ── Paths ───────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

# ── Logging ─────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger(service="dashboard")

# ── Application ─────────────────────────────────────────────────

app = FastAPI(
    title="Vyper Dashboard Service",
    description="API Gateway + Web UI for Vyper Smart Contract Bug Hunter",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Add global template variables
templates.env.globals["app_version"] = "1.0.0"
templates.env.globals["current_year"] = datetime.now().year

# ── Startup / Shutdown ──────────────────────────────────────────

_start_time: float = 0.0


@app.on_event("startup")
async def startup() -> None:
    global _start_time
    _start_time = time.time()
    logger.info("Starting Dashboard Service")
    await proxy.start()
    logger.info("Dashboard ready — http://localhost:8000")


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("Shutting down Dashboard Service")
    await proxy.close()


# ── Helpers ─────────────────────────────────────────────────────

def _ok(data: Any = None, **meta: Any) -> JSONResponse:
    return JSONResponse(
        content=ApiResponse(
            data=data,
            meta=Meta(
                status="ok",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        ).model_dump(mode="json"),
    )


def _err(message: str, status_code: int = 400, **meta: Any) -> JSONResponse:
    return JSONResponse(
        content={
            "data": None,
            "meta": {
                "status": "error",
                "error": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **meta,
            },
        },
        status_code=status_code,
    )


def _uptime() -> float:
    return time.time() - _start_time if _start_time else 0.0


# ═══════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return _ok(
        data=HealthData(
            service="dashboard",
            version="1.0.0",
            uptime_seconds=_uptime(),
        ).model_dump(mode="json"),
    )


# ═══════════════════════════════════════════════════════════════
# SSE — Server-Sent Events
# ═══════════════════════════════════════════════════════════════

@app.get("/events")
async def sse_events() -> StreamingResponse:
    """SSE stream for real-time dashboard updates."""
    queue = await sse_manager.connect()
    logger.info("SSE client connected")
    return StreamingResponse(
        sse_manager.event_stream(queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ═══════════════════════════════════════════════════════════════
# HTML Pages (Jinja2)
# ═══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Main dashboard page."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {"title": "Dashboard"},
    )


@app.get("/audits", response_class=HTMLResponse)
async def audits_page(request: Request) -> HTMLResponse:
    """Audits list page."""
    return templates.TemplateResponse(
        request,
        "audits.html",
        {"title": "Audits"},
    )


@app.get("/audits/{audit_id}", response_class=HTMLResponse)
async def audit_detail_page(request: Request, audit_id: str) -> HTMLResponse:
    """Audit detail page."""
    return templates.TemplateResponse(
        request,
        "audit_detail.html",
        {"title": "Audit Detail", "audit_id": audit_id},
    )


@app.get("/programs", response_class=HTMLResponse)
async def programs_page(request: Request) -> HTMLResponse:
    """Immunefi programs list page."""
    return templates.TemplateResponse(
        request,
        "programs.html",
        {"title": "Programs"},
    )


@app.get("/programs/{slug}", response_class=HTMLResponse)
async def program_detail_page(request: Request, slug: str) -> HTMLResponse:
    """Program detail page."""
    return templates.TemplateResponse(
        request,
        "program_detail.html",
        {"title": "Program", "slug": slug},
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    """Settings page."""
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"title": "Settings"},
    )


@app.get("/settings/notifications", response_class=HTMLResponse)
async def settings_notifications_page(request: Request) -> HTMLResponse:
    """Notification settings page."""
    return templates.TemplateResponse(
        request,
        "settings_notifications.html",
        {"title": "Notification Settings"},
    )


@app.get("/settings/webhooks", response_class=HTMLResponse)
async def settings_webhooks_page(request: Request) -> HTMLResponse:
    """Webhook settings page."""
    return templates.TemplateResponse(
        request,
        "settings_webhooks.html",
        {"title": "Webhook Settings"},
    )


@app.get("/metrics", response_class=HTMLResponse)
async def metrics_page(request: Request) -> HTMLResponse:
    """Metrics dashboard page."""
    return templates.TemplateResponse(
        request,
        "metrics.html",
        {"title": "Metrics"},
    )


@app.get("/daemon", response_class=HTMLResponse)
async def daemon_page(request: Request) -> HTMLResponse:
    """Daemon control page."""
    return templates.TemplateResponse(
        request,
        "daemon.html",
        {"title": "Daemon"},
    )


@app.get("/updates", response_class=HTMLResponse)
async def updates_page(request: Request) -> HTMLResponse:
    """Updates & backup page."""
    return templates.TemplateResponse(
        request,
        "updates.html",
        {"title": "Updates & Backup"},
    )


@app.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request) -> HTMLResponse:
    """Feedback management page."""
    return templates.TemplateResponse(
        request,
        "feedback.html",
        {"title": "Feedback"},
    )


# ═══════════════════════════════════════════════════════════════
# REST API Proxies
# ═══════════════════════════════════════════════════════════════

# ── Daemon ──────────────────────────────────────────────────────

@app.post("/api/daemon/start")
async def api_daemon_start() -> JSONResponse:
    """Start daemon (proxies to Orchestrator)."""
    try:
        result = await proxy.start_daemon()
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Daemon start failed", error=str(e))
        return _err(f"Daemon start failed: {e}", status_code=502)


@app.post("/api/daemon/stop")
async def api_daemon_stop() -> JSONResponse:
    """Stop daemon (proxies to Orchestrator)."""
    try:
        result = await proxy.stop_daemon()
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Daemon stop failed", error=str(e))
        return _err(f"Daemon stop failed: {e}", status_code=502)


@app.get("/api/daemon/status")
async def api_daemon_status() -> JSONResponse:
    """Get daemon status (proxies to Orchestrator)."""
    try:
        result = await proxy.get_daemon_status()
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Daemon status failed", error=str(e))
        return _err(f"Daemon status failed: {e}", status_code=502)


# ── Audits ──────────────────────────────────────────────────────

@app.get("/api/audits")
async def api_list_audits(
    state: Optional[str] = Query(None),
    program: Optional[str] = Query(None),
    chain: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """List audits (proxies to Orchestrator)."""
    try:
        result = await proxy.get_audits(
            state=state, program=program, chain=chain,
            limit=limit, offset=offset,
        )
        return _ok(
            data=result.get("data", []),
            total=result.get("meta", {}).get("total", 0),
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error("List audits failed", error=str(e))
        return _err(f"Failed to fetch audits: {e}", status_code=502)


@app.get("/api/audits/{audit_id}")
async def api_get_audit(audit_id: str) -> JSONResponse:
    """Get single audit (proxies to Orchestrator)."""
    try:
        result = await proxy.get_audit(audit_id)
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Get audit failed", audit_id=audit_id, error=str(e))
        return _err(f"Audit not found: {audit_id}", status_code=404)


@app.post("/api/audit")
async def api_start_audit(body: dict) -> JSONResponse:
    """Start a new audit (proxies to Orchestrator)."""
    try:
        result = await proxy.start_audit(
            chain=body.get("chain", ""),
            address=body.get("address", ""),
            program=body.get("program", ""),
            priority=body.get("priority", 5),
            metadata=body.get("metadata"),
        )
        # Broadcast via SSE
        audit_id = result.get("data", {}).get("audit_id", "")
        if audit_id:
            await sse_manager.broadcast_audit_progress(
                audit_id=audit_id,
                state="PENDING",
                progress=0.0,
                message="Audit queued",
            )
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Start audit failed", error=str(e))
        return _err(f"Failed to start audit: {e}", status_code=502)


@app.post("/api/audits/{audit_id}/retry")
async def api_retry_audit(audit_id: str) -> JSONResponse:
    """Retry a failed audit (proxies to Orchestrator)."""
    try:
        result = await proxy.retry_audit(audit_id)
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Retry audit failed", audit_id=audit_id, error=str(e))
        return _err(f"Failed to retry audit: {e}", status_code=502)


# ── Queue ───────────────────────────────────────────────────────

@app.get("/api/queue")
async def api_get_queue() -> JSONResponse:
    """Get priority queue (proxies to Orchestrator)."""
    try:
        result = await proxy.get_queue()
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Get queue failed", error=str(e))
        return _err(f"Failed to fetch queue: {e}", status_code=502)


@app.post("/api/queue")
async def api_add_to_queue(body: dict) -> JSONResponse:
    """Add to priority queue (proxies to Orchestrator)."""
    try:
        result = await proxy.add_to_queue(
            contract_id=body.get("contract_id", ""),
            chain=body.get("chain", ""),
            address=body.get("address", ""),
            program=body.get("program", ""),
            priority_score=body.get("priority_score", 0.0),
        )
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Add to queue failed", error=str(e))
        return _err(f"Failed to add to queue: {e}", status_code=502)


# ── Config ──────────────────────────────────────────────────────

@app.get("/api/config")
async def api_get_config() -> JSONResponse:
    """Get all config (proxies to Config Service)."""
    try:
        result = await proxy.get_all_config()
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Get config failed", error=str(e))
        return _err(f"Failed to fetch config: {e}", status_code=502)


@app.get("/api/config/{key}")
async def api_get_config_key(key: str) -> JSONResponse:
    """Get a single config key (proxies to Config Service)."""
    try:
        result = await proxy.get_config(key)
        return _ok(data=result.get("data"))
    except Exception as e:
        return _err(f"Config key not found: {key}", status_code=404)


@app.put("/api/config/{key}")
async def api_set_config(key: str, body: dict) -> JSONResponse:
    """Set a config value (proxies to Config Service)."""
    try:
        result = await proxy.set_config(key, body.get("value"))
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Set config failed", key=key, error=str(e))
        return _err(f"Failed to set config: {e}", status_code=502)


@app.put("/api/config/bulk")
async def api_set_bulk_config(body: dict) -> JSONResponse:
    """Set multiple config values at once (proxies to Config Service)."""
    try:
        result = await proxy.set_bulk_config(body.get("config", {}))
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Bulk config failed", error=str(e))
        return _err(f"Failed to set config: {e}", status_code=502)


# ── Metrics ─────────────────────────────────────────────────────

@app.get("/api/metrics")
async def api_get_metrics() -> JSONResponse:
    """Get classification metrics (proxies to Classifier)."""
    try:
        result = await proxy.get_metrics()
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Get metrics failed", error=str(e))
        return _err(f"Failed to fetch metrics: {e}", status_code=502)


@app.get("/api/stats")
async def api_get_stats() -> JSONResponse:
    """Get pipeline stats (proxies to Orchestrator)."""
    try:
        result = await proxy.get_orchestrator_stats()
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Get stats failed", error=str(e))
        return _err(f"Failed to fetch stats: {e}", status_code=502)


# ── Feedback ────────────────────────────────────────────────────

@app.get("/api/feedback")
async def api_list_feedback() -> JSONResponse:
    """List all feedback items (proxies to Classifier)."""
    try:
        result = await proxy.get_feedback_list()
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("List feedback failed", error=str(e))
        return _err(f"Failed to fetch feedback: {e}", status_code=502)


@app.post("/api/feedback")
async def api_submit_feedback(body: dict) -> JSONResponse:
    """Submit feedback for a finding (proxies to Classifier)."""
    try:
        result = await proxy.submit_feedback(
            finding_id=body.get("finding_id", ""),
            feedback=body.get("feedback", ""),
            status=body.get("status", "pending_review"),
        )
        # Broadcast via SSE
        await sse_manager.broadcast_feedback_received(
            finding_id=body.get("finding_id", ""),
            status=body.get("status", ""),
        )
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Submit feedback failed", error=str(e))
        return _err(f"Failed to submit feedback: {e}", status_code=502)


# ── Programs (Immunefi) ─────────────────────────────────────────

@app.get("/api/programs")
async def api_list_programs(
    search: Optional[str] = Query(None),
    chain: Optional[str] = Query(None),
) -> JSONResponse:
    """List Immunefi programs (proxies to Immunefi Service)."""
    try:
        result = await proxy.get_programs(search=search, chain=chain)
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("List programs failed", error=str(e))
        return _err(f"Failed to fetch programs: {e}", status_code=502)


@app.get("/api/programs/{slug}")
async def api_get_program(slug: str) -> JSONResponse:
    """Get single Immunefi program (proxies to Immunefi Service)."""
    try:
        result = await proxy.get_program(slug)
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Get program failed", slug=slug, error=str(e))
        return _err(f"Program not found: {slug}", status_code=404)


# ── Notifications ───────────────────────────────────────────────

@app.post("/api/notifications/test")
async def api_test_notification(body: dict) -> JSONResponse:
    """Send a test notification (proxies to Notifier)."""
    try:
        result = await proxy.send_test_notification(
            channel=body.get("channel", "discord")
        )
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Test notification failed", error=str(e))
        return _err(f"Failed to send test notification: {e}", status_code=502)


# ── Reports ─────────────────────────────────────────────────────

@app.post("/api/reports/generate")
async def api_generate_report(body: dict) -> JSONResponse:
    """Generate a report (proxies to Reporter)."""
    try:
        result = await proxy.generate_report(
            audit_id=body.get("audit_id", ""),
            format=body.get("format", "immunefi"),
        )
        return _ok(data=result.get("data"))
    except Exception as e:
        logger.error("Generate report failed", error=str(e))
        return _err(f"Failed to generate report: {e}", status_code=502)


# ── Daemon (from Dashboard API, additional) ─────────────────────

@app.post("/api/daemon/sync")
async def api_daemon_sync() -> JSONResponse:
    """Trigger an immediate sync/scan cycle (proxies to Orchestrator via daemon restart)."""
    try:
        # Stop then start to trigger re-scan
        await proxy.stop_daemon()
        result = await proxy.start_daemon()
        return _ok(data=result.get("data"), message="Sync triggered")
    except Exception as e:
        logger.error("Daemon sync failed", error=str(e))
        return _err(f"Daemon sync failed: {e}", status_code=502)


# ═══════════════════════════════════════════════════════════════
# Run (dev)
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.environ.get("DASHBOARD_PORT", "8000"))
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        log_level="info",
        reload=True,
    )
