"""
Job Persistence — Bridges in-memory job_queue with PostgreSQL storage.

Hooks into the job_event_bus to persist:
- Job state changes (create, start, complete, fail, cancel) → jobs table
- Node-level events → job_logs table

Also provides the auto-cleanup scheduler.
"""

import asyncio
import logging
from typing import Optional

from services.job_events import JobEvent
from services.job_queue import job_queue

logger = logging.getLogger(__name__)

# Reference to the workflow repository (set during startup)
_repo = None
_cleanup_task: Optional[asyncio.Task] = None
_listener_task: Optional[asyncio.Task] = None


def set_repository(repo) -> None:
    """Set the workflow repository for persistence. Called during app startup."""
    global _repo
    _repo = repo


async def start_persistence() -> None:
    """Start the persistence listener and cleanup scheduler."""
    global _listener_task, _cleanup_task

    if _repo is None:
        logger.warning("Job persistence: no repository configured, skipping")
        return

    # Start event listener
    _listener_task = asyncio.create_task(_event_listener(), name="job-persistence-listener")

    # Start cleanup scheduler
    _cleanup_task = asyncio.create_task(_cleanup_scheduler(), name="job-cleanup-scheduler")

    logger.info("Job persistence started (listener + cleanup scheduler)")


async def stop_persistence() -> None:
    """Stop the persistence listener and cleanup scheduler."""
    global _listener_task, _cleanup_task

    if _listener_task:
        _listener_task.cancel()
        _listener_task = None

    if _cleanup_task:
        _cleanup_task.cancel()
        _cleanup_task = None

    logger.info("Job persistence stopped")


# ---------------------------------------------------------------------------
# Event Listener — subscribes to ALL job events and persists them
# ---------------------------------------------------------------------------

async def _event_listener() -> None:
    """
    Listen to all job events and persist to PostgreSQL.

    This subscribes to a special "all jobs" channel on the event bus.
    """
    logger.debug("Job persistence listener started")

    while True:
        try:
            # Poll all jobs in the queue and sync their state
            # We use a different approach: hook into job_queue state changes
            # by periodically syncing active jobs
            await asyncio.sleep(2)  # Sync every 2 seconds

            if _repo is None:
                continue

            # Get all jobs from in-memory queue
            result = await job_queue.list_jobs(limit=100)
            jobs = result.get("jobs", [])

            for job in jobs:
                try:
                    # Check if job exists in DB
                    existing = await _repo.get_job(job.job_id)

                    if existing is None:
                        # Create in DB
                        nodes_data = [
                            {
                                "node_id": n.node_id,
                                "node_type": n.node_type,
                                "node_label": n.node_label,
                                "status": n.status if isinstance(n.status, str) else n.status.value,
                                "retry_count": n.retry_count,
                                "error": n.error,
                            }
                            for n in job.nodes
                        ]
                        await _repo.create_job(
                            workflow_id=job.workflow_id,
                            workflow_name=job.workflow_name,
                            nodes_data=nodes_data,
                            filename=job.filename,
                            file_count=job.file_count,
                            max_retries=job.max_retries,
                        )
                        # Update the ID to match in-memory
                        await _repo.update_job(
                            job_id=job.job_id,
                            status=job.status if isinstance(job.status, str) else job.status.value,
                            progress=job.progress,
                        )
                    else:
                        # Update existing
                        status = job.status if isinstance(job.status, str) else job.status.value
                        nodes_data = [
                            {
                                "node_id": n.node_id,
                                "node_type": n.node_type,
                                "node_label": n.node_label,
                                "status": n.status if isinstance(n.status, str) else n.status.value,
                                "retry_count": n.retry_count,
                                "error": n.error,
                            }
                            for n in job.nodes
                        ]

                        await _repo.update_job(
                            job_id=job.job_id,
                            status=status,
                            progress=job.progress,
                            nodes_data=nodes_data,
                            error=job.error,
                            started_at=job.started_at,
                            completed_at=job.completed_at,
                            cancelled_at=job.cancelled_at,
                        )
                except Exception as e:
                    logger.debug("Failed to sync job %s: %s", job.job_id, e)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("Job persistence listener error: %s", e)
            await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# Log Persistence — called by event bus subscribers
# ---------------------------------------------------------------------------

async def persist_job_event(event: JobEvent) -> None:
    """Persist a single job event to the job_logs table."""
    if _repo is None:
        return

    try:
        await _repo.add_job_log(
            job_id=event.job_id,
            event_type=event.event_type.value if hasattr(event.event_type, 'value') else event.event_type,
            node_id=event.data.get("node_id"),
            node_type=event.data.get("node_type"),
            node_label=event.data.get("node_label"),
            data=event.data,
        )
    except Exception as e:
        logger.debug("Failed to persist job event: %s", e)


# ---------------------------------------------------------------------------
# Cleanup Scheduler — runs every 60s, removes old completed jobs
# ---------------------------------------------------------------------------

CLEANUP_INTERVAL_SECONDS = 60
CLEANUP_MAX_AGE_HOURS = 24  # Keep jobs for 24 hours after completion


async def _cleanup_scheduler() -> None:
    """Periodically clean up old completed/failed/cancelled jobs."""
    logger.debug("Job cleanup scheduler started (interval=%ds, max_age=%dh)",
                 CLEANUP_INTERVAL_SECONDS, CLEANUP_MAX_AGE_HOURS)

    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

            if _repo is None:
                continue

            # Clean up DB
            deleted = await _repo.delete_old_jobs(older_than_hours=CLEANUP_MAX_AGE_HOURS)
            if deleted > 0:
                logger.info("Cleanup: removed %d old jobs from database", deleted)

            # Clean up in-memory queue
            removed = job_queue.cleanup_expired(ttl_seconds=CLEANUP_MAX_AGE_HOURS * 3600)
            if removed > 0:
                logger.info("Cleanup: removed %d expired jobs from memory", removed)

            # Clean up expired execution states (feat-007)
            from services import execution_state
            cleaned = await execution_state.cleanup_expired_states()
            if cleaned > 0:
                logger.info("Cleanup: cleaned %d expired execution states", cleaned)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("Cleanup scheduler error: %s", e)
            await asyncio.sleep(30)
