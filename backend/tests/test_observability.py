"""Tests for the Journey Observability system (feat-010).

Validates:
- Execution timeline retrieval
- Performance metrics aggregation
- Error analytics
- Audit log
- Dashboard summary
- Service initialization
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import observability


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_repo():
    """Reset the observability service repo between tests."""
    observability._repo = None
    yield
    observability._repo = None


@pytest.fixture
def mock_repo():
    """Create a mock repository with connection pool."""
    repo = MagicMock()
    repo._pool = MagicMock()
    return repo


# ---------------------------------------------------------------------------
# Service initialization
# ---------------------------------------------------------------------------


def test_set_repository():
    """set_repository stores the repo reference."""
    mock = MagicMock()
    observability.set_repository(mock)
    assert observability.get_repository() is mock


def test_get_repository_default_none():
    """get_repository returns None by default."""
    assert observability.get_repository() is None


# ---------------------------------------------------------------------------
# Execution Timeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_no_repo():
    """Returns None when no repo configured."""
    result = await observability.get_execution_timeline("fake-id")
    assert result is None


@pytest.mark.asyncio
async def test_timeline_job_not_found():
    """Returns None when job not found."""
    repo = MagicMock()
    repo.get_execution_state = AsyncMock(return_value=None)
    repo.get_job = AsyncMock(return_value=None)
    observability.set_repository(repo)

    result = await observability.get_execution_timeline("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_timeline_success():
    """Returns full timeline with per-node data."""
    now = datetime.now(timezone.utc)
    started = now - timedelta(seconds=10)
    completed = now

    repo = MagicMock()
    repo.get_execution_state = AsyncMock(return_value={
        "node_states": {
            "node-1": {"status": "completed", "duration_ms": 3000, "error": None, "saved_at": now.isoformat()},
            "node-2": {"status": "completed", "duration_ms": 5000, "error": None, "saved_at": now.isoformat()},
        }
    })
    repo.get_job = AsyncMock(return_value={
        "workflow_id": "wf-1",
        "workflow_name": "Test WF",
        "status": "completed",
        "started_at": started,
        "completed_at": completed,
        "nodes": [
            {"node_id": "node-1", "node_type": "parse", "node_label": "Parse Doc", "status": "completed"},
            {"node_id": "node-2", "node_type": "extract", "node_label": "Extract Data", "status": "completed"},
        ],
    })
    observability.set_repository(repo)

    result = await observability.get_execution_timeline("job-123")

    assert result is not None
    assert result["job_id"] == "job-123"
    assert result["workflow_name"] == "Test WF"
    assert result["status"] == "completed"
    assert result["total_duration_ms"] == 10000
    assert len(result["nodes"]) == 2
    assert result["nodes"][0]["duration_ms"] == 3000
    assert result["nodes"][1]["duration_ms"] == 5000


# ---------------------------------------------------------------------------
# Performance Metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_no_repo():
    """Returns error when no repo configured."""
    result = await observability.get_performance_metrics()
    assert "error" in result


@pytest.mark.asyncio
async def test_metrics_no_pool():
    """Returns error when pool not connected."""
    repo = MagicMock()
    repo._pool = None
    observability.set_repository(repo)

    result = await observability.get_performance_metrics()
    assert "error" in result


@pytest.mark.asyncio
async def test_metrics_success():
    """Returns aggregated metrics when DB is available."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={
        "total_jobs": 10,
        "completed_jobs": 8,
        "failed_jobs": 1,
        "cancelled_jobs": 1,
        "avg_duration_ms": 5000.0,
        "min_duration_ms": 1000.0,
        "max_duration_ms": 15000.0,
    })
    mock_conn.fetch = AsyncMock(return_value=[
        {
            "node_type": "parse",
            "execution_count": 10,
            "success_count": 9,
            "failure_count": 1,
            "avg_duration_ms": 3000,
            "min_duration_ms": 1000,
            "max_duration_ms": 8000,
        },
    ])

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncContextManager(mock_conn))

    repo = MagicMock()
    repo._pool = mock_pool
    observability.set_repository(repo)

    result = await observability.get_performance_metrics(days=7)

    assert "summary" in result
    assert result["summary"]["total_jobs"] == 10
    assert result["summary"]["success_rate"] == 80.0
    assert len(result["node_types"]) == 1
    assert result["node_types"][0]["node_type"] == "parse"


# ---------------------------------------------------------------------------
# Error Analytics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_errors_no_repo():
    """Returns error when no repo configured."""
    result = await observability.get_error_analytics()
    assert "error" in result


