"""LLMClient — Unified client for OpenAI and Anthropic APIs.

Supports GPT-4o, GPT-4, and Claude 3.5 Sonnet with:
  - async/await via httpx.AsyncClient
  - Exponential backoff retry via tenacity
  - Structured JSON output parsing
  - Circuit breaker for sustained failures
  - Configurable model selection
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.models import LlmAnalysis, Provider, Severity, Verdict

log = structlog.get_logger()

# ── Constants ──────────────────────────────────────────────

OPENAI_BASE_URL = "https://api.openai.com/v1"
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_TIMEOUT = 60.0
MAX_TOKENS = 4096
TEMPERATURE = 0.1  # Low temperature for deterministic analysis

# ── System Prompt ──────────────────────────────────────────

SYSTEM_PROMPT = """You are a world-class smart contract security expert with deep knowledge of Solidity, EVM internals, and DeFi attack vectors. Your task is to analyze scanner findings and provide accurate True Positive / False Positive classifications.

## Your Analysis Process

For each finding, follow these steps:

1. **Understand the finding** — Read the scanner's description. What vulnerability does it claim?

2. **Understand the context** — Read the source code around the flagged location. What does the code actually do?

3. **Validate the vulnerability** — Ask yourself:
   - Can this actually be exploited given the surrounding code structure?
   - Does the function follow checks-effects-interactions? If not, is reentrancy actually possible?
   - Is there an access control modifier that prevents the attack?
   - Is the dangerous operation protected by a require/if check elsewhere?
   - Could this finding be a false positive due to incomplete static analysis?
   - Has this code been in production without exploit? (Not definitive, but consider)
   - Is the finding in the right context? (e.g., a "reentrancy" finding in a function that clearly follows CEI is likely FP)

4. **Classify** — True Positive (real bug) or False Positive (noise/not exploitable)

5. **Assess severity** — If TP, determine the real-world severity:
   - **critical**: Direct loss of funds, unlimited minting, governance takeover
   - **high**: Loss of funds under specific conditions, permanent lock of assets
   - **medium**: Unexpected behavior, temporary lock, edge case DoS
   - **low**: Violation of best practices, informational, unlikely to cause loss
   - **informational**: Code style, gas optimization, naming conventions

6. **Provide reasoning** — Explain your analysis step-by-step. Reference specific code lines.

7. **Suggest a fix** — If TP, provide a concrete code fix. Be specific about what to change and why.

## Output Format

You MUST respond with a valid JSON object (no markdown, no code fences):

```json
{
  "verdict": "true_positive" | "false_positive",
  "confidence": 0.95,
  "severity": "critical" | "high" | "medium" | "low" | "informational",
  "reasoning": "Detailed step-by-step analysis...",
  "suggested_fix": "Specific code fix or null if FP..."
}
```

## Key Principles

- Be conservative: Only classify as TP if you are confident the vulnerability is exploitable
- Consider real-world exploitability, not just theoretical
- If insufficient context is provided, note this in your reasoning
- For False Positives, clearly explain why the finding is not exploitable
- For True Positives, provide actionable fix code

## Example

Finding: "Reentrancy in withdraw() — external call before state update"
Source: function withdraw() { uint amount = balances[msg.sender]; (bool ok,) = msg.sender.call{value: amount}(""); balances[msg.sender] = 0; }

Analysis: TP — The external call happens BEFORE the balance update. An attacker can re-enter withdraw() and drain the contract. This violates checks-effects-interactions.

