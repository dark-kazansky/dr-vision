"""
In-memory job store for background processing tasks.

Moved from core/background_tasks.py to services/job_manager.py as part of the
Langflow-inspired architecture migration.

Provides job creation, status polling, and result retrieval for
long-running document processing operations.

Requirements: 21.1, 21.2, 21.3
"""

import time
import uuid
import threading
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class JobManager:
    """
    In-memory job store for background processing tasks.

    Thread-safe via a reentrant lock so that route handlers and
    background threads can safely read/write job state concurrently.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_job(self) -> str:
        """Create a new job and return its unique ID."""
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "pending",
                "progress": None,
                "result": None,
                "error": None,
                "created_at": time.time(),
                "completed_at": None,
            }
        logger.info("Created background job %s", job_id)
        return job_id

    def update_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[float] = None,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        """Update the status of an existing job.

        Args:
            job_id: The job identifier.
            status: One of ``pending``, ``processing``, ``completed``, ``failed``.
            progress: Optional progress value between 0.0 and 1.0.
            result: Optional result payload (set on completion).
            error: Optional error message (set on failure).
        """
        with self._lock:
            if job_id not in self._jobs:
                logger.warning("update_status called for unknown job %s", job_id)
                return
            job = self._jobs[job_id]
            job["status"] = status
            if progress is not None:
                job["progress"] = progress
            if result is not None:
                job["result"] = result
            if error is not None:
                job["error"] = error
            if status in ("completed", "failed"):
                job["completed_at"] = time.time()

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return the status dict for a job, or ``None`` if not found."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                "job_id": job["job_id"],
                "status": job["status"],
                "progress": job["progress"],
                "created_at": job["created_at"],
                "completed_at": job["completed_at"],
            }

    def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return the full job dict including result/error, or ``None``."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return dict(job)

    def cleanup_expired(self, ttl_seconds: int = 3600) -> int:
        """Remove completed/failed jobs older than *ttl_seconds*.

        Returns the number of jobs removed.
        """
        now = time.time()
        removed = 0
        with self._lock:
            expired = [
                jid
                for jid, job in self._jobs.items()
                if job["status"] in ("completed", "failed")
                and job["completed_at"] is not None
                and (now - job["completed_at"]) > ttl_seconds
            ]
            for jid in expired:
                del self._jobs[jid]
                removed += 1
        if removed:
            logger.info("Cleaned up %d expired background jobs", removed)
        return removed


# Module-level singleton so routes and background threads share state.
job_manager = JobManager()
