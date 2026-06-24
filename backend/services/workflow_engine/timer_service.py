"""
Durable Timer Service — PostgreSQL-backed timers that survive process restarts.

Enables long-running business processes like:
- Timeout nghiệp vụ: "Cancel order if unpaid after 7 days"
- Delayed execution: "Send reminder email after 24 hours"
- Scheduled actions: "Run report at 9:00 AM daily"
- Activity timeouts: "Fail activity if not completed within 5 minutes"

Key properties:
- Durable: Timers persist in PostgreSQL, survive any number of restarts
- Accurate: Fired within polling interval of their scheduled time
- Cancelable: Timers can be cancelled before firing
- Idempotent: Firing a timer twice has no effect (status check)

The timer service runs a background loop that checks for due timers
and emits TIMER_FIRED events to resume waiting workflows.

Schema:
    durable_timers — persistent timer storage
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

import asyncpg

from services.workflow_engine.models import DurableTimer, TimerStatus

logger = logging.getLogger(__name__)


# =============================================================================
# SQL DDL
# =============================================================================

_CREATE_DURABLE_TIMERS_TABLE = """
CREATE TABLE IF NOT EXISTS durable_timers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_run_id UUID NOT NULL,
    name            TEXT NOT NULL DEFAULT '',
    fire_at         TIMESTAMPTZ NOT NULL,
    status          TEXT NOT NULL DEFAULT 'scheduled',
    payload         JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fired_at        TIMESTAMPTZ,

    UNIQUE(workflow_run_id, name)
);
"""

_CREATE_TIMER_INDEXES = [
    # Primary firing index: only check scheduled timers due before now
    """CREATE INDEX IF NOT EXISTS idx_timers_fire
       ON durable_timers(fire_at)
       WHERE status = 'scheduled'""",
    # Lookup by workflow run (for cancellation)
    "CREATE INDEX IF NOT EXISTS idx_timers_run ON durable_timers(workflow_run_id);",
    # Cleanup index
    "CREATE INDEX IF NOT EXISTS idx_timers_fired_at ON durable_timers(fired_at) WHERE status = 'fired';",
]


# =============================================================================
# Timer Service
# =============================================================================


class TimerService:
    """
    Durable timer service backed by PostgreSQL.

    Responsibilities:
    - Schedule timers (persist to DB)
    - Check for due timers (polling loop)
    - Fire timers (invoke callback, emit events)
    - Cancel timers
    - Cleanup old fired timers

    The on_timer_fired callback is called when a timer fires, typically
    used to emit a TIMER_FIRED event to the event store.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        poll_interval_seconds: float = 1.0,
        on_timer_fired: Optional[Callable[[DurableTimer], Coroutine[Any, Any, None]]] = None,
    ) -> None:
        self._pool = pool
        self._poll_interval = poll_interval_seconds
        self._on_timer_fired = on_timer_fired
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Schema initialization
    # ------------------------------------------------------------------

    async def init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_DURABLE_TIMERS_TABLE)
            for idx_sql in _CREATE_TIMER_INDEXES:
                await conn.execute(idx_sql)
        logger.info("TimerService: schema initialized")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the timer polling loop."""
        if self._running:
            return
        self._running = True
        self._poll_task = asyncio.create_task(
            self._poll_loop(), name="timer-service-poll"
        )
        logger.info("TimerService started (poll_interval=%.1fs)", self._poll_interval)

    async def stop(self) -> None:
        """Stop the timer polling loop."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        logger.info("TimerService stopped")

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    async def schedule(
        self,
        workflow_run_id: str,
        name: str,
        fire_at: datetime,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Schedule a durable timer.

        If a timer with the same (workflow_run_id, name) already exists,
        it will be updated (upsert).

        Args:
            workflow_run_id: The workflow run this timer belongs to.
            name: Unique timer name within the workflow run.
            fire_at: When the timer should fire (UTC).
            payload: Optional data to include when timer fires.

        Returns:
            The timer_id (UUID hex string).
        """
        timer_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO durable_timers
                    (id, workflow_run_id, name, fire_at, status, payload, created_at)
                VALUES ($1, $2, $3, $4, 'scheduled', $5::jsonb, $6)
                ON CONFLICT (workflow_run_id, name)
                DO UPDATE SET fire_at = EXCLUDED.fire_at,
                             status = 'scheduled',
                             payload = EXCLUDED.payload,
                             fired_at = NULL
                """,
                timer_id,
                uuid.UUID(workflow_run_id),
                name,
                fire_at,
                json.dumps(payload or {}, ensure_ascii=False),
                now,
            )

        logger.debug(
            "Scheduled timer '%s' for run %s (fires at %s)",
            name, workflow_run_id, fire_at.isoformat(),
        )
        return timer_id.hex

    async def schedule_delay(
        self,
        workflow_run_id: str,
        name: str,
        delay_seconds: float,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Schedule a timer with a relative delay from now.

        Convenience wrapper around schedule().
        """
        fire_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        return await self.schedule(workflow_run_id, name, fire_at, payload)

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    async def cancel(self, workflow_run_id: str, name: str) -> bool:
        """
        Cancel a scheduled timer.

        Returns True if a timer was actually cancelled (was in 'scheduled' state).
        """
        async with self._pool.acquire() as conn:
            tag = await conn.execute(
                """
                UPDATE durable_timers
                SET status = 'cancelled'
                WHERE workflow_run_id = $1 AND name = $2 AND status = 'scheduled'
                """,
                uuid.UUID(workflow_run_id),
                name,
            )

        cancelled = tag == "UPDATE 1"
        if cancelled:
            logger.debug("Cancelled timer '%s' for run %s", name, workflow_run_id)
        return cancelled

    async def cancel_all_for_run(self, workflow_run_id: str) -> int:
        """Cancel all scheduled timers for a workflow run."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE durable_timers
                SET status = 'cancelled'
                WHERE workflow_run_id = $1 AND status = 'scheduled'
                """,
                uuid.UUID(workflow_run_id),
            )

        cancelled = int(result.split()[-1]) if result else 0
        if cancelled > 0:
            logger.debug("Cancelled %d timers for run %s", cancelled, workflow_run_id)
        return cancelled

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get_timer(
        self, workflow_run_id: str, name: str
    ) -> Optional[DurableTimer]:
        """Get a specific timer by run ID and name."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM durable_timers
                WHERE workflow_run_id = $1 AND name = $2
                """,
                uuid.UUID(workflow_run_id),
                name,
            )

        if row is None:
            return None
        return _row_to_timer(row)

    async def get_pending_timers(
        self, workflow_run_id: str
    ) -> List[DurableTimer]:
        """Get all scheduled (not yet fired) timers for a workflow run."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM durable_timers
                WHERE workflow_run_id = $1 AND status = 'scheduled'
                ORDER BY fire_at ASC
                """,
                uuid.UUID(workflow_run_id),
            )
        return [_row_to_timer(r) for r in rows]

    # ------------------------------------------------------------------
    # Fire (check and execute due timers)
    # ------------------------------------------------------------------

    async def check_and_fire(self) -> List[DurableTimer]:
        """
        Check for due timers and fire them.

        Uses SELECT FOR UPDATE SKIP LOCKED to ensure each timer is fired
        exactly once, even with multiple timer service instances.

        Returns:
            List of timers that were fired in this check.
        """
        now = datetime.now(timezone.utc)
        fired_timers: List[DurableTimer] = []

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Atomically select and lock due timers
                rows = await conn.fetch(
                    """
                    SELECT * FROM durable_timers
                    WHERE status = 'scheduled' AND fire_at <= $1
                    ORDER BY fire_at ASC
                    LIMIT 50
                    FOR UPDATE SKIP LOCKED
                    """,
                    now,
                )

                if not rows:
                    return []

                # Mark all as fired
                timer_ids = [row["id"] for row in rows]
                await conn.execute(
                    """
                    UPDATE durable_timers
                    SET status = 'fired', fired_at = $1
                    WHERE id = ANY($2)
                    """,
                    now,
                    timer_ids,
                )

        # Build timer objects and invoke callback outside transaction
        for row in rows:
            timer = _row_to_timer(row)
            timer.status = TimerStatus.FIRED
            timer.fired_at = now
            fired_timers.append(timer)

        # Invoke callback for each fired timer
        if self._on_timer_fired:
            for timer in fired_timers:
                try:
                    await self._on_timer_fired(timer)
                except Exception as e:
                    logger.error(
                        "Error in timer callback for '%s' (run %s): %s",
                        timer.name, timer.workflow_run_id, e,
                    )

        if fired_timers:
            logger.info("Fired %d timer(s)", len(fired_timers))

        return fired_timers

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup_old_timers(self, older_than_hours: int = 168) -> int:
        """Delete fired/cancelled timers older than N hours (default 7 days)."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM durable_timers
                WHERE status IN ('fired', 'cancelled')
                  AND COALESCE(fired_at, created_at) < (NOW() - make_interval(hours => $1))
                """,
                older_than_hours,
            )

        deleted = int(result.split()[-1]) if result else 0
        if deleted > 0:
            logger.info("TimerService: cleaned up %d old timers", deleted)
        return deleted

    # ------------------------------------------------------------------
    # Background polling loop
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Background loop that checks for due timers."""
        logger.debug("Timer poll loop started")

        while self._running:
            try:
                await self.check_and_fire()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Timer poll error: %s", e)

            try:
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break

        logger.debug("Timer poll loop stopped")


# =============================================================================
# Helpers
# =============================================================================


def _row_to_timer(row: asyncpg.Record) -> DurableTimer:
    """Convert a database row to a DurableTimer model."""
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    return DurableTimer(
        timer_id=row["id"].hex,
        workflow_run_id=row["workflow_run_id"].hex,
        name=row["name"],
        fire_at=row["fire_at"],
        status=row["status"],
        payload=payload,
        created_at=row["created_at"],
        fired_at=row.get("fired_at"),
    )
