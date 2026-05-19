"""Halmos Scorer — L4 Intelligence.

Scoring untuk symbolic execution findings:
  - Status severity (critical fail > error > pass)
  - Calldata complexity (longer calldata = more specific attack)
  - Test time (longer = more complex path)
  - Category weight (reentrancy/access control = higher)
"""

from __future__ import annotations

from typing import Any

SEVERITY_BASE: dict[str, float] = {
    "critical": 90.0,
    "high": 65.0,
    "medium": 40.0,
    "low": 20.0,
    "info": 5.0,
}

CATEGORY_WEIGHT: dict[str, float] = {
    "reentrancy": 1.4,
    "access_control": 1.4,
    "arithmetic": 1.2,
    "accounting": 1.2,
    "oracle": 1.2,
    "flash_loan": 1.3,
    "invariant_break": 1.1,
    "assertion_violation": 1.0,
    "dos": 0.9,
    "unknown": 1.0,
}


class HalmosScorer:
    """Score Halmos symbolic execution findings."""

    def score_finding(
        self,
        finding: dict[str, Any],
    ) -> dict[str, Any]:
        severity = finding.get("severity", "high").lower()
        category = finding.get("category", "unknown")
        calldata = finding.get("calldata", "") or ""

        base = SEVERITY_BASE.get(severity, 40.0)
        cat_w = CATEGORY_WEIGHT.get(category, 1.0)

        # Calldata complexity: longer = more specific counter-example
        calldata_len = len(calldata) if calldata.startswith("0x") else 0
        complexity_boost = 1.0 + min(calldata_len / 500, 0.3)

        adjusted = base * cat_w * complexity_boost
        adjusted = max(0, min(100, adjusted))

        if adjusted >= 80:
            label, priority = "critical", 1
        elif adjusted >= 55:
            label, priority = "high", 2
        elif adjusted >= 30:
            label, priority = "medium", 3
        elif adjusted >= 10:
            label, priority = "low", 4
        else:
            label, priority = "info", 5

        return {
            "test_name": finding.get("test_name", "unknown"),
            "title": finding.get("title", ""),
            "severity": severity,
            "category": category,
            "calldata_length": calldata_len,
            "base_score": base,
            "category_weight": cat_w,
            "complexity_boost": round(complexity_boost, 3),
            "adjusted_score": round(adjusted, 2),
            "risk_label": label,
            "priority": priority,
        }

    def score_findings(
        self,
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        scored = [self.score_finding(f) for f in findings]
        scored.sort(key=lambda s: s["adjusted_score"], reverse=True)
        return scored

    def compute_aggregate(self, scored: list[dict[str, Any]]) -> dict[str, Any]:
        if not scored:
            return {
                "overall_score": 0,
                "overall_label": "passed",
                "total": 0,
                "critical_count": 0,
                "high_count": 0,
                "failed_count": 0,
            }

        failed = [s for s in scored if s["risk_label"] in ("critical", "high")]
        if not failed:
            return {
                "overall_score": 0,
                "overall_label": "passed",
                "total": len(scored),
                "critical_count": sum(1 for s in scored if s["risk_label"] == "critical"),
                "high_count": sum(1 for s in scored if s["risk_label"] == "high"),
                "failed_count": 0,
            }

        top3 = failed[:3]
        weights = [3, 2, 1][:len(top3)]
        overall = sum(s["adjusted_score"] * w for s, w in zip(top3, weights)) / sum(weights)

        return {
            "overall_score": round(overall, 2),
            "overall_label": "failing" if overall >= 50 else "weak",
            "total": len(scored),
            "critical_count": sum(1 for s in scored if s["risk_label"] == "critical"),
            "high_count": sum(1 for s in scored if s["risk_label"] == "high"),
            "failed_count": len(failed),
        }


def create_scorer() -> HalmosScorer:
    return HalmosScorer()
