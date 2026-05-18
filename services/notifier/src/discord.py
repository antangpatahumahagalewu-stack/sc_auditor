"""Discord webhook notifier for the Vyper Notifier Service.

Sends rich embed messages to Discord channels via webhook URLs.
Handles rate limits (Retry-After header) and network errors gracefully.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from src.models import DeliveryResult

log = structlog.get_logger()

# ── Embed Color Constants ───────────────────────────────────

EMBED_COLOR_CRITICAL: int = 0xE74C3C  # Red
EMBED_COLOR_HIGH: int = 0xE67E22  # Orange
EMBED_COLOR_MEDIUM: int = 0xF1C40F  # Yellow
EMBED_COLOR_LOW: int = 0x3498DB  # Blue
EMBED_COLOR_INFO: int = 0x2ECC71  # Green
EMBED_COLOR_DEFAULT: int = 0x5865F2  # Discord blurple


@dataclass
class DiscordEmbedField:
    """A single field within a Discord embed."""

    name: str
    value: str
    inline: bool = False


@dataclass
class DiscordEmbed:
    """A Discord embed object.

    See: https://discord.com/developers/docs/resources/message#embed-object
    """

    title: str = ""
    description: str = ""
    color: int = EMBED_COLOR_DEFAULT
    fields: list[DiscordEmbedField] = field(default_factory=list)
    footer_text: str = ""
    timestamp: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize this embed to a Discord API-compatible dictionary."""
        payload: dict[str, Any] = {
            "title": self.title,
            "description": self.description,
            "color": self.color,
        }
        if self.fields:
            payload["fields"] = [
                {"name": f.name, "value": f.value, "inline": f.inline}
                for f in self.fields
            ]
        if self.footer_text:
            payload["footer"] = {"text": self.footer_text}
        if self.timestamp:
            payload["timestamp"] = self.timestamp
        if self.url:
            payload["url"] = self.url
        return payload


# ── Color Selection ─────────────────────────────────────────


def _select_color(critical: int, high: int) -> int:
    """Pick an embed color based on finding severity counts."""
    if critical > 0:
        return EMBED_COLOR_CRITICAL
    if high > 0:
        return EMBED_COLOR_HIGH
    return EMBED_COLOR_DEFAULT


# ── Rate-Limited HTTP Client ────────────────────────────────


