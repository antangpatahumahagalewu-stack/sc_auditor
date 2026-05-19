"""Halmos Counter-Example Path Predictor — L4 Intelligence.

Extended exploit chains mencakup 11 bug severity tinggi.
Halmos symbolic execution cocok untuk bug yang membutuhkan
path discovery kompleks (multi-function, multi-contract).
"""

from __future__ import annotations

from typing import Any

EXPLOIT_CHAINS: list[dict[str, Any]] = [
    # ── B01 + B02: Unauthorized Reentrancy Drain ──
    {
        "name": "unauthorized_drain",
        "required": {"access_control", "accounting"},
        "boosters": {"reentrancy", "assertion_violation"},
        "severity": "critical",
        "confidence": 0.85,
        "covered_bugs": ["B01", "B02"],
        "narrative": [
            "Attacker bypasses access control check",
            "Calls withdrawal function with manipulated state",
            "Reentrancy path allows recursive withdrawal",
            "Accounting inconsistency allows excess withdrawal beyond balance",
        ],
        "impact": "Complete fund drain via access control bypass + reentrancy + accounting error",
    },
    # ── B03: Flash Loan + Oracle Price Attack ──
    {
        "name": "price_oracle_attack",
        "required": {"oracle", "flash_loan"},
        "boosters": {"arithmetic", "assertion_violation"},
        "severity": "critical",
        "confidence": 0.80,
        "covered_bugs": ["B03"],
        "narrative": [
            "Attacker takes flash loan for large capital",
            "Manipulates spot price oracle via large swap",
            "Protocol uses manipulated price for critical calculation",
            "Trades at manipulated price for profit",
            "Repays flash loan, keeps profit — all in one transaction",
        ],
        "impact": "Financial loss via flash loan price manipulation — single tx exploit",
    },
    # ── B02: Reentrancy ──
    {
        "name": "reentrancy_exploit",
        "required": {"reentrancy", "accounting"},
        "boosters": {"assertion_violation", "access_control"},
        "severity": "critical",
        "confidence": 0.90,
        "covered_bugs": ["B02"],
        "narrative": [
            "Attacker calls withdraw with malicious fallback/receive",
            "Fallback re-enters withdraw function before balance update",
            "Multiple recursive withdrawals drain contract balance",
            "State variables become inconsistent with actual balances",
        ],
        "impact": "Reentrancy attack draining contract balance via recursive callback",
    },
    # ── B04: Bridge Logic Error ──
    {
        "name": "bridge_logic_break",
        "required": {"assertion_violation", "accounting"},
        "boosters": {"access_control"},
        "severity": "critical",
        "confidence": 0.70,
        "covered_bugs": ["B04"],
        "narrative": [
            "Symbolic execution discovers path where bridge invariant broken",
            "Assertion failure in mint/burn accounting logic",
            "Supply tracking becomes inconsistent with actual locked funds",
            "Potential for unlimited minting or uncovered redemption",
        ],
        "impact": "Bridge insolvency — invariant violation in cross-chain accounting logic",
    },
    # ── B07 + B11: Arithmetic Precision Corruption ──
    {
        "name": "arithmetic_precision_attack",
        "required": {"arithmetic"},
        "boosters": {"accounting", "assertion_violation"},
        "severity": "high",
        "confidence": 0.75,
        "covered_bugs": ["B07", "B11"],
        "narrative": [
            "Symbolic execution finds integer overflow/underflow path",
            "Division before multiplication causes precision loss",
            "Rounding errors accumulate across multiple operations",
            "Final state diverges from expected accounting",
        ],
        "impact": "Accounting corruption via arithmetic overflow + precision loss",
    },
    # ── B10: Front-running / Race Condition ──
    {
        "name": "race_condition_mev",
        "required": {"assertion_violation", "dos"},
        "boosters": {"access_control"},
        "severity": "high",
        "confidence": 0.55,
        "covered_bugs": ["B10"],
        "narrative": [
            "Symbolic execution reveals race condition in state-dependent logic",
            "Two transactions can interleave creating inconsistent state",
            "Attacker can observe pending tx and front-run for profit",
            "Commit-reveal scheme may have timing manipulation path",
        ],
        "impact": "MEV exploitation via front-running — user gets worse execution",
    },
]


class HalmosPathPredictor:
    """Predict exploit chains from Halmos findings."""

    def predict_chains(
        self,
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        categories = set()
        for f in findings:
            cat = f.get("category", "unknown")
            if cat != "unknown":
                categories.add(cat)

        results: list[dict[str, Any]] = []
        for chain in EXPLOIT_CHAINS:
            required = chain["required"]
            if not required.issubset(categories):
                continue

            boosters_present = chain["boosters"].intersection(categories)
            booster_ratio = len(boosters_present) / max(len(chain["boosters"]), 1)
            confidence = chain["confidence"] * (0.8 + 0.2 * booster_ratio)
            confidence = min(1.0, max(0.1, confidence))

            results.append({
                **chain,
                "boosters_present": list(boosters_present),
                "confidence": round(confidence, 3),
                "triggered_by": list(required),
            })

        results.sort(key=lambda c: c["confidence"], reverse=True)
        return results

    def summarize(self, chains: list[dict[str, Any]]) -> dict[str, Any]:
        if not chains:
            return {
                "total_chains": 0,
                "worst_severity": "none",
                "unique_bugs_covered": [],
                "top_concern": "No exploit chains identified",
            }
        severities = [c["severity"] for c in chains]
        worst = "critical" if "critical" in severities else "high"
        top = max(chains, key=lambda c: c["confidence"])

        all_bugs: set[str] = set()
        for c in chains:
            all_bugs.update(c.get("covered_bugs", []))

        return {
            "total_chains": len(chains),
            "worst_severity": worst,
            "unique_bugs_covered": sorted(all_bugs),
            "top_concern": {
                "name": top["name"],
                "impact": top["impact"],
                "confidence": top["confidence"],
            },
        }


def create_path_predictor() -> HalmosPathPredictor:
    return HalmosPathPredictor()
