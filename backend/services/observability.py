"""
Observability Service — Metrics, timeline, and analytics for workflow executions.

Provides:
- Execution timeline per job (per-node durations and status)
- Performance metrics (avg/min/max per node type, total durations)
- Error analytics (failure rate per node type, common errors)
- Audit log (who ran what, when, result)
- Dashboard summary (health status across workflows)

Data sources:
- jobs table (lifecycle, timestamps, status)
- job_logs table (per-event timeline)
- execution_states table (per-node duration_ms via node_states JSONB)

This is the core service for feat-010 (Journey Observability).
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_repo = None


def set_repository(repo) -> None:
    """Set the workflow repository. Called during app startup."""
    global _repo
    _repo = repo


def get_repository():
    """Get the workflow repository."""
    return _repo


async def get_execution_timeline(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get execution timeline for a specific job.

    Returns per-node timing: start, end, duration_ms, status.
    Data sourced from execution_states.node_states JSONB.
    """
    if _repo is None:
        return None

    try:
        # Get execution state for node-level timing
        state = await _repo.get_execution_state(job_id)

        # Get job record for job-level timing
        job = await _repo.get_job(job_id)
        if job is None:
            return None

        nodes_timeline = []
        node_states = state.get("node_states", {}) if state else {}
        nodes_data = job.get("nodes") or []

        for node_info in nodes_data:
            node_id = node_info.get("node_id", "")
            node_state = node_states.get(node_id, {})

            nodes_timeline.append({
                "node_id": node_id,
                "node_type": node_info.get("node_type", ""),
                "node_label": node_info.get("node_label", ""),
                "status": node_state.get("status", node_info.get("status", "pending")),
                "duration_ms": node_state.get("duration_ms"),
                "error": node_state.get("error"),
                "saved_at": node_state.get("saved_at"),
            })

        # Calculate total duration
        total_duration_ms = None
        if job.get("started_at") and job.get("completed_at"):
            started = job["started_at"]
            completed = job["completed_at"]
            if isinstance(started, str):
                started = datetime.fromisoformat(started)
            if isinstance(completed, str):
                completed = datetime.fromisoformat(completed)
            total_duration_ms = int((completed - started).total_seconds() * 1000)

        return {
            "job_id": job_id,
            "workflow_id": job.get("workflow_id"),
            "workflow_name": job.get("workflow_name"),
            "status": job.get("status"),
            "total_duration_ms": total_duration_ms,
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
            "nodes": nodes_timeline,
        }
    except Exception as e:
        logger.warning("Failed to get execution timeline for job %s: %s", job_id, e)
        return None


