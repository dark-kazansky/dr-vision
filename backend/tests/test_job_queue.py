"""Tests for the Journey Job Queue system (feat-006).

Validates:
- Job submission and lifecycle (queued → running → completed/failed/cancelled)
- Per-node progress tracking
- Cancellation mechanism
- Job timeout
- Queue ordering and concurrency
- Retry logic
- Job listing with filters
- Cleanup of expired jobs
"""

import asyncio
import pytest
import pytest_asyncio

from services.job_queue import JobQueue, JobRecord, JobStatus, NodeStatus


@pytest_asyncio.fixture
async def queue():
    """Create a fresh JobQueue for each test."""
    q = JobQueue(max_concurrent=2)
    yield q
    # Ensure stopped after test
    if q._started:
        await q.stop()


@pytest_asyncio.fixture
async def started_queue():
    """Create and start a JobQueue for tests that need workers running."""
    q = JobQueue(max_concurrent=2)

    async def noop_executor(job: JobRecord, queue: JobQueue) -> None:
        """No-op executor for basic lifecycle tests."""
        pass

    q.set_executor(noop_executor)
    await q.start()
    yield q
    await q.stop()


class TestJobSubmission:
    """Test job creation and initial state."""

    @pytest.mark.asyncio
    async def test_submit_returns_job_record(self, queue):
        job = await queue.submit(
            workflow_name="Test Workflow",
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
            filename="test.pdf",
        )
        assert job.job_id
        assert job.status == JobStatus.QUEUED
        assert job.progress == 0.0
        assert job.workflow_name == "Test Workflow"
        assert job.filename == "test.pdf"
        assert len(job.nodes) == 1
        assert job.nodes[0].node_id == "n1"
        assert job.nodes[0].node_type == "parse"
        assert job.nodes[0].status == NodeStatus.PENDING

    @pytest.mark.asyncio
    async def test_submit_generates_unique_ids(self, queue):
        jobs = [await queue.submit(nodes=[{"id": f"n{i}", "type": "parse", "label": "P"}]) for i in range(10)]
        ids = {j.job_id for j in jobs}
        assert len(ids) == 10

    @pytest.mark.asyncio
    async def test_submit_with_multiple_nodes(self, queue):
        nodes = [
            {"id": "n1", "type": "parse", "label": "Parse"},
            {"id": "n2", "type": "classify", "label": "Classify"},
            {"id": "n3", "type": "extract", "label": "Extract"},
        ]
        job = await queue.submit(nodes=nodes)
        assert len(job.nodes) == 3
        assert job.nodes[0].node_type == "parse"
        assert job.nodes[1].node_type == "classify"
        assert job.nodes[2].node_type == "extract"

    @pytest.mark.asyncio
    async def test_submit_with_custom_max_retries(self, queue):
        job = await queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "P"}],
            max_retries=5,
        )
        assert job.max_retries == 5

    @pytest.mark.asyncio
    async def test_submit_with_timeout(self, queue):
        job = await queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "P"}],
            timeout_seconds=60,
        )
        assert job.timeout_seconds == 60

    @pytest.mark.asyncio
    async def test_default_timeout_is_300(self, queue):
        job = await queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "P"}],
        )
        assert job.timeout_seconds == 300


class TestJobLifecycle:
    """Test job state transitions."""

    @pytest.mark.asyncio
    async def test_job_transitions_to_running(self, started_queue):
        job = await started_queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
        )
        # Wait for worker to pick it up
        await asyncio.sleep(0.1)
        updated = await started_queue.get_job(job.job_id)
        assert updated is not None
        # Should be completed since noop executor finishes immediately
        assert updated.status in (JobStatus.RUNNING, JobStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_job_completes_after_execution(self, started_queue):
        job = await started_queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
        )
        await asyncio.sleep(0.2)
        updated = await started_queue.get_job(job.job_id)
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED
        assert updated.progress == 1.0
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_job_fails_on_executor_error(self):
        q = JobQueue(max_concurrent=1)

        async def failing_executor(job: JobRecord, queue: JobQueue) -> None:
            raise RuntimeError("Something went wrong")

        q.set_executor(failing_executor)
        await q.start()

        try:
            job = await q.submit(
                nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
            )
            await asyncio.sleep(0.2)
            updated = await q.get_job(job.job_id)
            assert updated is not None
            assert updated.status == JobStatus.FAILED
            assert "Something went wrong" in (updated.error or "")
        finally:
            await q.stop()


