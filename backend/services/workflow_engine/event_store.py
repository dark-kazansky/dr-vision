"""
Event Store — Append-only event log for durable workflow orchestration.

All workflow state changes are recorded as immutable events in PostgreSQL.
State is reconstructed by replaying events (event-sourcing pattern).

Key properties:
- Append-only: Events are never modified or deleted (except for retention cleanup)
- Ordered: Events have a monotonically increasing sequence_num per workflow run
- Durable: All events persisted to PostgreSQL immediately (no buffering)
- Queryable: Can load full history or filter by event type

Schema:
    workflow_events — append-only event log
    workflow_runs   — metadata/index table for quick lookups
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg

from services.workflow_engine.models import (
    WorkflowEvent,
    WorkflowRunStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SQL DDL
# =============================================================================

_CREATE_WORKFLOW_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     TEXT NOT NULL,
    workflow_name   TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
    input_data      JSONB NOT NULL DEFAULT '{}',
    output_data     JSONB NOT NULL DEFAULT '{}',
    error           TEXT,
    last_sequence   INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    timeout_seconds INTEGER NOT NULL DEFAULT 3600,
    metadata        JSONB NOT NULL DEFAULT '{}'
);
"""

_CREATE_WORKFLOW_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS workflow_events (
    id              BIGSERIAL PRIMARY KEY,
    workflow_run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    sequence_num    INTEGER NOT NULL,
    event_type      TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(workflow_run_id, sequence_num)
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_wf_runs_workflow ON workflow_runs(workflow_id);",
    "CREATE INDEX IF NOT EXISTS idx_wf_runs_status ON workflow_runs(status);",
    "CREATE INDEX IF NOT EXISTS idx_wf_runs_created ON workflow_runs(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_wf_events_run ON workflow_events(workflow_run_id, sequence_num);",
    "CREATE INDEX IF NOT EXISTS idx_wf_events_type ON workflow_events(workflow_run_id, event_type);",
    "CREATE INDEX IF NOT EXISTS idx_wf_events_created ON workflow_events(created_at DESC);",
]


# =============================================================================
# Event Store
# =============================================================================


