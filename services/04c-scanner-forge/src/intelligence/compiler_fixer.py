"""Compiler Error Fix Generator — L4 Intelligence.

Template-based fix suggestions untuk error kompilasi Solidity.
Sangat berguna untuk developer — langsung kasih solusi konkret.
"""

from __future__ import annotations

import re
from typing import Any

# ── Fix Templates ───────────────────────────────────────────

FIX_TEMPLATES: list[dict[str, Any]] = [
    # ── Syntax ──
    {
        "pattern": r"Expected\s*';'",
        "category": "syntax",
        "label": "Missing Semicolon",
        "fix": "Add a semicolon ';' at the end of the statement.",
        "before": "uint256 a = 10",
        "after": "uint256 a = 10;",
        "solidity_example": "// ❌\nuint256 a = 10\n\n// ✅\nuint256 a = 10;",
        "confidence": 0.95,
    },
    {
        "pattern": r"Expected\s+'(?:\)|\])'",
        "category": "syntax",
        "label": "Mismatched Parentheses",
        "fix": "Add the missing closing bracket ')' or ']'.",
        "before": "function f() {",
        "after": "function f() {\n    \n}",
        "solidity_example": "// ❌\nfunction foo() {\n    bar(a, b;\n\n// ✅\nfunction foo() {\n    bar(a, b);\n}",
        "confidence": 0.90,
    },
    {
        "pattern": r"Unexpected\s+token",
        "category": "syntax",
        "label": "Unexpected Token",
        "fix": "Remove or replace the unexpected character or keyword.",
        "before": "function foo() extra public {}",
        "after": "function foo() public {}",
        "solidity_example": "// ❌ Remove unexpected keyword\nfunction foo() extra public {}\n\n// ✅\nfunction foo() public {}",
        "confidence": 0.85,
    },
    {
        "pattern": r"Expected\s+'(?:string|uint|int|bool|address|bytes)'",
        "category": "syntax",
        "label": "Missing Type",
        "fix": "Add the expected type declaration before the variable or parameter.",
        "before": "function foo(a) public {}",
        "after": "function foo(uint256 a) public {}",
        "solidity_example": "// ❌ Missing parameter type\nfunction foo(a) public {}\n\n// ✅\nfunction foo(uint256 a) public {}",
        "confidence": 0.85,
    },
    # ── Type ──
    {
        "pattern": r"Type\s+.*is\s+not\s+implicitly\s+convertible",
        "category": "type",
        "label": "Implicit Type Conversion",
        "fix": "Use explicit type conversion (cast) to convert between incompatible types.",
        "before": "uint256 a = uint8(255);",
        "after": "uint256 a = uint256(uint8(255));",
        "solidity_example": "// ❌\nuint8 a = 255;\nuint256 b = a;\n\n// ✅\nuint8 a = 255;\nuint256 b = uint256(a);",
        "confidence": 0.85,
    },
    {
        "pattern": r"Return\s+argument\s+type\s+.*does\s+not\s+match",
        "category": "type",
        "label": "Return Type Mismatch",
        "fix": "Ensure the returned expression matches the declared return type.",
        "before": "function foo() public returns (uint256) { return 'hello'; }",
        "after": "function foo() public returns (uint256) { return 42; }",
        "solidity_example": "// ❌ Return type mismatch\nfunction getCount() public view returns (uint256) {\n    return true;\n}\n\n// ✅\nfunction getCount() public view returns (uint256) {\n    return count;\n}",
        "confidence": 0.90,
    },
    {
        "pattern": r"Wrong\s+number\s+of\s+(arguments|parameters)",
        "category": "type",
        "label": "Argument Count Mismatch",
        "fix": "Check the function signature and match the correct number of arguments.",
        "before": "foo(1, 2); // but foo(uint256) expects 1 param",
        "after": "foo(1);",
        "solidity_example": "// ❌ Too many arguments\nfoo(1, 2);  // expects foo(uint256)\n\n// ✅\nfoo(1);",
        "confidence": 0.90,
    },
    {
        "pattern": r"Member\s+'.*?'\s+not\s+found",
        "category": "type",
        "label": "Member Not Found",
        "fix": "The member does not exist on this type. Check your spelling or use a different type.",
        "before": "address addr = 0x...;\naddr.transfer(1 ether); // transfer is for payable",
        "after": "payable(addr).transfer(1 ether);",
        "solidity_example": "// ❌\naddress a = 0x1234;\na.transfer(1 ether);\n\n// ✅ (address must be payable)\naddress payable a = payable(0x1234);\na.transfer(1 ether);",
        "confidence": 0.80,
    },
    # ── Import ──
    {
        "pattern": r"(?:File|Source)\s+not\s+found",
        "category": "import",
        "label": "Import Not Found",
        "fix": "Make sure the imported file exists and the path is correct. Use relative paths relative to the project root.",
        "before": "import {IERC20} from \"./IERC20.sol\";",
        "after": "import {IERC20} from \"./interfaces/IERC20.sol\";",
        "solidity_example": "// ❌ Wrong path\nimport \"../something/Ownable.sol\";\n\n// ✅ Check path from project root\nimport \"@openzeppelin/contracts/access/Ownable.sol\";\nimport \"./interfaces/IMyContract.sol\";",
        "confidence": 0.85,
    },
    {
        "pattern": r"Circular\s+import",
        "category": "import",
        "label": "Circular Import",
        "fix": "Break the circular dependency by extracting common types into a shared interface file.",
        "before": "// File A imports B, File B imports A",
        "after": "// Create shared interface file C, both A and B import C",
        "solidity_example": "// ❌ Circular: A.sol imports B.sol imports A.sol\n\n// ✅ Create IShared.sol with interfaces\n// Both A.sol and B.sol import IShared.sol instead of each other",
        "confidence": 0.75,
    },
    # ── Visibility ──
    {
        "pattern": r"Missing.*visibility",
        "category": "visibility",
        "label": "Missing Visibility",
        "fix": "Add a visibility specifier: public, private, internal, or external.",
        "before": "function foo() {}",
        "after": "function foo() public {}",
        "solidity_example": "// ❌ No visibility\nfunction foo() {}\n\n// ✅ Add visibility\nfunction foo() public {}\nfunction bar() private {}\nfunction baz() external {}",
        "confidence": 0.95,
    },
    {
        "pattern": r"can\s+be\s+declared\s+(pure|view)",
        "category": "visibility",
        "label": "Missing Mutability",
        "fix": "Add 'pure' or 'view' keyword — the function does not modify state.",
        "before": "function add(uint a, uint b) public returns (uint) { return a + b; }",
        "after": "function add(uint a, uint b) public pure returns (uint) { return a + b; }",
        "solidity_example": "// ❌\nfunction get() public returns (uint) { return 42; }\n\n// ✅\nfunction get() public pure returns (uint) { return 42; }",
        "confidence": 0.90,
    },
    # ── Override ──
    {
        "pattern": r"missing\s+'override'",
        "category": "override",
        "label": "Missing Override",
        "fix": "Add the 'override' keyword to the function that overrides a parent contract.",
        "before": "function foo() public {}",
        "after": "function foo() public override {}",
        "solidity_example": "// ❌\nfunction foo() public {}\n\n// ✅\nfunction foo() public override {}",
        "confidence": 0.95,
    },
    {
        "pattern": r"marked\s+override\s+but\s+does\s+not\s+override",
        "category": "override",
        "label": "Unnecessary Override",
        "fix": "Remove the 'override' keyword — this function does not override a parent function.",
        "before": "function foo() public override {}",
        "after": "function foo() public {}",
        "solidity_example": "// ❌\nfunction foo() public override {}\n\n// ✅ (if no parent has foo())\nfunction foo() public {}",
        "confidence": 0.95,
    },
    # ── Pragma ──
    {
        "pattern": r"Pragma.*does\s+not\s+satisfy",
        "category": "pragma",
        "label": "Pragma Version Mismatch",
        "fix": "Update the pragma version or use the correct compiler version.",
        "before": "pragma solidity ^0.8.0; // using compiler 0.7.0",
        "after": "pragma solidity ^0.7.0; // match available compiler",
        "solidity_example": "// ❌\npragma solidity ^0.8.19;\n// but forge is using 0.8.0\n\n// ✅ Widen version or update forge\npragma solidity ^0.8.0;",
        "confidence": 0.85,
    },
    {
        "pattern": r"Experimental\s+feature\s+not\s+enabled",
        "category": "pragma",
        "label": "Experimental Feature",
        "fix": "Enable the experimental feature in the pragma directive.",
        "before": "// Solidity 0.7.x needs explicit ABIEncoderV2",
        "after": "pragma experimental ABIEncoderV2;",
        "solidity_example": "// ❌ (Solidity <0.8.0)\npragma solidity ^0.7.0;\n// using struct in function signature\n\n// ✅\npragma solidity ^0.7.0;\npragma experimental ABIEncoderV2;",
        "confidence": 0.85,
    },
    # ── Abstract ──
    {
        "pattern": r"should\s+be\s+marked\s+as\s+abstract",
        "category": "abstract",
        "label": "Missing Abstract",
        "fix": "Add the 'abstract' keyword to the contract declaration.",
        "before": "contract MyContract {",
        "after": "abstract contract MyContract {",
        "solidity_example": "// ❌\ncontract MyContract {\n    function foo() virtual;\n}\n\n// ✅\nabstract contract MyContract {\n    function foo() virtual;\n}",
        "confidence": 0.95,
    },
    # ── Receive / Fallback ──
    {
        "pattern": r"Receive\s+function\s+must\s+have",
        "category": "receive",
        "label": "Invalid Receive Ether",
        "fix": "The receive() function must be external and payable.",
        "before": "receive() external {}",
        "after": "receive() external payable {}",
        "solidity_example": "// ❌\nreceive() external {}\n\n// ✅\nreceive() external payable {}",
        "confidence": 0.95,
    },
    {
        "pattern": r"Fallback.*must\s+be\s+declared\s+as\s+external",
        "category": "receive",
        "label": "Fallback Visibility",
        "fix": "The fallback() function must be declared external.",
        "before": "fallback() {}",
        "after": "fallback() external {}",
        "solidity_example": "// ❌\nfallback() {}\n\n// ✅\nfallback() external {}",
        "confidence": 0.95,
    },
    # ── Warning ──
    {
        "pattern": r"is\s+not\s+used",
        "category": "warning",
        "label": "Unused Variable",
        "fix": "Remove unused variables or add an underscore prefix to suppress warning.",
        "before": "uint256 a = 10; // never used",
        "after": "// Remove: uint256 a = 10;\n// OR use it:\nfunction foo() { uint256 a = 10; emit Log(a); }",
        "solidity_example": "// ❌\nuint256 result = calculate();\n// result not used\n\n// ✅ Use it or prefix with _\nuint256 _result = calculate();\n// or\nuint256 result = calculate();\nemit LogResult(result);",
        "confidence": 0.90,
    },
    {
        "pattern": r"shadow",
        "category": "warning",
        "label": "Variable Shadowing",
        "fix": "Rename the local variable so it doesn't shadow an outer declaration.",
        "before": "uint256 owner; // state variable\nfunction set(uint256 owner) external { owner = owner; }",
        "after": "uint256 owner;\nfunction set(uint256 _owner) external { owner = _owner; }",
        "solidity_example": "// ❌ Shadows state variable\nuint256 public count;\nfunction set(uint256 count) public { count = count; }\n\n// ✅\nuint256 public count;\nfunction set(uint256 _count) public { count = _count; }",
        "confidence": 0.90,
    },
]


