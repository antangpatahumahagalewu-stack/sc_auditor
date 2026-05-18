"""Vyper shared utilities for smart contract auditing."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_standard_input_json(raw: str) -> dict[str, str] | None:
    """Parse Solidity Standard Input JSON into {filename: content} dict.

    Handles Etherscan's double-encoded JSON (``{{"language":"Solidity", ...}}``)
    as well as normal standard JSON input.

    Returns ``None`` if *raw* is not valid Standard Input JSON.
    """
    # Etherscan sometimes double-encodes the JSON (outer braces doubled)
    text = raw.strip()

    # Remove one layer of double-brace wrapping: ``{{ ... }}`` → ``{ ... }``
    if text.startswith("{{") and text.endswith("}}"):
        text = text[1:-1]

    try:
        data: dict[str, Any] = json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None

    # Standard Input JSON has ``language`` and ``sources`` keys
    language = data.get("language", "")
    if language != "Solidity":
        return None

    sources_raw: dict[str, Any] | None = data.get("sources")
    if not sources_raw:
        return None

    sources: dict[str, str] = {}
    for path, info in sources_raw.items():
        if isinstance(info, dict):
            content = info.get("content", "")
        elif isinstance(info, str):
            content = info
        else:
            continue

        if content:
            sources[path] = content

    return sources if sources else None
