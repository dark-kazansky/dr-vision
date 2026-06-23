"""
Workflow Repository — Async PostgreSQL storage for workflows and jobs.

Stores:
- User Canvas (workflow definitions with DSL) — RAGFlow-compatible schema
- User Canvas Versions (version history)
- Job records with lifecycle state, per-node progress, and results
- Job logs for historical auditing

Tables:
    user_canvas         — workflow definitions with DSL JSONB
    user_canvas_version — version history for each canvas
    workflows           — legacy table (kept for backward compat)
    jobs                — execution records with status, progress, results
    job_logs            — per-event log entries for each job

Usage:
    from storage.workflow_repository import WorkflowRepository

    repo = WorkflowRepository(database_url)
    await repo.connect()
    await repo.init_schema()

    canvas_id = await repo.create_canvas({...})
    job_id = await repo.create_job({...})

    await repo.close()
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


# =============================================================================
# SQL DDL
# =============================================================================

_CREATE_USER_CANVAS_TABLE = """
CREATE TABLE IF NOT EXISTS user_canvas (
    id                  VARCHAR(32) PRIMARY KEY,
    title               VARCHAR(255) NOT NULL,
    user_id             VARCHAR(255) NOT NULL DEFAULT 'default',
    canvas_category     VARCHAR(32) NOT NULL DEFAULT 'dataflow_canvas',
    release             BOOLEAN NOT NULL DEFAULT FALSE,
    description         TEXT,
    dsl                 JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_USER_CANVAS_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS user_canvas_version (
    id                  VARCHAR(32) PRIMARY KEY,
    user_canvas_id      VARCHAR(255) NOT NULL REFERENCES user_canvas(id) ON DELETE CASCADE,
    title               VARCHAR(255),
    release             BOOLEAN NOT NULL DEFAULT TRUE,
    dsl                 JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# Legacy table — kept for backward compatibility with existing jobs FK
_CREATE_WORKFLOWS_TABLE = """
CREATE TABLE IF NOT EXISTS workflows (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT,
    graph_data      JSONB NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'draft',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     UUID REFERENCES workflows(id) ON DELETE SET NULL,
    workflow_name   TEXT,
    status          TEXT NOT NULL DEFAULT 'queued',
    progress        REAL NOT NULL DEFAULT 0.0,
    nodes_data      JSONB NOT NULL DEFAULT '[]',
    filename        TEXT,
    file_count      INTEGER DEFAULT 1,
    max_retries     INTEGER DEFAULT 3,
    results         JSONB,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ
);
"""

_CREATE_JOB_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS job_logs (
    id              SERIAL PRIMARY KEY,
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    node_id         TEXT,
    node_type       TEXT,
    node_label      TEXT,
    data            JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_EXECUTION_STATES_TABLE = """
CREATE TABLE IF NOT EXISTS execution_states (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    workflow_id     UUID REFERENCES workflows(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'running',
    node_states     JSONB NOT NULL DEFAULT '{}',
    context         JSONB NOT NULL DEFAULT '{}',
    checkpoint_node TEXT,
    resume_from     TEXT,
    retention_hours INTEGER DEFAULT 72,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_UPLOADS_TABLE = """
CREATE TABLE IF NOT EXISTS uploads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID REFERENCES jobs(id) ON DELETE SET NULL,
    filename        TEXT NOT NULL,
    minio_path      TEXT NOT NULL,
    size_bytes      BIGINT,
    mime_type       TEXT,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_ALTER_JOBS_ADD_MINIO = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='jobs' AND column_name='minio_path') THEN
        ALTER TABLE jobs ADD COLUMN minio_path TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='jobs' AND column_name='result_minio_path') THEN
        ALTER TABLE jobs ADD COLUMN result_minio_path TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='jobs' AND column_name='steps_data') THEN
        ALTER TABLE jobs ADD COLUMN steps_data JSONB;
    END IF;
