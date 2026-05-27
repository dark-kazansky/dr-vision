"""
Job Event Bus — Pub/sub system for real-time job progress updates.

Provides:
- Event emission when job/node status changes
- Per-job subscriber management (SSE clients)
- Automatic cleanup when subscribers disconnect

Events are lightweight dicts serialized as JSON for SSE streaming.
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class JobEventType(str, Enum):
    """Types of events emitted during job execution."""

    JOB_QUEUED = "job_queued"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    JOB_PROGRESS = "job_progress"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    NODE_RETRYING = "node_retrying"
    NODE_SKIPPED = "node_skipped"


class JobEvent:
    """A single event in the job lifecycle."""

    __slots__ = ("event_type", "job_id", "data", "timestamp")

    def __init__(
        self,
        event_type: JobEventType,
        job_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.event_type = event_type
        self.job_id = job_id
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_sse_dict(self) -> Dict[str, Any]:
        """Convert to a dict suitable for SSE JSON serialization."""
        return {
            "event": self.event_type.value,
            "job_id": self.job_id,
            "timestamp": self.timestamp,
            **self.data,
        }


class JobEventBus:
    """
    Async pub/sub event bus for job progress.

    Subscribers register per job_id and receive events via asyncio.Queue.
    Supports multiple subscribers per job (e.g., multiple browser tabs).
    """

    def __init__(self) -> None:
        # job_id → set of subscriber queues
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, job_id: str) -> asyncio.Queue:
        """
        Subscribe to events for a specific job.

        Returns an asyncio.Queue that will receive JobEvent objects.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            if job_id not in self._subscribers:
                self._subscribers[job_id] = set()
            self._subscribers[job_id].add(queue)
        logger.debug("New subscriber for job %s (total: %d)", job_id, len(self._subscribers[job_id]))
        return queue

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue for a job."""
        async with self._lock:
            if job_id in self._subscribers:
                self._subscribers[job_id].discard(queue)
                if not self._subscribers[job_id]:
                    del self._subscribers[job_id]
        logger.debug("Subscriber removed for job %s", job_id)

    async def emit(self, event: JobEvent) -> None:
        """
        Emit an event to all subscribers of the given job.

        Non-blocking: if a subscriber's queue is full, the event is dropped
        for that subscriber (prevents slow consumers from blocking).
        Also persists the event to the database via job_persistence.
        """
        # Persist to DB (fire-and-forget, don't block on DB writes)
        try:
            from services.job_persistence import persist_job_event
            asyncio.create_task(persist_job_event(event))
        except Exception:
            pass  # Don't let persistence failures affect event delivery

        async with self._lock:
            subscribers = self._subscribers.get(event.job_id, set()).copy()

        if not subscribers:
            return

        dead_queues: List[asyncio.Queue] = []
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Dropping event for slow subscriber on job %s", event.job_id
                )
            except Exception:
                dead_queues.append(queue)

        # Clean up dead queues
        if dead_queues:
            async with self._lock:
                if event.job_id in self._subscribers:
                    for q in dead_queues:
                        self._subscribers[event.job_id].discard(q)

    async def emit_job_queued(self, job_id: str, workflow_name: Optional[str] = None) -> None:
        """Emit job_queued event."""
        await self.emit(JobEvent(
            JobEventType.JOB_QUEUED, job_id,
            {"workflow_name": workflow_name},
        ))

    async def emit_job_started(self, job_id: str) -> None:
        """Emit job_started event."""
        await self.emit(JobEvent(JobEventType.JOB_STARTED, job_id))

    async def emit_job_completed(self, job_id: str, progress: float = 1.0) -> None:
        """Emit job_completed event."""
        await self.emit(JobEvent(
            JobEventType.JOB_COMPLETED, job_id,
            {"progress": progress},
        ))

    async def emit_job_failed(self, job_id: str, error: str) -> None:
        """Emit job_failed event."""
        await self.emit(JobEvent(
            JobEventType.JOB_FAILED, job_id,
            {"error": error},
        ))

    async def emit_job_cancelled(self, job_id: str) -> None:
        """Emit job_cancelled event."""
        await self.emit(JobEvent(JobEventType.JOB_CANCELLED, job_id))

    async def emit_job_progress(self, job_id: str, progress: float) -> None:
        """Emit job_progress event (overall progress update)."""
        await self.emit(JobEvent(
            JobEventType.JOB_PROGRESS, job_id,
            {"progress": progress},
        ))

    async def emit_node_started(
        self, job_id: str, node_id: str, node_type: str, node_label: str
    ) -> None:
        """Emit node_started event."""
        await self.emit(JobEvent(
            JobEventType.NODE_STARTED, job_id,
            {"node_id": node_id, "node_type": node_type, "node_label": node_label},
        ))

    async def emit_node_completed(
        self, job_id: str, node_id: str, node_type: str, node_label: str,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Emit node_completed event."""
        data: Dict[str, Any] = {
            "node_id": node_id, "node_type": node_type, "node_label": node_label,
        }
        if duration_ms is not None:
            data["duration_ms"] = duration_ms
        await self.emit(JobEvent(JobEventType.NODE_COMPLETED, job_id, data))

    async def emit_node_failed(
        self, job_id: str, node_id: str, node_type: str, node_label: str, error: str
    ) -> None:
        """Emit node_failed event."""
        await self.emit(JobEvent(
            JobEventType.NODE_FAILED, job_id,
            {"node_id": node_id, "node_type": node_type, "node_label": node_label, "error": error},
        ))

    async def emit_node_retrying(
        self, job_id: str, node_id: str, node_type: str, node_label: str,
        attempt: int, max_retries: int,
    ) -> None:
        """Emit node_retrying event."""
        await self.emit(JobEvent(
            JobEventType.NODE_RETRYING, job_id,
            {
                "node_id": node_id, "node_type": node_type, "node_label": node_label,
                "attempt": attempt, "max_retries": max_retries,
            },
        ))

    async def emit_node_skipped(
        self, job_id: str, node_id: str, node_type: str, node_label: str
    ) -> None:
        """Emit node_skipped event."""
        await self.emit(JobEvent(
            JobEventType.NODE_SKIPPED, job_id,
            {"node_id": node_id, "node_type": node_type, "node_label": node_label},
        ))

    def has_subscribers(self, job_id: str) -> bool:
        """Check if a job has any active subscribers."""
        return job_id in self._subscribers and len(self._subscribers[job_id]) > 0

    async def cleanup_job(self, job_id: str) -> None:
        """Remove all subscribers for a completed job."""
        async with self._lock:
            self._subscribers.pop(job_id, None)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

job_event_bus = JobEventBus()
