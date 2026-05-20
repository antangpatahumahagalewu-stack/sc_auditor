"""Unit tests for Case confidence calculation.

Spec:
  - Single scanner: confidence = scanner's confidence
  - Multiple scanners (merged): confidence = average of ALL scanner confidences
  - Edge cases: confidence bounds [0.0, 1.0]
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/15-dashboard"))

from src.models import CaseCreate, ScannerFinding
from src.storage import create_case


@pytest.fixture(autouse=True)
def _patch_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect SC_AUDITOR_DIR to a temp directory."""
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setattr("src.storage.SC_AUDITOR_DIR", tmp)
    monkeypatch.setattr("src.storage.CASES_DIR", tmp / "cases")
    monkeypatch.setattr("src.storage.LEARNING_DIR", tmp / "learning")
    (tmp / "cases").mkdir(parents=True, exist_ok=True)
    (tmp / "learning").mkdir(parents=True, exist_ok=True)


def _scan(name: str, confidence: float, detector: str = "reentrancy") -> ScannerFinding:
    return ScannerFinding(name=name, detector=detector, confidence=confidence)


def _make(project: str = "test", title: str = "Test",
          contract: str = "Vault", function: str = "withdraw",
          scanners: list[ScannerFinding] | None = None,
          severity: str = "High", description: str = "", recommendation: str = "") -> CaseCreate:
    return CaseCreate(
        project=project, title=title, contract=contract, function=function,
        scanners=scanners or [_scan("slither", 0.85)],
        severity=severity, description=description, recommendation=recommendation,
    )


class TestConfidence:
    """Confidence calculation tests."""

    def test_single_scanner(self) -> None:
        """Single scanner → confidence = its confidence."""
        case = create_case(_make(scanners=[_scan("slither", 0.70)]))
        assert case.confidence == 0.70

    def test_average_two_scanners(self) -> None:
        """Two scanners → confidence = average."""
        case1 = create_case(_make(scanners=[_scan("slither", 0.70)]))
        case2 = create_case(_make(
            scanners=[_scan("mythril", 0.90)],
            contract="Vault", function="withdraw"))  # same contract/function → merge
        assert case2.case_id == case1.case_id
        assert case2.confidence == 0.80  # (0.70 + 0.90) / 2

    def test_average_three_scanners(self) -> None:
        """Three scanners → confidence = average of all three."""
        case = create_case(_make(
            scanners=[
                _scan("slither", 0.70),
                _scan("mythril", 0.90),
                _scan("echidna", 0.80),
            ]
        ))
        # All three are in one CaseCreate, no merge needed
        assert case.scanner_count == 3
        expected = round((0.70 + 0.90 + 0.80) / 3, 2)
        assert case.confidence == expected

    def test_merge_confidence_average(self) -> None:
        """After merge, confidence = avg of all scanners."""
        c1 = create_case(_make(scanners=[_scan("slither", 0.70)]))
        c2 = create_case(_make(
            scanners=[_scan("mythril", 0.86), _scan("echidna", 0.90)],
            contract="Vault", function="withdraw"))
        assert c2.case_id == c1.case_id
        expected = round((0.70 + 0.86 + 0.90) / 3, 2)
        assert c2.confidence == expected

    def test_confidence_zero(self) -> None:
        """Confidence of 0 is allowed."""
        case = create_case(_make(scanners=[_scan("slither", 0.0)]))
        assert case.confidence == 0.0

    def test_confidence_one(self) -> None:
        """Confidence of 1.0 is allowed."""
        case = create_case(_make(scanners=[_scan("slither", 1.0)]))
        assert case.confidence == 1.0

    def test_confidence_bounds(self) -> None:
        """Confidence always in [0.0, 1.0]."""
        for conf in [0.0, 0.25, 0.5, 0.75, 1.0]:
            case = create_case(_make(scanners=[_scan("slither", conf)]))
            assert 0.0 <= case.confidence <= 1.0
