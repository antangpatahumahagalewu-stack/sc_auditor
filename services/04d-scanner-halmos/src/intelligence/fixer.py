"""Halmos Fix Generator — L4 Intelligence.

Template-based fix suggestions based on failure category.
Focuses on symbolic execution counter-example interpretation.
"""

from __future__ import annotations

import re
from typing import Any

FIX_TEMPLATES: list[dict[str, Any]] = [
    {
        "pattern": r"assertion_violation",
        "category": "assertion_violation",
        "fix": "Review the assertion condition — the symbolic executor found inputs that violate it. Add edge case handling or adjust the assertion to match intended behavior.",
        "before": "assert(balance >= amount);",
        "after": "if (balance < amount) revert InsufficientBalance(balance, amount);",
        "solidity_example": "// ❌ Assertion may be too strict\nassert(balance >= amount);\n\n// ✅ Handle edge case explicitly\nif (balance < amount) {\n    revert InsufficientBalance(balance, amount);\n}",
        "references": ["https://swcregistry.io/docs/SWC-110"],
        "confidence": 0.85,
    },
    {
        "pattern": r"reentrancy",
        "category": "reentrancy",
        "fix": "Apply Checks-Effects-Interactions pattern: update state before making external calls.",
        "before": "function withdraw(uint256 a) external {\n    (bool s,) = msg.sender.call{value: a}(\"\");\n    require(s);\n    balances[msg.sender] -= a;\n}",
        "after": "function withdraw(uint256 a) external {\n    balances[msg.sender] -= a;\n    (bool s,) = msg.sender.call{value: a}(\"\");\n    require(s);\n}",
        "solidity_example": "// Apply Checks-Effects-Interactions pattern\nfunction withdraw(uint256 amount) external {\n    // Checks\n    require(amount > 0, \"Zero amount\");\n    // Effects\n    balances[msg.sender] -= amount;\n    // Interactions\n    (bool success,) = msg.sender.call{value: amount}(\"\");\n    require(success, \"Transfer failed\");\n}",
        "references": ["https://swcregistry.io/docs/SWC-107"],
        "confidence": 0.95,
    },
    {
        "pattern": r"arithmetic",
        "category": "arithmetic",
        "fix": "Use Solidity >=0.8.0 built-in overflow protection or SafeMath for older versions.",
        "before": "uint256 c = a + b;",
        "after": "uint256 c = a + b; // Solidity 0.8+ has built-in overflow check",
        "solidity_example": "// Solidity 0.8+ protects against overflow automatically\nfunction add(uint256 a, uint256 b) pure returns (uint256) {\n    return a + b; // reverts on overflow\n}\n\n// For older versions, use SafeMath\nimport \"@openzeppelin/contracts/utils/math/SafeMath.sol\";\nusing SafeMath for uint256;\nfunction add(uint256 a, uint256 b) pure returns (uint256) {\n    return a.add(b);\n}",
        "references": ["https://swcregistry.io/docs/SWC-101"],
        "confidence": 0.90,
    },
    {
        "pattern": r"access_control",
        "category": "access_control",
        "fix": "Add proper access control modifiers (onlyOwner, role-based) to restricted functions.",
        "before": "function withdrawAll() external {\n    payable(msg.sender).transfer(address(this).balance);\n}",
        "after": "function withdrawAll() external onlyOwner {\n    payable(msg.sender).transfer(address(this).balance);\n}",
        "solidity_example": "modifier onlyOwner() {\n    require(msg.sender == owner, \"Not owner\");\n    _;\n}\n\nfunction withdrawAll() external onlyOwner {\n    payable(msg.sender).transfer(address(this).balance);\n}",
        "references": ["https://swcregistry.io/docs/SWC-105"],
        "confidence": 0.95,
    },
    {
        "pattern": r"accounting",
        "category": "accounting",
        "fix": "Review balance tracking logic. Ensure all token/ETH movements are correctly accounted for in state variables.",
        "before": "function deposit() external payable {\n    balances[msg.sender] += msg.value;\n}\n\nfunction withdraw() external {\n    payable(msg.sender).transfer(balances[msg.sender]);\n    balances[msg.sender] = 0;\n}",
        "after": "function deposit() external payable {\n    balances[msg.sender] += msg.value;\n}\n\nfunction withdraw() external {\n    uint256 amount = balances[msg.sender];\n    balances[msg.sender] = 0;\n    payable(msg.sender).transfer(amount);\n}",
        "solidity_example": "// Use Checks-Effects-Interactions for all accounting\nfunction withdraw() external {\n    uint256 amount = balances[msg.sender];\n    balances[msg.sender] = 0;\n    (bool success,) = msg.sender.call{value: amount}(\"\");\n    require(success);\n}",
        "references": [],
        "confidence": 0.85,
    },
    {
        "pattern": r"oracle",
        "category": "oracle",
        "fix": "Use a decentralized oracle (Chainlink) instead of manipulable sources like block.timestamp or spot price from a single DEX.",
        "solidity_example": "import \"@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol\";\n\ncontract MyContract {\n    AggregatorV3Interface internal priceFeed;\n    \n    constructor() {\n        priceFeed = AggregatorV3Interface(0x...);\n    }\n    \n    function getLatestPrice() public view returns (int) {\n        (, int price,,,) = priceFeed.latestRoundData();\n        return price;\n    }\n}",
        "references": ["https://swcregistry.io/docs/SWC-119"],
        "confidence": 0.85,
    },
    {
        "pattern": r"flash_loan",
        "category": "flash_loan",
        "fix": "Ensure price calculations use TWAP (time-weighted average price) instead of spot price to prevent flash loan manipulation.",
        "solidity_example": "// Use Uniswap V2 TWAP or Chainlink oracle\n// instead of spot price from reserves\n\n// ❌ Vulnerable to flash loan\nuint256 spotPrice = reserve1 * 1e18 / reserve0;\n\n// ✅ Use TWAP\n(uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast) = IUniswapV2Pair(pair).getReserves();\nuint32 timeElapsed = block.timestamp - blockTimestampLast;\nuint256 price = \n    timeElapsed > 0 ? \n    _calculateTWAP(reserve0, reserve1, timeElapsed) :\n    _calculateSpotPrice(reserve0, reserve1);",
        "references": [],
        "confidence": 0.80,
    },
]