class TestJobCancellation:
    """Test cancellation mechanism."""

    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, queue):
        # Don't start workers so job stays queued
        job = await queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
        )
        success = await queue.cancel(job.job_id)
        assert success is True
        updated = await queue.get_job(job.job_id)
        assert updated is not None
        assert updated.status == JobStatus.CANCELLED
        assert updated.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_running_job(self):
        q = JobQueue(max_concurrent=1)

        async def slow_executor(job: JobRecord, queue: JobQueue) -> None:
            for i in range(10):
                if queue.is_cancelled(job.job_id):
                    return
                await asyncio.sleep(0.05)

        q.set_executor(slow_executor)
        await q.start()

        try:
            job = await q.submit(
                nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
            )
            await asyncio.sleep(0.1)  # Let it start
            success = await q.cancel(job.job_id)
            assert success is True
            await asyncio.sleep(0.2)  # Let cancellation propagate
            updated = await q.get_job(job.job_id)
            assert updated is not None
            assert updated.status == JobStatus.CANCELLED
        finally:
            await q.stop()

    @pytest.mark.asyncio
    async def test_cancel_completed_job_returns_false(self, started_queue):
        job = await started_queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
        )
        await asyncio.sleep(0.2)  # Let it complete
        success = await started_queue.cancel(job.job_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job_returns_false(self, queue):
        success = await queue.cancel("nonexistent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_is_cancelled_returns_correct_state(self, queue):
        job = await queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
        )
        assert queue.is_cancelled(job.job_id) is False
        await queue.cancel(job.job_id)
        assert queue.is_cancelled(job.job_id) is True


class TestJobTimeout:
    """Test job timeout mechanism."""

    @pytest.mark.asyncio
    async def test_job_times_out(self):
        q = JobQueue(max_concurrent=1)

        async def forever_executor(job: JobRecord, queue: JobQueue) -> None:
            await asyncio.sleep(999)  # Will be interrupted by timeout

        q.set_executor(forever_executor)
        await q.start()

        try:
            job = await q.submit(
                nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
                timeout_seconds=1,  # 1 second timeout
            )
            await asyncio.sleep(1.5)  # Wait for timeout
            updated = await q.get_job(job.job_id)
            assert updated is not None
            assert updated.status == JobStatus.FAILED
            assert "timed out" in (updated.error or "").lower()
        finally:
            await q.stop()


class TestNodeProgress:
    """Test per-node progress tracking."""

    @pytest.mark.asyncio
    async def test_update_node_status_to_running(self, queue):
        job = await queue.submit(
            nodes=[
                {"id": "n1", "type": "parse", "label": "Parse"},
                {"id": "n2", "type": "classify", "label": "Classify"},
            ],
        )
        await queue.update_node_status(job.job_id, "n1", NodeStatus.RUNNING)
        updated = await queue.get_job(job.job_id)
        assert updated is not None
        assert updated.nodes[0].status == NodeStatus.RUNNING
        assert updated.nodes[0].started_at is not None
        assert updated.nodes[1].status == NodeStatus.PENDING

    @pytest.mark.asyncio
    async def test_update_node_status_to_completed(self, queue):
        job = await queue.submit(
            nodes=[
                {"id": "n1", "type": "parse", "label": "Parse"},
                {"id": "n2", "type": "classify", "label": "Classify"},
            ],
        )
        await queue.update_node_status(job.job_id, "n1", NodeStatus.COMPLETED)
        updated = await queue.get_job(job.job_id)
        assert updated is not None
        assert updated.nodes[0].status == NodeStatus.COMPLETED
        assert updated.nodes[0].completed_at is not None
        # Progress should be 50% (1 of 2 nodes done)
        assert updated.progress == 0.5

    @pytest.mark.asyncio
    async def test_update_node_status_with_error(self, queue):
        job = await queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
        )
        await queue.update_node_status(
            job.job_id, "n1", NodeStatus.FAILED, error="Parse failed"
        )
        updated = await queue.get_job(job.job_id)
        assert updated is not None
        assert updated.nodes[0].status == NodeStatus.FAILED
        assert updated.nodes[0].error == "Parse failed"

    @pytest.mark.asyncio
    async def test_update_node_retry(self, queue):
        job = await queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
        )
        await queue.update_node_retry(job.job_id, "n1")
        updated = await queue.get_job(job.job_id)
        assert updated is not None
        assert updated.nodes[0].retry_count == 1
        assert updated.nodes[0].status == NodeStatus.RETRYING

    @pytest.mark.asyncio
    async def test_progress_calculation(self, queue):
        job = await queue.submit(
            nodes=[
                {"id": "n1", "type": "parse", "label": "Parse"},
                {"id": "n2", "type": "classify", "label": "Classify"},
                {"id": "n3", "type": "extract", "label": "Extract"},
            ],
        )
        # Complete first node
        await queue.update_node_status(job.job_id, "n1", NodeStatus.COMPLETED)
        updated = await queue.get_job(job.job_id)
        assert updated is not None
        assert abs(updated.progress - 1 / 3) < 0.01

        # Complete second node
        await queue.update_node_status(job.job_id, "n2", NodeStatus.COMPLETED)
        updated = await queue.get_job(job.job_id)
        assert updated is not None
        assert abs(updated.progress - 2 / 3) < 0.01

        # Skip third node
        await queue.update_node_status(job.job_id, "n3", NodeStatus.SKIPPED)
        updated = await queue.get_job(job.job_id)
        assert updated is not None
        assert updated.progress == 1.0


