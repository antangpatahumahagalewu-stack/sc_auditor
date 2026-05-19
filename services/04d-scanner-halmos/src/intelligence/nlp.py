"""Halmos NLP — Rule-based natural language query.

Menjawab pertanyaan tentang hasil symbolic execution Halmos.
"""

from __future__ import annotations

from typing import Any

INTENT_PATTERNS: list[dict[str, Any]] = [
    {"intent": "summary", "keywords": ["summary", "overview", "overall", "result", "status"]},
    {"intent": "failed", "keywords": ["fail", "failed", "failing", "counter", "broken"]},
    {"intent": "calldata", "keywords": ["calldata", "input", "attack", "exploit"]},
    {"intent": "category", "keywords": ["access", "reentrancy", "oracle", "arithmetic", "accounting", "flash"]},
    {"intent": "fix", "keywords": ["fix", "repair", "solve", "how to", "patch"]},
    {"intent": "chain", "keywords": ["chain", "combine", "scenario", "attack path"]},
]


class HalmosNLP:
    """"""

    def ask(
        self,
        query: str,
        findings: list[dict[str, Any]],
        chains: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        q = query.lower().strip()
        intent = self._classify_intent(q)

        if intent == "summary":
            answer, filtered = self._summary(findings)
        elif intent == "failed":
            answer, filtered = self._failed(findings)
        elif intent == "calldata":
            answer, filtered = self._calldata(findings)
        elif intent == "category":
            answer, filtered = self._by_category(findings, q)
        elif intent == "fix":
            answer, filtered = self._fix(findings)
        elif intent == "chain":
            answer, filtered = self._chains(findings, chains)
        else:
            answer, filtered = self._fallback(q)

        return {
            "query": query,
            "intent": intent,
            "answer": answer,
            "context": {"total_findings": len(findings)},
            "findings": filtered,
            "follow_up_questions": self._follow_ups(intent),
        }

    @staticmethod
    def _classify_intent(query: str) -> str:
        scores: dict[str, int] = {}
        for p in INTENT_PATTERNS:
            score = sum(1 for kw in p["keywords"] if kw in query)
            if score > 0:
                scores[p["intent"]] = score
        return max(scores, key=scores.get) if scores else "unknown"

    @staticmethod
    def _summary(findings: list) -> tuple[str, list]:
        categories: dict[str, int] = {}
        statuses: dict[str, int] = {}
        for f in findings:
            cat = f.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            status = f.get("status", "unknown")
            statuses[status] = statuses.get(status, 0) + 1

        cat_str = ", ".join(f"{k}={v}" for k, v in sorted(categories.items()))
        st_str = ", ".join(f"{k}={v}" for k, v in sorted(statuses.items()))

        if not findings:
            return "✅ All symbolic execution tests passed.", []
        return f"**{len(findings)}** symbolic execution result(s). Status: {st_str}. Categories: {cat_str}.", findings

    @staticmethod
    def _failed(findings: list) -> tuple[str, list]:
        failed = [f for f in findings if f.get("status") in ("fail", "error")]
        if not failed:
            return "✅ No failed symbolic execution tests.", []
        lines = [f"Found **{len(failed)}** failed symbolic test(s):\n"]
        for i, f in enumerate(failed[:10], 1):
            cat = f.get("category", "?")
            test = f.get("test_name", "?")
            sev = f.get("severity", "?")
            lines.append(f"  {i}. [{sev}] {test} ({cat})")
        return "\n".join(lines), failed

    @staticmethod
    def _calldata(findings: list) -> tuple[str, list]:
        with_calldata = [f for f in findings if f.get("calldata")]
        if not with_calldata:
            return "No counter-example calldata available.", []
        lines = [f"**{len(with_calldata)}** counter-example(s) with calldata:\n"]
        for i, f in enumerate(with_calldata[:5], 1):
            calldata = f.get("calldata", "")[:66]
            test = f.get("test_name", "?")
            lines.append(f"  {i}. {test}: {calldata}...")
        return "\n".join(lines), with_calldata

    @staticmethod
    def _by_category(findings: list, query: str) -> tuple[str, list]:
        for cat in ["access_control", "reentrancy", "oracle", "arithmetic", "accounting", "flash_loan"]:
            if cat.replace("_", " ") in query or cat in query:
                filtered = [f for f in findings if f.get("category") == cat]
                if not filtered:
                    return f"No findings in category '{cat}'.", []
                lines = [f"**{len(filtered)}** finding(s) in '{cat}':\n"]
                for i, f in enumerate(filtered[:10], 1):
                    lines.append(f"  {i}. {f.get('test_name', '?')} — {f.get('severity', '?')}")
                return "\n".join(lines), filtered
        return "Category not recognized. Try: access control, reentrancy, oracle, arithmetic.", []

    @staticmethod
    def _fix(findings: list) -> tuple[str, list]:
        if not findings:
            return "No findings to fix.", []
        lines = ["Fix suggestions:\n"]
        for f in findings[:5]:
            test = f.get("test_name", "?")
            cat = f.get("category", "?")
            fix = f.get("fix", "Review the counter-example calldata.")
            lines.append(f"- **{test}** ({cat}): {fix}")
        return "\n".join(lines), findings

    @staticmethod
    def _chains(findings: list, chains: list | None) -> tuple[str, list]:
        if not chains:
            return "No exploit chains identified.", findings
        lines = [f"**{len(chains)}** exploit chain(s) possible:\n"]
        for i, c in enumerate(chains[:5], 1):
            lines.append(f"### {i}. {c.get('name', '?')}")
            lines.append(f"Severity: **{c.get('severity', '?')}**")
            lines.append(f"Confidence: **{c.get('confidence', 0) * 100:.0f}%**")
            lines.append(f"Impact: {c.get('impact', '')}")
            lines.append("")
        return "\n".join(lines), findings

    @staticmethod
    def _fallback(query: str) -> tuple[str, list]:
        return (
            "Coba: 'summary', 'failed tests', 'show calldata', "
            "'access control', 'how to fix', 'exploit chains'.",
            [],
        )

    @staticmethod
    def _follow_ups(intent: str) -> list[str]:
        return {
            "summary": ["Show failed tests", "Show calldata", "Exploit chains"],
            "failed": ["Show calldata", "How to fix?", "Exploit chains"],
            "calldata": ["Show access control", "Failed tests"],
            "category": ["Show failed", "How to fix?"],
            "fix": ["Show failed tests", "Exploit chains"],
            "chain": ["Show failed tests", "Show calldata"],
        }.get(intent, ["Show summary", "Show failed tests"])


def create_nlp() -> HalmosNLP:
    return HalmosNLP()
