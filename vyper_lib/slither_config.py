"""Slither configuration builder.

Builds Slither configuration JSON objects for fine-grained control over
which detectors are enabled, severity thresholds, and output preferences.
"""

from __future__ import annotations

from typing import Any

import structlog

log = structlog.get_logger()

# Detectors that are overly noisy in routine scans.
NOISY_DETECTORS: frozenset[str] = frozenset({
    "naming-convention",
    "pragma",
    "solc-version",
    "constable-states",
    "immutable-states",
    "too-many-digits",
    "conformance-to-solidity-naming-conventions",
    "redundant-statements",
    "similar-names",
    "incorrect-versions-of-solidity",
})

# Detectors that produce true positives worth investigating.
HIGH_VALUE_DETECTORS: frozenset[str] = frozenset({
    "reentrancy-eth",
    "reentrancy-no-eth",
    "unchecked-lowlevel",
    "unchecked-send",
    "tx-origin",
    "arbitrary-send",
    "controlled-delegatecall",
    "controlled-array-length",
    "incorrect-equality",
    "locked-ether",
    "shadowing-state",
    "shadowing-abstract",
    "suicidal",
    "controlled-delegatecall",
    "uninitialized-state",
    "uninitialized-storage",
    "uninitialized-implementation",
    "unused-return",
    "write-after-write",
    "missing-zero-check",
    "cyclomatic-complexity",
    "calls-loop",
    "timestamp",
    "assembly",
    "low-level-calls",
    "naming-convention",
    "external-function",
    "multiple-constructors",
    "reentrancy-events",
    "variable-scope",
})


class SlitherConfigBuilder:
    """Build Slither configuration dictionaries.

    Usage::

        builder = SlitherConfigBuilder()
        config = builder.with_tier("strict").disable_noisy().build()

    Args:
        default_tier: Default configuration preset name.
    """

    # Preset configurations
    PRESETS: dict[str, dict[str, Any]] = {
        "strict": {
            "detector_to_exclude": [],
            "filter_paths": [],
            "compile_force_framework": "hardhat",
            "compile_remove_metadata": True,
            "disable_color": True,
            "exclude_informational": False,
            "exclude_low": False,
            "exclude_medium": False,
            "exclude_high": False,
            "fail_on": ["high", "medium"],
            "fail_patch": None,
            "json": "-",
            "legacy_ast": False,
            "minimum_confidence": "medium",
            "print_help": False,
            "solc_ast": True,
            "triage_mode": False,
        },
        "default": {
            "detector_to_exclude": list(NOISY_DETECTORS),
            "filter_paths": [],
            "compile_force_framework": "hardhat",
            "compile_remove_metadata": True,
            "disable_color": True,
            "exclude_informational": False,
            "exclude_low": False,
            "exclude_medium": False,
            "exclude_high": False,
            "fail_on": ["high"],
            "json": "-",
            "legacy_ast": False,
            "minimum_confidence": "medium",
            "solc_ast": True,
            "triage_mode": False,
        },
        "noisy": {
            "detector_to_exclude": [],
            "filter_paths": [],
            "disable_color": True,
            "exclude_informational": True,
            "exclude_low": True,
            "json": "-",
            "minimum_confidence": "low",
            "solc_ast": True,
        },
        "minimal": {
            "detector_to_exclude": [],
            "filter_paths": [],
            "disable_color": True,
            "exclude_informational": True,
            "exclude_low": True,
            "exclude_medium": True,
            "exclude_high": False,
            "json": "-",
            "minimum_confidence": "high",
            "solc_ast": True,
            "detectors": [
                "reentrancy-eth",
                "reentrancy-no-eth",
                "unchecked-lowlevel",
                "unchecked-send",
                "tx-origin",
                "arbitrary-send",
                "controlled-delegatecall",
                "suicidal",
                "uninitialized-state",
                "uninitialized-storage",
                "incorrect-equality",
                "locked-ether",
            ],
        },
    }

    def __init__(self, default_tier: str = "default") -> None:
        self._tier = default_tier
        self._overrides: dict[str, Any] = {}
        self._enabled_detectors: list[str] | None = None
        self._disabled_detectors: list[str] | None = None

    # ------------------------------------------------------------------
    # Configuration methods
    # ------------------------------------------------------------------

    def with_tier(self, tier: str) -> SlitherConfigBuilder:
        """Set the configuration preset by name.

        Args:
            tier: One of ``"strict"``, ``"default"``, ``"noisy"``, ``"minimal"``.

        Returns:
            Self for chaining.
        """
        if tier not in self.PRESETS:
            log.warning("slither_config.unknown_tier", tier=tier)
            tier = "default"
        self._tier = tier
        return self

    def disable_noisy(self) -> SlitherConfigBuilder:
        """Disable known noisy detectors from the config.

        Returns:
            Self for chaining.
        """
        self._disabled_detectors = list(NOISY_DETECTORS)
        return self

    def enable_only(self, detectors: list[str]) -> SlitherConfigBuilder:
        """Run only the specified detectors.

        Args:
            detectors: List of detector names to enable.

        Returns:
            Self for chaining.
        """
        self._enabled_detectors = detectors
        return self

    def disable_detectors(self, detectors: list[str]) -> SlitherConfigBuilder:
        """Explicitly disable specific detectors.

        Args:
            detectors: List of detector names to disable.

        Returns:
            Self for chaining.
        """
        self._disabled_detectors = (self._disabled_detectors or []) + detectors
        return self

    def with_threshold(self, severity: str, confidence: str = "medium") -> SlitherConfigBuilder:
        """Set severity and confidence thresholds.

        Args:
            severity: Minimum severity (``"high"``, ``"medium"``, ``"low"``).
            confidence: Minimum confidence (``"high"``, ``"medium"``, ``"low"``).

        Returns:
            Self for chaining.
        """
        if severity in ("high", "medium", "low", "informational"):
            if severity == "high":
                self._overrides.update({
                    "exclude_low": True,
                    "exclude_medium": True,
                    "exclude_informational": True,
                })
            elif severity == "medium":
                self._overrides.update({
                    "exclude_low": True,
                    "exclude_informational": True,
                })
            elif severity == "low":
                self._overrides.update({
                    "exclude_informational": True,
                })

        if confidence in ("high", "medium", "low"):
            self._overrides["minimum_confidence"] = confidence

        return self

    def with_override(self, key: str, value: Any) -> SlitherConfigBuilder:
        """Set a raw Slither configuration key.

        Args:
            key: Configuration key name.
            value: Configuration value.

        Returns:
            Self for chaining.
        """
        self._overrides[key] = value
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> dict[str, Any]:
        """Build the final Slither configuration dict.

        Returns:
            A dict suitable for saving as ``.slither.config.json``.
        """
        base = dict(self.PRESETS.get(self._tier, self.PRESETS["default"]))

        if self._disabled_detectors:
            base["detector_to_exclude"] = list(set(
                base.get("detector_to_exclude", []) + self._disabled_detectors
            ))

        if self._enabled_detectors:
            all_detectors = set(HIGH_VALUE_DETECTORS) | set(NOISY_DETECTORS)
            extra = {
                "divide-before-multiply",
                "encode-packed-collision",
                "enum-conversion",
                "events-access",
                "events-matchers",
                "function-init-state",
                "incorrect-modifier",
                "msg-value-loop",
                "missing-inheritance",
                "reentrancy-bridge",
                "reentrancy-functional",
                "return-bomb",
                "storage-order",
                "unused-state",
            }
            all_detectors.update(extra)
            excluded = all_detectors - set(self._enabled_detectors)
            base["detector_to_exclude"] = list(excluded)

        base.update(self._overrides)

        log.debug(
            "slither_config.built",
            tier=self._tier,
            excluded_detectors=len(base.get("detector_to_exclude", [])),
        )

        return base


# ------------------------------------------------------------------
# Convenience factory
# ------------------------------------------------------------------


def create_slither_config(tier: str = "default") -> dict[str, Any]:
    """Create a Slither configuration dict in one call.

    Args:
        tier: Configuration preset name (``"strict"``, ``"default"``, etc.).

    Returns:
        A configuration dict for Slither.
    """
    return SlitherConfigBuilder().with_tier(tier).build()
