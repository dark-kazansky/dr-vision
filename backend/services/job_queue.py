"""
Journey Job Queue — Production-grade job management for workflow execution.

Provides:
- Job creation with full lifecycle (queued → running → completed/failed/cancelled)
- Async queue with configurable concurrency
- Per-node retry logic with exponential backoff
- Cancel mechanism via cancellation tokens
- Job history with filtering and pagination

This replaces the simple in-memory job_manager for Journey workflow executions.
The original job_manager.py remains for backward-compatible /job/{id}/status endpoints.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_event_bus = None


def _get_event_bus():
    """Lazy-load the event bus singleton."""
    global _event_bus
    if _event_bus is None:
        from services.job_events import job_event_bus
        _event_bus = job_event_bus
    return _event_bus


# ---------------------------------------------------------------------------
# Enums & Models
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    """Job lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(str, Enum):
    """Individual node execution states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class NodeProgress(BaseModel):
    """Progress tracking for a single node within a job."""

    node_id: str
    node_type: str
    node_label: str
    status: NodeStatus = NodeStatus.PENDING
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class JobRecord(BaseModel):
    """Full job record stored in the queue."""

    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0  # 0.0 to 1.0
    nodes: List[NodeProgress] = Field(default_factory=list)
    max_retries: int = 3
    retry_delay_base: float = 1.0  # seconds, exponential backoff base
    timeout_seconds: int = 300  # 5 minutes default timeout per job

    # File metadata
    filename: Optional[str] = None
    file_count: int = 0

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # Results
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# Job Queue
# ---------------------------------------------------------------------------


class JobQueue:
    """
    Async job queue for workflow execution.

    Features:
    - Configurable max concurrent jobs
    - FIFO ordering
    - Cancellation tokens
    - Per-node progress tracking
    - Auto-retry with exponential backoff
    """

    def __init__(self, max_concurrent: int = 2) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._cancellation_tokens: Dict[str, bool] = {}
        self._max_concurrent = max_concurrent
        self._workers: List[asyncio.Task] = []
        self._executor: Optional[Callable] = None
        self._started = False
        self._lock = asyncio.Lock()

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    def set_executor(
        self,
        executor: Callable[[JobRecord, "JobQueue"], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Set the executor coroutine that processes jobs.

        The executor receives (job_record, job_queue) and is responsible for:
        - Iterating through nodes
        - Calling update_node_status for progress
        - Checking is_cancelled before each node
        - Handling retries via retry_node helper
        """
        self._executor = executor

    async def start(self) -> None:
        """Start worker tasks to consume from the queue."""
        if self._started:
            return
        self._started = True
        for i in range(self._max_concurrent):
            task = asyncio.create_task(self._worker(i), name=f"job-worker-{i}")
            self._workers.append(task)
        logger.info(
            "JobQueue started with %d workers", self._max_concurrent
        )

    async def stop(self) -> None:
        """Gracefully stop all workers."""
        if not self._started:
            return
        self._started = False
        # Send poison pills
        for _ in self._workers:
            await self._queue.put("")
        for task in self._workers:
            task.cancel()
        self._workers.clear()
        logger.info("JobQueue stopped")

    async def submit(
        self,
        workflow_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        filename: Optional[str] = None,
        file_count: int = 1,
        max_retries: int = 3,
        timeout_seconds: int = 300,
    ) -> JobRecord:
        """
        Submit a new job to the queue.

        Returns the JobRecord immediately (status=queued).
        """
        node_progress = []
        if nodes:
            for n in nodes:
                node_progress.append(
                    NodeProgress(
                        node_id=n.get("id", uuid.uuid4().hex),
                        node_type=n.get("type", "unknown"),
                        node_label=n.get("label", n.get("type", "Unknown")),
                    )
                )

        job = JobRecord(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            nodes=node_progress,
            filename=filename,
            file_count=file_count,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )

        async with self._lock:
            self._jobs[job.job_id] = job
            self._cancellation_tokens[job.job_id] = False

        await self._queue.put(job.job_id)
        logger.info(
            "Job %s submitted (workflow=%s, nodes=%d)",
            job.job_id,
            workflow_name,
            len(node_progress),
        )
        return job

    async def cancel(self, job_id: str) -> bool:
        """
        Request cancellation of a job.

        Returns True if the job was found and cancellation was requested.
        If the job is already completed/failed/cancelled, returns False.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in (
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            ):
                return False
            self._cancellation_tokens[job_id] = True

            # If still queued (not yet picked up by worker), mark immediately
            if job.status == JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
                job.cancelled_at = datetime.now(timezone.utc)

        logger.info("Cancellation requested for job %s", job_id)
        return True

    def is_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled. Used by executor between nodes."""
        return self._cancellation_tokens.get(job_id, False)

    async def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Get a job record by ID."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(
        self,
        status: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List jobs with optional filtering and pagination.

        Returns dict with 'jobs', 'total', 'limit', 'offset'.
        """
        async with self._lock:
            jobs = list(self._jobs.values())

        # Filter
        if status:
            jobs = [j for j in jobs if j.status == status]
        if workflow_id:
            jobs = [j for j in jobs if j.workflow_id == workflow_id]

        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        total = len(jobs)
        jobs = jobs[offset : offset + limit]

        return {
            "jobs": jobs,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def update_node_status(
        self,
        job_id: str,
        node_id: str,
        status: NodeStatus,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Update the status of a specific node within a job."""
        node_type = ""
        node_label = ""
        progress = 0.0

        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return

            for node in job.nodes:
                if node.node_id == node_id:
                    node.status = status
                    node_type = node.node_type
                    node_label = node.node_label
                    if status == NodeStatus.RUNNING and node.started_at is None:
                        node.started_at = datetime.now(timezone.utc)
                    if status in (NodeStatus.COMPLETED, NodeStatus.FAILED):
                        node.completed_at = datetime.now(timezone.utc)
                    if error is not None:
                        node.error = error
                    if result is not None:
                        node.result = result
                    break

            # Recalculate overall progress
            total_nodes = len(job.nodes)
            if total_nodes > 0:
                completed = sum(
                    1
                    for n in job.nodes
                    if n.status in (NodeStatus.COMPLETED, NodeStatus.SKIPPED)
                )
                job.progress = completed / total_nodes
                progress = job.progress

        # Emit events outside the lock
        bus = _get_event_bus()
        if status == NodeStatus.RUNNING:
            await bus.emit_node_started(job_id, node_id, node_type, node_label)
        elif status == NodeStatus.COMPLETED:
            await bus.emit_node_completed(job_id, node_id, node_type, node_label, duration_ms=duration_ms)
            await bus.emit_job_progress(job_id, progress)
        elif status == NodeStatus.FAILED:
            await bus.emit_node_failed(
                job_id, node_id, node_type, node_label, error or "Unknown error"
            )
        elif status == NodeStatus.SKIPPED:
            await bus.emit_node_skipped(job_id, node_id, node_type, node_label)

    async def update_node_retry(self, job_id: str, node_id: str) -> None:
        """Increment retry count for a node."""
        node_type = ""
        node_label = ""
        retry_count = 0
        max_retries = 3

        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            max_retries = job.max_retries
            for node in job.nodes:
                if node.node_id == node_id:
                    node.retry_count += 1
                    node.status = NodeStatus.RETRYING
                    node_type = node.node_type
                    node_label = node.node_label
                    retry_count = node.retry_count
                    break

        # Emit event outside the lock
        bus = _get_event_bus()
        await bus.emit_node_retrying(
            job_id, node_id, node_type, node_label, retry_count, max_retries
        )

    async def _mark_job_running(self, job_id: str) -> None:
        """Mark a job as running."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.QUEUED:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
        bus = _get_event_bus()
        await bus.emit_job_started(job_id)

    async def _mark_job_completed(
        self, job_id: str, results: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Mark a job as completed."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
                job.completed_at = datetime.now(timezone.utc)
                if results is not None:
                    job.results = results
        bus = _get_event_bus()
        await bus.emit_job_completed(job_id)

    async def _mark_job_failed(self, job_id: str, error: str) -> None:
        """Mark a job as failed."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                job.error = error
        bus = _get_event_bus()
        await bus.emit_job_failed(job_id, error)

    async def _mark_job_cancelled(self, job_id: str) -> None:
        """Mark a running job as cancelled."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.RUNNING:
                job.status = JobStatus.CANCELLED
                job.cancelled_at = datetime.now(timezone.utc)
        bus = _get_event_bus()
        await bus.emit_job_cancelled(job_id)

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes jobs from the queue."""
        logger.debug("Worker %d started", worker_id)
        while self._started:
            try:
                job_id = await self._queue.get()

                # Poison pill check
                if not job_id:
                    break

                # Check if already cancelled while queued
                if self.is_cancelled(job_id):
                    await self._mark_job_cancelled(job_id)
                    self._queue.task_done()
                    continue

                await self._mark_job_running(job_id)

                job = await self.get_job(job_id)
                if job is None:
                    self._queue.task_done()
                    continue

                if self._executor is None:
                    logger.error("No executor set for JobQueue")
                    await self._mark_job_failed(job_id, "No executor configured")
                    self._queue.task_done()
                    continue

                try:
                    await asyncio.wait_for(
                        self._executor(job, self),
                        timeout=job.timeout_seconds,
                    )
                    # If not cancelled during execution, mark completed
                    if not self.is_cancelled(job_id):
                        await self._mark_job_completed(job_id)
                    else:
                        await self._mark_job_cancelled(job_id)
                except asyncio.TimeoutError:
                    logger.error("Job %s timed out after %ds", job_id, job.timeout_seconds)
                    await self._mark_job_failed(
                        job_id,
                        f"Job timed out after {job.timeout_seconds} seconds",
                    )
                except asyncio.CancelledError:
                    await self._mark_job_cancelled(job_id)
                except Exception as e:
                    logger.exception("Job %s failed: %s", job_id, e)
                    await self._mark_job_failed(job_id, str(e))

                self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker %d error: %s", worker_id, e)

        logger.debug("Worker %d stopped", worker_id)

    def cleanup_expired(self, ttl_seconds: int = 86400) -> int:
        """
        Remove completed/failed/cancelled jobs older than ttl_seconds.

        Note: This is synchronous for compatibility with scheduled cleanup.
        """
        now = datetime.now(timezone.utc)
        removed = 0
        expired_ids = []

        for job_id, job in self._jobs.items():
            if job.status in (
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            ):
                if job.completed_at or job.cancelled_at:
                    end_time = job.completed_at or job.cancelled_at
                    if end_time and (now - end_time).total_seconds() > ttl_seconds:
                        expired_ids.append(job_id)

        for job_id in expired_ids:
            del self._jobs[job_id]
            self._cancellation_tokens.pop(job_id, None)
            removed += 1

        if removed:
            logger.info("Cleaned up %d expired jobs", removed)
        return removed


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

job_queue = JobQueue(max_concurrent=2)