class CompilerFixer:
    """Generate fix suggestions for compiler errors."""

    def __init__(self) -> None:
        self._compiled: list[dict[str, Any]] = []
        for tpl in FIX_TEMPLATES:
            try:
                regex = re.compile(tpl["pattern"], re.IGNORECASE)
                self._compiled.append({**tpl, "_regex": regex})
            except re.error:
                pass

    def generate_fix(self, error_message: str, category: str = "") -> dict[str, Any]:
        """Generate fix for single error message."""
        for entry in self._compiled:
            if entry["_regex"].search(error_message):
                return {
                    "category": entry["category"],
                    "label": entry["label"],
                    "fix": entry["fix"],
                    "before": entry.get("before", ""),
                    "after": entry.get("after", ""),
                    "solidity_example": entry.get("solidity_example", ""),
                    "confidence": entry.get("confidence", 0.7),
                }

        return {
            "category": category or "unknown",
            "label": "General Compiler Error",
            "fix": f"Review the error message and fix the issue: {error_message[:200]}",
            "before": "",
            "after": "",
            "solidity_example": "",
            "confidence": 0.4,
        }

    def generate_fixes(
        self,
        errors: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Generate fixes for multiple errors."""
        result: dict[str, list[dict[str, Any]]] = {}
        for e in errors:
            msg = e.get("error", e.get("message", ""))
            cat = e.get("category", "")
            fix = self.generate_fix(msg, category=cat)
            cat_key = fix["category"]
            result.setdefault(cat_key, []).append(fix)
        return result

    def get_known_categories(self) -> list[str]:
        seen: set[str] = set()
        for tpl in FIX_TEMPLATES:
            seen.add(tpl["category"])
        return sorted(seen)

    def get_stats(self) -> dict[str, Any]:
        return {
            "known_templates": len(FIX_TEMPLATES),
            "categories": self.get_known_categories(),
            "per_category": self._count_per_category(),
        }

    def _count_per_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for tpl in FIX_TEMPLATES:
            cat = tpl["category"]
            counts[cat] = counts.get(cat, 0) + 1
        return counts


def create_fixer() -> CompilerFixer:
    return CompilerFixer()
