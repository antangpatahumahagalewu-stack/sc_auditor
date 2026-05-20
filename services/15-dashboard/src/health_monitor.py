"""Health monitor — periodically checks all 20 services and aggregates status.

Endpoints (registered in app.py):
  GET /api/health/graph     → Dependency graph + status per service
  GET /api/health/metrics   → Aggregated metrics across all services
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog

log = structlog.get_logger(service="health_monitor")


@dataclass
class ServiceDef:
    """Definition of a service to monitor."""
    name: str
    url: str
    depends_on: list[str] = field(default_factory=list)


SERVICES: list[ServiceDef] = [
    ServiceDef("01-config", "http://01-config:8000"),
    ServiceDef("02-immunefi", "http://02-immunefi:8000", ["01-config"]),
    ServiceDef("03-source", "http://03-source:8000", ["01-config"]),
    ServiceDef("04-scanner", "http://04-scanner:8000", ["01-config"]),
    ServiceDef("04a-slither", "http://04a-scanner-slither:8000", ["01-config"]),
    ServiceDef("04b-echidna", "http://04b-scanner-echidna:8000", ["01-config"]),
    ServiceDef("04c-forge", "http://04c-scanner-forge:8000", ["01-config"]),
    ServiceDef("04d-halmos", "http://04d-scanner-halmos:8000", ["01-config"]),
    ServiceDef("05-mythril", "http://05-scanner-mythril:8000", ["01-config"]),
    ServiceDef("06-ai", "http://06-ai:8000", ["01-config"]),
    ServiceDef("07-classifier", "http://07-classifier:8000", ["06-ai", "01-config"]),
    ServiceDef("08-exploit", "http://08-exploit:8000", ["07-classifier", "01-config"]),
    ServiceDef("09-reporter", "http://09-reporter:8000", ["08-exploit", "01-config"]),
    ServiceDef("10-notifier", "http://10-notifier:8000", ["09-reporter", "01-config"]),
    ServiceDef("11-orchestrator", "http://11-orchestrator:8000",
               ["02-immunefi", "03-source", "04-scanner", "06-ai",
                "07-classifier", "08-exploit", "09-reporter", "10-notifier", "01-config"]),
    ServiceDef("12-webhook", "http://12-webhook:8000", ["01-config"]),
    ServiceDef("13-upkeep", "http://13-upkeep:8000", ["01-config"]),
    ServiceDef("14-agent", "http://14-agent:8000", ["01-config"]),
    ServiceDef("15-dashboard", "http://localhost:8000", ["11-orchestrator", "01-config"]),
    ServiceDef("16-submission", "http://16-submission:8000", ["01-config"]),
]


class HealthMonitor:
    """Periodically checks all services and caches their status."""

    def __init__(self, check_interval: float = 30.0) -> None:
        self.check_interval = check_interval
        self._status: dict[str, dict[str, Any]] = {}
        self._history: dict[str, list[dict[str, Any]]] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background health checking."""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        log.info("health_monitor.started", interval=self.check_interval)

    async def stop(self) -> None:
        """Stop background health checking."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("health_monitor.stopped")

    async def _loop(self) -> None:
        """Background loop — check all services periodically."""
        while self._running:
            await self.check_all()
            await asyncio.sleep(self.check_interval)

    async def check_all(self) -> dict[str, dict[str, Any]]:
        """Check health of all services in parallel.

        Returns dict of {service_name: {status, latency, ...}}.
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            tasks = {
                svc.name: self._check_one(client, svc)
                for svc in SERVICES
            }
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        now = datetime.now(timezone.utc).isoformat()
        statuses: dict[str, dict[str, Any]] = {}
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                statuses[name] = {
                    "status": "down",
                    "error": str(result),
                    "latency_ms": None,
                    "last_checked": now,
                }
            else:
                statuses[name] = result

        self._status = statuses
        self._update_history(statuses)
        return statuses

    async def _check_one(self, client: httpx.AsyncClient,
                         svc: ServiceDef) -> dict[str, Any]:
        """Check a single service health."""
        import time
        start = time.monotonic()
        try:
            resp = await client.get(f"{svc.url}/health")
            latency_ms = round((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                return {
                    "status": "healthy",
                    "code": resp.status_code,
                    "latency_ms": latency_ms,
                    "last_checked": datetime.now(timezone.utc).isoformat(),
                    "depends_on": svc.depends_on,
                }
            return {
                "status": "degraded",
                "code": resp.status_code,
                "latency_ms": latency_ms,
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "depends_on": svc.depends_on,
            }
        except httpx.ConnectError:
            latency_ms = round((time.monotonic() - start) * 1000)
            return {
                "status": "down",
                "code": None,
                "latency_ms": latency_ms,
                "error": "Connection refused",
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "depends_on": svc.depends_on,
            }
        except httpx.TimeoutException:
            latency_ms = round((time.monotonic() - start) * 1000)
            return {
                "status": "down",
                "code": None,
                "latency_ms": latency_ms,
                "error": "Timeout",
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "depends_on": svc.depends_on,
            }

    def _update_history(self, statuses: dict[str, dict[str, Any]]) -> None:
        """Keep last 60 check results per service."""
        now = datetime.now(timezone.utc).isoformat()
        for name, st in statuses.items():
            if name not in self._history:
                self._history[name] = []
            self._history[name].append({
                "status": st.get("status"),
                "latency_ms": st.get("latency_ms"),
                "timestamp": now,
            })
            # Keep only last 60 entries (30 min at 30s interval)
            if len(self._history[name]) > 60:
                self._history[name] = self._history[name][-60:]

    def get_status(self) -> dict[str, dict[str, Any]]:
        """Get current status of all services."""
        if not self._status:
            return {}
        return self._status

    def get_graph(self) -> dict[str, Any]:
        """Get dependency graph data.

        Returns:
            {nodes: [{id, name, status, latency_ms}],
             edges: [{from, to, relation: "depends_on"}]}
        """
        nodes = []
        edges = []

        for svc in SERVICES:
            st = self._status.get(svc.name, {"status": "unknown"})
            nodes.append({
                "id": svc.name,
                "name": svc.name,
                "status": st.get("status", "unknown"),
                "latency_ms": st.get("latency_ms"),
                "code": st.get("code"),
            })
            for dep in svc.depends_on:
                edges.append({
                    "from": svc.name,
                    "to": dep,
                    "relation": "depends_on",
                })

        return {"nodes": nodes, "edges": edges}

    def get_metrics(self) -> dict[str, Any]:
        """Get aggregated metrics across all services."""
        total = len(SERVICES)
        healthy = sum(1 for s in self._status.values() if s.get("status") == "healthy")
        degraded = sum(1 for s in self._status.values() if s.get("status") == "degraded")
        down = sum(1 for s in self._status.values() if s.get("status") == "down")

        latencies = [s.get("latency_ms") for s in self._status.values()
                     if s.get("latency_ms") is not None]

        return {
            "total": total,
            "healthy": healthy,
            "degraded": degraded,
            "down": down,
            "uptime_pct": round(healthy / total * 100, 1) if total > 0 else 0.0,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "services": {
                name: {"status": s.get("status"), "latency_ms": s.get("latency_ms")}
                for name, s in self._status.items()
            },
        }