END $$;
"""

_CREATE_DATA_STORE_TABLE = """
CREATE TABLE IF NOT EXISTS data_store (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        TEXT NOT NULL,
    action_tag      TEXT NOT NULL,
    result_data     TEXT,
    model_used      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_user_canvas_user ON user_canvas(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_user_canvas_category ON user_canvas(canvas_category);",
    "CREATE INDEX IF NOT EXISTS idx_user_canvas_updated ON user_canvas(updated_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_user_canvas_version_canvas ON user_canvas_version(user_canvas_id);",
    "CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);",
    "CREATE INDEX IF NOT EXISTS idx_workflows_updated ON workflows(updated_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_jobs_workflow ON jobs(workflow_id);",
    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);",
    "CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_job_logs_job ON job_logs(job_id);",
    "CREATE INDEX IF NOT EXISTS idx_job_logs_created ON job_logs(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_exec_states_job ON execution_states(job_id);",
    "CREATE INDEX IF NOT EXISTS idx_exec_states_workflow ON execution_states(workflow_id);",
    "CREATE INDEX IF NOT EXISTS idx_exec_states_status ON execution_states(status);",
    "CREATE INDEX IF NOT EXISTS idx_exec_states_updated ON execution_states(updated_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_uploads_job ON uploads(job_id);",
    "CREATE INDEX IF NOT EXISTS idx_uploads_uploaded ON uploads(uploaded_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_data_store_tag ON data_store(action_tag);",
    "CREATE INDEX IF NOT EXISTS idx_data_store_created ON data_store(created_at DESC);",
]


# =============================================================================
# Repository
# =============================================================================

