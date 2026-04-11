"""Tests for background task support (Task 9.4).

Validates Requirements 21.1, 21.2, 21.3:
- Backend accepts heavy requests and returns a job ID immediately
- /job/{job_id}/status endpoint provides progress polling
- /job/{job_id}/result endpoint returns completed results
"""

import time
import pytest

from core.background_tasks import JobManager


@pytest.fixture
def manager():
    """Return a fresh JobManager for each test."""
    return JobManager()


class TestJobManagerLifecycle:
    """Test the full create → update → status → result lifecycle."""

    def test_create_job_returns_unique_ids(self, manager):
        ids = {manager.create_job() for _ in range(50)}
        assert len(ids) == 50

    def test_new_job_has_pending_status(self, manager):
        job_id = manager.create_job()
        status = manager.get_status(job_id)
        assert status is not None
        assert status["status"] == "pending"
        assert status["progress"] is None
        assert status["completed_at"] is None

    def test_update_status_to_processing(self, manager):
        job_id = manager.create_job()
        manager.update_status(job_id, "processing", progress=0.3)
        status = manager.get_status(job_id)
        assert status["status"] == "processing"
        assert status["progress"] == 0.3

    def test_update_status_to_completed_with_result(self, manager):
        job_id = manager.create_job()
        manager.update_status(job_id, "completed", progress=1.0, result={"text": "hello"})
        result = manager.get_result(job_id)
        assert result["status"] == "completed"
        assert result["result"] == {"text": "hello"}
        assert result["completed_at"] is not None

    def test_update_status_to_failed_with_error(self, manager):
        job_id = manager.create_job()
        manager.update_status(job_id, "failed", error="something broke")
        result = manager.get_result(job_id)
        assert result["status"] == "failed"
        assert result["error"] == "something broke"
        assert result["completed_at"] is not None

    def test_get_status_unknown_job_returns_none(self, manager):
        assert manager.get_status("nonexistent") is None

    def test_get_result_unknown_job_returns_none(self, manager):
        assert manager.get_result("nonexistent") is None

    def test_update_status_unknown_job_is_noop(self, manager):
        # Should not raise
        manager.update_status("nonexistent", "completed")


class TestJobManagerCleanup:
    """Test expired job cleanup."""

    def test_cleanup_removes_old_completed_jobs(self, manager):
        job_id = manager.create_job()
        manager.update_status(job_id, "completed", result="done")
        # Manually backdate the completed_at timestamp
        with manager._lock:
            manager._jobs[job_id]["completed_at"] = time.time() - 7200
        removed = manager.cleanup_expired(ttl_seconds=3600)
        assert removed == 1
        assert manager.get_status(job_id) is None

    def test_cleanup_keeps_recent_completed_jobs(self, manager):
        job_id = manager.create_job()
        manager.update_status(job_id, "completed", result="done")
        removed = manager.cleanup_expired(ttl_seconds=3600)
        assert removed == 0
        assert manager.get_status(job_id) is not None

    def test_cleanup_keeps_pending_jobs(self, manager):
        job_id = manager.create_job()
        removed = manager.cleanup_expired(ttl_seconds=0)
        assert removed == 0
        assert manager.get_status(job_id) is not None
