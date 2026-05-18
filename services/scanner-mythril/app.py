"""Vyper Scanner Mythril Service — Isolated Mythril analysis microservice.

Mythril has irreconcilable dependency conflicts with web3 6.x (eth-hash clash).
This service runs in its own container with mythril-compatible deps.

Port: 8013
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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

SERVICE_NAME = "scanner-mythril"
SERVICE_VERSION = "0.1.0"
DATA_DIR = Path("/data/scanner-mythril")

# ── Models ─────────────────────────────────────────────────


class Meta(BaseModel):
    service: str = SERVICE_NAME
    version: str = SERVICE_VERSION


class ApiResponse(BaseModel):
    ok: bool
    data: Any | None = None
    error: str | None = None
    meta: Meta = Field(default_factory=Meta)


class AnalyzerFinding(BaseModel):
    """A single finding returned by Mythril."""

    title: str
    description: str
    severity: str  # Low / Medium / High / Critical
    swc_id: str | None = None
    swc_title: str | None = None
    function: str | None = None
    address: int | None = None


class AnalyzeRequest(BaseModel):
    """Request to analyze Solidity source code."""

    sources: dict[str, str]  # {filename: source_code}
    compiler_version: str | None = None
    timeout: int = 120  # seconds


class AnalyzeResponse(BaseModel):
    """Result of a Mythril analysis run."""

    findings: list[AnalyzerFinding]
    tool: str = "mythril"
    tool_version: str | None = None
    errors: list[str] = []


class HealthInfo(BaseModel):
    service: str = SERVICE_NAME
    version: str = SERVICE_VERSION
    mythril_available: bool = False
    mythril_version: str | None = None


# ── Runner ─────────────────────────────────────────────────


def check_mythril() -> tuple[bool, str | None]:
    """Check if mythril CLI is available and return its version."""
    try:
        result = subprocess.run(
            ["myth", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip() or result.stderr.strip()
        return True, version or "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None


def run_mythril_analyze(
    sources: dict[str, str],
    compiler_version: str | None = None,
    timeout: int = 120,
) -> tuple[list[AnalyzerFinding], list[str]]:
    """Run ``mythril analyze`` on the given Solidity sources.

    Writes sources to a temp directory and runs mythril CLI.

    Returns:
        Tuple of (findings, errors).
    """
    findings: list[AnalyzerFinding] = []
    errors: list[str] = []

    with tempfile.TemporaryDirectory(prefix="mythril_") as tmpdir:
        # Write all sources
        for path, content in sources.items():
            filepath = Path(tmpdir) / path
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")

        # Find the main contract file
        main_file = None
        for path in sources:
            if path.endswith(".sol"):
                main_file = Path(tmpdir) / path
                break

        if not main_file:
            errors.append("No .sol file found in sources")
            return findings, errors

        # Build CLI args
        cmd = [
            "myth", "analyze",
            str(main_file),
            "--solc-json", str(Path(tmpdir) / "solc.json"),
            "--out", "json",
            "--max-depth", "32",
        ]

        # Add compiler version if provided
        if compiler_version:
            cmd.extend(["--solc-version", compiler_version])

        # Create minimal solc.json
        solc_config = {
            "language": "Solidity",
            "sources": {},
            "settings": {
                "optimizer": {"enabled": False},
                "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}},
            },
        }
        for path in sources:
            solc_config["sources"][path] = {"content": sources[path]}
        (Path(tmpdir) / "solc.json").write_text(
            json.dumps(solc_config), encoding="utf-8"
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
            )

            stdout = result.stdout
            stderr = result.stderr

            # Mythril outputs JSON to stdout
            parsed = _parse_mythril_output(stdout)
            findings.extend(parsed)

            if stderr:
                errors.append(stderr[:2000])  # truncate

        except subprocess.TimeoutExpired:
            errors.append(f"Mythril analysis timed out after {timeout}s")
        except FileNotFoundError:
            errors.append("Myth CLI not found")
        except Exception as exc:
            errors.append(f"Mythril execution error: {str(exc)[:500]}")

    return findings, errors


def _parse_mythril_output(output: str) -> list[AnalyzerFinding]:
    """Parse Mythril JSON output into AnalyzerFinding list."""
    findings: list[AnalyzerFinding] = []

    # Mythril outputs JSON lines or JSON array
    lines = output.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Mythril can output different formats
        # Format 1: {"issues": [...]}
        # Format 2: direct issue objects
        issues = data if isinstance(data, list) else data.get("issues", [data])

        for issue in issues if isinstance(issues, list) else [issues]:
            if not isinstance(issue, dict):
                continue
            findings.append(
                AnalyzerFinding(
                    title=issue.get("title", issue.get("swc-title", "Unknown")),
                    description=issue.get("description", ""),
                    severity=issue.get("severity", "Medium"),
                    swc_id=issue.get("swc-id", issue.get("swcID")),
                    swc_title=issue.get(
                        "swc-title",
                        issue.get("swcTitle"),
                    ),
                    function=issue.get("function", issue.get("functionName")),
                    address=issue.get("address"),
                )
            )

    return findings


# ── App State ──────────────────────────────────────────────


class AppState:
    """Shared application state."""

    def __init__(self) -> None:
        self.mythril_available: bool = False
        self.mythril_version: str | None = None
        self._shutdown_requested: bool = False

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def request_shutdown(self) -> None:
        self._shutdown_requested = True


# ── Lifespan ───────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: check mythril availability. Shutdown: clean exit."""
    state = AppState()
    app.state.vyper = state

    available, version = check_mythril()
    state.mythril_available = available
    state.mythril_version = version

    log.info(
        "mythril_service.startup",
        mythril_available=available,
        mythril_version=version,
    )

    yield

    log.info("mythril_service.shutdown")