Response: {"verdict": "true_positive", "confidence": 0.98, "severity": "critical", "reasoning": "The withdraw function makes an external call (msg.sender.call) before updating the user's balance to zero. This allows the recipient to re-enter the withdraw function recursively, draining the contract before any balance update occurs. This is a classic reentrancy vulnerability.", "suggested_fix": "Move balances[msg.sender] = 0 before the external call, or add a reentrancy guard."}"""


# ── LLM Response Parsing ──────────────────────────────────


def _parse_llm_response(raw: str) -> LlmAnalysis:
    """Parse the LLM response into a structured LlmAnalysis.

    Handles responses that may be wrapped in markdown code fences
    or contain trailing text after the JSON object.

    Args:
        raw: Raw text response from the LLM.

    Returns:
        Parsed LlmAnalysis object.

    Raises:
        ValueError: If the response cannot be parsed into valid JSON
                    with the expected structure.
    """
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        # Remove opening fence (possibly with language tag)
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        # Remove closing fence
        closing = text.rfind("```")
        if closing != -1:
            text = text[:closing]
        text = text.strip()

    # Parse JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        log.error("llm_json_parse_failed", raw=raw[:500], error=str(exc))
        raise ValueError(f"Failed to parse LLM response as JSON: {exc}") from exc

    # Validate required fields
    verdict_raw = data.get("verdict")
    if verdict_raw not in ("true_positive", "false_positive"):
        raise ValueError(f"Invalid verdict: {verdict_raw!r}")
    verdict: Verdict = verdict_raw

    confidence = float(data.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    severity_raw = data.get("severity", "medium")
    valid_severities = ("critical", "high", "medium", "low", "informational")
    if severity_raw not in valid_severities:
        severity_raw = "medium"
    severity: Severity = severity_raw

    reasoning = str(data.get("reasoning", ""))
    suggested_fix = data.get("suggested_fix")

    return LlmAnalysis(
        verdict=verdict,
        confidence=confidence,
        severity=severity,
        reasoning=reasoning,
        suggested_fix=suggested_fix,
    )


# ── Circuit Breaker ───────────────────────────────────────


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open and calls are blocked."""


class CircuitBreaker:
    """Simple circuit breaker for LLM API calls.

    Tracks failure count and opens the circuit after a threshold.
    After a reset timeout, transitions to half-open and allows
    a single test request.

    Attributes:
        failure_threshold: Number of consecutive failures before opening.
        reset_timeout: Seconds to wait before attempting half-open.
    """

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0) -> None:
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._state: str = "closed"  # closed, open, half-open

    @property
    def state(self) -> str:
        return self._state

    async def call(self, coro: Any) -> Any:
        """Execute a coroutine with circuit breaker protection.

        Args:
            coro: The async operation to execute.

        Returns:
            The result of the coroutine.

        Raises:
            CircuitBreakerOpenError: If the circuit is open.
            Exception: Any exception from the coroutine.
        """
        if self._state == "open":
            if time.monotonic() - self._last_failure_time >= self._reset_timeout:
                self._state = "half-open"
                log.info("circuit_breaker_half_open")
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = await coro
            self._failure_count = 0
            self._state = "closed"
            return result
        except Exception:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self._failure_threshold:
                self._state = "open"
                log.warning(
                    "circuit_breaker_opened",
                    failures=self._failure_count,
                    threshold=self._failure_threshold,
                    reset_timeout=self._reset_timeout,
                )
            raise


# ── LLM Client ────────────────────────────────────────────


