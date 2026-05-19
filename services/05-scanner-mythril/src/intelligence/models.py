"""Standalone Pydantic models for Mythril intelligence engine.

Tidak bergantung pada vyper_lib.models karena dependency conflict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntelFinding:
    """Finding yang sudah diperkaya dengan intelligence."""

    title: str
    description: str
    severity: str
    swc_id: str | None = None
    swc_title: str | None = None
    function: str | None = None
    address: int | None = None

    # Enriched fields
    swc_category: str = "unknown"
    swc_severity: str = "medium"
    confidence: float = 0.5
    risk_score: float = 0.0
    risk_label: str = "medium"
    priority: int = 3
    exploit_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "swc_id": self.swc_id,
            "swc_title": self.swc_title,
            "function": self.function,
            "address": self.address,
            "swc_category": self.swc_category,
            "swc_severity": self.swc_severity,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "risk_label": self.risk_label,
            "priority": self.priority,
            "exploit_path": self.exploit_path,
        }


@dataclass
class IntelScore:
    """Risk score for a Mythril finding."""

    title: str
    swc_id: str
    severity: str
    exploitability: float = 0.5
    swc_severity_weight: float = 0.5
    historical_confidence: float = 0.5
    adjusted_score: float = 0.0
    risk_label: str = "medium"
    priority: int = 3
    recommendation: str = ""


@dataclass
class IntelFix:
    """Fix suggestion for a Mythril finding."""

    swc_id: str
    swc_title: str
    title: str
    description: str
    before: str = ""
    after: str = ""
    solidity_example: str = ""
    references: list[str] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class IntelAnalysis:
    """Full intelligence analysis for a finding."""

    finding: IntelFinding
    score: IntelScore | None = None
    fix: IntelFix | None = None
    exploit_chain: list[str] = field(default_factory=list)