# ── App Factory ────────────────────────────────────────────

app = FastAPI(
    title="Vyper Scanner Mythril Service",
    description=(
        "Isolated Mythril analysis microservice. Runs mythril analyze "
        "on Solidity source code with its own compatible dependency tree."
    ),
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception Handlers ─────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content=ApiResponse(ok=False, error=f"Internal server error: {str(exc)[:200]}").model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(ok=False, error=exc.detail).model_dump(),
    )


# ── Helper ─────────────────────────────────────────────────


def ok(data: Any = None) -> ApiResponse:
    return ApiResponse(ok=True, data=data)


# ── Routes ─────────────────────────────────────────────────


@app.get("/health")
async def health(request: Request) -> ApiResponse:
    """Health check with mythril availability status."""
    state: AppState = request.app.state.vyper  # type: ignore[attr-defined]
    return ok(
        HealthInfo(
            mythril_available=state.mythril_available,
            mythril_version=state.mythril_version,
        )
    )


@app.post("/analyze")
async def analyze(body: AnalyzeRequest, request: Request) -> ApiResponse:
    """Run Mythril analysis on the provided Solidity sources.

    **Request body**::

        {
            "sources": {
                "Contract.sol": "// SPDX... pragma solidity ^0.8.0; ..."
            },
            "compiler_version": "0.8.20",
            "timeout": 120
        }

    Returns findings in Vyper standard format.
    """
    state: AppState = request.app.state.vyper  # type: ignore[attr-defined]

    if not state.mythril_available:
        return ApiResponse(ok=False, error="Mythril CLI is not available")

    findings, errors = await asyncio.to_thread(
        run_mythril_analyze,
        body.sources,
        body.compiler_version,
        body.timeout,
    )

    return ok(
        AnalyzeResponse(
            findings=findings,
            tool="mythril",
            tool_version=state.mythril_version,
            errors=errors,
        )
    )


@app.post("/analyze/raw")
async def analyze_raw(request: Request) -> JSONResponse:
    """Accept raw Solidity source files as multipart upload.

    Alternative to the JSON /analyze endpoint for direct file uploads.
    """
    # This is a placeholder — the JSON endpoint is the primary API
    return JSONResponse(
        content=ApiResponse(
            ok=False, error="Use POST /analyze with JSON body instead"
        ).model_dump(),
        status_code=400,
    )
