"""SyncManager — Orchestrates full sync of Immunefi programs."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog

from src.models import Contract, Program, Repo, SyncStatus
from src.repo_detector import RepoDetector
from src.scraper import ImmunefiScraper, ProgramNotFoundError

log = structlog.get_logger()

# ── Constants ──────────────────────────────────────────────

PROGRAMS_FILE = "programs.json"
COMMIT_HASH_URL = (
    "https://api.github.com/repos/"
    "infosec-us-team/Immunefi-Bug-Bounty-Programs-Unofficial/commits/main"
)


# ── SyncManager ────────────────────────────────────────────

class SyncManager:
    """Manages program data sync from Immunefi GitHub mirror.

    Data is stored as JSON at ``data_dir / programs.json``.

    Usage:
        mgr = SyncManager(Path("/data/immunefi"))
        mgr.load_programs()

        # Full sync
        async with httpx.AsyncClient() as client:
            status = await mgr.sync_all(client)
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.programs_path = data_dir / PROGRAMS_FILE

        # In-memory state
        self._programs: dict[str, Program] = {}
        self._last_synced: str | None = None
        self._commit_hash: str | None = None

        # Sync tracking
        self._syncs: dict[str, SyncStatus] = {}

    # ── Load / Save ─────────────────────────────────────────

    def load_programs(self) -> dict[str, Program]:
        """Load programs from disk into memory. Returns the programs dict."""
        if not self.programs_path.exists():
            log.info("sync.load.no_file", path=str(self.programs_path))
            self._programs = {}
            return self._programs

        try:
            raw = self.programs_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            self._last_synced = data.get("last_synced")
            self._commit_hash = data.get("commit_hash")

            programs: dict[str, Program] = {}
            for slug, pdata in data.get("programs", {}).items():
                programs[slug] = Program(**pdata)
            self._programs = programs

            log.info(
                "sync.load.success",
                count=len(programs),
                last_synced=self._last_synced,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning("sync.load.error", error=str(e))
            self._programs = {}

        return self._programs

    def save_programs(self, programs: dict[str, Program] | None = None) -> bool:
        """Atomically save programs to disk. Returns True on success."""
        if programs is not None:
            self._programs = programs

        serialized: dict[str, Any] = {
            s: p.model_dump(mode="json")
            for s, p in self._programs.items()
        }

        payload = {
            "last_synced": datetime.now(timezone.utc).isoformat(),
            "commit_hash": self._commit_hash or "",
            "programs": serialized,
        }

        # Atomic write: write to .tmp, then replace
        tmp_path = self.programs_path.with_suffix(".tmp")
        try:
            tmp_path.write_text(
                json.dumps(payload, indent=2, default=str),
                encoding="utf-8",
            )
            tmp_path.replace(self.programs_path)
            log.info("sync.save.success", count=len(self._programs))
            return True
        except (OSError, PermissionError) as e:
            log.error("sync.save.error", error=str(e))
            if tmp_path.exists():
                tmp_path.unlink()
            return False

    # ── Sync Operations ────────────────────────────────────

    async def sync_all(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> SyncStatus:
        """Run a full sync: fetch list → detail for each → save.

        Returns a SyncStatus that can be polled via get_sync_status().
        """
        sync_id = uuid.uuid4().hex[:12]
        started_at = datetime.now(timezone.utc).isoformat()

        status = SyncStatus(
            sync_id=sync_id,
            status="running",
            started_at=started_at,
        )
        self._syncs[sync_id] = status

        log.info("sync.all.start", sync_id=sync_id)

        try:
            async with ImmunefiScraper(client) as scraper:
                # Step 1: Fetch program list
                raw_list = await scraper.fetch_program_list()
                status.total = len(raw_list)
                log.info("sync.all.list_fetched", total=status.total)

                # Step 2: Fetch detail for each program
                programs: dict[str, Program] = {}
                repo_detector = RepoDetector()

                for i, item in enumerate(raw_list):
                    slug = item.get("slug", "")
                    if not slug:
                        continue

                    try:
                        detail = await scraper.fetch_program_detail(slug)
                    except ProgramNotFoundError:
                        log.warning("sync.all.slug_not_found", slug=slug)
                        # Still add basic entry from list data
                        detail = item
                    except Exception as e:
                        log.warning("sync.all.slug_error", slug=slug, error=str(e))
                        detail = item

                    program = self._build_program(item, detail, repo_detector)
                    programs[slug] = program
                    status.programs_synced = i + 1

                # Step 3: Update commit hash
                await self._update_commit_hash(client)

                # Step 4: Save
                self._programs = programs
                self._last_synced = datetime.now(timezone.utc).isoformat()
                self.save_programs()

                status.status = "completed"
                status.completed_at = datetime.now(timezone.utc).isoformat()
                log.info(
                    "sync.all.complete",
                    sync_id=sync_id,
                    total=status.total,
                    synced=status.programs_synced,
                )

        except Exception as e:
            status.status = "failed"
            status.completed_at = datetime.now(timezone.utc).isoformat()
            status.error = str(e)
            log.error("sync.all.failed", sync_id=sync_id, error=str(e))

        self._syncs[sync_id] = status
        return status

    async def has_updates(self, client: httpx.AsyncClient | None = None) -> bool:
        """Quick check if the remote repo has new commits.

        Compares the stored commit hash with the latest remote commit.
        """
        if self._commit_hash is None:
            return True  # never synced

        try:
            close_client = client is None
            if close_client:
                client = httpx.AsyncClient(timeout=10.0)

            try:
                resp = await client.get(COMMIT_HASH_URL)
                resp.raise_for_status()
                latest_sha = resp.json().get("sha", "")
                has_updates = latest_sha != self._commit_hash
                log.info(
                    "sync.has_updates",
                    has_updates=has_updates,
                    stored=self._commit_hash[:8],
                    remote=latest_sha[:8],
                )
                return has_updates
            finally:
                if close_client:
                    await client.aclose()
        except Exception as e:
            log.warning("sync.has_updates.error", error=str(e))
            return True  # assume updates on error

    # ── Sync Status ─────────────────────────────────────────

    def get_sync_status(self, sync_id: str) -> SyncStatus | None:
        """Get the status of a specific sync operation."""
        return self._syncs.get(sync_id)

    # ── Accessors ───────────────────────────────────────────

    @property
    def programs(self) -> dict[str, Program]:
        return self._programs

    @property
    def last_synced(self) -> str | None:
        return self._last_synced

    # ── Internal Helpers ────────────────────────────────────

    async def _update_commit_hash(
        self,
        client: httpx.AsyncClient | None,
    ) -> None:
        """Fetch the latest commit SHA from the mirror repo."""
        if client is None:
            return  # cannot fetch without client

        try:
            resp = await client.get(COMMIT_HASH_URL)
            resp.raise_for_status()
            self._commit_hash = resp.json().get("sha", "")
            log.info("sync.commit_hash_updated", sha=self._commit_hash[:8])
        except Exception as e:
            log.warning("sync.commit_hash_error", error=str(e))

    @staticmethod
    def _build_program(
        list_item: dict[str, Any],
        detail: dict[str, Any],
        repo_detector: RepoDetector,
    ) -> Program:
        """Build a Program model from list + detail data."""
        # Parse bounty info
        max_bounty = detail.get("maxBounty") or list_item.get("maxBounty")
        min_bounty = detail.get("minBounty") or list_item.get("minBounty")

        # Normalize numeric bounty values
        if max_bounty is not None:
            try:
                max_bounty = float(max_bounty)
            except (ValueError, TypeError):
                max_bounty = None
        if min_bounty is not None:
            try:
                min_bounty = float(min_bounty)
            except (ValueError, TypeError):
                min_bounty = None

        # Parse contracts
        raw_contracts = ImmunefiScraper.parse_contracts(detail)
        contracts = [Contract(**c) for c in raw_contracts]

        # Detect repos
        repos = repo_detector.detect(detail)

        # Chains
        chains = detail.get("chains") or list_item.get("chains") or []

        return Program(
            slug=str(detail.get("slug") or list_item.get("slug", "")),
            name=str(detail.get("name") or list_item.get("name", "")),
            chains=list(chains) if isinstance(chains, list) else [str(chains)],
            max_bounty=max_bounty,
            min_bounty=min_bounty,
            currency=str(detail.get("currency", "USD") or "USD"),
            status=str(detail.get("status") or list_item.get("status", "unknown")),
            repos=repos,
            contracts=contracts,
            project_url=str(detail.get("project_url") or detail.get("url", "")),
            logo=str(detail.get("logo", "") or ""),
            description=str(detail.get("description", "") or ""),
            tags=detail.get("tags", []) or list_item.get("tags", []),
            updated_at=str(detail.get("updatedAt") or detail.get("updated_at", "")),
        )