async def get_performance_metrics(
    workflow_id: Optional[str] = None,
    days: int = 7,
) -> Dict[str, Any]:
    """
    Get aggregated performance metrics.

    Returns:
    - Per node_type: avg/min/max duration, execution count
    - Overall: total jobs, avg job duration, success rate
    """
    if _repo is None:
        return {"error": "Repository not configured"}

    try:
        pool = _repo._pool
        if not pool:
            return {"error": "Database not connected"}

        async with pool.acquire() as conn:
            # Overall job metrics
            job_stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total_jobs,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed_jobs,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed_jobs,
                    COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_jobs,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)
                        FILTER (WHERE started_at IS NOT NULL AND completed_at IS NOT NULL)
                        AS avg_duration_ms,
                    MIN(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)
                        FILTER (WHERE started_at IS NOT NULL AND completed_at IS NOT NULL)
                        AS min_duration_ms,
                    MAX(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)
                        FILTER (WHERE started_at IS NOT NULL AND completed_at IS NOT NULL)
                        AS max_duration_ms
                FROM jobs
                WHERE created_at > NOW() - INTERVAL '1 day' * $1
                  AND ($2::uuid IS NULL OR workflow_id = $2::uuid)
                """,
                days,
                workflow_id,
            )

            # Per node type metrics from execution_states — via jobs + execution_states join
            node_type_metrics_rows = await conn.fetch(
                """
                WITH node_durations AS (
                    SELECT
                        n_elem ->> 'node_type' AS node_type,
                        (es_node.value ->> 'duration_ms')::int AS duration_ms,
                        (es_node.value ->> 'status') AS node_status
                    FROM jobs j
                    CROSS JOIN LATERAL jsonb_array_elements(j.nodes_data) AS n_elem
                    LEFT JOIN execution_states es ON es.job_id = j.id
                    LEFT JOIN LATERAL jsonb_each(es.node_states) AS es_node(key, value)
                        ON es_node.key = (n_elem ->> 'node_id')
                    WHERE j.created_at > NOW() - INTERVAL '1 day' * $1
                      AND ($2::uuid IS NULL OR j.workflow_id = $2::uuid)
                      AND es_node.value ->> 'duration_ms' IS NOT NULL
                )
                SELECT
                    node_type,
                    COUNT(*) AS execution_count,
                    COUNT(*) FILTER (WHERE node_status = 'completed') AS success_count,
                    COUNT(*) FILTER (WHERE node_status = 'failed') AS failure_count,
                    ROUND(AVG(duration_ms)) AS avg_duration_ms,
                    MIN(duration_ms) AS min_duration_ms,
                    MAX(duration_ms) AS max_duration_ms
                FROM node_durations
                WHERE node_type IS NOT NULL
                GROUP BY node_type
                ORDER BY execution_count DESC
                """,
                days,
                workflow_id,
            )

        total_jobs = job_stats["total_jobs"] if job_stats else 0
        completed = job_stats["completed_jobs"] if job_stats else 0
        success_rate = (completed / total_jobs * 100) if total_jobs > 0 else 0.0

        return {
            "period_days": days,
            "workflow_id": workflow_id,
            "summary": {
                "total_jobs": total_jobs,
                "completed_jobs": completed,
                "failed_jobs": job_stats["failed_jobs"] if job_stats else 0,
                "cancelled_jobs": job_stats["cancelled_jobs"] if job_stats else 0,
                "success_rate": round(success_rate, 1),
                "avg_duration_ms": int(job_stats["avg_duration_ms"]) if job_stats and job_stats["avg_duration_ms"] else None,
                "min_duration_ms": int(job_stats["min_duration_ms"]) if job_stats and job_stats["min_duration_ms"] else None,
                "max_duration_ms": int(job_stats["max_duration_ms"]) if job_stats and job_stats["max_duration_ms"] else None,
            },
            "node_types": [
                {
                    "node_type": row["node_type"],
                    "execution_count": row["execution_count"],
                    "success_count": row["success_count"],
                    "failure_count": row["failure_count"],
                    "failure_rate": round(row["failure_count"] / row["execution_count"] * 100, 1) if row["execution_count"] > 0 else 0.0,
                    "avg_duration_ms": int(row["avg_duration_ms"]) if row["avg_duration_ms"] else None,
                    "min_duration_ms": row["min_duration_ms"],
                    "max_duration_ms": row["max_duration_ms"],
                }
                for row in node_type_metrics_rows
            ],
        }
    except Exception as e:
        logger.warning("Failed to get performance metrics: %s", e)
        return {"error": str(e)}


async def get_error_analytics(
    workflow_id: Optional[str] = None,
    days: int = 7,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Get error analytics: failure rates by node type, common errors.
    """
    if _repo is None:
        return {"error": "Repository not configured"}

    try:
        pool = _repo._pool
        if not pool:
            return {"error": "Database not connected"}

        async with pool.acquire() as conn:
            # Top errors from job_logs
            error_rows = await conn.fetch(
                """
                SELECT
                    node_type,
                    node_label,
                    data ->> 'error' AS error_message,
                    COUNT(*) AS occurrence_count,
                    MAX(created_at) AS last_occurred
                FROM job_logs
                WHERE event_type IN ('node_failed')
                  AND created_at > NOW() - INTERVAL '1 day' * $1
                  AND data ->> 'error' IS NOT NULL
                GROUP BY node_type, node_label, data ->> 'error'
                ORDER BY occurrence_count DESC
                LIMIT $2
                """,
                days,
                limit,
            )

            # Failure rate by node type
            failure_rate_rows = await conn.fetch(
                """
                WITH node_events AS (
                    SELECT
                        node_type,
                        event_type,
                        COUNT(*) AS cnt
                    FROM job_logs
                    WHERE event_type IN ('node_completed', 'node_failed')
                      AND created_at > NOW() - INTERVAL '1 day' * $1
                      AND node_type IS NOT NULL
                    GROUP BY node_type, event_type
                )
                SELECT
                    node_type,
                    COALESCE(SUM(cnt) FILTER (WHERE event_type = 'node_completed'), 0) AS successes,
                    COALESCE(SUM(cnt) FILTER (WHERE event_type = 'node_failed'), 0) AS failures,
                    COALESCE(SUM(cnt), 0) AS total
                FROM node_events
                GROUP BY node_type
                ORDER BY failures DESC
                """,
                days,
            )

        return {
            "period_days": days,
            "top_errors": [
                {
                    "node_type": row["node_type"],
                    "node_label": row["node_label"],
                    "error_message": row["error_message"],
                    "occurrence_count": row["occurrence_count"],
                    "last_occurred": row["last_occurred"].isoformat() if row["last_occurred"] else None,
                }
                for row in error_rows
            ],
            "failure_rates": [
                {
                    "node_type": row["node_type"],
                    "successes": row["successes"],
                    "failures": row["failures"],
                    "total": row["total"],
                    "failure_rate": round(row["failures"] / row["total"] * 100, 1) if row["total"] > 0 else 0.0,
                }
                for row in failure_rate_rows
            ],
        }
    except Exception as e:
        logger.warning("Failed to get error analytics: %s", e)
        return {"error": str(e)}