class EventStore:
    """
    Append-only event store backed by PostgreSQL.

    Responsibilities:
    - Create workflow runs (metadata record)
    - Append events with auto-incrementing sequence numbers
    - Load event history for replay
    - Query runs by status for recovery
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ------------------------------------------------------------------
    # Schema initialization
    # ------------------------------------------------------------------

    async def init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_WORKFLOW_RUNS_TABLE)
            await conn.execute(_CREATE_WORKFLOW_EVENTS_TABLE)
            for idx_sql in _CREATE_INDEXES:
                await conn.execute(idx_sql)
        logger.info("EventStore: schema initialized")

    # ------------------------------------------------------------------
    # Workflow Run lifecycle
    # ------------------------------------------------------------------

    async def create_run(
        self,
        workflow_id: str,
        workflow_name: str = "",
        input_data: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 3600,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new workflow run record.

        Returns the run_id (UUID hex string).
        """
        run_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workflow_runs
                    (id, workflow_id, workflow_name, status, input_data,
                     timeout_seconds, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7::jsonb, $8)
                """,
                run_id,
                workflow_id,
                workflow_name,
                WorkflowRunStatus.PENDING,
                json.dumps(input_data or {}, ensure_ascii=False),
                timeout_seconds,
                json.dumps(metadata or {}, ensure_ascii=False),
                now,
            )

        logger.debug("Created workflow run %s for workflow %s", run_id.hex, workflow_id)
        return run_id.hex

    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow run metadata by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_runs WHERE id = $1",
                uuid.UUID(run_id),
            )

        if row is None:
            return None
        return _row_to_run(row)

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        error: Optional[str] = None,
        output_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update the run's denormalized status (for quick queries)."""
        sets = ["status = $2"]
        params: list = [uuid.UUID(run_id), status]
        idx = 3

        now = datetime.now(timezone.utc)

        if status == WorkflowRunStatus.RUNNING:
            sets.append(f"started_at = ${idx}")
            params.append(now)
            idx += 1
        elif status in (
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLED,
            WorkflowRunStatus.TIMED_OUT,
        ):
            sets.append(f"completed_at = ${idx}")
            params.append(now)
            idx += 1

        if error is not None:
            sets.append(f"error = ${idx}")
            params.append(error)
            idx += 1

        if output_data is not None:
            sets.append(f"output_data = ${idx}::jsonb")
            params.append(json.dumps(output_data, ensure_ascii=False))
            idx += 1

        sql = f"UPDATE workflow_runs SET {', '.join(sets)} WHERE id = $1"
        async with self._pool.acquire() as conn:
            await conn.execute(sql, *params)

    async def list_runs_by_status(
        self,
        status: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List workflow runs with a given status. Used for recovery."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM workflow_runs
                WHERE status = $1
                ORDER BY created_at ASC
                LIMIT $2
                """,
                status,
                limit,
            )
        return [_row_to_run(r) for r in rows]

    async def list_stale_runs(
        self,
        running_statuses: Optional[List[str]] = None,
        stale_seconds: int = 600,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Find runs that are in a running state but haven't had events recently.
        Used by recovery orchestrator to detect dead workflows.
        """
        if running_statuses is None:
            running_statuses = [
                WorkflowRunStatus.RUNNING,
                WorkflowRunStatus.WAITING_ACTIVITY,
                WorkflowRunStatus.WAITING_TIMER,
            ]

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT wr.* FROM workflow_runs wr
                WHERE wr.status = ANY($1)
                  AND NOT EXISTS (
                      SELECT 1 FROM workflow_events we
                      WHERE we.workflow_run_id = wr.id
                        AND we.created_at > (NOW() - make_interval(secs => $2))
                  )
                ORDER BY wr.created_at ASC
                LIMIT $3
                """,
                running_statuses,
                float(stale_seconds),
                limit,
            )
        return [_row_to_run(r) for r in rows]

    # ------------------------------------------------------------------
    # Event append & load
    # ------------------------------------------------------------------

    async def append(
        self,
        run_id: str,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> WorkflowEvent:
        """
        Append an event to the workflow run's event log.

        Atomically increments the sequence number.
        Returns the created WorkflowEvent with assigned event_id and sequence_num.
        """
        run_uuid = uuid.UUID(run_id)
        now = datetime.now(timezone.utc)
        payload_json = json.dumps(payload or {}, ensure_ascii=False)

        async with self._pool.acquire() as conn:
            # Use a transaction to atomically get next sequence and insert
            async with conn.transaction():
                # Get and increment sequence
                seq = await conn.fetchval(
                    """
                    UPDATE workflow_runs
                    SET last_sequence = last_sequence + 1
                    WHERE id = $1
                    RETURNING last_sequence
                    """,
                    run_uuid,
                )

                if seq is None:
                    raise ValueError(f"Workflow run {run_id} not found")

                # Insert event
                event_id = await conn.fetchval(
                    """
                    INSERT INTO workflow_events
                        (workflow_run_id, sequence_num, event_type, payload, created_at)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    RETURNING id
                    """,
                    run_uuid,
                    seq,
                    event_type,
                    payload_json,
                    now,
                )

        event = WorkflowEvent(
            event_id=event_id,
            workflow_run_id=run_id,
            sequence_num=seq,
            event_type=event_type,
            timestamp=now,
            payload=payload or {},
        )

        logger.debug(
            "Appended event %s (seq=%d) to run %s",
            event_type, seq, run_id,
        )
        return event

    async def load_history(
        self,
        run_id: str,
        after_sequence: int = 0,
    ) -> List[WorkflowEvent]:
        """
        Load event history for a workflow run.

        Args:
            run_id: The workflow run ID.
            after_sequence: Only load events after this sequence number (for incremental replay).

        Returns:
            List of WorkflowEvent ordered by sequence_num.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, workflow_run_id, sequence_num, event_type, payload, created_at
                FROM workflow_events
                WHERE workflow_run_id = $1 AND sequence_num > $2
                ORDER BY sequence_num ASC
                """,
                uuid.UUID(run_id),
                after_sequence,
            )

        events = []
        for row in rows:
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)

            events.append(WorkflowEvent(
                event_id=row["id"],
                workflow_run_id=run_id,
                sequence_num=row["sequence_num"],
                event_type=row["event_type"],
                timestamp=row["created_at"],
                payload=payload,
            ))

        return events

    async def get_last_event(self, run_id: str) -> Optional[WorkflowEvent]:
        """Get the most recent event for a workflow run."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, workflow_run_id, sequence_num, event_type, payload, created_at
                FROM workflow_events
                WHERE workflow_run_id = $1
                ORDER BY sequence_num DESC
                LIMIT 1
                """,
                uuid.UUID(run_id),
            )

        if row is None:
            return None

        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)

        return WorkflowEvent(
            event_id=row["id"],
            workflow_run_id=run_id,
            sequence_num=row["sequence_num"],
            event_type=row["event_type"],
            timestamp=row["created_at"],
            payload=payload,
        )

    async def count_events(self, run_id: str) -> int:
        """Count total events for a workflow run."""
        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM workflow_events WHERE workflow_run_id = $1",
                uuid.UUID(run_id),
            )
        return count or 0

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def delete_old_runs(self, older_than_hours: int = 168) -> int:
        """
        Delete completed/failed/cancelled runs older than N hours.
        Cascades to workflow_events via FK.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM workflow_runs
                WHERE status IN ('completed', 'failed', 'cancelled', 'timed_out')
                  AND completed_at < (NOW() - make_interval(hours => $1))
                """,
                older_than_hours,
            )
        # Parse "DELETE N" result
        deleted = int(result.split()[-1]) if result else 0
        if deleted > 0:
            logger.info("EventStore: cleaned up %d old workflow runs", deleted)
        return deleted


# =============================================================================
# Helpers
# =============================================================================


def _row_to_run(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert a database row to a run dict."""
    input_data = row["input_data"]
    if isinstance(input_data, str):
        input_data = json.loads(input_data)

    output_data = row["output_data"]
    if isinstance(output_data, str):
        output_data = json.loads(output_data)

    metadata = row["metadata"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata)

    return {
        "run_id": row["id"].hex,
        "workflow_id": row["workflow_id"],
        "workflow_name": row["workflow_name"],
        "status": row["status"],
        "input_data": input_data,
        "output_data": output_data,
        "error": row["error"],
        "last_sequence": row["last_sequence"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "timeout_seconds": row["timeout_seconds"],
        "metadata": metadata,
    }