@pytest.mark.asyncio
async def test_errors_success():
    """Returns error analytics from DB."""
    now = datetime.now(timezone.utc)

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(side_effect=[
        # First call: top errors
        [
            {
                "node_type": "extract",
                "node_label": "Extract Fields",
                "error_message": "Model timeout",
                "occurrence_count": 5,
                "last_occurred": now,
            },
        ],
        # Second call: failure rates
        [
            {
                "node_type": "extract",
                "successes": 15,
                "failures": 5,
                "total": 20,
            },
        ],
    ])

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncContextManager(mock_conn))

    repo = MagicMock()
    repo._pool = mock_pool
    observability.set_repository(repo)

    result = await observability.get_error_analytics(days=7)

    assert "top_errors" in result
    assert len(result["top_errors"]) == 1
    assert result["top_errors"][0]["error_message"] == "Model timeout"
    assert result["failure_rates"][0]["failure_rate"] == 25.0


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_no_repo():
    """Returns empty when no repo configured."""
    result = await observability.get_audit_log()
    assert result["entries"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_audit_success():
    """Returns audit entries from DB."""
    import uuid
    now = datetime.now(timezone.utc)
    job_uuid = uuid.uuid4()

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[
        {
            "job_id": job_uuid,
            "workflow_id": None,
            "workflow_name": "Test Workflow",
            "status": "completed",
            "filename": "test.pdf",
            "file_count": 1,
            "progress": 1.0,
            "error": None,
            "created_at": now,
            "started_at": now - timedelta(seconds=5),
            "completed_at": now,
            "cancelled_at": None,
            "duration_ms": 5000,
        },
    ])
    mock_conn.fetchval = AsyncMock(return_value=1)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncContextManager(mock_conn))

    repo = MagicMock()
    repo._pool = mock_pool
    observability.set_repository(repo)

    result = await observability.get_audit_log(days=7)

    assert result["total"] == 1
    assert len(result["entries"]) == 1
    assert result["entries"][0]["workflow_name"] == "Test Workflow"
    assert result["entries"][0]["status"] == "completed"


# ---------------------------------------------------------------------------
# Dashboard Summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_no_repo():
    """Returns error when no repo configured."""
    result = await observability.get_dashboard_summary()
    assert "error" in result


@pytest.mark.asyncio
async def test_dashboard_success():
    """Returns dashboard summary with workflow health."""
    import uuid
    now = datetime.now(timezone.utc)
    wf_uuid = uuid.uuid4()

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[
        {
            "workflow_id": wf_uuid,
            "workflow_name": "OCR Pipeline",
            "total_jobs": 20,
            "completed": 18,
            "failed": 1,
            "running": 1,
            "queued": 0,
            "last_run": now,
            "avg_duration_ms": 4500.0,
        },
    ])
    mock_conn.fetchrow = AsyncMock(return_value={
        "total_jobs": 20,
        "completed": 18,
        "failed": 1,
        "running": 1,
        "queued": 0,
        "unique_workflows": 1,
    })

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncContextManager(mock_conn))

    repo = MagicMock()
    repo._pool = mock_pool
    observability.set_repository(repo)

    result = await observability.get_dashboard_summary(days=7)

    assert "system" in result
    assert result["system"]["total_jobs"] == 20
    assert result["system"]["health"] == "healthy"
    assert len(result["workflows"]) == 1
    assert result["workflows"][0]["workflow_name"] == "OCR Pipeline"
    assert result["workflows"][0]["health"] == "healthy"


@pytest.mark.asyncio
async def test_dashboard_critical_health():
    """Dashboard shows 'critical' when failure rate > 30%."""
    import uuid
    now = datetime.now(timezone.utc)
    wf_uuid = uuid.uuid4()

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[
        {
            "workflow_id": wf_uuid,
            "workflow_name": "Bad Pipeline",
            "total_jobs": 10,
            "completed": 5,
            "failed": 4,
            "running": 0,
            "queued": 1,
            "last_run": now,
            "avg_duration_ms": 2000.0,
        },
    ])
    mock_conn.fetchrow = AsyncMock(return_value={
        "total_jobs": 10,
        "completed": 5,
        "failed": 4,
        "running": 0,
        "queued": 1,
        "unique_workflows": 1,
    })

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncContextManager(mock_conn))

    repo = MagicMock()
    repo._pool = mock_pool
    observability.set_repository(repo)

    result = await observability.get_dashboard_summary(days=7)

    assert result["system"]["health"] == "critical"
    assert result["workflows"][0]["health"] == "critical"


# ---------------------------------------------------------------------------
# Helper: AsyncContextManager for mocking pool.acquire()
# ---------------------------------------------------------------------------


class AsyncContextManager:
    """Mock async context manager for pool.acquire()."""

    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass
