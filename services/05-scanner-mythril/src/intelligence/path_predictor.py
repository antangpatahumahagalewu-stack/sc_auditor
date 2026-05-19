"""Mythril Exploit Chain Predictor — L4 Intelligence.

Mythril sudah melakukan symbolic execution — setiap finding sudah memiliki
exploit path. Modul ini mengelompokkan findings yang bisa di-chain untuk
membentuk exploit scenario yang lebih kompleks.

Extended dengan 10 exploit chain yang mencakup 11 bug severity tinggi:

  B01 Access Control → B02 Reentrancy  = Privilege Escalation Drain
  B05 Uninitialized Proxy → B08 Delegatecall = Full Contract Takeover
  B03 Flash Loan + B03 Oracle = Price Manipulation Attack
  B04 Bridge + B09 Signature = Cross-chain Insolvency
  B07 Overflow + B11 Precision = Accounting Corruption
  B02 Reentrancy + B06 Unchecked Call = Amplified Reentrancy
  B01 Access + B06 Unchecked Call = Silent Drain
  B08 Delegatecall + B01 Access = Execution Redirect
  B03 Oracle + B07 Arithmetic = Pricing Breakdown
  B10 Front-running + B02 Reentrancy = MEV + Reentrancy
"""

from __future__ import annotations

from typing import Any

# ── 10 Exploit Chains untuk 11 Bugs ─────────────────────────

EXPLOIT_CHAINS: list[dict[str, Any]] = [
    # ── B05 + B08: Contract Takeover ──
    {
        "name": "contract_takeover",
        "required": {"SWC-112"},
        "boosters": {"SWC-104", "SWC-108", "SWC-111", "SWC-109", "SWC-110"},
        "steps": [
            "Attacker provides malicious implementation address",
            "delegatecall executes arbitrary code in proxy context",
            "Attacker modifies storage (owner, balances)",
            "Full contract takeover",
        ],
        "impact": "Complete contract compromise — all funds lost",
        "severity": "critical",
        "confidence": 0.90,
        "covered_bugs": ["B05", "B08"],
    },
    # ── B01 + B02: Privilege Escalation + Reentrancy Drain ──
    {
        "name": "privilege_escalation_drain",
        "required": {"SWC-105", "SWC-107"},
        "boosters": {"SWC-104", "SWC-115", "SWC-108"},
        "steps": [
            "Attacker exploits missing/weak access control on withdraw",
            "Reentrancy via external call in withdrawal function",
            "Recursive withdrawals before balance update",
            "Contract balance completely drained",
        ],
        "impact": "Fund loss via unauthorized + recursive withdrawal",
        "severity": "critical",
        "confidence": 0.92,
        "covered_bugs": ["B01", "B02"],
    },
    # ── B03: Flash Loan + Oracle Manipulation ──
    {
        "name": "price_oracle_manipulation",
        "required": {"SWC-116", "SWC-119"},
        "boosters": {"SWC-104", "SWC-101", "SWC-102"},
        "steps": [
            "Timestamp/block manipulation by miner within ~30s window",
            "Combined with spot price oracle manipulation",
            "Arithmetic overflow amplifies pricing error",
            "Attacker extracts value through price discrepancy",
        ],
        "impact": "Financial loss via price oracle manipulation",
        "severity": "critical",
        "confidence": 0.60,
        "covered_bugs": ["B03"],
    },
    # ── B02 + B06: Amplified Reentrancy ──
    {
        "name": "amplified_reentrancy",
        "required": {"SWC-107", "SWC-104"},
        "boosters": {"SWC-105", "SWC-101"},
        "steps": [
            "External call without return value check",
            "Reentrancy via fallback function",
            "Multiple recursive calls drain contract",
            "Unchecked call means failed sub-calls don't revert",
        ],
        "impact": "Reentrancy attack amplified by unchecked calls — harder to stop mid-exploit",
        "severity": "critical",
        "confidence": 0.85,
        "covered_bugs": ["B02", "B06"],
    },
    # ── B05 + B08: Proxy Initialization Attack ──
    {
        "name": "proxy_initialization_attack",
        "required": {"SWC-108", "SWC-110"},
        "boosters": {"SWC-112", "SWC-109"},
        "steps": [
            "Proxy state variables visible to attacker",
            "Uninitialized storage allows attacker-controlled initialization",
            "Delegatecall routes to attacker's implementation",
            "Attacker gains control over proxy contract",
        ],
        "impact": "Proxy contract compromise via uninitialized storage + delegatecall",
        "severity": "critical",
        "confidence": 0.80,
        "covered_bugs": ["B05", "B08"],
    },
    # ── B04 + B09: Cross-chain Bridge Attack ──
    {
        "name": "cross_chain_bridge_exploit",
        "required": {"SWC-121"},
        "boosters": {"SWC-108", "SWC-105"},
        "steps": [
            "Signature validation does not include chain ID",
            "Same signature replayed on multiple chains",
            "Tokens minted on all chains without corresponding lock",
            "Bridge becomes insolvent — cannot redeem all supplies",
        ],
        "impact": "Bridge insolvency — unlimited token minting via signature replay across chains",
        "severity": "critical",
        "confidence": 0.55,
        "covered_bugs": ["B04", "B09"],
    },
    # ── B10: MEV / Front-running ──
    {
        "name": "frontrunning_sandwich",
        "required": {"SWC-114"},
        "boosters": {"SWC-116"},
        "steps": [
            "Transaction ordering dependence allows front-running",
            "Attacker monitors mempool for target transactions",
            "Buy before and sell after target transaction",
            "User gets worse execution price, attacker profits",
        ],
        "impact": "User financial loss via MEV sandwich attack",
        "severity": "high",
        "confidence": 0.50,
        "covered_bugs": ["B10"],
    },
    # ── B07 + B11: Arithmetic Corruption ──
    {
        "name": "arithmetic_state_corruption",
        "required": {"SWC-101"},
        "boosters": {"SWC-102"},
        "steps": [
            "Integer overflow in accounting logic",
            "Combined with precision loss from division-before-multiplication",
            "State variables reach inconsistent values",
            "Contract accounting corrupted — incorrect balances",
        ],
        "impact": "Accounting corruption via overflow + precision loss",
        "severity": "high",
        "confidence": 0.65,
        "covered_bugs": ["B07", "B11"],
    },
    # ── B01 + B06: Silent Drain ──
    {
        "name": "silent_fund_drain",
        "required": {"SWC-105", "SWC-104"},
        "boosters": {"SWC-115"},
        "steps": [
            "Unprotected withdraw function (missing access control)",
            "Low-level call without return value check",
            "Failed transfer does not revert transaction",
            "Funds can be drained silently without detection",
        ],
        "impact": "Silent fund drain — failed transfers don't revert, attacker can iterate",
        "severity": "high",
        "confidence": 0.75,
        "covered_bugs": ["B01", "B06"],
    },
    # ── B08 + B01: Execution Redirect ──
    {
        "name": "execution_redirect",
        "required": {"SWC-111", "SWC-112"},
        "boosters": {"SWC-108", "SWC-105"},
        "steps": [
            "Delegatecall to attacker-controlled address",
            "Access control on delegatecall function is missing",
            "Attacker executes arbitrary logic in proxy context",
            "Storage, balance, and permissions fully controlled",
        ],
        "impact": "Full execution control via unsafe delegatecall + missing access control",
        "severity": "critical",
        "confidence": 0.88,
        "covered_bugs": ["B08", "B01"],
    },
]


class MythrilChainPredictor:
    """Predict exploit chains dari kombinasi SWC findings."""

    def predict_chains(
        self,
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        swc_set = set()
        for f in findings:
            swc = f.get("swc_id", "").upper().strip()
            if swc.startswith("SWC-"):
                swc_set.add(swc)

        results: list[dict[str, Any]] = []
        for chain in EXPLOIT_CHAINS:
            required = chain["required"]
            if not required.issubset(swc_set):
                continue

            boosters_present = chain["boosters"].intersection(swc_set)
            booster_ratio = len(boosters_present) / max(len(chain["boosters"]), 1)
            confidence = chain["confidence"] * (0.8 + 0.2 * booster_ratio)
            confidence = min(1.0, max(0.1, confidence))

            results.append({
                "name": chain["name"],
                "steps": chain["steps"],
                "impact": chain["impact"],
                "severity": chain["severity"],
                "confidence": round(confidence, 3),
                "detectors_used": list(required),
                "boosters_present": list(boosters_present),
                "covered_bugs": chain["covered_bugs"],
            })

        results.sort(key=lambda c: c["confidence"], reverse=True)
        return results

    def summarize(self, chains: list[dict[str, Any]]) -> dict[str, Any]:
        if not chains:
            return {
                "total_chains": 0,
                "worst_severity": "none",
                "top_concern": "No exploit chains identified",
            }

        severities = [c["severity"] for c in chains]
        worst = "critical" if "critical" in severities else (
            "high" if "high" in severities else "medium"
        )
        top = max(chains, key=lambda c: c["confidence"])

        # Unique bugs covered
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


def create_path_predictor() -> MythrilChainPredictor:
    return MythrilChainPredictor()