async def get_audit_log(
    workflow_id: Optional[str] = None,
    days: int = 7,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Get audit log: who ran what, when, result.

    Returns job-level entries with timestamps and outcomes.
    """
    if _repo is None:
        return {"entries": [], "total": 0}

    try:
        pool = _repo._pool
        if not pool:
            return {"entries": [], "total": 0}

        async with pool.acquire() as conn:
            where_clauses = ["j.created_at > NOW() - INTERVAL '1 day' * $1"]
            params: List[Any] = [days]
            idx = 2

            if workflow_id:
                where_clauses.append(f"j.workflow_id = ${idx}::uuid")
                params.append(workflow_id)
                idx += 1

            where = " AND ".join(where_clauses)

            rows = await conn.fetch(
                f"""
                SELECT
                    j.id AS job_id,
                    j.workflow_id,
                    j.workflow_name,
                    j.status,
                    j.filename,
                    j.file_count,
                    j.progress,
                    j.error,
                    j.created_at,
                    j.started_at,
                    j.completed_at,
                    j.cancelled_at,
                    EXTRACT(EPOCH FROM (j.completed_at - j.started_at)) * 1000 AS duration_ms
                FROM jobs j
                WHERE {where}
                ORDER BY j.created_at DESC
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *params, limit, offset,
            )

            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM jobs j WHERE {where}",
                *params,
            )

        entries = []
        for row in rows:
            entries.append({
                "job_id": str(row["job_id"]),
                "workflow_id": str(row["workflow_id"]) if row["workflow_id"] else None,
                "workflow_name": row["workflow_name"],
                "status": row["status"],
                "filename": row["filename"],
                "file_count": row["file_count"],
                "progress": row["progress"],
                "error": row["error"],
                "duration_ms": int(row["duration_ms"]) if row["duration_ms"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "cancelled_at": row["cancelled_at"].isoformat() if row["cancelled_at"] else None,
            })

        return {
            "entries": entries,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.warning("Failed to get audit log: %s", e)
        return {"entries": [], "total": 0, "error": str(e)}


async def get_dashboard_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get dashboard summary: health status across all workflows.

    Returns per-workflow stats + overall system health.
    """
    if _repo is None:
        return {"error": "Repository not configured"}

    try:
        pool = _repo._pool
        if not pool:
            return {"error": "Database not connected"}

        async with pool.acquire() as conn:
            # Per workflow summary
            workflow_rows = await conn.fetch(
                """
                SELECT
                    workflow_id,
                    workflow_name,
                    COUNT(*) AS total_jobs,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                    COUNT(*) FILTER (WHERE status = 'running') AS running,
                    COUNT(*) FILTER (WHERE status = 'queued') AS queued,
                    MAX(created_at) AS last_run,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)
                        FILTER (WHERE started_at IS NOT NULL AND completed_at IS NOT NULL)
                        AS avg_duration_ms
                FROM jobs
                WHERE created_at > NOW() - INTERVAL '1 day' * $1
                  AND workflow_id IS NOT NULL
                GROUP BY workflow_id, workflow_name
                ORDER BY total_jobs DESC
                LIMIT 50
                """,
                days,
            )

            # Overall system metrics
            system_row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total_jobs,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                    COUNT(*) FILTER (WHERE status = 'running') AS running,
                    COUNT(*) FILTER (WHERE status = 'queued') AS queued,
                    COUNT(DISTINCT workflow_id) AS unique_workflows
                FROM jobs
                WHERE created_at > NOW() - INTERVAL '1 day' * $1
                """,
                days,
            )

        workflows = []
        for row in workflow_rows:
            total = row["total_jobs"]
            completed = row["completed"]
            failed = row["failed"]
            success_rate = (completed / total * 100) if total > 0 else 0.0

            # Determine health status
            if failed / total > 0.3 if total > 0 else False:
                health = "critical"
            elif failed / total > 0.1 if total > 0 else False:
                health = "warning"
            else:
                health = "healthy"

            workflows.append({
                "workflow_id": str(row["workflow_id"]),
                "workflow_name": row["workflow_name"],
                "total_jobs": total,
                "completed": completed,
                "failed": failed,
                "running": row["running"],
                "queued": row["queued"],
                "success_rate": round(success_rate, 1),
                "health": health,
                "last_run": row["last_run"].isoformat() if row["last_run"] else None,
                "avg_duration_ms": int(row["avg_duration_ms"]) if row["avg_duration_ms"] else None,
            })

        total_jobs = system_row["total_jobs"] if system_row else 0
        total_completed = system_row["completed"] if system_row else 0
        total_failed = system_row["failed"] if system_row else 0

        return {
            "period_days": days,
            "system": {
                "total_jobs": total_jobs,
                "completed": total_completed,
                "failed": total_failed,
                "running": system_row["running"] if system_row else 0,
                "queued": system_row["queued"] if system_row else 0,
                "unique_workflows": system_row["unique_workflows"] if system_row else 0,
                "success_rate": round(total_completed / total_jobs * 100, 1) if total_jobs > 0 else 0.0,
                "health": "critical" if total_jobs > 0 and total_failed / total_jobs > 0.3
                    else "warning" if total_jobs > 0 and total_failed / total_jobs > 0.1
                    else "healthy",
            },
            "workflows": workflows,
        }
    except Exception as e:
        logger.warning("Failed to get dashboard summary: %s", e)
        return {"error": str(e)}
