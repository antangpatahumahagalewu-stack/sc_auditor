"""Compiler Error Classifier — 30+ pattern regex for Solidity errors.

Mengklasifikasikan pesan error dari ``forge build`` ke dalam kategori:
  - syntax     (missing semicolon, parentheses mismatch)
  - type       (type mismatch, implicit conversion)
  - import     (file not found, unresolved import)
  - visibility (function visibility, mutability)
  - abi        (ABI encoding/decoding)
  - yul        (Yul/inline assembly)
  - override   (override specifier, virtual)
  - constructor (constructor syntax, params)
  - modifier   (modifier syntax)
  - state      (state variable shadowing, mutability)
  - event      (event parameter, anonymous)
  - error_decl (custom error declaration)
  - library    (library function, using for)
  - pragma     (pragma version, experimental)
  - abstract   (unimplemented function)
  - receive    (receive/fallback function)
  - unknown
"""

from __future__ import annotations

import re
from typing import Any

# ── Error Pattern Definitions ───────────────────────────────
# Setiap pattern punya: regex, category, severity, label

ERROR_PATTERNS: list[dict[str, Any]] = [
    # ── Syntax Errors ──
    {
        "pattern": r"Expected\s*';'",
        "category": "syntax",
        "severity": "blocking",
        "label": "Missing Semicolon",
        "description": "Missing semicolon at end of statement.",
    },
    {
        "pattern": r"Expected\s*(?:'(?:\)|\]|\}|\)|\))'|closing.+?\))",
        "category": "syntax",
        "severity": "blocking",
        "label": "Mismatched Parentheses/Brackets",
        "description": "Unmatched or mismatched closing bracket/parenthesis.",
    },
    {
        "pattern": r"Expected\s*'(?:string|uint|int|bool|address|bytes)'",
        "category": "syntax",
        "severity": "blocking",
        "label": "Missing Type",
        "description": "Type declaration expected but not found.",
    },
    {
        "pattern": r"Unexpected\s+token",
        "category": "syntax",
        "severity": "blocking",
        "label": "Unexpected Token",
        "description": "Parser encountered an unexpected token.",
    },
    {
        "pattern": r"Expected\s+'(?:;|,|\||\^|&|>|<|=|\+|\-|\*|\/)'",
        "category": "syntax",
        "severity": "blocking",
        "label": "Missing Operator/Punctuation",
        "description": "Expected an operator or punctuation.",
    },
    {
        "pattern": r"Documentation\s+tag.*@(?:param|return|dev|notice).*is\s+not\s+(?:valid|allowed)",
        "category": "syntax",
        "severity": "warning",
        "label": "Invalid NatSpec Tag",
        "description": "Invalid or misplaced NatSpec documentation tag.",
    },
    # ── Type Errors ──
    {
        "pattern": r"Type\s+(?:string|uint\d*|int\d*|bool|address|bytes\d*|byte)\s+is\s+not\s+implicitly\s+convertible",
        "category": "type",
        "severity": "blocking",
        "label": "Implicit Type Conversion",
        "description": "Implicit type conversion not allowed — explicit cast required.",
    },
    {
        "pattern": r"Return\s+argument\s+type\s+.*does\s+not\s+match",
        "category": "type",
        "severity": "blocking",
        "label": "Return Type Mismatch",
        "description": "Returned value type does not match declared return type.",
    },
    {
        "pattern": r"Operator\s+[+\-*/%]\s+not\s+compatible\s+with\s+type",
        "category": "type",
        "severity": "blocking",
        "label": "Operator Type Incompatibility",
        "description": "Operator cannot be applied to given types.",
    },
    {
        "pattern": r"Member\s+'.*?'\s+not\s+found",
        "category": "type",
        "severity": "blocking",
        "label": "Member Not Found",
        "description": "Referenced member does not exist on the type.",
    },
    {
        "pattern": r"Wrong\s+number\s+of\s+(arguments|parameters)",
        "category": "type",
        "severity": "blocking",
        "label": "Argument Count Mismatch",
        "description": "Function called with wrong number of arguments.",
    },
    {
        "pattern": r"Invalid\s+type\s+for\s+argument",
        "category": "type",
        "severity": "blocking",
        "label": "Invalid Argument Type",
        "description": "Argument type does not match function parameter type.",
    },
    {
        "pattern": r"Data\s+location\s+can\s+only\s+be\s+(memory|storage|calldata)",
        "category": "type",
        "severity": "blocking",
        "label": "Invalid Data Location",
        "description": "Invalid data location specifier for the type.",
    },
    # ── Import Errors ──
    {
        "pattern": r"File\s+not\s+found\s+(?:at|for)\s+import",
        "category": "import",
        "severity": "blocking",
        "label": "Import File Not Found",
        "description": "Referenced import file was not found in the project.",
    },
    {
        "pattern": r"Source\s+['\"].+?['\"]\s+not\s+found",
        "category": "import",
        "severity": "blocking",
        "label": "Source Not Found",
        "description": "Referenced source file does not exist.",
    },
    {
        "pattern": r"Import\s+path\s+is\s+not\s+(relative|absolute)",
        "category": "import",
        "severity": "blocking",
        "label": "Invalid Import Path",
        "description": "Import path format is invalid.",
    },
    {
        "pattern": r"Circular\s+import",
        "category": "import",
        "severity": "blocking",
        "label": "Circular Import",
        "description": "Circular dependency detected between source files.",
    },
    # ── Visibility / Mutability ──
    {
        "pattern": r"Function\s+.*?\s+(must|needs|should)\s+(be\s+)?declared\s+(as\s+)?(internal|external|public|private)",
        "category": "visibility",
        "severity": "blocking",
        "label": "Missing Function Visibility",
        "description": "Function visibility specifier is missing or incorrect.",
    },
    {
        "pattern": r"State\s+variable\s+.*?\s+must\s+be\s+declared\s+(as\s+)?(public|private|internal)",
        "category": "visibility",
        "severity": "blocking",
        "label": "Missing Variable Visibility",
        "description": "State variable visibility specifier is missing.",
    },
    {
        "pattern": r"Function\s+.*?\s+(can|should)\s+be\s+declared\s+(as\s+)?(pure|view)",
        "category": "visibility",
        "severity": "warning",
        "label": "Missing Mutability Specifier",
        "description": "Function can be declared as pure/view.",
    },
    # ── Override ──
    {
        "pattern": r"Overriding\s+function\s+.*?\s+missing\s+'override'\s+specifier",
        "category": "override",
        "severity": "blocking",
        "label": "Missing Override Specifier",
        "description": "Function overrides a parent but missing 'override' keyword.",
    },
    {
        "pattern": r"Function\s+.*?\s+marked\s+(as\s+)?override\s+but\s+does\s+not\s+override",
        "category": "override",
        "severity": "blocking",
        "label": "Unnecessary Override",
        "description": "Function marked override but does not override anything.",
    },
    # ── Constructor ──
    {
        "pattern": r"Constructor\s+must\s+be\s+declared\s+as\s+(public|internal)",
        "category": "constructor",
        "severity": "blocking",
        "label": "Constructor Visibility",
        "description": "Constructor visibility is invalid (was removed in Solidity 0.7+).",
    },
    {
        "pattern": r"Modifier\s+with\s+no\s+parameters\s+should\s+use\s+'_'",
        "category": "constructor",
        "severity": "warning",
        "label": "Modifier Style",
        "description": "Modifier without parameters should use underscore placeholder.",
    },
    # ── Pragma ──
    {
        "pattern": r"Pragma\s+version\s+.*?\s+does\s+not\s+satisfy",
        "category": "pragma",
        "severity": "blocking",
        "label": "Pragma Version Mismatch",
        "description": "Compiler version does not satisfy the pragma requirement.",
    },
    {
        "pattern": r"Experimental\s+feature\s+not\s+enabled",
        "category": "pragma",
        "severity": "blocking",
        "label": "Experimental Feature Disabled",
        "description": "Required experimental feature (e.g. ABIEncoderV2) not enabled.",
    },
    # ── Abstract / Interface ──
    {
        "pattern": r"Contract\s+.*?\s+should\s+be\s+marked\s+as\s+abstract",
        "category": "abstract",
        "severity": "blocking",
        "label": "Missing Abstract Keyword",
        "description": "Contract has unimplemented functions but not marked abstract.",
    },
    {
        "pattern": r"Unimplemented\s+(function|modifier)",
        "category": "abstract",
        "severity": "blocking",
        "label": "Unimplemented Function",
        "description": "Contract inherits unimplemented functions.",
    },
    # ── Receive / Fallback ──
    {
        "pattern": r"Fallback\s+function\s+must\s+be\s+declared\s+as\s+external",
        "category": "receive",
        "severity": "blocking",
        "label": "Fallback Visibility",
        "description": "Fallback function must be declared external.",
    },
    {
        "pattern": r"Receive\s+function\s+must\s+have\s+(?:payable|external)",
        "category": "receive",
        "severity": "blocking",
        "label": "Receive Ether Signature",
        "description": "Receive function must be external and payable.",
    },
    # ── Library ──
    {
        "pattern": r"Library\s+.*?\s+must\s+be\s+declared\s+as\s+internal",
        "category": "library",
        "severity": "blocking",
        "label": "Library Function Visibility",
        "description": "Library functions must be internal.",
    },
    {
        "pattern": r"Using\s+for\s+.*?\s+not\s+found",
        "category": "library",
        "severity": "blocking",
        "label": "Using For Not Found",
        "description": "Library type not found for 'using for' directive.",
    },
    # ── Yul / Assembly ──
    {
        "pattern": r"Only\s+non\-view\s+functions\s+can\s+use\s+assembly",
        "category": "yul",
        "severity": "blocking",
        "label": "Assembly in View Function",
        "description": "Inline assembly not allowed in pure/view functions.",
    },
    {
        "pattern": r"Function\s+expected\s+but\s+not\s+found\s+in\s+inline\s+assembly",
        "category": "yul",
        "severity": "blocking",
        "label": "Assembly Function Not Found",
        "description": "Referenced function in inline assembly does not exist.",
    },
    # ── Other ──
    {
        "pattern": r"Warning:\s+.*?\s+is\s+not\s+used",
        "category": "warning",
        "severity": "warning",
        "label": "Unused Variable",
        "description": "Variable declared but never used.",
    },
    {
        "pattern": r"Warning:\s+.*?\s+shadow(?:s|ed)",
        "category": "warning",
        "severity": "warning",
        "label": "Variable Shadowing",
        "description": "Local variable shadows outer declaration.",
    },
]

