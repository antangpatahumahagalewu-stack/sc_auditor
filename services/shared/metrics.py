"""Shared Prometheus metrics module untuk semua Vyper services.

Setiap service cukup:
    from shared.metrics import metrics, register_metrics_endpoint
    
    # Register /metrics endpoint
    register_metrics_endpoint(app)
    
    # Auto-tracked:
    # - vyper_request_count{service, method, endpoint, status}
    # - vyper_request_duration_seconds{service, method, endpoint}
    # - vyper_error_count{service, method, endpoint, error_type}
    # - vyper_service_info{service, version}
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY
from prometheus_client.exposition import CONTENT_TYPE_LATEST

# ── Metrics ────────────────────────────────────────────────────

request_count = Counter(
    "vyper_request_count",
    "Total requests per service",
    ["service", "method", "endpoint", "status"],
)

request_duration = Histogram(
    "vyper_request_duration_seconds",
    "Request latency per service",
    ["service", "method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

error_count = Counter(
    "vyper_error_count",
    "Total errors per service",
    ["service", "method", "endpoint", "error_type"],
)

service_info = Gauge(
    "vyper_service_info",
    "Service metadata (always 1 if running)",
    ["service", "version"],
)

# ── Middleware ──────────────────────────────────────────────────


class MetricsMiddleware:
    """FastAPI middleware — auto-track request count, duration, errors."""

    def __init__(self, service_name: str = "unknown") -> None:
        self.service_name = service_name

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        path = request.url.path

        # Skip /metrics endpoint to avoid recursion
        if path == "/metrics":
            return await call_next(request)

        start = time.monotonic()
        try:
            response = await call_next(request)
            status = str(response.status_code)
            request_count.labels(self.service_name, method, path, status).inc()
            request_duration.labels(self.service_name, method, path).observe(
                time.monotonic() - start
            )
            if response.status_code >= 500:
                error_count.labels(
                    self.service_name, method, path, "server_error"
                ).inc()
            elif response.status_code >= 400:
                error_count.labels(
                    self.service_name, method, path, "client_error"
                ).inc()
            return response
        except Exception as e:
            status = "500"
            request_count.labels(self.service_name, method, path, status).inc()
            request_duration.labels(self.service_name, method, path).observe(
                time.monotonic() - start
            )
            error_count.labels(
                self.service_name, method, path, type(e).__name__
            ).inc()
            raise


# ── Endpoint Registration ──────────────────────────────────────


def register_metrics_endpoint(app: FastAPI, service_name: str = "unknown",
                               service_version: str = "1.0.0") -> None:
    """Register /metrics endpoint + middleware on a FastAPI app.

    Usage:
        register_metrics_endpoint(app, service_name="04a-scanner-slither")
    """
    # Set service info gauge
    service_info.labels(service_name, service_version).set(1)

    # Add middleware
    app.add_middleware(MetricsMiddleware, service_name=service_name)

    # Add /metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )

    import structlog
    log = structlog.get_logger(service=service_name)
    log.info("metrics.registered", service=service_name, version=service_version)
