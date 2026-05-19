"""Echidna Fix Generator — L4 Intelligence.

Template-based fix suggestions untuk setiap kategori failure fuzzing.
Setiap template mencakup:
- Deskripsi masalah
- Before/after code snippet
- Penjelasan kenapa fix tersebut bekerja
- Referensi eksternal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class FixSuggestion:
    """Saran fix untuk satu finding fuzzing."""

    category: str
    title: str
    description: str
    severity: str
    before: str = ""
    after: str = ""
    solidity_example: str = ""
    references: list[str] = field(default_factory=list)
    confidence: float = 0.8


# ── Fix Templates ───────────────────────────────────────────

FIX_TEMPLATES: dict[str, dict[str, Any]] = {
    "reentrancy": {
        "description": "Echidna mendeteksi bahwa properti reentrancy dapat dilanggar. Kontrak memungkinkan pemanggilan ulang sebelum state selesai diupdate.",
        "before": (
            "function withdraw(uint256 amount) external {\n"
            "    require(balances[msg.sender] >= amount);\n"
            "    (bool s, ) = msg.sender.call{value: amount}(\"\");\n"
            "    require(s);\n"
            "    balances[msg.sender] -= amount;  // ❌ state update AFTER external call\n"
            "}"
        ),
        "after": (
            "function withdraw(uint256 amount) external {\n"
            "    require(balances[msg.sender] >= amount);\n"
            "    balances[msg.sender] -= amount;  // ✅ state update BEFORE external call\n"
            "    (bool s, ) = msg.sender.call{value: amount}(\"\");\n"
            "    require(s);\n"
            "}"
        ),
        "solidity_example": (
            "// 🔒 Fix: Checks-Effects-Interactions pattern\n"
            "// 1. Update state BEFORE external call\n"
            "// 2. Consider OpenZeppelin ReentrancyGuard\n\n"
            "import \"@openzeppelin/contracts/security/ReentrancyGuard.sol\";\n\n"
            "contract Secure is ReentrancyGuard {\n"
            "    function withdraw(uint256 amount) external nonReentrant {\n"
            "        require(balances[msg.sender] >= amount);\n"
            "        balances[msg.sender] -= amount;\n"
            "        (bool s, ) = msg.sender.call{value: amount}(\"\");\n"
            "        require(s);\n"
            "    }\n"
            "}"
        ),
        "references": ["SWC-107", "OpenZeppelin ReentrancyGuard"],
        "confidence": 0.95,
    },
    "access_control": {
        "description": "Echidna mendeteksi bahwa fungsi kritis dapat dipanggil tanpa otorisasi yang tepat.",
        "before": "function mint(address to, uint256 amount) external {\n    _mint(to, amount);  // ❌ No access control\n}",
        "after": "function mint(address to, uint256 amount) external onlyOwner {\n    _mint(to, amount);  // ✅ onlyOwner\n}",
        "solidity_example": (
            "// 🔒 Fix: Tambahkan access control modifier\n\n"
            "import \"@openzeppelin/contracts/access/Ownable.sol\";\n\n"
            "contract Secure is Ownable {\n"
            "    function mint(address to, uint256 amount) external onlyOwner {\n"
            "        _mint(to, amount);\n"
            "    }\n"
            "}"
        ),
        "references": ["SWC-105", "OpenZeppelin Ownable"],
        "confidence": 0.95,
    },
    "arithmetic": {
        "description": "Echidna mendeteksi overflow/underflow atau manipulasi numerik yang tidak aman.",
        "before": "function add(uint256 a, uint256 b) external pure returns (uint256) {\n    return a + b;  // ❌ Unchecked\n}",
        "after": "function add(uint256 a, uint256 b) external pure returns (uint256) {\n    return a + b;  // ✅ Solidity 0.8+ auto-check\n}",
        "solidity_example": (
            "// 🔒 Fix: Gunakan SafeMath atau Solidity 0.8+\n"
            "// Solidity >=0.8.0 sudah memiliki built-in overflow check\n\n"
            "// Jika perlu backward compatibility:\n"
            "import \"@openzeppelin/contracts/utils/math/SafeMath.sol\";\n\n"
            "contract Secure {\n"
            "    using SafeMath for uint256;\n"
            "    function add(uint256 a, uint256 b) external pure returns (uint256) {\n"
            "        return a.add(b);\n"
            "    }\n"
            "}"
        ),
        "references": ["SWC-101"],
        "confidence": 0.90,
    },
    "fund_loss": {
        "description": "Echidna mendeteksi kemungkinan kehilangan dana — ETH atau token dapat dikuras.",
        "before": (
            "function withdrawAll() external {\n"
            "    payable(msg.sender).transfer(address(this).balance);  // ❌ No balance tracking\n"
            "}"
        ),
        "after": (
            "function withdraw(uint256 amount) external {\n"
            "    require(amount <= balances[msg.sender]);\n"
            "    balances[msg.sender] -= amount;\n"
            "    payable(msg.sender).transfer(amount);\n"
            "}"
        ),
        "solidity_example": (
            "// 🔒 Fix: Track balances secara individual\n\n"
            "mapping(address => uint256) public balances;\n\n"
            "function withdraw(uint256 amount) external {\n"
            "    require(amount <= balances[msg.sender]);\n"
            "    balances[msg.sender] -= amount;\n"
            "    payable(msg.sender).transfer(amount);\n"
            "}"
        ),
        "references": [],
        "confidence": 0.85,
    },
    "oracle_manipulation": {
        "description": "Echidna mendeteksi bahwa oracle price dapat dimanipulasi.",
        "before": "function getPrice() external view returns (uint256) {\n    return price;  // ❌ Single source\n}",
        "after": "function getPrice() external view returns (uint256) {\n    // ✅ Gunakan TWAP atau multi-source oracle\n    return oracle.consult(address(this), amount);\n}",
        "solidity_example": (
            "// 🔒 Fix: Gunakan decentralized oracle\n\n"
            "import \"@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol\";\n\n"
            "contract Secure {\n"
            "    AggregatorV3Interface internal priceFeed;\n\n"
            "    function getPrice() external view returns (uint256) {\n"
            "        (, int256 price, , , ) = priceFeed.latestRoundData();\n"
            "        require(price > 0);\n"
            "        return uint256(price);\n"
            "    }\n"
            "}"
        ),
        "references": ["SWC-120", "Chainlink Price Feeds"],
        "confidence": 0.75,
    },
    "invariant_break": {
        "description": "Echidna mendeteksi invariant contract dilanggar. Perlu investigasi lebih lanjut untuk menentukan penyebab.",
        "before": "",
        "after": "",
        "solidity_example": (
            "// 🔒 Investigasi: Cari tahu invariant mana yang broken\n"
            "// 1. Review call sequence dari Echidna\n"
            "// 2. Identifikasi state changes yang unexpected\n"
            "// 3. Tambahkan require/assert untuk menjaga invariant\n\n"
            "function update(uint256 value) external {\n"
            "    // ✅ Maintain invariant\n"
            "    require(value <= MAX_VALUE, \"Invariant: value exceeds max\");\n"
            "    totalValue += value;\n"
            "}"
        ),
        "references": [],
        "confidence": 0.50,
    },
}


class EchidnaFixer:
    """Generate fix suggestions untuk Echidna findings."""

    def __init__(self) -> None:
        self._templates = FIX_TEMPLATES

    def generate_fix(
        self,
        category: str,
        title: str,
        severity: str,
    ) -> FixSuggestion:
        template = self._templates.get(category)
        if template is None:
            return FixSuggestion(
                category=category,
                title=title,
                description=f"Review dan fix issues terkait {category}.",
                severity=severity,
                confidence=0.4,
            )

        return FixSuggestion(
            category=category,
            title=title,
            description=template["description"],
            severity=severity,
            before=template.get("before", ""),
            after=template.get("after", ""),
            solidity_example=template.get("solidity_example", ""),
            references=template.get("references", []),
            confidence=template.get("confidence", 0.7),
        )

    def generate_fixes(
        self,
        findings: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for f in findings:
            category = f.get("failure_category", "unknown")
            fix = self.generate_fix(
                category=category,
                title=f.get("title", ""),
                severity=f.get("failure_severity", f.get("severity", "medium")),
            )
            result.setdefault(category, []).append({
                "title": fix.title,
                "description": fix.description,
                "before": fix.before,
                "after": fix.after,
                "solidity_example": fix.solidity_example,
                "references": fix.references,
                "confidence": fix.confidence,
            })
        return result

    def get_available_categories(self) -> list[str]:
        return sorted(self._templates.keys())

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_templates": len(self._templates),
            "categories": sorted(self._templates.keys()),
        }


def create_fixer() -> EchidnaFixer:
    return EchidnaFixer()
