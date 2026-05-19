"""Compiler Error Scorer — L4 Intelligence.

Scoring untuk compiler errors berbeda dengan security findings:
  - blocking = build gagal, harus diperbaiki sebelum deploy
  - warning  = best practice, sebaiknya diperbaiki
  - info     = informational, tidak blocking

Skor agregat memberikan gambaran "compiler health" dari source code.
"""

from __future__ import annotations

from typing import Any

SEVERITY_WEIGHTS: dict[str, float] = {
    "blocking": 80.0,
    "warning": 30.0,
}

CATEGORY_BOOST: dict[str, float] = {
    "syntax": 1.3,      # Syntax error = high impact
    "import": 1.2,      # Import error = structural
    "type": 1.1,        # Type error = medium
    "pragma": 1.0,
    "constructor": 1.0,
    "override": 0.9,
    "visibility": 0.8,
    "abstract": 0.8,
    "yul": 0.7,
    "library": 0.7,
    "receive": 0.7,
    "warning": 0.5,
    "unknown": 1.0,
}


class CompilerScorer:
    """Score compiler errors."""

    def score_error(self, error_message: str, category: str, severity: str) -> dict[str, Any]:
        base = SEVERITY_WEIGHTS.get(severity, 30.0)
        boost = CATEGORY_BOOST.get(category, 1.0)

        adjusted = base * boost
        adjusted = max(0, min(100, adjusted))

        if adjusted >= 70:
            label, priority = "critical", 1
        elif adjusted >= 45:
            label, priority = "high", 2
        elif adjusted >= 20:
            label, priority = "medium", 3
        else:
            label, priority = "low", 4

        return {
            "error": error_message[:200],
            "category": category,
            "severity": severity,
            "base_score": base,
            "category_boost": boost,
            "adjusted_score": round(adjusted, 2),
            "risk_label": label,
            "priority": priority,
        }

    def score_errors(
        self,
        errors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Score classified errors (each already has category + severity)."""
        scored = []
        for e in errors:
            s = self.score_error(
                error_message=e.get("error", e.get("message", "")),
                category=e.get("category", "unknown"),
                severity=e.get("severity", "blocking"),
            )
            # Merge original data
            scored.append({**e, **s})
        scored.sort(key=lambda x: x["adjusted_score"], reverse=True)
        return scored

    def compute_aggregate(self, scored: list[dict[str, Any]]) -> dict[str, Any]:
        if not scored:
            return {
                "overall_score": 0,
                "overall_label": "clean",
                "total_errors": 0,
                "blocking_count": 0,
                "warning_count": 0,
                "top_errors": [],
            }

        blocking = sum(1 for s in scored if s.get("severity") == "blocking")
        warnings = sum(1 for s in scored if s.get("severity") == "warning")

        # Weighted average: blocking errors weighted 3x
        total_weight = blocking * 3 + warnings
        if total_weight == 0:
            overall = 0
        else:
            weighted_sum = sum(
                s["adjusted_score"] * (3 if s.get("severity") == "blocking" else 1)
                for s in scored
            )
            overall = weighted_sum / total_weight

        return {
            "overall_score": round(overall, 2),
            "overall_label": self._label(overall),
            "total_errors": len(scored),
            "blocking_count": blocking,
            "warning_count": warnings,
            "top_errors": [
                {
                    "error": s.get("error", "")[:100],
                    "category": s.get("category", "unknown"),
                    "score": s.get("adjusted_score", 0),
                    "label": s.get("label", ""),
                }
                for s in scored[:5]
            ],
        }

    @staticmethod
    def _label(score: float) -> str:
        if score >= 70:
            return "failing"
        if score >= 40:
            return "poor"
        if score >= 20:
            return "fair"
        if score >= 5:
            return "good"
        return "clean"


def create_scorer() -> CompilerScorer:
    return CompilerScorer()
