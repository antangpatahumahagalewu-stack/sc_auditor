"""Echidna Failure Classifier — L2 Intelligence.

Mengklasifikasikan Echidna property violations berdasarkan:
- Test function name (echidna_*)
- Call sequence patterns
- Error message keywords

Category detection enables:
- Smart severity assignment
- Targeted fix suggestions
- Priority-based remediation ordering
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FailureCategory:
    """Kategori failure beserta metadata."""

    name: str
    label: str
    severity: str
    priority: int  # 1=critical … 5=info
    description: str
    confidence: float = 0.0
    matched_patterns: list[str] = field(default_factory=list)


# ── Failure Pattern Definitions ─────────────────────────────

FAILURE_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "reentrancy",
        "label": "Reentrancy",
        "severity": "critical",
        "priority": 1,
        "description": "Property violation terkait reentrancy — kontrak dapat dipanggil kembali sebelum state selesai diupdate.",
        "patterns": [
            r"reentran",
            r"no_reentran",
            r"balance_after",
            r"ether_leak",
            r"drain",
            r"withdraw.*after",
        ],
    },
    {
        "name": "access_control",
        "label": "Access Control",
        "severity": "critical",
        "priority": 1,
        "description": "Property violation terkait akses — fungsi dapat dipanggil oleh pihak yang tidak berwenang.",
        "patterns": [
            r"only_owner",
            r"only_admin",
            r"access_control",
            r"unauthorized",
            r"permission",
            r"role_",
            r"acl_",
            r"only_role",
        ],
    },
    {
        "name": "arithmetic",
        "label": "Arithmetic / Overflow",
        "severity": "high",
        "priority": 2,
        "description": "Property violation terkait arithmetic — overflow, underflow, atau manipulasi numerik.",
        "patterns": [
            r"overflow",
            r"underflow",
            r"arithmetic",
            r"balance_safe",
            r"supply_",
            r"total_supply",
            r"wrap_around",
            r"precision",
        ],
    },
    {
        "name": "fund_loss",
        "label": "Fund Loss",
        "severity": "critical",
        "priority": 1,
        "description": "Property violation yang mengakibatkan kehilangan dana (ETH atau token).",
        "patterns": [
            r"no_loss",
            r"no_drain",
            r"balance_positive",
            r"preserve_balance",
            r"fund_safe",
            r"no_theft",
            r"solvent",
        ],
    },
    {
        "name": "oracle_manipulation",
        "label": "Oracle Manipulation",
        "severity": "high",
        "priority": 2,
        "description": "Property violation terkait oracle — harga atau data eksternal dapat dimanipulasi.",
        "patterns": [
            r"oracle",
            r"price_",
            r"spot_price",
            r"pegged",
            r"exchange_rate",
        ],
    },
    {
        "name": "flash_loan",
        "label": "Flash Loan Attack",
        "severity": "high",
        "priority": 2,
        "description": "Property violation terkait flash loan — protocol dapat dimanipulasi via flash loan.",
        "patterns": [
            r"flash",
            r"liquid",
            r"no_arbitrage",
            r"price_manipulation",
        ],
    },
    {
        "name": "supply_cap",
        "label": "Supply Cap Violation",
        "severity": "high",
        "priority": 2,
        "description": "Property violation — batas maksimal supply token terlampaui.",
        "patterns": [
            r"supply_cap",
            r"max_supply",
            r"no_mint_beyond",
            r"cap_",
            r"mint_limit",
        ],
    },
    {
        "name": "invariant_break",
        "label": "Invariant Break",
        "severity": "high",
        "priority": 3,
        "description": "Invariant umum contract dilanggar — perlu investigasi lebih lanjut.",
        "patterns": [
            r"echidna_test",
            r"invariant",
            r"property_",
            r"test_",
        ],
    },
    {
        "name": "assertion_failure",
        "label": "Assertion Failure",
        "severity": "high",
        "priority": 3,
        "description": "Assertion failed selama fuzzing — kondisi yang dianggap selalu true ternyata bisa false.",
        "patterns": [
            r"assert",
            r"panic",
            r"require.*false",
        ],
    },
    {
        "name": "unknown",
        "label": "Unclassified Failure",
        "severity": "medium",
        "priority": 4,
        "description": "Failure yang tidak terklasifikasi — perlu review manual.",
        "patterns": [],
    },
]


class EchidnaClassifier:
    """Mengklasifikasikan Echidna property violations ke dalam kategori.

    Usage:
        classifier = EchidnaClassifier()
        category = classifier.classify(test_function_name, error_message)
        print(category.label, category.severity)
    """

    def __init__(self) -> None:
        self._patterns = FAILURE_PATTERNS
        # Precompile regex patterns
        self._compiled: list[dict[str, Any]] = []
        for pdef in self._patterns:
            compiled = []
            for pattern_str in pdef["patterns"]:
                try:
                    compiled.append(re.compile(pattern_str, re.IGNORECASE))
                except re.error:
                    pass
            self._compiled.append({
                "def": pdef,
                "compiled": compiled,
            })

    def classify(
        self,
        test_function: str = "",
        error_message: str = "",
        call_sequence: str = "",
    ) -> FailureCategory:
        """Classify a single Echidna finding.

        Args:
            test_function: Nama test function (echidna_*).
            error_message: Error message dari output.
            call_sequence: Call sequence yang memicu failure.

        Returns:
            FailureCategory dengan severity dan priority.
        """
        combined = f"{test_function} {error_message} {call_sequence}".lower()
        matches: list[tuple[int, str]] = []  # (match_count, name)

        for entry in self._compiled:
            match_count = 0
            matched_patterns: list[str] = []
            for regex in entry["compiled"]:
                if regex.search(combined):
                    match_count += 1
                    matched_patterns.append(regex.pattern)

            if match_count > 0:
                matches.append((match_count, entry["def"]["name"], matched_patterns))

        if not matches:
            # Return unknown
            unknown = self._patterns[-1]
            return FailureCategory(
                name=unknown["name"],
                label=unknown["label"],
                severity=unknown["severity"],
                priority=unknown["priority"],
                description=unknown["description"],
                confidence=0.0,
            )

        # Pick best match (highest count)
        best = max(matches, key=lambda m: m[0])
        matched_def = next(p for p in self._patterns if p["name"] == best[1])

        # Heuristic confidence based on match ratio
        total_patterns = len(matched_def["patterns"])
        match_ratio = best[0] / max(total_patterns, 1)
        confidence = min(1.0, match_ratio * 1.2)  # Boost a bit

        return FailureCategory(
            name=matched_def["name"],
            label=matched_def["label"],
            severity=matched_def["severity"],
            priority=matched_def["priority"],
            description=matched_def["description"],
            confidence=round(confidence, 3),
            matched_patterns=best[2],
        )

    def classify_batch(
        self,
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Classify multiple findings sekaligus — inject category ke finding."""
        enriched = []
        for f in findings:
            category = self.classify(
                test_function=f.get("test_function", ""),
                error_message=f.get("description", ""),
                call_sequence=f.get("failing_input", ""),
            )
            enriched.append({
                **f,
                "failure_category": category.name,
                "failure_label": category.label,
                "failure_severity": category.severity,
                "failure_priority": category.priority,
                "failure_confidence": category.confidence,
            })
        return enriched

    def get_available_categories(self) -> list[dict[str, Any]]:
        """List semua kategori failure yang diketahui."""
        return [
            {
                "name": p["name"],
                "label": p["label"],
                "severity": p["severity"],
                "priority": p["priority"],
                "description": p["description"],
            }
            for p in self._patterns
        ]


def create_classifier() -> EchidnaClassifier:
    return EchidnaClassifier()
