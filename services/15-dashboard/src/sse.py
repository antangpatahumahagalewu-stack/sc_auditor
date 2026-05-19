"""SSE (Server-Sent Events) Manager for real-time dashboard updates.

Broadcasts events to all connected dashboard clients using asyncio.Queue.
Events are JSON-encoded and follow the format:
    event: <type>
    data: <json payload>
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog

logger = structlog.get_logger(service="dashboard", module="sse")


class SSEManager:
    """Manages SSE connections and broadcasts events to all clients.

    Each connected client gets an asyncio.Queue. The manager fans out
    every event to all active queues. Clients that are too slow (queue
    full) are dropped with a warning.
    """

    def __init__(self, max_queue_size: int = 128) -> None:
        self._queues: set = set()
        self._max_queue_size = max_queue_size
        self._lock = asyncio.Lock()

    # ── Client lifecycle ─────────────────────────────────────────

    async def connect(self):
        """Register a new client and return its event queue."""
        queue = asyncio.Queue(maxsize=self._max_queue_size)
        async with self._lock:
            self._queues.add(queue)
        logger.debug("SSE client connected", active=len(self._queues))
        return queue

    async def disconnect(self, queue) -> None:
        """Remove a client queue."""
        async with self._lock:
            self._queues.discard(queue)
        logger.debug("SSE client disconnected", active=len(self._queues))

    # ── Broadcasting ─────────────────────────────────────────────

    async def send_event(
        self,
        event_type: str,
        data: Any,
    ) -> None:
        """Broadcast an event to all connected clients.

        Args:
            event_type: SSE event name (e.g. "audit_progress", "daemon_status").
            data: JSON-serializable payload.
        """
        payload = json.dumps(data, default=str)
        async with self._lock:
            dead: list[asyncio.Queue] = []
            for queue in self._queues:
                try:
                    queue.put_nowait((event_type, payload))
                except asyncio.QueueFull:
                    dead.append(queue)
                    logger.warning(
                        "Dropping slow SSE client — queue full",
                        queue_size=self._max_queue_size,
                    )
            for q in dead:
                self._queues.discard(q)

        logger.debug(
            "SSE event sent",
            event_type=event_type,
            recipients=len(self._queues),
        )

    # ── Event stream generator ───────────────────────────────────

    async def event_stream(
        self,
        queue,
    ) -> AsyncGenerator[str, None]:
        """Async generator that yields SSE-formatted strings.

        Usage in FastAPI:
            return StreamingResponse(manager.event_stream(queue), media_type="text/event-stream")

        Yields:
            SSE-formatted lines: "event: <type>\\ndata: <json>\\n\\n"
        """
        try:
            while True:
                event_type, payload = await queue.get()
                yield f"event: {event_type}\ndata: {payload}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await self.disconnect(queue)

    # ── Utility ──────────────────────────────────────────────────

    @property
    def active_connections(self) -> int:
        return len(self._queues)

    async def broadcast_audit_progress(
        self,
        audit_id: str,
        state: str,
        progress: float = 0.0,
        message: str = "",
    ) -> None:
        """Convenience: broadcast audit pipeline progress."""
        await self.send_event(
            "audit_progress",
            {
                "audit_id": audit_id,
                "state": state,
                "progress": progress,
                "message": message,
            },
        )

    async def broadcast_audit_complete(
        self,
        audit_id: str,
        state: str,
        findings_count: int = 0,
    ) -> None:
        """Convenience: broadcast audit completion."""
        await self.send_event(
            "audit_complete",
            {
                "audit_id": audit_id,
                "state": state,
                "findings_count": findings_count,
            },
        )

    async def broadcast_daemon_status(self, status: str, message: str = "") -> None:
        """Convenience: broadcast daemon status change."""
        await self.send_event(
            "daemon_status",
            {"status": status, "message": message},
        )

    async def broadcast_feedback_received(
        self,
        finding_id: str,
        status: str,
    ) -> None:
        """Convenience: broadcast feedback update."""
        await self.send_event(
            "feedback_received",
            {"finding_id": finding_id, "status": status},
        )


# Module-level singleton for app-wide use
sse_manager = SSEManager()