class TestJobListing:
    """Test job listing with filters and pagination."""

    @pytest.mark.asyncio
    async def test_list_all_jobs(self, queue):
        await queue.submit(workflow_name="Job 1", nodes=[{"id": "n1", "type": "parse", "label": "P"}])
        await queue.submit(workflow_name="Job 2", nodes=[{"id": "n2", "type": "parse", "label": "P"}])
        await queue.submit(workflow_name="Job 3", nodes=[{"id": "n3", "type": "parse", "label": "P"}])

        result = await queue.list_jobs()
        assert result["total"] == 3
        assert len(result["jobs"]) == 3

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_status(self, queue):
        job1 = await queue.submit(workflow_name="Job 1", nodes=[{"id": "n1", "type": "parse", "label": "P"}])
        await queue.submit(workflow_name="Job 2", nodes=[{"id": "n2", "type": "parse", "label": "P"}])

        # Cancel first job
        await queue.cancel(job1.job_id)

        result = await queue.list_jobs(status="cancelled")
        assert result["total"] == 1
        assert result["jobs"][0].job_id == job1.job_id

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_workflow_id(self, queue):
        await queue.submit(workflow_id="wf-1", nodes=[{"id": "n1", "type": "parse", "label": "P"}])
        await queue.submit(workflow_id="wf-2", nodes=[{"id": "n2", "type": "parse", "label": "P"}])
        await queue.submit(workflow_id="wf-1", nodes=[{"id": "n3", "type": "parse", "label": "P"}])

        result = await queue.list_jobs(workflow_id="wf-1")
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, queue):
        for i in range(5):
            await queue.submit(workflow_name=f"Job {i}", nodes=[{"id": f"n{i}", "type": "parse", "label": "P"}])

        result = await queue.list_jobs(limit=2, offset=0)
        assert len(result["jobs"]) == 2
        assert result["total"] == 5

        result2 = await queue.list_jobs(limit=2, offset=2)
        assert len(result2["jobs"]) == 2

    @pytest.mark.asyncio
    async def test_list_jobs_sorted_newest_first(self, queue):
        job1 = await queue.submit(workflow_name="First", nodes=[{"id": "n1", "type": "parse", "label": "P"}])
        await asyncio.sleep(0.01)
        job2 = await queue.submit(workflow_name="Second", nodes=[{"id": "n2", "type": "parse", "label": "P"}])

        result = await queue.list_jobs()
        assert result["jobs"][0].job_id == job2.job_id
        assert result["jobs"][1].job_id == job1.job_id


class TestJobCleanup:
    """Test expired job cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_completed_jobs(self, started_queue):
        job = await started_queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
        )
        await asyncio.sleep(0.2)  # Let it complete

        # Verify it completed
        updated = await started_queue.get_job(job.job_id)
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED

        # Cleanup with 0 TTL should remove it
        removed = started_queue.cleanup_expired(ttl_seconds=0)
        assert removed == 1
        assert await started_queue.get_job(job.job_id) is None

    @pytest.mark.asyncio
    async def test_cleanup_keeps_active_jobs(self, queue):
        job = await queue.submit(
            nodes=[{"id": "n1", "type": "parse", "label": "Parse"}],
        )
        # Job is still queued
        removed = queue.cleanup_expired(ttl_seconds=0)
        assert removed == 0
        assert await queue.get_job(job.job_id) is not None


class TestQueueConcurrency:
    """Test concurrent job processing."""

    @pytest.mark.asyncio
    async def test_max_concurrent_jobs(self):
        q = JobQueue(max_concurrent=2)
        running_count = 0
        max_running = 0
        lock = asyncio.Lock()

        async def tracking_executor(job: JobRecord, queue: JobQueue) -> None:
            nonlocal running_count, max_running
            async with lock:
                running_count += 1
                max_running = max(max_running, running_count)
            await asyncio.sleep(0.1)
            async with lock:
                running_count -= 1

        q.set_executor(tracking_executor)
        await q.start()

        try:
            # Submit 4 jobs
            for i in range(4):
                await q.submit(nodes=[{"id": f"n{i}", "type": "parse", "label": "P"}])

            # Wait for all to complete
            await asyncio.sleep(0.5)

            # Max concurrent should not exceed 2
            assert max_running <= 2
        finally:
            await q.stop()

    @pytest.mark.asyncio
    async def test_fifo_ordering(self):
        q = JobQueue(max_concurrent=1)
        execution_order = []

        async def order_tracking_executor(job: JobRecord, queue: JobQueue) -> None:
            execution_order.append(job.workflow_name)
            await asyncio.sleep(0.05)

        q.set_executor(order_tracking_executor)
        await q.start()

        try:
            await q.submit(workflow_name="first", nodes=[{"id": "n1", "type": "parse", "label": "P"}])
            await q.submit(workflow_name="second", nodes=[{"id": "n2", "type": "parse", "label": "P"}])
            await q.submit(workflow_name="third", nodes=[{"id": "n3", "type": "parse", "label": "P"}])

            await asyncio.sleep(0.5)

            assert execution_order == ["first", "second", "third"]
        finally:
            await q.stop()
