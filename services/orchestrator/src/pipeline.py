"""Pipeline — the core state machine that runs a full audit workflow.

Workflow states:
  PENDING → FETCHING_PROGRAM → FETCHING_SOURCE → SCANNING → AI_ANALYSIS
  → CLASSIFYING → (EXPLOITING if critical/high) → (REPORTING) → (NOTIFYING) → COMPLETED

Failure states:
  FETCH_FAILED, SCAN_FAILED, AI_FAILED, CLASSIFY_FAILED,
  EXPLOIT_FAILED, REPORT_FAILED, NOTIFY_FAILED, TIMEOUT

Implements Saga compensation pattern: if step N fails, rollback steps N-1…1.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import config
from src.models import (
    AuditRecord,
    PipelineState,
    PipelineStep,
    PipelineStats,
)
from src.resource_governor import ResourceGovernor, ToolType

logger = logging.getLogger("vyper.orchestrator.pipeline")

# ── Type alias ──────────────────────────────────────────────────
StepHandler = Callable[[AuditRecord], Any]


class Pipeline:
    """Orchestrates the multi-step audit pipeline for a single contract.

    Usage:
        pipeline = Pipeline(resource_governor)
        result = await pipeline.run(audit_id)
    """

    # Ordered workflow: (state, handler_method_name, resource_tool?)
    WORKFLOW: List[Tuple[PipelineState, str, Optional[ToolType]]] = [
        (PipelineState.FETCHING_PROGRAM, "_fetch_program", ToolType.SOURCE),
        (PipelineState.FETCHING_SOURCE, "_fetch_source", ToolType.SOURCE),
        (PipelineState.SCANNING, "_run_scan", ToolType.SCANNER),
        (PipelineState.AI_ANALYSIS, "_run_ai_analysis", ToolType.AI),
        (PipelineState.CLASSIFYING, "_classify_findings", ToolType.CLASSIFIER),
        (PipelineState.EXPLOITING, "_generate_exploit", ToolType.EXPLOIT),
        (PipelineState.REPORTING, "_generate_report", ToolType.REPORTER),
        (PipelineState.NOTIFYING, "_notify", None),
    ]

    # State → failure mapping
    FAILURE_MAP: Dict[PipelineState, PipelineState] = {
        PipelineState.FETCHING_PROGRAM: PipelineState.FETCH_FAILED,
        PipelineState.FETCHING_SOURCE: PipelineState.FETCH_FAILED,
        PipelineState.SCANNING: PipelineState.SCAN_FAILED,
        PipelineState.AI_ANALYSIS: PipelineState.AI_FAILED,
        PipelineState.CLASSIFYING: PipelineState.CLASSIFY_FAILED,
        PipelineState.EXPLOITING: PipelineState.EXPLOIT_FAILED,
        PipelineState.REPORTING: PipelineState.REPORT_FAILED,
        PipelineState.NOTIFYING: PipelineState.NOTIFY_FAILED,
    }

    # Compensations: step -> (list of compensation handler names)
    COMPENSATIONS: Dict[PipelineState, List[str]] = {
        PipelineState.NOTIFYING: ["_compensate_notify"],
        PipelineState.REPORTING: ["_compensate_report"],
        PipelineState.EXPLOITING: ["_compensate_exploit"],
        PipelineState.CLASSIFYING: ["_compensate_classify"],
        PipelineState.AI_ANALYSIS: ["_compensate_ai"],
        PipelineState.SCANNING: ["_compensate_scan"],
        PipelineState.FETCHING_SOURCE: ["_compensate_fetch"],
        PipelineState.FETCHING_PROGRAM: [],
    }

    def __init__(self, resource_governor: ResourceGovernor) -> None:
        self._governor = resource_governor
        self._client: Optional[httpx.AsyncClient] = None
        self._audit_log: Dict[str, AuditRecord] = {}
        self._running: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._load_audit_log()

    # ── HTTP client ─────────────────────────────────────────────

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=config.step_timeout_seconds)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── Audit log persistence ───────────────────────────────────

    def _load_audit_log(self) -> None:
        path = config.audit_log_file
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text("utf-8"))
            for item in raw:
                record = AuditRecord(**item)
                self._audit_log[record.audit_id] = record
        except (json.JSONDecodeError, OSError, Exception) as exc:
            logger.warning("Failed to load audit log: %s", exc)

    def _save_audit_log(self) -> None:
        path = config.audit_log_file
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [record.model_dump(mode="json") for record in self._audit_log.values()]
        path.write_text(json.dumps(payload, indent=2, default=str), "utf-8")

    # ── Core run method ─────────────────────────────────────────

    async def run(self, audit_id: str) -> AuditRecord:
        """Execute the full pipeline for an audit. Returns the final record."""
        record = self._get_or_create(audit_id)
        if record.state in (PipelineState.PENDING,):
            record.state = PipelineState.FETCHING_PROGRAM
            self._save_audit_log()

        start_time = time.monotonic()
        task = asyncio.create_task(self._run_pipeline(record, start_time))
        self._running[audit_id] = task

        try:
            return await asyncio.wait_for(
                task, timeout=config.pipeline_global_timeout_seconds
            )
        except asyncio.TimeoutError:
            record.fail(PipelineState.TIMEOUT, "Pipeline global timeout exceeded")
            self._save_audit_log()
            return record
        finally:
            self._running.pop(audit_id, None)

    async def _run_pipeline(self, record: AuditRecord, start_time: float) -> AuditRecord:
        """Walk through the WORKFLOW table executing each step."""
        # Determine where to start/resume
        start_idx = 0
        for idx, (state, _, _) in enumerate(self.WORKFLOW):
            if state == record.state:
                start_idx = idx
                break
            # If we've already completed this step, skip ahead
            existing = next((s for s in record.steps if s.name == state.value), None)
            if existing and existing.completed_at is not None:
                start_idx = idx + 1

        for idx in range(start_idx, len(self.WORKFLOW)):
            state, handler_name, tool_type = self.WORKFLOW[idx]
            failure_state = self.FAILURE_MAP.get(state, PipelineState.UNKNOWN_FAILED)

            # Check if exploit step should be skipped
            if state == PipelineState.EXPLOITING:
                should_exploit = await self._should_run_exploit(record)
                if not should_exploit:
                    logger.info("Skipping EXPLOITING for %s (not critical/high)", record.audit_id)
                    continue

            # Check if reporting should be skipped
            if state == PipelineState.REPORTING:
                should_report = await self._should_run_report(record)
                if not should_report:
                    logger.info("Skipping REPORTING for %s", record.audit_id)
                    continue

            # Check if notifying should be skipped
            if state == PipelineState.NOTIFYING:
                should_notify = await self._should_run_notify(record)
                if not should_notify:
                    logger.info("Skipping NOTIFYING for %s", record.audit_id)
                    continue

            # Execute the step
            step = PipelineStep(name=state.value, state=state, started_at=datetime.now(timezone.utc))
            record.add_step(step)
            self._save_audit_log()

            try:
                if tool_type:
                    async with await self._governor.acquire(tool_type):
                        result = await self._execute_step(handler_name, record)
                else:
                    result = await self._execute_step(handler_name, record)

                step.completed_at = datetime.now(timezone.utc)
                step.duration_seconds = step.elapsed
                step.result = result if isinstance(result, dict) else {"status": "ok"}
                record.updated_at = datetime.now(timezone.utc)
                self._save_audit_log()

            except Exception as exc:
                logger.exception("Step %s failed for audit %s", state.value, record.audit_id)
                step.error = str(exc)
                step.completed_at = datetime.now(timezone.utc)
                record.fail(failure_state, str(exc))
                self._save_audit_log()

                # Saga compensation: rollback completed steps
                await self._compensate(record, idx)
                return record

        # All steps succeeded
        duration = time.monotonic() - start_time
        record.complete(duration)
        self._save_audit_log()
        logger.info("Audit %s completed in %.1fs", record.audit_id, duration)
        return record

    async def _execute_step(self, handler_name: str, record: AuditRecord) -> Any:
        """Execute a step handler by name with retry logic."""
        handler: StepHandler = getattr(self, handler_name)
        return await self._retry_call(handler, record)

    # ── Retry decorator ─────────────────────────────────────────

    async def _retry_call(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Wrap a step handler with tenacity retry + exponential backoff."""
        for attempt in range(1, config.retry_max_attempts + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                logger.warning(
                    "Attempt %d/%d failed: %s", attempt, config.retry_max_attempts, exc
                )
                if attempt == config.retry_max_attempts:
                    raise
                delay = min(
                    config.retry_base_delay_seconds * (2 ** (attempt - 1)),
                    config.retry_max_delay_seconds,
                )
                await asyncio.sleep(delay)
        # Should not reach here
        raise RuntimeError("Retry exhausted unexpectedly")

    # ── Step handlers ───────────────────────────────────────────

    async def _fetch_program(self, record: AuditRecord) -> Dict[str, Any]:
        """Call the Immunefi service to get program details.

        If no program slug is provided, skip this step gracefully.
        """
        if not record.program:
            logger.info("No program specified for %s — skipping FETCHING_PROGRAM", record.audit_id)
            return {"status": "skipped", "reason": "no program slug"}

        url = f"{config.immunefi_url}/programs/{record.program}"
        resp = await self.client.get(url)
        resp.raise_for_status()
        data = resp.json()
        record.metadata["program_data"] = data.get("data")
        return data

    async def _fetch_source(self, record: AuditRecord) -> Dict[str, Any]:
        """Call the Source service to fetch contract source code.

        If source data is already provided in metadata (e.g. via direct upload),
        skip the external fetch.
        """
        # Check if source data already provided
        existing = record.metadata.get("source_data")
        if existing and existing.get("sources"):
            logger.info("Source already in metadata for %s — skipping fetch", record.audit_id)
            return {"status": "skipped", "reason": "source already in metadata"}

        url = f"{config.source_url}/fetch"
        payload = {"chain": record.chain, "address": record.address}
        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        source_data = data.get("data") or {}
        record.metadata["source_data"] = source_data
        # Store compiler version from source for downstream services
        if source_data.get("compiler_version"):
            record.metadata["compiler_version"] = source_data["compiler_version"]
        return data

    async def _run_scan(self, record: AuditRecord) -> Dict[str, Any]:
        """Call the Scanner service for static/dynamic analysis."""
        url = f"{config.scanner_url}/scan"
        source_data = record.metadata.get("source_data") or {}
        sources = source_data.get("sources") or {}
        compiler = record.metadata.get("compiler_version") or "0.8.20"
        payload = {
            "chain": record.chain,
            "address": record.address,
            "sources": sources,
            "compiler": compiler,
        }
        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        record.metadata["scan_results"] = data.get("data")
        # Store compiler version from scanner response (authoritative)
        scan_data = data.get("data") or {}
        if scan_data.get("compiler"):
            record.metadata["compiler_version"] = scan_data["compiler"]
        return data

    async def _run_ai_analysis(self, record: AuditRecord) -> Dict[str, Any]:
        """Call the AI Service to analyse scan findings."""
        url = f"{config.ai_url}/analyze"
        source_data = record.metadata.get("source_data") or {}
        sources = source_data.get("sources") or {}
        scan_data = record.metadata.get("scan_results") or {}
        findings_raw = scan_data.get("all_findings") or []

        # Transform scanner findings to AI Finding format
        ai_findings = []
        for i, f in enumerate(findings_raw, 1):
            ai_findings.append({
                "id": f.get("title", f"F-{i:03d}")[:8],
                "tool": f.get("tool", "scanner"),
                "title": f.get("title", ""),
                "description": f.get("description", ""),
                "severity": f.get("severity", "informational"),
                "location": {
                    "file": f.get("contract"),
                    "line": f.get("line"),
                    "snippet": "",
                },
            })

        payload = {
            "audit_id": record.audit_id,
            "source": sources,
            "findings": ai_findings,
            "compiler": record.metadata.get("compiler_version"),
            "contract_name": None,
        }
        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        record.metadata["ai_results"] = data.get("data")
        return data

    async def _classify_findings(self, record: AuditRecord) -> Dict[str, Any]:
        """Call the Classifier service to classify findings."""
        url = f"{config.classifier_url}/classify"
        ai_results = record.metadata.get("ai_results") or []

        payload = {
            "audit_id": record.audit_id,
            "findings": ai_results if isinstance(ai_results, list) else [],
        }
        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        classified = data.get("data") or {}
        record.metadata["classified_findings"] = classified.get("classified_findings", classified)
        record.findings = classified.get("classified_findings", classified)
        return data

    async def _generate_exploit(self, record: AuditRecord) -> Dict[str, Any]:
        """Call the Exploit service to generate PoC for the most severe finding."""
        url = f"{config.exploit_url}/exploit"
        source_data = record.metadata.get("source_data") or {}
        sources = source_data.get("sources") or {}

        # Find the most severe finding with enough context
        findings = record.findings or record.metadata.get("classified_findings") or []
        if isinstance(findings, dict):
            findings = findings.get("classified_findings", findings.get("findings", []))

        if not findings:
            logger.info("No findings to exploit for %s", record.audit_id)
            return {"status": "skipped", "reason": "no findings"}

        # Sort by severity: critical > high > medium > low > informational
        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
        target = min(
            findings,
            key=lambda f: (
                severity_rank.get(
                    (f.get("severity") or f.get("ai_severity") or "").lower(), 99
                ),
            ),
        )

        # Extract vulnerable function name from finding data
        vuln_func = (
            target.get("function")
            or target.get("vulnerable_function")
            or (target.get("location") or {}).get("function")
            or "unknown"
        )

        # Map finding title to attack type
        title_lower = (target.get("title") or "").lower()
        if "reentrancy" in title_lower:
            attack_type = "reentrancy"
        elif "access" in title_lower or "owner" in title_lower or "role" in title_lower:
            attack_type = "access_control"
        elif "arithmetic" in title_lower or "overflow" in title_lower:
            attack_type = "arithmetic"
        elif "oracle" in title_lower:
            attack_type = "oracle_manipulation"
        elif "flash" in title_lower:
            attack_type = "flash_loan"
        else:
            attack_type = "auto"

        payload = {
            "audit_id": record.audit_id,
            "finding_id": target.get("id", target.get("finding_id", "F-001")),
            "source": sources,
            "compiler": record.metadata.get("compiler_version", "0.8.20"),
            "vulnerable_function": vuln_func,
            "attack_type": attack_type,
            "chain": record.chain,
            "use_ai": True,
            "max_hypotheses": 5,
        }

        logger.info(
            "Generating exploit for finding",
            audit_id=record.audit_id,
            finding_id=payload["finding_id"],
            attack_type=attack_type,
            function=vuln_func,
        )

        resp = await self.client.post(url, json=payload, timeout=600.0)
        resp.raise_for_status()
        data = resp.json()
        record.metadata["exploit_data"] = data.get("data")
        return data

    async def _generate_report(self, record: AuditRecord) -> Dict[str, Any]:
        """Call the Reporter service to generate audit report."""
        url = f"{config.reporter_url}/report"
        source_data = record.metadata.get("source_data") or {}
        findings = record.findings or record.metadata.get("classified_findings") or []
        if isinstance(findings, dict):
            findings = findings.get("classified_findings", findings.get("findings", []))

        # Build source info
        source_info = {
            "provider": source_data.get("provider", ""),
            "files": list(source_data.get("sources", {}).keys()),
            "file_count": len(source_data.get("sources", {})),
            "lines_of_code": sum(
                len(c.splitlines()) for c in (source_data.get("sources") or {}).values()
            ),
            "has_tests": False,
            "has_foundry": False,
            "is_full_repo": False,
            "compiler_versions": [record.metadata.get("compiler_version")]
            if record.metadata.get("compiler_version")
            else [],
        }

        # Build exploit results list
        exploit_data = record.metadata.get("exploit_data") or {}
        exploit_results = [exploit_data] if exploit_data else []

        payload = {
            "audit_id": record.audit_id,
            "program": record.program or "",
            "chain": record.chain,
            "address": record.address,
            "findings": findings if isinstance(findings, list) else [],
            "metrics": None,
            "exploit_results": exploit_results,
            "source_info": source_info,
        }
        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        report_data = data.get("data") or {}
        if isinstance(report_data, dict):
            record.report_path = report_data.get("immunefi_path") or report_data.get("full_path")
        record.metadata["report_data"] = report_data
        return data

    async def _notify(self, record: AuditRecord) -> Dict[str, Any]:
        """Call the Notifier service to send notifications."""
        url = f"{config.notifier_url}/notify"

        # Count findings by severity
        findings = record.findings or record.metadata.get("classified_findings") or []
        if isinstance(findings, dict):
            findings = findings.get("classified_findings", findings.get("findings", []))
        if not isinstance(findings, list):
            findings = []

        critical_count = sum(
            1 for f in findings
            if (f.get("severity") or f.get("ai_severity") or "").lower() == "critical"
        )
        high_count = sum(
            1 for f in findings
            if (f.get("severity") or f.get("ai_severity") or "").lower() == "high"
        )

        summary = (
            f"Audit {record.audit_id[:8]} — "
            f"{len(findings)} findings: "
            f"{critical_count} critical, {high_count} high"
        )

        payload = {
            "type": "audit_complete",
            "channel": "all",
            "audit_id": record.audit_id,
            "findings_count": len(findings),
            "critical_count": critical_count,
            "high_count": high_count,
            "summary": summary,
            "report_url": record.report_path,
            "program": record.program,
            "chain": record.chain,
            "address": record.address,
        }
        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        record.metadata["notification_data"] = data.get("data")
        return data

    # ── Conditional step guards ─────────────────────────────────

    async def _should_run_exploit(self, record: AuditRecord) -> bool:
        """Run exploit generation only if critical or high findings exist."""
        findings = record.findings or record.metadata.get("classified_findings") or []
        if isinstance(findings, dict):
            findings = findings.get("classified_findings", findings.get("findings", []))

        if not isinstance(findings, list):
            findings = []

        for f in findings:
            sev = (f.get("severity") or f.get("ai_severity") or "").lower()
            if sev in ("critical", "high"):
                return True
        return False

    async def _should_run_report(self, record: AuditRecord) -> bool:
        """Always run reporting if we have findings."""
        return record.findings is not None

    async def _should_run_notify(self, record: AuditRecord) -> bool:
        """Check if notifications are configured to run."""
        # Could check env or record metadata
        return bool(record.metadata.get("notify_enabled", True))

    # ── Saga compensation ───────────────────────────────────────

    async def _compensate(self, record: AuditRecord, failed_step_idx: int) -> None:
        """Rollback completed steps in reverse order (Saga pattern)."""
        logger.info("Starting Saga compensation for audit %s", record.audit_id)
        for idx in range(failed_step_idx - 1, -1, -1):
            state, _, _ = self.WORKFLOW[idx]
            compensators = self.COMPENSATIONS.get(state, [])
            for comp_name in compensators:
                try:
                    comp_fn = getattr(self, comp_name, None)
                    if comp_fn:
                        await comp_fn(record)
                        logger.info("Compensation %s succeeded for step %s", comp_name, state.value)
                except Exception as exc:
                    logger.warning(
                        "Compensation %s failed for step %s: %s",
                        comp_name, state.value, exc,
                    )

    async def _compensate_fetch(self, record: AuditRecord) -> None:
        """Remove cached source data."""
        record.metadata.pop("source_data", None)
        record.metadata.pop("program_data", None)

    async def _compensate_scan(self, record: AuditRecord) -> None:
        """Remove scan results."""
        record.metadata.pop("scan_results", None)

    async def _compensate_ai(self, record: AuditRecord) -> None:
        """Remove AI analysis results."""
        record.metadata.pop("ai_results", None)

    async def _compensate_classify(self, record: AuditRecord) -> None:
        """Remove classified findings."""
        record.metadata.pop("classified_findings", None)
        record.findings = None

    async def _compensate_exploit(self, record: AuditRecord) -> None:
        """Remove exploit data."""
        record.metadata.pop("exploit_data", None)

    async def _compensate_report(self, record: AuditRecord) -> None:
        """Remove report path."""
        record.report_path = None
        record.metadata.pop("report_data", None)

    async def _compensate_notify(self, record: AuditRecord) -> None:
        """No compensation needed for notifications."""
        pass

    # ── Status queries ─────────────────────────────────────────

    def get_record(self, audit_id: str) -> Optional[AuditRecord]:
        return self._audit_log.get(audit_id)

    def get_all_records(
        self,
        state: Optional[PipelineState] = None,
        program: Optional[str] = None,
        chain: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[AuditRecord], int]:
        """List audit records with optional filtering and pagination."""
        records = list(self._audit_log.values())

        if state:
            records = [r for r in records if r.state == state]
        if program:
            records = [r for r in records if r.program == program]
        if chain:
            records = [r for r in records if r.chain == chain]

        total = len(records)
        # Sort by created_at descending
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[offset: offset + limit], total

    def get_stats(self) -> PipelineStats:
        """Compute aggregate pipeline statistics."""
        records = list(self._audit_log.values())
        total = len(records)
        completed = sum(1 for r in records if r.state == PipelineState.COMPLETED)
        failed = sum(1 for r in records if r.state.is_failure)
        in_progress = sum(1 for r in records if not r.state.is_terminal)
        timeouts = sum(1 for r in records if r.state == PipelineState.TIMEOUT)

        durations = [r.duration_seconds for r in records if r.duration_seconds is not None]
        avg_dur = sum(durations) / len(durations) if durations else None

        by_state: Dict[str, int] = {}
        for r in records:
            by_state[r.state.value] = by_state.get(r.state.value, 0) + 1

        by_program: Dict[str, int] = {}
        for r in records:
            prog = r.program or "unknown"
            by_program[prog] = by_program.get(prog, 0) + 1

        return PipelineStats(
            total_audits=total,
            completed=completed,
            failed=failed,
            in_progress=in_progress,
            success_rate=(completed / total * 100) if total > 0 else 0.0,
            avg_duration_seconds=avg_dur,
            by_state=by_state,
            by_program=by_program,
            timeouts=timeouts,
            last_updated=datetime.now(timezone.utc),
        )

    # ── Internal helpers ────────────────────────────────────────

    def _get_or_create(self, audit_id: str) -> AuditRecord:
        if audit_id not in self._audit_log:
            record = AuditRecord(audit_id=audit_id, chain="", address="")
            self._audit_log[audit_id] = record
        return self._audit_log[audit_id]

    def register_audit(self, chain: str, address: str, program: str, priority: int) -> str:
        """Create a new audit record and return its ID."""
        import uuid
        audit_id = str(uuid.uuid4())
        record = AuditRecord(
            audit_id=audit_id,
            chain=chain,
            address=address,
            program=program,
            priority=priority,
        )
        self._audit_log[audit_id] = record
        self._save_audit_log()
        return audit_id

    def update_record(self, record: AuditRecord) -> None:
        self._audit_log[record.audit_id] = record
        self._save_audit_log()


__all__ = ["Pipeline"]
