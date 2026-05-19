"""Echidna Call Sequence Analyzer — L4 Intelligence.

Echidna menghasilkan call sequence yang memicu failure. Modul ini
mengubah sequence tersebut menjadi narasi exploit yang mudah dipahami.

Berbeda dengan 04a yang memprediksi chain dari detector combination,
04b langsung menerima call sequence real dari Echidna.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

log = structlog.get_logger()


class SequenceAnalyzer:
    """Analyze and format Echidna call sequences."""

    @staticmethod
    def analyze_sequence(
        call_sequence: str | None,
        test_function: str = "",
    ) -> dict[str, Any]:
        """Parse dan analisis call sequence dari Echidna.

        Args:
            call_sequence: Raw call sequence string.
            test_function: Nama test function yang gagal.

        Returns:
            Dict dengan steps, narrative, severity, dll.
        """
        if not call_sequence:
            return {
                "has_sequence": False,
                "steps": [],
                "narrative": "No call sequence available.",
                "complexity": "unknown",
                "step_count": 0,
                "involves_eth": False,
                "involves_delegatecall": False,
            }

        # Parse lines
        lines = [l.strip() for l in call_sequence.split("\n") if l.strip()]
        steps = []
        involves_eth = False
        involves_delegatecall = False
        functions_called: list[str] = []

        for line in lines:
            # Detect function calls
            func_match = re.match(
                r"^(?:from:\s*\w+\s+)?(\w+)\(([^)]*)\)",
                line, re.IGNORECASE
            )
            if func_match:
                func_name = func_match.group(1)
                args = func_match.group(2)
                functions_called.append(func_name)
                steps.append({
                    "type": "call",
                    "function": func_name,
                    "args": args[:100] if args else "",
                    "raw": line[:120],
                })
                if "value" in args.lower() or "eth" in args.lower():
                    involves_eth = True
                if "delegatecall" in line.lower():
                    involves_delegatecall = True
                continue

            # Detect transfers
            if re.search(r"(transfer|send|call)\b", line, re.IGNORECASE):
                involves_eth = True
                steps.append({
                    "type": "transfer",
                    "raw": line[:120],
                })
                continue

            # Fallback
            steps.append({
                "type": "unknown",
                "raw": line[:120],
            })

        step_count = len(steps)
        if step_count <= 2:
            complexity = "simple"
        elif step_count <= 5:
            complexity = "moderate"
        else:
            complexity = "complex"

        # Build narrative
        if functions_called:
            func_str = " → ".join(functions_called[:5])
            if involves_eth:
                narrative = (
                    f"Call sequence involves ETH movement via {func_str}. "
                    f"Total {step_count} steps."
                )
            elif involves_delegatecall:
                narrative = (
                    f"Call sequence involves delegatecall via {func_str}. "
                    f"Potential storage corruption risk."
                )
            else:
                narrative = (
                    f"Call sequence: {func_str}. "
                    f"Total {step_count} steps."
                )
        else:
            narrative = f"Call sequence with {step_count} step(s). Review manually."

        return {
            "has_sequence": True,
            "steps": steps[:20],  # Cap at 20 steps
            "narrative": narrative,
            "complexity": complexity,
            "step_count": step_count,
            "functions_called": functions_called[:10],
            "involves_eth": involves_eth,
            "involves_delegatecall": involves_delegatecall,
        }

    @staticmethod
    def analyze_findings(
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Analyze sequences for all findings."""
        enriched = []
        for f in findings:
            seq = f.get("failing_input")
            analysis = SequenceAnalyzer.analyze_sequence(
                seq,
                test_function=f.get("test_function", ""),
            )
            enriched.append({
                **f,
                "sequence_analysis": analysis,
            })
        return enriched


def create_path_predictor() -> SequenceAnalyzer:
    return SequenceAnalyzer()