class WorkflowRepository:
    """Async PostgreSQL repository for workflows and jobs."""

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create a connection pool."""
        if self._pool is not None:
            return

        dsn = self._database_url
        if "sslmode" not in dsn:
            separator = "&" if "?" in dsn else "?"
            dsn = f"{dsn}{separator}sslmode=disable"

        self._pool = await asyncpg.create_pool(
            dsn, min_size=2, max_size=10, command_timeout=30,
        )
        logger.info("WorkflowRepository: PostgreSQL pool created")

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("WorkflowRepository: PostgreSQL pool closed")

    async def init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        if not self._pool:
            raise RuntimeError("Not connected")
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_USER_CANVAS_TABLE)
            await conn.execute(_CREATE_USER_CANVAS_VERSION_TABLE)
            await conn.execute(_CREATE_WORKFLOWS_TABLE)
            await conn.execute(_CREATE_JOBS_TABLE)
            await conn.execute(_CREATE_JOB_LOGS_TABLE)
            await conn.execute(_CREATE_EXECUTION_STATES_TABLE)
            await conn.execute(_CREATE_UPLOADS_TABLE)
            await conn.execute(_CREATE_DATA_STORE_TABLE)
            await conn.execute(_ALTER_JOBS_ADD_MINIO)
            for idx_sql in _CREATE_INDEXES:
                await conn.execute(idx_sql)
        logger.info("WorkflowRepository: schema initialized")

    # ------------------------------------------------------------------
    # User Canvas CRUD (new schema)
    # ------------------------------------------------------------------

    async def create_canvas(
        self,
        title: str,
        user_id: str = "default",
        canvas_category: str = "dataflow_canvas",
        description: Optional[str] = None,
        dsl: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new user canvas."""
        if not self._pool:
            raise RuntimeError("Not connected")

        canvas_id = uuid.uuid4().hex[:32]
        now = datetime.now(timezone.utc)
        dsl_json = json.dumps(dsl or _default_dsl(), ensure_ascii=False)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_canvas (id, title, user_id, canvas_category, release, description, dsl, created_at, updated_at)
                VALUES ($1, $2, $3, $4, FALSE, $5, $6::jsonb, $7, $8)
                """,
                canvas_id, title, user_id, canvas_category, description, dsl_json, now, now,
            )

        return {
            "id": canvas_id,
            "title": title,
            "user_id": user_id,
            "canvas_category": canvas_category,
            "release": False,
            "description": description,
            "dsl": dsl or _default_dsl(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    async def get_canvas(self, canvas_id: str) -> Optional[Dict[str, Any]]:
        """Get a canvas by ID."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_canvas WHERE id = $1", canvas_id,
            )

        if row is None:
            return None
        return _row_to_canvas(row)

    async def list_canvases(
        self,
        user_id: Optional[str] = None,
        canvas_category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List canvases with optional filtering."""
        if not self._pool:
            raise RuntimeError("Not connected")

        conditions = []
        params: List[Any] = []
        idx = 1

        if user_id:
            conditions.append(f"user_id = ${idx}")
            params.append(user_id)
            idx += 1
        if canvas_category:
            conditions.append(f"canvas_category = ${idx}")
            params.append(canvas_category)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM user_canvas {where} ORDER BY updated_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
                *params, limit, offset,
            )
            count = await conn.fetchval(
                f"SELECT COUNT(*) FROM user_canvas {where}", *params,
            )

        return {
            "canvases": [_row_to_canvas(r) for r in rows],
            "total": count,
            "limit": limit,
            "offset": offset,
        }

    async def update_canvas(
        self,
        canvas_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        dsl: Optional[Dict[str, Any]] = None,
        release: Optional[bool] = None,
        canvas_category: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update a canvas. Returns updated record or None."""
        if not self._pool:
            raise RuntimeError("Not connected")

        sets = []
        params: List[Any] = []
        idx = 1

        if title is not None:
            sets.append(f"title = ${idx}")
            params.append(title)
            idx += 1
        if description is not None:
            sets.append(f"description = ${idx}")
            params.append(description)
            idx += 1
        if dsl is not None:
            sets.append(f"dsl = ${idx}::jsonb")
            params.append(json.dumps(dsl, ensure_ascii=False))
            idx += 1
        if release is not None:
            sets.append(f"release = ${idx}")
            params.append(release)
            idx += 1
        if canvas_category is not None:
            sets.append(f"canvas_category = ${idx}")
            params.append(canvas_category)
            idx += 1

        if not sets:
            return await self.get_canvas(canvas_id)

        sets.append(f"updated_at = ${idx}")
        params.append(datetime.now(timezone.utc))
        idx += 1

        params.append(canvas_id)
        sql = f"UPDATE user_canvas SET {', '.join(sets)} WHERE id = ${idx} RETURNING *"

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)

        if row is None:
            return None
        return _row_to_canvas(row)

    async def delete_canvas(self, canvas_id: str) -> bool:
        """Delete a canvas and its versions."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM user_canvas WHERE id = $1", canvas_id,
            )
        return result == "DELETE 1"

    async def publish_canvas_version(
        self,
        canvas_id: str,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a version snapshot of the current canvas DSL."""
        if not self._pool:
            raise RuntimeError("Not connected")

        canvas = await self.get_canvas(canvas_id)
        if canvas is None:
            return None

        version_id = uuid.uuid4().hex[:32]
        version_title = title or f"v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        dsl_json = json.dumps(canvas["dsl"], ensure_ascii=False)
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_canvas_version (id, user_canvas_id, title, release, dsl, created_at)
                VALUES ($1, $2, $3, TRUE, $4::jsonb, $5)
                """,
                version_id, canvas_id, version_title, dsl_json, now,
            )
            # Mark canvas as released
            await conn.execute(
                "UPDATE user_canvas SET release = TRUE, updated_at = $1 WHERE id = $2",
                now, canvas_id,
            )

        return {
            "id": version_id,
            "user_canvas_id": canvas_id,
            "title": version_title,
            "release": True,
            "dsl": canvas["dsl"],
            "created_at": now.isoformat(),
        }

    async def list_canvas_versions(
        self, canvas_id: str, limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List versions for a canvas."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM user_canvas_version WHERE user_canvas_id = $1 ORDER BY created_at DESC LIMIT $2",
                canvas_id, limit,
            )

        return [_row_to_canvas_version(r) for r in rows]

    # ------------------------------------------------------------------
    # Workflows CRUD (legacy — kept for backward compat with jobs FK)
    # ------------------------------------------------------------------

    async def create_workflow(
        self,
        name: str,
        description: Optional[str] = None,
        graph_data: Optional[Dict[str, Any]] = None,
        status: str = "draft",
    ) -> Dict[str, Any]:
        """Create a new workflow. Returns the full record."""
        if not self._pool:
            raise RuntimeError("Not connected")

        wf_id = uuid.uuid4()
        graph_json = json.dumps(graph_data or {}, ensure_ascii=False)
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workflows (id, name, description, graph_data, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
                """,
                wf_id, name, description, graph_json, status, now, now,
            )

        return {
            "workflow_id": str(wf_id),
            "name": name,
            "description": description,
            "graph_data": graph_data or {},
            "status": status,
            "created_at": now,
            "updated_at": now,
        }

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a workflow by ID."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflows WHERE id = $1",
                uuid.UUID(workflow_id),
            )

        if row is None:
            return None

        return _row_to_workflow(row)

    async def list_workflows(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List workflows with optional filtering."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    "SELECT * FROM workflows WHERE status = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
                    status, limit, offset,
                )
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM workflows WHERE status = $1", status,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM workflows ORDER BY updated_at DESC LIMIT $1 OFFSET $2",
                    limit, offset,
                )
                count = await conn.fetchval("SELECT COUNT(*) FROM workflows")

        return {
            "workflows": [_row_to_workflow(r) for r in rows],
            "total": count,
            "limit": limit,
            "offset": offset,
        }

    async def update_workflow(
        self,
        workflow_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        graph_data: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update a workflow. Returns updated record or None if not found."""
        if not self._pool:
            raise RuntimeError("Not connected")

        # Build dynamic SET clause
        sets = []
        params: List[Any] = []
        idx = 1

        if name is not None:
            sets.append(f"name = ${idx}")
            params.append(name)
            idx += 1
        if description is not None:
            sets.append(f"description = ${idx}")
            params.append(description)
            idx += 1
        if graph_data is not None:
            sets.append(f"graph_data = ${idx}::jsonb")
            params.append(json.dumps(graph_data, ensure_ascii=False))
            idx += 1
        if status is not None:
            sets.append(f"status = ${idx}")
            params.append(status)
            idx += 1

        if not sets:
            return await self.get_workflow(workflow_id)

        sets.append(f"updated_at = ${idx}")
        params.append(datetime.now(timezone.utc))
        idx += 1

        params.append(uuid.UUID(workflow_id))

        sql = f"UPDATE workflows SET {', '.join(sets)} WHERE id = ${idx} RETURNING *"

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)

        if row is None:
            return None
        return _row_to_workflow(row)

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow. Returns True if deleted."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM workflows WHERE id = $1", uuid.UUID(workflow_id),
            )
        return result == "DELETE 1"

    # ------------------------------------------------------------------
    # Jobs CRUD
    # ------------------------------------------------------------------

    async def create_job(
        self,
        workflow_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        nodes_data: Optional[List[Dict[str, Any]]] = None,
        steps_data: Optional[List[Dict[str, Any]]] = None,
        filename: Optional[str] = None,
        file_count: int = 1,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Create a new job record. steps_data stores full node configs for resume."""
        if not self._pool:
            raise RuntimeError("Not connected")

        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        nodes_json = json.dumps(nodes_data or [], ensure_ascii=False)
        steps_json = json.dumps(steps_data or [], ensure_ascii=False) if steps_data else None
        wf_uuid = uuid.UUID(workflow_id) if workflow_id else None

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO jobs (id, workflow_id, workflow_name, status, progress,
                                  nodes_data, steps_data, filename, file_count, max_retries, created_at)
                VALUES ($1, $2, $3, 'queued', 0.0, $4::jsonb, $5::jsonb, $6, $7, $8, $9)
                """,
                job_id, wf_uuid, workflow_name, nodes_json, steps_json,
                filename, file_count, max_retries, now,
            )

        return {
            "job_id": str(job_id),
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "status": "queued",
            "progress": 0.0,
            "nodes_data": nodes_data or [],
            "steps_data": steps_data or [],
            "filename": filename,
            "file_count": file_count,
            "max_retries": max_retries,
            "created_at": now,
        }

    async def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        nodes_data: Optional[List[Dict[str, Any]]] = None,
        results: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> None:
        """Update job fields."""
        if not self._pool:
            raise RuntimeError("Not connected")

        sets = []
        params: List[Any] = []
        idx = 1

        if status is not None:
            sets.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        if progress is not None:
            sets.append(f"progress = ${idx}")
            params.append(progress)
            idx += 1
        if nodes_data is not None:
            sets.append(f"nodes_data = ${idx}::jsonb")
            params.append(json.dumps(nodes_data, ensure_ascii=False))
            idx += 1
        if results is not None:
            sets.append(f"results = ${idx}::jsonb")
            params.append(json.dumps(results, ensure_ascii=False))
            idx += 1
        if error is not None:
            sets.append(f"error = ${idx}")
            params.append(error)
            idx += 1
        if started_at is not None:
            sets.append(f"started_at = ${idx}")
            params.append(started_at)
            idx += 1
        if completed_at is not None:
            sets.append(f"completed_at = ${idx}")
            params.append(completed_at)
            idx += 1
        if cancelled_at is not None:
            sets.append(f"cancelled_at = ${idx}")
            params.append(cancelled_at)
            idx += 1

        if not sets:
            return

        params.append(uuid.UUID(job_id))
        sql = f"UPDATE jobs SET {', '.join(sets)} WHERE id = ${idx}"

        async with self._pool.acquire() as conn:
            await conn.execute(sql, *params)

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM jobs WHERE id = $1", uuid.UUID(job_id),
            )

        if row is None:
            return None
        return _row_to_job(row)

    async def list_jobs(
        self,
        status: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List jobs with optional filtering."""
        if not self._pool:
            raise RuntimeError("Not connected")

        conditions = []
        params: List[Any] = []
        idx = 1

        if status:
            conditions.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        if workflow_id:
            conditions.append(f"workflow_id = ${idx}")
            params.append(uuid.UUID(workflow_id))
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM jobs {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
                *params, limit, offset,
            )
            count = await conn.fetchval(
                f"SELECT COUNT(*) FROM jobs {where}", *params,
            )

        return {
            "jobs": [_row_to_job(r) for r in rows],
            "total": count,
            "limit": limit,
            "offset": offset,
        }

    async def delete_old_jobs(self, older_than_hours: int = 24) -> int:
        """Delete jobs older than specified hours. Returns count deleted."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM jobs
                WHERE status IN ('completed', 'failed', 'cancelled')
                  AND created_at < NOW() - INTERVAL '1 hour' * $1
                """,
                older_than_hours,
            )
        count = int(result.split()[-1]) if result else 0
        if count > 0:
            logger.info("Deleted %d old jobs", count)
        return count

    async def delete_job(self, job_id: str) -> bool:
        """Delete a single job by ID. Returns True if deleted."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM jobs WHERE job_id = $1", job_id
            )
        return result and "DELETE 1" in result

    # ------------------------------------------------------------------
    # Job Logs
    # ------------------------------------------------------------------

    async def add_job_log(
        self,
        job_id: str,
        event_type: str,
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        node_label: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a log entry for a job."""
        if not self._pool:
            raise RuntimeError("Not connected")

        data_json = json.dumps(data, ensure_ascii=False) if data else None

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO job_logs (job_id, event_type, node_id, node_type, node_label, data)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """,
                uuid.UUID(job_id), event_type, node_id, node_type, node_label, data_json,
            )

    async def get_job_logs(
        self, job_id: str, limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Get logs for a job."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM job_logs WHERE job_id = $1 ORDER BY created_at ASC LIMIT $2",
                uuid.UUID(job_id), limit,
            )

        return [
            {
                "id": row["id"],
                "job_id": str(row["job_id"]),
                "event_type": row["event_type"],
                "node_id": row["node_id"],
                "node_type": row["node_type"],
                "node_label": row["node_label"],
                "data": json.loads(row["data"]) if row["data"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Execution States CRUD
    # ------------------------------------------------------------------

    async def create_execution_state(
        self,
        job_id: str,
        workflow_id: Optional[str] = None,
        retention_hours: int = 72,
    ) -> Dict[str, Any]:
        """Create a new execution state for a job."""
        if not self._pool:
            raise RuntimeError("Not connected")

        state_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        wf_uuid = uuid.UUID(workflow_id) if workflow_id else None

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO execution_states
                    (id, job_id, workflow_id, status, node_states, context,
                     retention_hours, created_at, updated_at)
                VALUES ($1, $2, $3, 'running', '{}'::jsonb, '{}'::jsonb, $4, $5, $6)
                """,
                state_id, uuid.UUID(job_id), wf_uuid, retention_hours, now, now,
            )

        return {
            "state_id": str(state_id),
            "job_id": job_id,
            "workflow_id": workflow_id,
            "status": "running",
            "node_states": {},
            "context": {},
            "checkpoint_node": None,
            "resume_from": None,
            "retention_hours": retention_hours,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    async def get_execution_state(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get execution state by job_id."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM execution_states WHERE job_id = $1 ORDER BY created_at DESC LIMIT 1",
                uuid.UUID(job_id),
            )

        if row is None:
            return None
        return _row_to_execution_state(row)

    async def get_execution_state_by_id(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Get execution state by its own ID."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM execution_states WHERE id = $1",
                uuid.UUID(state_id),
            )

        if row is None:
            return None
        return _row_to_execution_state(row)

    async def update_execution_state(
        self,
        job_id: str,
        node_states: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        checkpoint_node: Optional[str] = None,
        resume_from: Optional[str] = None,
    ) -> None:
        """Update execution state fields."""
        if not self._pool:
            raise RuntimeError("Not connected")

        sets = []
        params: List[Any] = []
        idx = 1

        if node_states is not None:
            sets.append(f"node_states = ${idx}::jsonb")
            params.append(json.dumps(node_states, ensure_ascii=False))
            idx += 1
        if context is not None:
            sets.append(f"context = ${idx}::jsonb")
            params.append(json.dumps(context, ensure_ascii=False))
            idx += 1
        if status is not None:
            sets.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        if checkpoint_node is not None:
            sets.append(f"checkpoint_node = ${idx}")
            params.append(checkpoint_node)
            idx += 1
        if resume_from is not None:
            sets.append(f"resume_from = ${idx}")
            params.append(resume_from)
            idx += 1

        if not sets:
            return

        sets.append(f"updated_at = ${idx}")
        params.append(datetime.now(timezone.utc))
        idx += 1

        params.append(uuid.UUID(job_id))
        sql = (
            f"UPDATE execution_states SET {', '.join(sets)} "
            f"WHERE job_id = ${idx} AND status != 'cleaned'"
        )

        async with self._pool.acquire() as conn:
            await conn.execute(sql, *params)

    async def save_node_output(
        self,
        job_id: str,
        node_id: str,
        output: Any,
        node_status: str = "completed",
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Save a single node's output into the execution state."""
        if not self._pool:
            raise RuntimeError("Not connected")

        now = datetime.now(timezone.utc)

        # Use jsonb_set to update the specific node without overwriting others
        node_data = json.dumps({
            "output": output,
            "status": node_status,
            "error": error,
            "duration_ms": duration_ms,
            "saved_at": now.isoformat(),
        }, ensure_ascii=False)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE execution_states
                SET node_states = jsonb_set(
                    COALESCE(node_states, '{}'::jsonb),
                    $1::text[],
                    $2::jsonb
                ),
                checkpoint_node = $3,
                updated_at = $4
                WHERE job_id = $5 AND status != 'cleaned'
                """,
                [node_id],
                node_data,
                node_id,
                now,
                uuid.UUID(job_id),
            )

    async def save_context_data(
        self,
        job_id: str,
        key: str,
        value: Any,
    ) -> None:
        """Save a key-value pair into the shared execution context."""
        if not self._pool:
            raise RuntimeError("Not connected")

        now = datetime.now(timezone.utc)
        value_json = json.dumps(value, ensure_ascii=False)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE execution_states
                SET context = jsonb_set(
                    COALESCE(context, '{}'::jsonb),
                    $1::text[],
                    $2::jsonb
                ),
                updated_at = $3
                WHERE job_id = $4 AND status != 'cleaned'
                """,
                [key],
                value_json,
                now,
                uuid.UUID(job_id),
            )

    async def list_execution_states(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List execution states with optional filtering."""
        if not self._pool:
            raise RuntimeError("Not connected")

        conditions = []
        params: List[Any] = []
        idx = 1

        if workflow_id:
            conditions.append(f"workflow_id = ${idx}")
            params.append(uuid.UUID(workflow_id))
            idx += 1
        if status:
            conditions.append(f"status = ${idx}")
            params.append(status)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM execution_states {where} ORDER BY updated_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
                *params, limit, offset,
            )
            count = await conn.fetchval(
                f"SELECT COUNT(*) FROM execution_states {where}", *params,
            )

        return {
            "states": [_row_to_execution_state(r) for r in rows],
            "total": count,
            "limit": limit,
            "offset": offset,
        }

    async def cleanup_execution_states(self) -> int:
        """Clean up execution states past their retention period."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE execution_states
                SET status = 'cleaned', node_states = '{}'::jsonb, context = '{}'::jsonb
                WHERE status IN ('completed', 'failed', 'cancelled')
                  AND updated_at < NOW() - (retention_hours || ' hours')::interval
                """
            )
        count = int(result.split()[-1]) if result else 0
        if count > 0:
            logger.info("Cleaned up %d expired execution states", count)
        return count

    # ------------------------------------------------------------------
    # Uploads CRUD
    # ------------------------------------------------------------------

    async def create_upload(
        self,
        job_id: Optional[str] = None,
        filename: str = "",
        minio_path: str = "",
        size_bytes: Optional[int] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an upload record."""
        if not self._pool:
            raise RuntimeError("Not connected")

        upload_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        job_uuid = uuid.UUID(job_id) if job_id else None

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO uploads (id, job_id, filename, minio_path, size_bytes, mime_type, uploaded_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                upload_id, job_uuid, filename, minio_path, size_bytes, mime_type, now,
            )

        return {
            "upload_id": str(upload_id),
            "job_id": job_id,
            "filename": filename,
            "minio_path": minio_path,
            "size_bytes": size_bytes,
            "mime_type": mime_type,
            "uploaded_at": now.isoformat(),
        }

    async def get_upload(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Get an upload record by ID."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM uploads WHERE id = $1", uuid.UUID(upload_id),
            )

        if row is None:
            return None
        return _row_to_upload(row)

    async def get_uploads_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all uploads for a job."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM uploads WHERE job_id = $1 ORDER BY uploaded_at DESC",
                uuid.UUID(job_id),
            )

        return [_row_to_upload(r) for r in rows]

    async def list_uploads(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List all uploads."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM uploads ORDER BY uploaded_at DESC LIMIT $1 OFFSET $2",
                limit, offset,
            )
            count = await conn.fetchval("SELECT COUNT(*) FROM uploads")

        return {
            "uploads": [_row_to_upload(r) for r in rows],
            "total": count,
            "limit": limit,
            "offset": offset,
        }

    # ------------------------------------------------------------------
    # Jobs — minio_path updates
    # ------------------------------------------------------------------

    async def set_job_minio_path(self, job_id: str, minio_path: str) -> None:
        """Set the MinIO path for a job's input file."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE jobs SET minio_path = $1 WHERE id = $2",
                minio_path, uuid.UUID(job_id),
            )

    async def set_job_result_minio_path(self, job_id: str, result_minio_path: str) -> None:
        """Set the MinIO path for a job's result output."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE jobs SET result_minio_path = $1 WHERE id = $2",
                result_minio_path, uuid.UUID(job_id),
            )

    async def get_pending_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get jobs that are queued or running (for hydration on startup)."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM jobs
                WHERE status IN ('queued', 'running')
                ORDER BY created_at ASC
                LIMIT $1
                """,
                limit,
            )

        return [_row_to_job(row) for row in rows]


# =============================================================================
# Helpers
# =============================================================================

def _row_to_workflow(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert a DB row to a workflow dict."""
    graph_data = row["graph_data"]
    if isinstance(graph_data, str):
        graph_data = json.loads(graph_data)

    return {
        "workflow_id": str(row["id"]),
        "name": row["name"],
        "description": row["description"],
        "graph_data": graph_data,
        "status": row["status"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _row_to_job(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert a DB row to a job dict."""
    nodes_data = row["nodes_data"]
    if isinstance(nodes_data, str):
        nodes_data = json.loads(nodes_data)

    results = row["results"]
    if isinstance(results, str):
        results = json.loads(results)

    steps_data = row.get("steps_data")
    if isinstance(steps_data, str):
        steps_data = json.loads(steps_data)

    return {
        "job_id": str(row["id"]),
        "workflow_id": str(row["workflow_id"]) if row["workflow_id"] else None,
        "workflow_name": row["workflow_name"],
        "status": row["status"],
        "progress": row["progress"],
        "nodes": nodes_data,
        "filename": row["filename"],
        "file_count": row["file_count"],
        "max_retries": row["max_retries"],
        "results": results,
        "steps_data": steps_data,
        "error": row["error"],
        "minio_path": row.get("minio_path"),
        "result_minio_path": row.get("result_minio_path"),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
        "cancelled_at": row["cancelled_at"].isoformat() if row["cancelled_at"] else None,
    }


def _row_to_upload(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert a DB row to an upload dict."""
    return {
        "upload_id": str(row["id"]),
        "job_id": str(row["job_id"]) if row["job_id"] else None,
        "filename": row["filename"],
        "minio_path": row["minio_path"],
        "size_bytes": row["size_bytes"],
        "mime_type": row["mime_type"],
        "uploaded_at": row["uploaded_at"].isoformat() if row["uploaded_at"] else None,
    }


def _row_to_canvas(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert a DB row to a canvas dict."""
    dsl = row["dsl"]
    if isinstance(dsl, str):
        dsl = json.loads(dsl)

    return {
        "id": row["id"],
        "title": row["title"],
        "user_id": row["user_id"],
        "canvas_category": row["canvas_category"],
        "release": row["release"],
        "description": row["description"],
        "dsl": dsl,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _row_to_canvas_version(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert a DB row to a canvas version dict."""
    dsl = row["dsl"]
    if isinstance(dsl, str):
        dsl = json.loads(dsl)

    return {
        "id": row["id"],
        "user_canvas_id": row["user_canvas_id"],
        "title": row["title"],
        "release": row["release"],
        "dsl": dsl,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def _default_dsl() -> Dict[str, Any]:
    """Return a default empty DSL structure."""
    return {
        "components": {},
        "graph": {
            "nodes": [],
            "edges": [],
        },
        "globals": {
            "sys.query": "",
            "sys.conversation_turns": 0,
            "sys.files": [],
            "sys.history": [],
        },
        "path": [],
        "history": [],
        "variables": {},
    }


def _row_to_execution_state(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert a DB row to an execution state dict."""
    node_states = row["node_states"]
    if isinstance(node_states, str):
        node_states = json.loads(node_states)

    context = row["context"]
    if isinstance(context, str):
        context = json.loads(context)

    return {
        "state_id": str(row["id"]),
        "job_id": str(row["job_id"]),
        "workflow_id": str(row["workflow_id"]) if row["workflow_id"] else None,
        "status": row["status"],
        "node_states": node_states,
        "context": context,
        "checkpoint_node": row["checkpoint_node"],
        "resume_from": row["resume_from"],
        "retention_hours": row["retention_hours"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }
