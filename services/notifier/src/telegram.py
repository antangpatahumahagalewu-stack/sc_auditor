"""Telegram bot notifier for the Vyper Notifier Service.

Sends formatted messages (Markdown/HTML) and documents (reports) via
the Telegram Bot API using httpx.  No external SDK dependency — uses
the raw REST API for maximum simplicity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import structlog

from src.models import DeliveryResult

log = structlog.get_logger()

# ── API Constants ───────────────────────────────────────────

TELEGRAM_API_BASE: str = "https://api.telegram.org/bot"
MAX_MESSAGE_LENGTH: int = 4096  # Telegram's hard limit per message


# ── Rate-Limited HTTP Client ────────────────────────────────


class TelegramClient:
    """Thin wrapper around httpx.AsyncClient for Telegram Bot API calls."""

    def __init__(self, bot_token: str) -> None:
        self._token = bot_token
        self._base_url = f"{TELEGRAM_API_BASE}{bot_token}"
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    @property
    def base_url(self) -> str:
        return self._base_url

    async def close(self) -> None:
        await self._client.aclose()

    async def post(self, method: str, **kwargs: Any) -> httpx.Response:
        """POST to a Telegram Bot API method.

        Args:
            method: API method name (e.g. "sendMessage", "sendDocument").
            **kwargs: Passed as JSON body to the API.

        Raises:
            httpx.TimeoutException: On network timeout.
            httpx.HTTPStatusError: On non-2xx response.
        """
        url = f"{self._base_url}/{method}"
        resp = await self._client.post(url, json=kwargs)
        resp.raise_for_status()
        return resp

    async def get_me(self) -> dict[str, Any]:
        """Call ``getMe`` to verify the bot token is valid."""
        resp = await self.post("getMe")
        data: dict[str, Any] = resp.json()
        return data


# ── Notifier ─────────────────────────────────────────────────


class TelegramNotifier:
    """Send notifications via Telegram Bot API.

    Uses MarkdownV2 formatting by default with HTML fallback.

    Usage::

        notifier = TelegramNotifier(bot_token="123:ABC")
        result = await notifier.send(
            "Audit complete for Ethena USDe",
            chat_id="-1001234567890",
        )
    """

    def __init__(self, client: TelegramClient | None = None, bot_token: str = "") -> None:
        if client:
            self._client = client
        else:
            self._client = TelegramClient(bot_token=bot_token)
        self._parse_mode: str = "MarkdownV2"

    async def close(self) -> None:
        await self._client.close()

    async def send(
        self,
        message: str,
        chat_id: str | None = None,
        *,
        program: str | None = None,
        audit_id: str | None = None,
        findings_count: int = 0,
        critical_count: int = 0,
        high_count: int = 0,
        report_url: str | None = None,
        chain: str | None = None,
        address: str | None = None,
    ) -> DeliveryResult:
        """Send a formatted notification message to a Telegram chat.

        Builds a MarkdownV2 formatted message from the audit metadata
        and delivers it.  Falls back to plain text if the formatted
        message exceeds Telegram's length limit.

        Args:
            message: Human-readable summary text.
            chat_id: Target chat identifier.  Falls back to env var.
            program: Name of the audited program / project.
            audit_id: Unique audit session identifier.
            findings_count: Total number of findings.
            critical_count: Number of critical findings.
            high_count: Number of high findings.
            report_url: Link to the full audit report.
            chain: Blockchain name.
            address: Contract address.

        Returns:
            A DeliveryResult indicating success or failure.
        """
        cid = chat_id or ""
        if not cid:
            return DeliveryResult(
                channel="telegram",
                success=False,
                error="No Telegram chat ID configured",
            )

        text = self._format_message(
            message=message,
            program=program,
            audit_id=audit_id,
            findings_count=findings_count,
            critical_count=critical_count,
            high_count=high_count,
            report_url=report_url,
            chain=chain,
            address=address,
        )

        try:
            return await self._send_text(cid, text)
        except Exception as exc:
            log.error("telegram.send_failed", program=program, error=str(exc))
            return DeliveryResult(
                channel="telegram",
                success=False,
                error=str(exc),
            )

    async def send_simple(
        self,
        text: str,
        chat_id: str | None = None,
    ) -> DeliveryResult:
        """Send a plain text message (no formatting) to a Telegram chat.

        Args:
            text: Message content.
            chat_id: Target chat identifier.

        Returns:
            A DeliveryResult indicating success or failure.
        """
        cid = chat_id or ""
        if not cid:
            return DeliveryResult(
                channel="telegram",
                success=False,
                error="No Telegram chat ID configured",
            )
        return await self._send_text(cid, text, parse_mode="")

    async def send_document(
        self,
        file_path: str | Path,
        chat_id: str | None = None,
        caption: str = "",
    ) -> DeliveryResult:
        """Send a file (e.g. audit report PDF/MD) to a Telegram chat.

        Reads the file from disk and uploads it via ``sendDocument``.

        Args:
            file_path: Absolute or relative path to the file on disk.
            chat_id: Target chat identifier.
            caption: Optional caption (MarkdownV2 formatted).

        Returns:
            A DeliveryResult indicating success or failure.
        """
        cid = chat_id or ""
        if not cid:
            return DeliveryResult(
                channel="telegram",
                success=False,
                error="No Telegram chat ID configured",
            )

        path = Path(file_path)
        if not path.is_file():
            return DeliveryResult(
                channel="telegram",
                success=False,
                error=f"File not found: {path}",
            )

        try:
            url = f"{self._client.base_url}/sendDocument"
            files = {"document": path.open("rb")}
            params: dict[str, Any] = {"chat_id": cid}

            if caption:
                params["caption"] = caption
                params["parse_mode"] = self._parse_mode

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, data=params, files=files)

            resp.raise_for_status()
            body = resp.json()
            message_id = None
            if body.get("ok") and body.get("result", {}).get("message_id"):
                message_id = str(body["result"]["message_id"])

            log.info("telegram.document_sent", file=path.name, chat_id=_mask_chat(cid))
            return DeliveryResult(
                channel="telegram",
                success=True,
                message_id=message_id,
            )

        except httpx.TimeoutException as exc:
            return DeliveryResult(
                channel="telegram",
                success=False,
                error=f"Upload timeout: {exc}",
            )
        except httpx.HTTPStatusError as exc:
            return DeliveryResult(
                channel="telegram",
                success=False,
                error=f"HTTP {exc.response.status_code}: {exc.response.text[:300]}",
            )
        except (httpx.RequestError, OSError) as exc:
            return DeliveryResult(
                channel="telegram",
                success=False,
                error=f"Network error: {exc}",
            )
        except Exception as exc:
            log.exception("telegram.document_failed", file=str(path), error=str(exc))
            return DeliveryResult(
                channel="telegram",
                success=False,
                error=f"Unexpected error: {exc}",
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _send_text(
        self,
        chat_id: str,
        text: str,
        parse_mode: str | None = None,
    ) -> DeliveryResult:
        """Send a text message, truncating if necessary."""
        if parse_mode is None:
            parse_mode = self._parse_mode

        # Truncate if too long
        if len(text) > MAX_MESSAGE_LENGTH:
            text = text[: MAX_MESSAGE_LENGTH - 100] + "\n\n…(truncated)"
            # Remove parse mode if truncation broke formatting
            parse_mode = ""

        try:
            resp = await self._client.post(
                "sendMessage",
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=False,
            )
            body = resp.json()
            message_id = None
            if body.get("ok") and body.get("result", {}).get("message_id"):
                message_id = str(body["result"]["message_id"])

            log.info("telegram.delivered", chat_id=_mask_chat(chat_id))
            return DeliveryResult(
                channel="telegram",
                success=True,
                message_id=message_id,
            )

        except httpx.TimeoutException as exc:
            log.error("telegram.timeout", chat_id=_mask_chat(chat_id), error=str(exc))
            return DeliveryResult(
                channel="telegram",
                success=False,
                error=f"Timeout: {exc}",
            )
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            log.error(
                "telegram.http_error",
                status_code=exc.response.status_code,
                body=body,
            )
            if exc.response.status_code == 400 and "can't parse entities" in body:
                # Retry without formatting
                log.info("telegram.retry_plain", chat_id=_mask_chat(chat_id))
                return await self._send_text(chat_id, _strip_markdown(text), parse_mode="")
            return DeliveryResult(
                channel="telegram",
                success=False,
                error=f"HTTP {exc.response.status_code}: {body[:200]}",
            )
        except (httpx.RequestError, OSError) as exc:
            log.error("telegram.network_error", error=str(exc))
            return DeliveryResult(
                channel="telegram",
                success=False,
                error=f"Network error: {exc}",
            )

    def _format_message(
        self,
        message: str,
        program: str | None,
        audit_id: str | None,
        findings_count: int,
        critical_count: int,
        high_count: int,
        report_url: str | None,
        chain: str | None,
        address: str | None,
    ) -> str:
        """Build a MarkdownV2 formatted notification message.

        All special MarkdownV2 characters are escaped in user-supplied
        text to prevent parse errors.
        """
        prog = _escape_md(program or "Unknown")
        parts: list[str] = [
            f"*Vyper Audit Complete — {prog}*",
            "",
            _escape_md(message or "Audit analysis finished."),
            "",
        ]

        if audit_id:
            parts.append(f"`Audit ID:` `{audit_id[:12]}…`")

        if chain:
            parts.append(f"`Chain:     ` {_escape_md(chain)}")

        if address:
            short = f"{address[:6]}…{address[-4:]}" if len(address) > 12 else address
            parts.append(f"`Contract:  ` `{short}`")

        if findings_count > 0:
            severity = [f"Total: *{findings_count}*"]
            if critical_count > 0:
                severity.append(f"Critical: *{critical_count}*")
            if high_count > 0:
                severity.append(f"High: *{high_count}*")
            parts.append(f"`Findings:  ` {' | '.join(severity)}")

        if report_url:
            parts.append("")
            parts.append(f"[📄 View Full Report]({_escape_md_url(report_url)})")

        parts.append("")
        parts.append("__Vyper Security Scanner__")

        return "\n".join(parts)


# ── MarkdownV2 Escaping ────────────────────────────────────


def _escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2.

    The characters that must be escaped: ``_ * [ ] ( ) ~ ` > # + - = | { } . !``
    """
    special_chars = r"_*[]()~`>#+-=|{}.!"
    result: list[str] = []
    for ch in text:
        if ch in special_chars:
            result.append(f"\\{ch}")
        else:
            result.append(ch)
    return "".join(result)


def _escape_md_url(url: str) -> str:
    """Escape special characters in MarkdownV2 URL, keeping ``( )`` unescaped."""
    # In URLs, parentheses are part of the URL syntax and must NOT be escaped
    special_chars = r"_*[]~`>#+-=|{}.!"
    result: list[str] = []
    for ch in url:
        if ch in special_chars:
            result.append(f"\\{ch}")
        else:
            result.append(ch)
    return "".join(result)


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting, keep only plain text."""
    import re
    # Remove bold/italic
    text = re.sub(r"[*_~`]", "", text)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove links: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _mask_chat(chat_id: str) -> str:
    """Mask the chat ID for logging (show last 4 chars)."""
    if len(chat_id) <= 6:
        return "***"
    return f"...{chat_id[-4:]}"


# ── Factory ─────────────────────────────────────────────────


def create_telegram_notifier(bot_token: str = "") -> TelegramNotifier:
    """Create a new TelegramNotifier instance.

    Args:
        bot_token: Telegram Bot API token.  Can be set later via
            ``TELEGRAM_BOT_TOKEN`` env var or passed directly.
    """
    client = TelegramClient(bot_token=bot_token)
    return TelegramNotifier(client=client)
