"""
Task Queue — PostgreSQL-backed distributed task queue with visibility timeout.

Workers poll for tasks using SELECT FOR UPDATE SKIP LOCKED, which provides:
- Atomic task acquisition (no double-processing)
- Natural backpressure (slow workers = fewer tasks consumed)
- Horizontal scaling (add workers without coordination)

Visibility timeout pattern:
- When a worker polls a task, it becomes invisible to other workers for N seconds
- Worker must heartbeat to extend visibility (proves it's still alive)
- If heartbeat lapses, task becomes visible again → another worker picks it up
- This handles worker crashes without explicit failure detection

Schema:
    task_queue — distributed activity task queue
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import asyncpg

from services.workflow_engine.models import ActivityTask, TaskStatus

logger = logging.getLogger(__name__)


# =============================================================================
# SQL DDL
# =============================================================================

_CREATE_TASK_QUEUE_TABLE = """
CREATE TABLE IF NOT EXISTS task_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_name      TEXT NOT NULL DEFAULT 'default',
    workflow_run_id UUID NOT NULL,
    activity_id     TEXT NOT NULL,
    activity_type   TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'pending',
    worker_id       TEXT,
    visible_after   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    heartbeat_at    TIMESTAMPTZ,
    timeout_seconds INTEGER NOT NULL DEFAULT 300,
    attempt         INTEGER NOT NULL DEFAULT 0,
    max_attempts    INTEGER NOT NULL DEFAULT 3,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    result          JSONB,
    error           TEXT
);
"""

_CREATE_TASK_QUEUE_INDEXES = [
    # Primary poll index: queue + status + visibility (for efficient polling)
    """CREATE INDEX IF NOT EXISTS idx_taskq_poll
       ON task_queue(queue_name, status, visible_after)
       WHERE status = 'pending'""",
    # Lookup by workflow run (for cancellation)
    "CREATE INDEX IF NOT EXISTS idx_taskq_run ON task_queue(workflow_run_id);",
    # Heartbeat timeout detection
    """CREATE INDEX IF NOT EXISTS idx_taskq_heartbeat
       ON task_queue(heartbeat_at, timeout_seconds)
       WHERE status = 'processing'""",
    # Cleanup old completed tasks
    "CREATE INDEX IF NOT EXISTS idx_taskq_completed ON task_queue(completed_at) WHERE status IN ('completed', 'failed');",
]


# =============================================================================
# Task Queue
# =============================================================================


class TaskQueue:
    """
    PostgreSQL-backed distributed task queue.

    Key operations:
    - enqueue: Add a task (immediately visible or with delay)
    - poll: Atomically acquire a task (SELECT FOR UPDATE SKIP LOCKED)
    - ack: Mark task completed (with optional result)
    - nack: Return task to queue (with optional delay for retry)
    - heartbeat: Extend visibility timeout (worker still alive)
    - reclaim: Make timed-out tasks visible again (recovery)
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ------------------------------------------------------------------
    # Schema initialization
    # ------------------------------------------------------------------

    async def init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TASK_QUEUE_TABLE)
            for idx_sql in _CREATE_TASK_QUEUE_INDEXES:
                await conn.execute(idx_sql)
        logger.info("TaskQueue: schema initialized")

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    async def enqueue(
        self,
        workflow_run_id: str,
        activity_id: str,
        activity_type: str,
        payload: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        timeout_seconds: int = 300,
        max_attempts: int = 3,
        attempt: int = 0,
        delay_seconds: float = 0,
    ) -> str:
        """
        Add a task to the queue.

        Args:
            workflow_run_id: The parent workflow run.
            activity_id: The activity this task executes.
            activity_type: Type of activity (e.g., "ocr_parse").
            payload: Input data for the activity.
            queue_name: Which queue to place the task in.
            timeout_seconds: How long the worker has to complete the task.
            max_attempts: Maximum number of execution attempts.
            attempt: Current attempt number (for retries).
            delay_seconds: Delay before task becomes visible (for backoff).

        Returns:
            The task_id (UUID hex string).
        """
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        visible_after = now + timedelta(seconds=delay_seconds) if delay_seconds > 0 else now

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO task_queue
                    (id, queue_name, workflow_run_id, activity_id, activity_type,
                     payload, status, timeout_seconds, max_attempts, attempt,
                     visible_after, created_at)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, 'pending', $7, $8, $9, $10, $11)
                """,
                task_id,
                queue_name,
                uuid.UUID(workflow_run_id),
                activity_id,
                activity_type,
                json.dumps(payload or {}, ensure_ascii=False),
                timeout_seconds,
                max_attempts,
                attempt,
                visible_after,
                now,
            )

        logger.debug(
            "Enqueued task %s (activity=%s, queue=%s, delay=%.1fs)",
            task_id.hex, activity_type, queue_name, delay_seconds,
        )
        return task_id.hex

    # ------------------------------------------------------------------
    # Poll (worker acquires a task)
    # ------------------------------------------------------------------

    async def poll(
        self,
        worker_id: str,
        queue_name: str = "default",
        batch_size: int = 1,
    ) -> List[ActivityTask]:
        """
        Atomically acquire one or more tasks from the queue.

        Uses SELECT FOR UPDATE SKIP LOCKED for lock-free concurrent polling.
        Sets visibility timeout — if worker doesn't heartbeat or ack within
        timeout_seconds, the task becomes available again.

        Args:
            worker_id: Unique identifier for this worker.
            queue_name: Which queue to poll from.
            batch_size: Number of tasks to acquire (default 1).

        Returns:
            List of acquired ActivityTask objects (may be empty if queue is empty).
        """
        now = datetime.now(timezone.utc)
        tasks: List[ActivityTask] = []

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(
                    """
                    SELECT id, queue_name, workflow_run_id, activity_id, activity_type,
                           payload, timeout_seconds, attempt, max_attempts, created_at
                    FROM task_queue
                    WHERE queue_name = $1
                      AND status = 'pending'
                      AND visible_after <= $2
                    ORDER BY created_at ASC
                    LIMIT $3
                    FOR UPDATE SKIP LOCKED
                    """,
                    queue_name,
                    now,
                    batch_size,
                )

                if not rows:
                    return []

                # Mark all acquired tasks as processing
                task_ids = [row["id"] for row in rows]
                await conn.execute(
                    """
                    UPDATE task_queue
                    SET status = 'processing',
                        worker_id = $1,
                        heartbeat_at = $2,
                        started_at = $2
                    WHERE id = ANY($3)
                    """,
                    worker_id,
                    now,
                    task_ids,
                )

        # Build ActivityTask objects
        for row in rows:
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)

            tasks.append(ActivityTask(
                task_id=row["id"].hex,
                queue_name=row["queue_name"],
                workflow_run_id=row["workflow_run_id"].hex,
                activity_id=row["activity_id"],
                activity_type=row["activity_type"],
                payload=payload,
                attempt=row["attempt"],
                max_attempts=row["max_attempts"],
                timeout_seconds=row["timeout_seconds"],
                created_at=row["created_at"],
                worker_id=worker_id,
                heartbeat_at=now,
                status=TaskStatus.PROCESSING,
            ))

        logger.debug(
            "Worker %s polled %d task(s) from queue '%s'",
            worker_id, len(tasks), queue_name,
        )
        return tasks

    # ------------------------------------------------------------------
    # Ack (task completed successfully)
    # ------------------------------------------------------------------

    async def ack(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Acknowledge task completion (success).

        Args:
            task_id: The task to acknowledge.
            result: Optional result data from the activity.

        Returns:
            True if the task was successfully acknowledged.
        """
        now = datetime.now(timezone.utc)
        result_json = json.dumps(result, ensure_ascii=False) if result else None

        async with self._pool.acquire() as conn:
            tag = await conn.execute(
                """
                UPDATE task_queue
                SET status = 'completed',
                    completed_at = $2,
                    result = $3::jsonb
                WHERE id = $1 AND status = 'processing'
                """,
                uuid.UUID(task_id),
                now,
                result_json,
            )

        success = tag == "UPDATE 1"
        if success:
            logger.debug("Task %s acknowledged (completed)", task_id)
        else:
            logger.warning("Failed to ack task %s (not in processing state)", task_id)
        return success

    # ------------------------------------------------------------------
    # Nack (task failed, return to queue)
    # ------------------------------------------------------------------

    async def nack(
        self,
        task_id: str,
        error: Optional[str] = None,
        retry_delay_seconds: float = 0,
    ) -> bool:
        """
        Negative acknowledge — task failed, return to queue for retry.

        If retry_delay_seconds > 0, the task won't be visible until the delay passes.

        Args:
            task_id: The task that failed.
            error: Error description.
            retry_delay_seconds: Delay before task becomes visible again.

        Returns:
            True if the task was successfully returned to the queue.
        """
        now = datetime.now(timezone.utc)
        visible_after = now + timedelta(seconds=retry_delay_seconds)

        async with self._pool.acquire() as conn:
            # Check if max attempts reached
            row = await conn.fetchrow(
                "SELECT attempt, max_attempts FROM task_queue WHERE id = $1",
                uuid.UUID(task_id),
            )

            if row is None:
                return False

            new_attempt = row["attempt"] + 1
            max_attempts = row["max_attempts"]

            if new_attempt >= max_attempts:
                # Exhausted retries — mark as failed permanently
                await conn.execute(
                    """
                    UPDATE task_queue
                    SET status = 'failed',
                        error = $2,
                        completed_at = $3,
                        attempt = $4
                    WHERE id = $1
                    """,
                    uuid.UUID(task_id),
                    error,
                    now,
                    new_attempt,
                )
                logger.info(
                    "Task %s permanently failed after %d attempts: %s",
                    task_id, new_attempt, error,
                )
            else:
                # Return to queue with delay
                await conn.execute(
                    """
                    UPDATE task_queue
                    SET status = 'pending',
                        worker_id = NULL,
                        heartbeat_at = NULL,
                        started_at = NULL,
                        visible_after = $2,
                        attempt = $3,
                        error = $4
                    WHERE id = $1
                    """,
                    uuid.UUID(task_id),
                    visible_after,
                    new_attempt,
                    error,
                )
                logger.debug(
                    "Task %s returned to queue (attempt %d/%d, delay=%.1fs)",
                    task_id, new_attempt, max_attempts, retry_delay_seconds,
                )

        return True

    # ------------------------------------------------------------------
    # Heartbeat (worker is still alive)
    # ------------------------------------------------------------------

    async def heartbeat(self, task_id: str) -> bool:
        """
        Extend the visibility timeout for a task.

        Workers should call this periodically (e.g., every timeout/3 seconds)
        to prove they're still processing the task. If heartbeat lapses,
        the task will be reclaimed by the recovery process.

        Returns:
            True if heartbeat was accepted (task still in processing state).
        """
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            tag = await conn.execute(
                """
                UPDATE task_queue
                SET heartbeat_at = $2
                WHERE id = $1 AND status = 'processing'
                """,
                uuid.UUID(task_id),
                now,
            )

        return tag == "UPDATE 1"

    # ------------------------------------------------------------------
    # Reclaim (recovery — make timed-out tasks visible)
    # ------------------------------------------------------------------

    async def reclaim_timed_out(self) -> int:
        """
        Find tasks where the worker hasn't heartbeated within timeout_seconds
        and make them available again.

        This is the core of failure recovery: if a worker dies, its tasks
        automatically become available after the visibility timeout expires.

        Returns:
            Number of tasks reclaimed.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE task_queue
                SET status = 'pending',
                    worker_id = NULL,
                    heartbeat_at = NULL,
                    started_at = NULL,
                    visible_after = NOW()
                WHERE status = 'processing'
                  AND heartbeat_at IS NOT NULL
                  AND heartbeat_at + make_interval(secs => timeout_seconds) < NOW()
                """
            )

        reclaimed = int(result.split()[-1]) if result else 0
        if reclaimed > 0:
            logger.info("TaskQueue: reclaimed %d timed-out tasks", reclaimed)
        return reclaimed

    # ------------------------------------------------------------------
    # Cancel (workflow cancelled — remove pending tasks)
    # ------------------------------------------------------------------

    async def cancel_by_run(self, workflow_run_id: str) -> int:
        """
        Cancel all pending tasks for a workflow run.

        Processing tasks are left alone (worker will check cancellation).

        Returns:
            Number of tasks cancelled.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE task_queue
                SET status = 'failed',
                    error = 'Workflow cancelled',
                    completed_at = NOW()
                WHERE workflow_run_id = $1
                  AND status = 'pending'
                """,
                uuid.UUID(workflow_run_id),
            )

        cancelled = int(result.split()[-1]) if result else 0
        if cancelled > 0:
            logger.info(
                "Cancelled %d pending tasks for workflow run %s",
                cancelled, workflow_run_id,
            )
        return cancelled

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get_task(self, task_id: str) -> Optional[ActivityTask]:
        """Get a task by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM task_queue WHERE id = $1",
                uuid.UUID(task_id),
            )

        if row is None:
            return None
        return _row_to_task(row)

    async def get_pending_count(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue."""
        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM task_queue
                WHERE queue_name = $1 AND status = 'pending' AND visible_after <= NOW()
                """,
                queue_name,
            )
        return count or 0

    async def get_processing_count(self, queue_name: str = "default") -> int:
        """Get the number of currently processing tasks in a queue."""
        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM task_queue
                WHERE queue_name = $1 AND status = 'processing'
                """,
                queue_name,
            )
        return count or 0

    async def get_tasks_by_run(
        self,
        workflow_run_id: str,
        status: Optional[str] = None,
    ) -> List[ActivityTask]:
        """Get all tasks for a workflow run, optionally filtered by status."""
        conditions = ["workflow_run_id = $1"]
        params: list = [uuid.UUID(workflow_run_id)]

        if status:
            conditions.append("status = $2")
            params.append(status)

        sql = f"SELECT * FROM task_queue WHERE {' AND '.join(conditions)} ORDER BY created_at"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return [_row_to_task(row) for row in rows]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup_old_tasks(self, older_than_hours: int = 72) -> int:
        """Delete completed/failed tasks older than N hours."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM task_queue
                WHERE status IN ('completed', 'failed')
                  AND completed_at < (NOW() - make_interval(hours => $1))
                """,
                older_than_hours,
            )

        deleted = int(result.split()[-1]) if result else 0
        if deleted > 0:
            logger.info("TaskQueue: cleaned up %d old tasks", deleted)
        return deleted

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_queue_stats(self, queue_name: str = "default") -> Dict[str, int]:
        """Get task counts by status for a queue."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT status, COUNT(*) as count
                FROM task_queue
                WHERE queue_name = $1
                GROUP BY status
                """,
                queue_name,
            )

        stats = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
        for row in rows:
            stats[row["status"]] = row["count"]
        return stats


# =============================================================================
# Helpers
# =============================================================================


def _row_to_task(row: asyncpg.Record) -> ActivityTask:
    """Convert a database row to an ActivityTask model."""
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    return ActivityTask(
        task_id=row["id"].hex,
        queue_name=row["queue_name"],
        workflow_run_id=row["workflow_run_id"].hex,
        activity_id=row["activity_id"],
        activity_type=row["activity_type"],
        payload=payload,
        attempt=row["attempt"],
        max_attempts=row["max_attempts"],
        timeout_seconds=row["timeout_seconds"],
        created_at=row["created_at"],
        worker_id=row.get("worker_id"),
        heartbeat_at=row.get("heartbeat_at"),
        status=row["status"],
    )