# ── Fallback ──

FALLBACK: dict[str, Any] = {
    "category": "unknown",
    "severity": "blocking",
    "label": "Unknown Compiler Error",
    "description": "Error pattern could not be classified.",
}


class CompilerClassifier:
    """Classify compiler errors from forge build output."""

    def __init__(self) -> None:
        # Pre-compile regex
        self._compiled: list[dict[str, Any]] = []
        for p in ERROR_PATTERNS:
            try:
                regex = re.compile(p["pattern"], re.IGNORECASE)
                self._compiled.append({**p, "_regex": regex})
            except re.error as exc:
                import structlog
                log = structlog.get_logger()
                log.warning("classifier.invalid_pattern", pattern=p["pattern"], error=str(exc))

    def classify(self, error_message: str) -> dict[str, Any]:
        """Classify a single compiler error/warning message."""
        for entry in self._compiled:
            if entry["_regex"].search(error_message):
                return {
                    "category": entry["category"],
                    "severity": entry["severity"],
                    "label": entry["label"],
                    "description": entry["description"],
                    "confidence": 0.9,
                }
        return {
            "category": FALLBACK["category"],
            "severity": FALLBACK["severity"],
            "label": FALLBACK["label"],
            "description": FALLBACK["description"],
            "confidence": 0.3,
        }

    def classify_batch(
        self,
        errors: list[str],
    ) -> list[dict[str, Any]]:
        """Classify multiple error messages."""
        return [self.classify(e) for e in errors]

    def get_categories(self) -> list[str]:
        """Return all available categories."""
        seen: set[str] = set()
        for p in ERROR_PATTERNS:
            seen.add(p["category"])
        return sorted(seen)

    def get_pattern_count(self) -> dict[str, int]:
        """Count patterns per category."""
        counts: dict[str, int] = {}
        for p in ERROR_PATTERNS:
            cat = p["category"]
            counts[cat] = counts.get(cat, 0) + 1
        return counts


def create_classifier() -> CompilerClassifier:
    return CompilerClassifier()
