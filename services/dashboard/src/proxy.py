"""ServiceProxy — forwards requests to internal Vyper backend services.

Each service (Orchestrator, Config, Classifier, Immunefi, Scanner, etc.)
has its own base URL configured via environment variables. The proxy
uses a shared httpx.AsyncClient with connection pooling for efficiency.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(service="dashboard", module="proxy")


# ── Default service URLs (from env, with fallbacks) ─────────────

def _env_or(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass
class ServiceURLs:
    orchestrator: str = field(
        default_factory=lambda: _env_or("ORCHESTRATOR_URL", "http://localhost:8009")
    )
    config: str = field(
        default_factory=lambda: _env_or("CONFIG_URL", "http://localhost:8011")
    )
    scanner: str = field(
        default_factory=lambda: _env_or("SCANNER_URL", "http://localhost:8003")
    )
    classifier: str = field(
        default_factory=lambda: _env_or("CLASSIFIER_URL", "http://localhost:8005")
    )
    immunefi: str = field(
        default_factory=lambda: _env_or("IMMUNEFI_URL", "http://localhost:8001")
    )
    source: str = field(
        default_factory=lambda: _env_or("SOURCE_URL", "http://localhost:8002")
    )
    reporter: str = field(
        default_factory=lambda: _env_or("REPORTER_URL", "http://localhost:8007")
    )
    notifier: str = field(
        default_factory=lambda: _env_or("NOTIFIER_URL", "http://localhost:8008")
    )
    exploit: str = field(
        default_factory=lambda: _env_or("EXPLOIT_URL", "http://localhost:8006")
    )
    agent: str = field(
        default_factory=lambda: _env_or("AGENT_URL", "http://localhost:8014")
    )


# ── Retry decorator ─────────────────────────────────────────────

_retry = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.3, max=2.0),
    reraise=True,
)


class ServiceProxy:
    """HTTP client proxy for Vyper backend services.

    Usage:
        proxy = ServiceProxy()
        audits = await proxy.get_audits()
        result = await proxy.start_audit(chain="ethereum", address="0x...")
    """

    def __init__(
        self,
        urls: Optional[ServiceURLs] = None,
        timeout: float = 30.0,
    ) -> None:
        self.urls = urls or ServiceURLs()
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("ServiceProxy initialised", urls=urls or self.urls)

    # ── Lifecycle ────────────────────────────────────────────────

    async def start(self) -> None:
        """Create the shared HTTP client (call at app startup)."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            headers={"User-Agent": "Vyper-Dashboard/1.0"},
        )
        logger.info("HTTP client created")

    async def close(self) -> None:
        """Close the shared HTTP client (call at app shutdown)."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("HTTP client closed")

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("ServiceProxy not started — call await proxy.start()")
        return self._client

    # ── Helpers ──────────────────────────────────────────────────

    async def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _post(
        self, url: str, json: Optional[Dict[str, Any]] = None
    ) -> Any:
        resp = await self.client.post(url, json=json)
        resp.raise_for_status()
        return resp.json()

    async def _put(
        self, url: str, json: Optional[Dict[str, Any]] = None
    ) -> Any:
        resp = await self.client.put(url, json=json)
        resp.raise_for_status()
        return resp.json()

    async def _delete(self, url: str) -> Any:
        resp = await self.client.delete(url)
        resp.raise_for_status()
        return resp.json()

    # ═══════════════════════════════════════════════════════════
    # Orchestrator Service
    # ═══════════════════════════════════════════════════════════

    async def get_health(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.orchestrator}/health")

    async def get_audits(
        self,
        state: Optional[str] = None,
        program: Optional[str] = None,
        chain: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if state:
            params["state"] = state
        if program:
            params["program"] = program
        if chain:
            params["chain"] = chain
        return await self._get(f"{self.urls.orchestrator}/audits", params=params)

    async def get_audit(self, audit_id: str) -> Dict[str, Any]:
        return await self._get(f"{self.urls.orchestrator}/audit/{audit_id}")

    async def start_audit(
        self,
        chain: str,
        address: str,
        program: str = "",
        priority: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body = {
            "chain": chain,
            "address": address,
            "program": program,
            "priority": priority,
            "metadata": metadata or {},
        }
        return await self._post(f"{self.urls.orchestrator}/audit", json=body)

    async def start_daemon(self) -> Dict[str, Any]:
        return await self._post(f"{self.urls.orchestrator}/daemon/start")

    async def stop_daemon(self) -> Dict[str, Any]:
        return await self._post(f"{self.urls.orchestrator}/daemon/stop")

    async def get_daemon_status(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.orchestrator}/daemon/status")

    async def get_orchestrator_stats(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.orchestrator}/stats")

    async def retry_audit(self, audit_id: str) -> Dict[str, Any]:
        return await self._post(f"{self.urls.orchestrator}/pipeline/retry/{audit_id}")

    async def add_to_queue(
        self,
        contract_id: str,
        chain: str,
        address: str,
        program: str = "",
        priority_score: float = 0.0,
    ) -> Dict[str, Any]:
        body = {
            "contract_id": contract_id,
            "chain": chain,
            "address": address,
            "program": program,
            "priority_score": priority_score,
        }
        return await self._post(f"{self.urls.orchestrator}/queue", json=body)

    async def get_queue(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.orchestrator}/queue")

    # ═══════════════════════════════════════════════════════════
    # Config Service
    # ═══════════════════════════════════════════════════════════

    async def get_config(self, key: str) -> Dict[str, Any]:
        return await self._get(f"{self.urls.config}/config/{key}")

    async def get_all_config(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.config}/config")

    async def set_config(self, key: str, value: Any) -> Dict[str, Any]:
        return await self._put(
            f"{self.urls.config}/config/{key}", json={"value": value}
        )

    async def set_bulk_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(
            f"{self.urls.config}/config/bulk", json={"config": config}
        )

    # ═══════════════════════════════════════════════════════════
    # Classifier Service
    # ═══════════════════════════════════════════════════════════

    async def get_metrics(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.classifier}/metrics")

    async def submit_feedback(
        self,
        finding_id: str,
        feedback: str,
        status: str,
    ) -> Dict[str, Any]:
        body = {
            "finding_id": finding_id,
            "feedback": feedback,
            "status": status,
        }
        return await self._post(f"{self.urls.classifier}/feedback", json=body)

    async def get_feedback_list(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.classifier}/feedback")

    # ═══════════════════════════════════════════════════════════
    # Immunefi Service
    # ═══════════════════════════════════════════════════════════

    async def get_programs(
        self,
        search: Optional[str] = None,
        chain: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if search:
            params["search"] = search
        if chain:
            params["chain"] = chain
        return await self._get(f"{self.urls.immunefi}/programs", params=params)

    async def get_program(self, slug: str) -> Dict[str, Any]:
        return await self._get(f"{self.urls.immunefi}/programs/{slug}")

    async def get_updates(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.immunefi}/updates")

    # ═══════════════════════════════════════════════════════════
    # Notifier Service
    # ═══════════════════════════════════════════════════════════

    async def send_test_notification(self, channel: str) -> Dict[str, Any]:
        return await self._post(
            f"{self.urls.notifier}/test", json={"channel": channel}
        )

    # ═══════════════════════════════════════════════════════════
    # Reporter Service
    # ═══════════════════════════════════════════════════════════

    async def generate_report(self, audit_id: str, format: str = "immunefi") -> Dict[str, Any]:
        return await self._post(
            f"{self.urls.reporter}/generate",
            json={"audit_id": audit_id, "format": format},
        )


    # ═══════════════════════════════════════════════════════════
    # Agent Service
    # ═══════════════════════════════════════════════════════════

    async def get_team_structure(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.agent}/team/structure")

    async def run_team_audit(
        self,
        task_type: str = "full_audit",
        input_data: Optional[Dict[str, Any]] = None,
        goal: str = "",
        max_delegations: int = 15,
    ) -> Dict[str, Any]:
        body = {
            "task_type": task_type,
            "input_data": input_data or {},
            "goal": goal,
            "max_delegations": max_delegations,
        }
        return await self._post(f"{self.urls.agent}/team/run", json=body)

    async def get_team_sessions(
        self, limit: int = 20, status: Optional[str] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return await self._get(f"{self.urls.agent}/team/sessions", params=params)

    async def get_team_session(self, session_id: str) -> Dict[str, Any]:
        return await self._get(f"{self.urls.agent}/team/{session_id}")

    async def run_agent(
        self,
        task_type: str = "full_audit",
        input_data: Optional[Dict[str, Any]] = None,
        goal: str = "",
        max_steps: int = 25,
    ) -> Dict[str, Any]:
        body = {
            "task_type": task_type,
            "input_data": input_data or {},
            "goal": goal,
            "max_steps": max_steps,
        }
        return await self._post(f"{self.urls.agent}/agent/run", json=body)

    async def get_agent_sessions(
        self, limit: int = 20, status: Optional[str] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return await self._get(f"{self.urls.agent}/agent/sessions", params=params)

    async def get_agent_session(self, session_id: str) -> Dict[str, Any]:
        return await self._get(f"{self.urls.agent}/agent/{session_id}")

    async def get_agent_skills(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.agent}/skills")

    async def get_agent_memory(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.agent}/memory")

    async def get_agent_health(self) -> Dict[str, Any]:
        return await self._get(f"{self.urls.agent}/health")


# Module-level singleton
proxy = ServiceProxy()