class DiscordClient:
    """Thin wrapper around httpx.AsyncClient with rate-limit handling."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def post_webhook(self, webhook_url: str, payload: dict[str, Any]) -> httpx.Response:
        """POST a payload to a Discord webhook URL, handling rate limits.

        If the response contains a Retry-After header, waits that many
        seconds (up to 60) before retrying once.
        """
        for attempt in range(2):
            resp = await self._client.post(webhook_url, json=payload)
            if resp.status_code == 429 and attempt == 0:
                retry_after = _parse_retry_after(resp)
                if retry_after and retry_after <= 60:
                    log.warning(
                        "discord.rate_limited",
                        retry_after=retry_after,
                        webhook_url=_mask_url(webhook_url),
                    )
                    await asyncio.sleep(retry_after)
                    continue
            resp.raise_for_status()
            return resp
        # If we exhausted retries, return the last response
        return resp


def _parse_retry_after(resp: httpx.Response) -> float | None:
    """Extract the Retry-After value from a 429 response."""
    try:
        body = resp.json()
        return float(body.get("retry_after", 0))
    except (ValueError, KeyError):
        return None


def _mask_url(url: str) -> str:
    """Mask the token portion of a Discord webhook URL for logging."""
    # https://discord.com/api/webhooks/{id}/{token}
    parts = url.rsplit("/", 1)
    if len(parts) == 2 and len(parts[1]) > 8:
        return f"{parts[0]}/***{parts[1][-4:]}"
    return "<webhook>"


# ── Notifier ─────────────────────────────────────────────────


class DiscordNotifier:
    """Send notifications via Discord webhooks.

    Usage::

        notifier = DiscordNotifier()
        result = await notifier.send(
            "Ethena USDe audit complete — 5 findings, 2 critical",
            webhook_url="https://discord.com/api/webhooks/..."
        )
    """

    def __init__(self, client: DiscordClient | None = None) -> None:
        self._client = client or DiscordClient()

    async def close(self) -> None:
        await self._client.close()

    async def send(
        self,
        message: str,
        webhook_url: str | None = None,
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
        """Send a notification to a Discord webhook.

        Builds a rich embed from the audit metadata and delivers it.

        Args:
            message: Human-readable summary text.
            webhook_url: Discord webhook URL. Falls back to env var.
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
        url = webhook_url or ""
        if not url:
            return DeliveryResult(
                channel="discord",
                success=False,
                error="No Discord webhook URL configured",
            )

        embed = self._build_embed(
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

        payload: dict[str, Any] = {
            "embeds": [embed.to_dict()],
        }

        try:
            resp = await self._client.post_webhook(url, payload)
            message_id = None
            try:
                body = resp.json()
                message_id = str(body.get("id", ""))
            except (ValueError, KeyError):
                pass

            log.info(
                "discord.delivered",
                program=program,
                audit_id=audit_id,
                status_code=resp.status_code,
            )
            return DeliveryResult(
                channel="discord",
                success=True,
                message_id=message_id,
            )

        except httpx.TimeoutException as exc:
            log.error("discord.timeout", program=program, error=str(exc))
            return DeliveryResult(
                channel="discord",
                success=False,
                error=f"Timeout: {exc}",
            )
        except httpx.HTTPStatusError as exc:
            log.error(
                "discord.http_error",
                program=program,
                status_code=exc.response.status_code,
                body=exc.response.text[:500],
            )
            return DeliveryResult(
                channel="discord",
                success=False,
                error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            )
        except (httpx.RequestError, OSError) as exc:
            log.error("discord.network_error", program=program, error=str(exc))
            return DeliveryResult(
                channel="discord",
                success=False,
                error=f"Network error: {exc}",
            )
        except Exception as exc:
            log.exception("discord.unexpected_error", program=program, error=str(exc))
            return DeliveryResult(
                channel="discord",
                success=False,
                error=f"Unexpected error: {exc}",
            )

    def _build_embed(
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
    ) -> DiscordEmbed:
        """Build a rich embed from audit metadata."""
        prog = program or "Unknown"
        color = _select_color(critical_count, high_count)

        embed = DiscordEmbed(
            title=f"Vyper Audit Complete — {prog}",
            description=message or "Audit analysis finished.",
            color=color,
            footer_text="Vyper Security Scanner",
        )

        if audit_id:
            embed.fields.append(
                DiscordEmbedField(name="Audit ID", value=f"`{audit_id[:12]}…`", inline=True)
            )

        if chain:
            embed.fields.append(
                DiscordEmbedField(name="Chain", value=chain, inline=True)
            )

        if address:
            short_addr = f"{address[:6]}…{address[-4:]}" if len(address) > 12 else address
            embed.fields.append(
                DiscordEmbedField(name="Contract", value=f"`{short_addr}`", inline=True)
            )

        if findings_count > 0:
            severity_parts = [f"Total: **{findings_count}**"]
            if critical_count > 0:
                severity_parts.append(f"🔴 Critical: **{critical_count}**")
            if high_count > 0:
                severity_parts.append(f"🟠 High: **{high_count}**")
            embed.fields.append(
                DiscordEmbedField(
                    name="Findings",
                    value=" | ".join(severity_parts),
                    inline=False,
                )
            )

        if report_url:
            embed.fields.append(
                DiscordEmbedField(name="Report", value=report_url, inline=False)
            )

        return embed

    async def send_embed(
        self,
        title: str,
        description: str,
        color: int = EMBED_COLOR_DEFAULT,
        fields: list[dict[str, Any]] | None = None,
        webhook_url: str | None = None,
    ) -> DeliveryResult:
        """Send an arbitrary rich embed to a Discord webhook.

        Args:
            title: Embed title.
            description: Embed description (Markdown supported).
            color: Integer hex colour (e.g. 0xE74C3C for red).
            fields: List of dicts with keys ``name``, ``value``, ``inline``.
            webhook_url: Discord webhook URL. Falls back to env var.

        Returns:
            A DeliveryResult indicating success or failure.
        """
        url = webhook_url or ""
        if not url:
            return DeliveryResult(
                channel="discord",
                success=False,
                error="No Discord webhook URL configured",
            )

        embed = DiscordEmbed(
            title=title,
            description=description,
            color=color,
            footer_text="Vyper Security Scanner",
        )

        if fields:
            for f in fields:
                embed.fields.append(
                    DiscordEmbedField(
                        name=str(f.get("name", "")),
                        value=str(f.get("value", "")),
                        inline=bool(f.get("inline", False)),
                    )
                )

        payload: dict[str, Any] = {"embeds": [embed.to_dict()]}

        try:
            resp = await self._client.post_webhook(url, payload)
            log.info("discord.embed_delivered", title=title, status_code=resp.status_code)
            return DeliveryResult(channel="discord", success=True)
        except Exception as exc:
            log.error("discord.embed_failed", title=title, error=str(exc))
            return DeliveryResult(
                channel="discord",
                success=False,
                error=str(exc),
            )

    async def send_simple(self, content: str, webhook_url: str | None = None) -> DeliveryResult:
        """Send a simple text message (no embed) to a Discord webhook.

        Useful for test messages or non-audit notifications.

        Args:
            content: Plain text or Markdown content.
            webhook_url: Discord webhook URL.

        Returns:
            A DeliveryResult indicating success or failure.
        """
        url = webhook_url or ""
        if not url:
            return DeliveryResult(
                channel="discord",
                success=False,
                error="No Discord webhook URL configured",
            )

        payload: dict[str, Any] = {"content": content}

        try:
            resp = await self._client.post_webhook(url, payload)
            log.info("discord.simple_delivered", status_code=resp.status_code)
            return DeliveryResult(channel="discord", success=True)
        except Exception as exc:
            log.error("discord.simple_failed", error=str(exc))
            return DeliveryResult(
                channel="discord",
                success=False,
                error=str(exc),
            )


# ── Factory ─────────────────────────────────────────────────


def create_discord_notifier() -> DiscordNotifier:
    """Create a new DiscordNotifier instance."""
    return DiscordNotifier()
