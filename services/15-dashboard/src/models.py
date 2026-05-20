"""Pydantic v2 models for the Vyper Dashboard Service.

All models follow the standard Vyper envelope format:
    {"data": ..., "meta": {"status": "ok", "timestamp": "..."}}
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ───────────────────────────────────────────────────────

class DaemonStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class PipelineState(str, Enum):
    PENDING = "PENDING"
    FETCHING_PROGRAM = "FETCHING_PROGRAM"
    FETCHING_SOURCE = "FETCHING_SOURCE"
    SCANNING = "SCANNING"
    AI_ANALYSIS = "AI_ANALYSIS"
    CLASSIFYING = "CLASSIFYING"
    EXPLOITING = "EXPLOITING"
    REPORTING = "REPORTING"
    NOTIFYING = "NOTIFYING"
    COMPLETED = "COMPLETED"
    FETCH_FAILED = "FETCH_FAILED"
    SCAN_FAILED = "SCAN_FAILED"
    AI_FAILED = "AI_FAILED"
    CLASSIFY_FAILED = "CLASSIFY_FAILED"
    EXPLOIT_FAILED = "EXPLOIT_FAILED"
    REPORT_FAILED = "REPORT_FAILED"
    NOTIFY_FAILED = "NOTIFY_FAILED"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_FAILED = "UNKNOWN_FAILED"


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"


# Mapping from lowercase to display-friendly values
SEVERITY_MAP = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "info": "Info",
    "informational": "Info",
}


class FeedbackStatus(str, Enum):
    UNKNOWN = "unknown"
    CONFIRMED_TP = "confirmed_tp"
    REJECTED_FP = "rejected_fp"
    MARKED_FN = "marked_fn"
    PENDING_REVIEW = "pending_review"


# ── Response Envelope ───────────────────────────────────────────

class Meta(BaseModel):
    status: str = "ok"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ApiResponse(BaseModel):
    data: Any = None
    meta: Meta = Field(default_factory=Meta)


# ── Dashboard-specific Models ───────────────────────────────────

class HealthData(BaseModel):
    service: str = "dashboard"
    version: str = "1.0.0"
    uptime_seconds: Optional[float] = None


class DaemonState(BaseModel):
    status: DaemonStatus = DaemonStatus.STOPPED
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    total_contracts_audited: int = 0
    total_cycles_completed: int = 0
    last_error: Optional[str] = None


class FindingExport(BaseModel):
    finding_id: str
    tool: str
    severity: str
    title: str
    classification: str = "unknown"
    status: FeedbackStatus = FeedbackStatus.UNKNOWN


class AuditOverview(BaseModel):
    audit_id: str
    program: str = ""
    contract: str = ""
    chain: str = ""
    status: str = "PENDING"
    findings_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    duration_seconds: Optional[float] = None
    created_at: Optional[str] = None


class MetricsSummary(BaseModel):
    total_audits: int = 0
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    true_positive_rate: float = 0.0
    per_tool: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ProgramSummary(BaseModel):
    slug: str
    name: str = ""
    max_bounty: Optional[str] = None
    chains: List[str] = Field(default_factory=list)
    status: str = "active"


class FeedbackItem(BaseModel):
    finding_id: str
    original_classification: str
    user_feedback: Optional[str] = None
    status: FeedbackStatus = FeedbackStatus.PENDING_REVIEW
    created_at: Optional[str] = None


class ConfigEntry(BaseModel):
    key: str
    value: Any


class BackupInfo(BaseModel):
    id: str
    created_at: str
    size_bytes: int
    description: str = ""


class UpdateInfo(BaseModel):
    current_version: str = "1.0.0"
    latest_version: Optional[str] = None
    update_available: bool = False
    changelog: Optional[str] = None


class NotificationConfig(BaseModel):
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""


class WebhookConfig(BaseModel):
    url: str = ""
    events: List[str] = Field(default_factory=list)
    secret: str = ""
    active: bool = True


class ProgramDetail(BaseModel):
    slug: str
    name: str = ""
    website: Optional[str] = None
    max_bounty: Optional[str] = None
    status: str = "active"
    chains: List[str] = Field(default_factory=list)
    contracts: List[Dict[str, str]] = Field(default_factory=list)
    repos: List[str] = Field(default_factory=list)
    audit_history: List[Dict[str, Any]] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Case Management — Agenda 05: Each Bug Is Cases
# ═══════════════════════════════════════════════════════════════


class ConfidenceLabel(str, Enum):
    """Empat label confidence — Agenda 06: Confidence atas Temuan."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


# Urutan untuk sorting: Critical = 0 (paling atas), Low = 3 (paling bawah)
CONFIDENCE_LABEL_ORDER: dict[str, int] = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
}


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ClosedReason(str, Enum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    FALSE_POSITIVE = "false_positive"


class ScannerFinding(BaseModel):
    name: str
    detector: str
    confidence: float = Field(ge=0.0, le=1.0)


class CaseCreate(BaseModel):
    """Payload from Agent to create a new case."""
    project: str
    scanners: List[ScannerFinding]
    severity: str = "Medium"
    title: str
    contract: str = ""
    function: str = ""
    line: int = 0
    description: str = ""
    recommendation: str = ""
    proof_of_concept: str = ""
    platform: str = ""
    notes: str = ""

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Normalize severity to display-friendly format."""
        if v in SEVERITY_MAP:
            return SEVERITY_MAP[v]
        if v not in {e.value for e in Severity}:
            raise ValueError(f"Invalid severity: '{v}'. Must be one of: {[e.value for e in Severity]}")
        return v


class CaseClose(BaseModel):
    """Payload from User to close a case."""
    closed_reason: ClosedReason
    bounty_amount: Optional[float] = None
    notes: str = ""


class Case(BaseModel):
    """Full Case model — stored as YAML in ~/.sc_auditor/cases/CASE-XXX/meta.yaml."""
    case_id: str
    status: CaseStatus = CaseStatus.OPEN
    project: str = ""
    scanners: List[ScannerFinding] = Field(default_factory=list)
    confidence: float = 0.0
    confidence_label: str = "Medium"
    confidence_factors: List[str] = Field(default_factory=list)
    scanner_count: int = 0
    severity: str = "Medium"
    title: str = ""
    contract: str = ""
    function: str = ""
    line: int = 0
    description: str = ""
    recommendation: str = ""
    proof_of_concept: str = ""
    platform: str = ""
    bounty_amount: Optional[float] = None
    notes: str = ""
    created_at: str = ""
    closed_at: Optional[str] = None
    closed_reason: Optional[str] = None


class CaseStats(BaseModel):
    """Aggregated case statistics for dashboard."""
    total_cases: int = 0
    open_cases: int = 0
    closed_cases: int = 0
    total_bounty: float = 0.0
    avg_confidence: float = 0.0
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_scanner: Dict[str, int] = Field(default_factory=dict)
    label_distribution: Dict[str, int] = Field(default_factory=dict)
    recent_cases: List[Case] = Field(default_factory=list)
