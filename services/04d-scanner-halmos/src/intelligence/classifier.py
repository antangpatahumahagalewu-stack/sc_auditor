"""Halmos Failure Classifier — L2 Intelligence.

Mengklasifikasikan symbolic execution failures berdasarkan
test function name + error message patterns.

Failure categories:
  - assertion_violation   — assert() / require() failure
  - reentrancy           — reentrancy detected symbolically
  - arithmetic           — overflow / underflow
  - access_control       — authorization bypass
  - accounting           — balance / supply inconsistency
  - oracle               — price / timestamp manipulation
  - flash_loan           — flash loan attack path
  - invariant_break      — invariant property violation
  - dos                  — denial of service path
  - unknown
"""

from __future__ import annotations

import re
from typing import Any

FAILURE_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": r"(?:assert|require)\s*\(.*?(?:false|fail|should|must)",
        "category": "assertion_violation",
        "severity": "high",
        "label": "Assertion Violation",
        "description": "Symbolic execution found a path violating assert() or require().",
    },
    {
        "pattern": r"(?:reentrancy|reentrant|callback|call.*loop)",
        "category": "reentrancy",
        "severity": "critical",
        "label": "Reentrancy Path",
        "description": "Symbolic execution found a reentrancy path via external call.",
    },
    {
        "pattern": r"(?:overflow|underflow|wrap[^p]|uint.*max|int.*min)",
        "category": "arithmetic",
        "severity": "high",
        "label": "Arithmetic Boundary",
        "description": "Arithmetic operation reaches boundary condition.",
    },
    {
        "pattern": r"(?:access|owner|admin|auth|only|permission|role)",
        "category": "access_control",
        "severity": "critical",
        "label": "Access Control",
        "description": "Symbolic execution bypassed an access control check.",
    },
    {
        "pattern": r"(?:balance|supply|totalSupply|accounting|token.*amount|eth.*amount)",
        "category": "accounting",
        "severity": "high",
        "label": "Accounting Inconsistency",
        "description": "Balance or supply inconsistency detected symbolically.",
    },
    {
        "pattern": r"(?:oracle|price|manipulate|timestamp|block\.number)",
        "category": "oracle",
        "severity": "high",
        "label": "Oracle Manipulation",
        "description": "Price oracle manipulation path detected.",
    },
    {
        "pattern": r"(?:flash.?loan|flashloan|flash_loan)",
        "category": "flash_loan",
        "severity": "high",
        "label": "Flash Loan Attack",
        "description": "Flash loan-based attack path found.",
    },
    {
        "pattern": r"(?:invariant|property|echidna_test|crytic)",
        "category": "invariant_break",
        "severity": "high",
        "label": "Invariant Violation",
        "description": "Contract invariant property violated.",
    },
    {
        "pattern": r"(?:dos|denial|gas|out.?of.?gas|loop.*unbounded)",
        "category": "dos",
        "severity": "medium",
        "label": "Denial of Service",
        "description": "DoS path: unbounded loop or gas exhaustion.",
    },
]

FALLBACK: dict[str, Any] = {
    "category": "unknown",
    "severity": "high",
    "label": "Unknown Symbolic Failure",
    "description": "Could not classify failure pattern.",
}


class HalmosClassifier:
    """Classify Halmos symbolic execution failures."""

    def __init__(self) -> None:
        self._compiled: list[dict[str, Any]] = []
        for p in FAILURE_PATTERNS:
            try:
                regex = re.compile(p["pattern"], re.IGNORECASE)
                self._compiled.append({**p, "_regex": regex})
            except re.error:
                pass
        self._fallback_regex = re.compile(r".*", re.IGNORECASE)

    def classify(self, finding: dict[str, Any]) -> dict[str, Any]:
        """Classify a single Halmos finding."""
        text = f"{finding.get('test_name', '')} {finding.get('title', '')} {finding.get('description', '')}"
        text_lower = text.lower()

        for entry in self._compiled:
            if entry["_regex"].search(text_lower):
                return {
                    "category": entry["category"],
                    "severity": entry["severity"],
                    "label": entry["label"],
                    "description": entry["description"],
                    "confidence": 0.85,
                }

        return {
            "category": FALLBACK["category"],
            "severity": finding.get("severity", "high"),
            "label": FALLBACK["label"],
            "description": FALLBACK["description"],
            "confidence": 0.4,
        }

    def classify_batch(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{**f, **self.classify(f)} for f in findings]

    def get_categories(self) -> list[str]:
        seen: set[str] = set()
        for p in FAILURE_PATTERNS:
            seen.add(p["category"])
        return sorted(seen)


def create_classifier() -> HalmosClassifier:
    return HalmosClassifier()