class LLMClient:
    """Unified client for OpenAI and Anthropic LLM APIs.

    Supports GPT-4o, GPT-4, and Claude 3.5 Sonnet with automatic
    retry, circuit breaking, and structured response parsing.

    Attributes:
        openai_key: OpenAI API key (from env OPENAI_API_KEY).
        anthropic_key: Anthropic API key (from env ANTHROPIC_API_KEY).
        openai_model: OpenAI model name (default: gpt-4o).
        anthropic_model: Anthropic model name (default: claude-3-5-sonnet-20241022).
        preferred_provider: "openai" or "anthropic".
        http_client: Shared httpx.AsyncClient for connection pooling.
        circuit_breaker: CircuitBreaker for API failure protection.
    """

    def __init__(
        self,
        openai_key: str | None = None,
        anthropic_key: str | None = None,
        openai_model: str = "gpt-4o",
        anthropic_model: str = "claude-3-5-sonnet-20241022",
        preferred_provider: Provider = "openai",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.openai_model = openai_model
        self.anthropic_model = anthropic_model
        self.preferred_provider = preferred_provider

        self._http_client = http_client
        self._owned_client = http_client is None
        self.circuit_breaker = CircuitBreaker()

        log.info(
            "llm_client_initialized",
            provider=self.preferred_provider,
            openai_model=self.openai_model,
            anthropic_model=self.anthropic_model,
            openai_configured=bool(self.openai_key),
            anthropic_configured=bool(self.anthropic_key),
        )

    async def __aenter__(self) -> LLMClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(DEFAULT_TIMEOUT, connect=10.0),
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=20,
                ),
            )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._owned_client and self._http_client is not None:
            await self._http_client.aclose()

    # ── Public API ─────────────────────────────────────────

    async def analyze(
        self,
        source_code: str,
        finding_title: str,
        finding_description: str,
        finding_location: dict[str, Any] | None = None,
        compiler: str | None = None,
    ) -> LlmAnalysis:
        """Analyze a single scanner finding using the LLM.

        Sends the finding details and relevant source code to the LLM
        and returns a structured analysis verdict.

        Args:
            source_code: The full source code of the contract or relevant snippet.
            finding_title: The title/name of the finding.
            finding_description: Detailed description of the finding.
            finding_location: Source location info (file, line, code snippet).
            compiler: Solidity compiler version string (optional).

        Returns:
            Structured LlmAnalysis with verdict, confidence, severity, etc.

        Raises:
            CircuitBreakerOpenError: If the circuit breaker is open.
            RuntimeError: If no API key is configured.
        """
        if not self.openai_key and not self.anthropic_key:
            raise RuntimeError(
                "No API keys configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
            )

        # Build the user prompt
        user_prompt = self._build_prompt(
            source_code=source_code,
            finding_title=finding_title,
            finding_description=finding_description,
            finding_location=finding_location,
            compiler=compiler,
        )

        # Determine provider (preferred with fallback)
        provider, model = self._select_provider()

        log.info(
            "llm_analyze_calling",
            provider=provider,
            model=model,
            finding=finding_title,
        )

        try:
            if provider == "openai":
                raw = await self._circuit_call(
                    self._call_openai, model=model, messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ]
                )
            else:
                raw = await self._circuit_call(
                    self._call_anthropic, model=model, messages=[
                        {"role": "user", "content": user_prompt},
                    ]
                )
        except CircuitBreakerOpenError:
            log.error("llm_circuit_breaker_open", provider=provider)
            raise

        return _parse_llm_response(raw)

    async def suggest_fix(
        self,
        source_code: str,
        finding_title: str,
        finding_description: str,
        finding_location: dict[str, Any] | None = None,
        compiler: str | None = None,
    ) -> LlmAnalysis:
        """Get a fix suggestion from the LLM with focus on remediation.

        Similar to analyze() but with a prompt tuned for fix generation
        rather than TP/FP classification.

        Args:
            source_code: Full source code of the contract.
            finding_title: Title of the finding.
            finding_description: Description of the finding.
            finding_location: Source location info.
            compiler: Solidity compiler version.

        Returns:
            LlmAnalysis with detailed fix suggestion.
        """
        return await self.analyze(
            source_code=source_code,
            finding_title=finding_title,
            finding_description=finding_description,
            finding_location=finding_location,
            compiler=compiler,
        )

    # ── Internal: Provider Selection ───────────────────────

    def _select_provider(self) -> tuple[Provider, str]:
        """Select the active provider and model based on availability.

        Returns:
            Tuple of (provider_name, model_name).
        """
        if self.preferred_provider == "openai" and self.openai_key:
            return ("openai", self.openai_model)
        if self.anthropic_key:
            return ("anthropic", self.anthropic_model)
        if self.openai_key:
            return ("openai", self.openai_model)
        return ("openai", self.openai_model)

    # ── Internal: Prompt Building ──────────────────────────

    def _build_prompt(
        self,
        source_code: str,
        finding_title: str,
        finding_description: str,
        finding_location: dict[str, Any] | None = None,
        compiler: str | None = None,
    ) -> str:
        """Build the user message prompt for the LLM.

        Args:
            source_code: Contract source code.
            finding_title: Finding title.
            finding_description: Finding description.
            finding_location: Location info.
            compiler: Compiler version.

        Returns:
            Formatted prompt string.
        """
        parts: list[str] = [
            "## Source Code",
            "```solidity",
            source_code,
            "```",
            "",
            "## Finding",
        ]

        if finding_location:
            file_name = finding_location.get("file", "unknown.sol")
            line = finding_location.get("line", "?")
            snippet = finding_location.get("snippet", "")
            parts.append(f"- **File**: {file_name}")
            parts.append(f"- **Line**: {line}")
            if snippet:
                parts.append(f"- **Snippet**: `{snippet}`")

        parts.append(f"- **Title**: {finding_title}")
        parts.append(f"- **Description**: {finding_description}")

        if compiler:
            parts.append(f"- **Compiler**: {compiler}")

        parts.append(
            "\nAnalyze this finding following your expert process. "
            "Respond with a JSON object containing: verdict, confidence, severity, reasoning, and suggested_fix."
        )

        return "\n".join(parts)

    # ── Internal: API Calls ────────────────────────────────

    async def _circuit_call(self, fn: Any, **kwargs: Any) -> str:
        """Execute an API call through the circuit breaker.

        Args:
            fn: The async function to call.
            **kwargs: Arguments to pass to the function.

        Returns:
            The raw response text.
        """
        return await self.circuit_breaker.call(fn(**kwargs))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.HTTPStatusError, httpx.NetworkError)
        ),
        reraise=True,
    )
    async def _call_openai(
        self,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        """Call the OpenAI chat completions API.

        Args:
            model: Model name (e.g. "gpt-4o").
            messages: Chat messages in OpenAI format.

        Returns:
            Response content text.

        Raises:
            httpx.TimeoutException: On timeout.
            httpx.HTTPStatusError: On non-2xx status.
        """
        if self._http_client is None:
            raise RuntimeError("HTTP client not initialized. Use async context manager.")

        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }

        body = {
            "model": model,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
        }

        resp = await self._http_client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json=body,
        )

        if resp.status_code == 429:
            log.warning("openai_rate_limited", retry_after=resp.headers.get("retry-after"))
            resp.raise_for_status()  # tenacity will retry

        if resp.status_code == 401:
            log.error("openai_auth_failed")
            raise RuntimeError("OpenAI authentication failed. Check your API key.")

        resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.HTTPStatusError, httpx.NetworkError)
        ),
        reraise=True,
    )
    async def _call_anthropic(
        self,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        """Call the Anthropic messages API.

        Args:
            model: Model name (e.g. "claude-3-5-sonnet-20241022").
            messages: Chat messages (Anthropic format uses system as separate param).

        Returns:
            Response content text.

        Raises:
            httpx.TimeoutException: On timeout.
            httpx.HTTPStatusError: On non-2xx status.
        """
        if self._http_client is None:
            raise RuntimeError("HTTP client not initialized. Use async context manager.")

        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        body = {
            "model": model,
            "system": SYSTEM_PROMPT,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
        }

        resp = await self._http_client.post(
            f"{ANTHROPIC_BASE_URL}/messages",
            headers=headers,
            json=body,
        )

        if resp.status_code == 429:
            log.warning("anthropic_rate_limited", retry_after=resp.headers.get("retry-after"))
            resp.raise_for_status()

        if resp.status_code == 401:
            log.error("anthropic_auth_failed")
            raise RuntimeError("Anthropic authentication failed. Check your API key.")

        resp.raise_for_status()

        data = resp.json()
        content = data["content"][0]["text"]
        return content
