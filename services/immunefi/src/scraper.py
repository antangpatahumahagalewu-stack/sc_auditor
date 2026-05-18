"""ImmunefiScraper — Fetches bug bounty programs from the Immunefi GitHub mirror."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = structlog.get_logger()

# ── Constants ──────────────────────────────────────────────

PROGRAM_LIST_URL = (
    "https://raw.githubusercontent.com/"
    "infosec-us-team/Immunefi-Bug-Bounty-Programs-Unofficial/main/projects.json"
)
PROGRAM_DETAIL_URL = (
    "https://raw.githubusercontent.com/"
    "infosec-us-team/Immunefi-Bug-Bounty-Programs-Unofficial/main/project/{slug}.json"
)

TIMEOUT = httpx.Timeout(30.0, connect=10.0)
MAX_RETRIES = 3


# ── Exceptions ─────────────────────────────────────────────

class ScraperError(Exception):
    """Base scraper exception."""
    pass


class ProgramNotFoundError(ScraperError):
    """Program slug not found on remote."""
    pass


# ── Retry Decorator ───────────────────────────────────────

scraper_retry = retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type(
        (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
    ),
    reraise=True,
)


# ── Scraper ────────────────────────────────────────────────

class ImmunefiScraper:
    """Fetch program data from the Immunefi GitHub mirror.

    Usage:
        async with ImmunefiScraper() as scraper:
            programs = await scraper.fetch_program_list()
            detail = await scraper.fetch_program_detail("some-slug")
    """

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client

    async def __aenter__(self) -> ImmunefiScraper:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client is not None:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Scraper not initialized (use 'async with' or pass a client)")
        return self._client

    # ── Public Methods ──────────────────────────────────────

    @scraper_retry
    async def fetch_program_list(self) -> list[dict[str, Any]]:
        """Fetch the full program list from projects.json.

        Returns a list of program dicts with keys:
            slug, name, chains, maxBounty, status, etc.
        """
        log.info("fetch_program_list.start")
        try:
            resp = await self.client.get(PROGRAM_LIST_URL)
            resp.raise_for_status()
            data: list[dict[str, Any]] = resp.json()
            log.info("fetch_program_list.success", count=len(data))
            return data
        except httpx.HTTPStatusError as e:
            log.warning("fetch_program_list.http_error", status=e.response.status_code)
            raise
        except Exception as e:
            log.warning("fetch_program_list.error", error=str(e))
            raise

    @scraper_retry
    async def fetch_program_detail(self, slug: str) -> dict[str, Any]:
        """Fetch detail for a single program by slug.

        Returns the full program detail dict from project/{slug}.json.
        Raises ProgramNotFoundError if slug does not exist.
        """
        url = PROGRAM_DETAIL_URL.format(slug=slug)
        log.info("fetch_program_detail.start", slug=slug)
        try:
            resp = await self.client.get(url)
            if resp.status_code == 404:
                raise ProgramNotFoundError(f"Program '{slug}' not found")
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            log.info("fetch_program_detail.success", slug=slug)
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ProgramNotFoundError(f"Program '{slug}' not found")
            log.warning("fetch_program_detail.http_error", slug=slug, status=e.response.status_code)
            raise
        except ProgramNotFoundError:
            raise
        except Exception as e:
            log.warning("fetch_program_detail.error", slug=slug, error=str(e))
            raise

    # ── Parsing Helpers ─────────────────────────────────────

    @staticmethod
    def parse_contracts(detail: dict[str, Any]) -> list[dict[str, str]]:
        """Extract contract addresses from program detail."""
        contracts: list[dict[str, str]] = []
        raw = detail.get("contracts", [])
        if isinstance(raw, list):
            for c in raw:
                if isinstance(c, dict):
                    contracts.append({
                        "address": str(c.get("address", "")),
                        "chain": str(c.get("chain", "")),
                        "name": str(c.get("name", "")),
                    })
                elif isinstance(c, str):
                    contracts.append({"address": c, "chain": "", "name": ""})
        return contracts

    @staticmethod
    def parse_social_links(detail: dict[str, Any]) -> list[str]:
        """Extract all social/profile URLs from program detail."""
        links: list[str] = []
        urls = detail.get("social", []) or detail.get("links", []) or detail.get("urls", [])
        if isinstance(urls, list):
            for u in urls:
                if isinstance(u, dict):
                    url = u.get("url", "") or u.get("link", "")
                    if url:
                        links.append(url)
                elif isinstance(u, str):
                    links.append(u)
        return links