class HalmosFixer:
    """Generate fix suggestions for Halmos findings."""

    def __init__(self) -> None:
        self._compiled: list[dict[str, Any]] = []
        for tpl in FIX_TEMPLATES:
            try:
                regex = re.compile(tpl["pattern"], re.IGNORECASE)
                self._compiled.append({**tpl, "_regex": regex})
            except re.error:
                pass

    def generate_fix(self, finding: dict[str, Any]) -> dict[str, Any]:
        category = finding.get("category", "unknown")
        for entry in self._compiled:
            if entry["_regex"].search(category):
                return {
                    "category": entry["category"],
                    "fix": entry["fix"],
                    "before": entry.get("before", ""),
                    "after": entry.get("after", ""),
                    "solidity_example": entry.get("solidity_example", ""),
                    "references": entry.get("references", []),
                    "confidence": entry.get("confidence", 0.7),
                }

        return {
            "category": category,
            "fix": f"Review test '{finding.get('test_name', 'unknown')}' — the symbolic executor found a counter-example. Examine the calldata to understand the attack path.",
            "before": "",
            "after": "",
            "solidity_example": "",
            "references": [],
            "confidence": 0.4,
        }

    def generate_fixes(self, findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for f in findings:
            cat = f.get("category", "unknown")
            fix = self.generate_fix(f)
            result.setdefault(cat, []).append(fix)
        return result

    def get_stats(self) -> dict[str, Any]:
        return {
            "known_templates": len(FIX_TEMPLATES),
            "categories": [t["category"] for t in FIX_TEMPLATES],
        }


def create_fixer() -> HalmosFixer:
    return HalmosFixer()
