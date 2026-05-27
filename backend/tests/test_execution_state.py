"""Tests for the Execution State service (feat-007).

Validates:
- Execution state creation and retrieval
- Node output saving (checkpointing)
- Context passing between nodes
- State lifecycle (running → completed/failed)
- Resume point tracking
- Completed node ID retrieval
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services import execution_state


class FakeRepository:
    """In-memory fake of WorkflowRepository for execution state methods."""

    def __init__(self):
        self._states = {}  # job_id → state dict
        self._counter = 0

    async def create_execution_state(self, job_id, workflow_id=None, retention_hours=72):
        self._counter += 1
        state = {
            "state_id": f"state-{self._counter}",
            "job_id": job_id,
            "workflow_id": workflow_id,
            "status": "running",
            "node_states": {},
            "context": {},
            "checkpoint_node": None,
            "resume_from": None,
            "retention_hours": retention_hours,
            "created_at": "2026-05-21T00:00:00Z",
            "updated_at": "2026-05-21T00:00:00Z",
        }
        self._states[job_id] = state
        return state

    async def get_execution_state(self, job_id):
        return self._states.get(job_id)

    async def update_execution_state(self, job_id, **kwargs):
        state = self._states.get(job_id)
        if state is None:
            return
        for key, value in kwargs.items():
            if value is not None and key in state:
                state[key] = value
        state["updated_at"] = "2026-05-21T01:00:00Z"

    async def save_node_output(self, job_id, node_id, output, node_status="completed", error=None, duration_ms=None):
        state = self._states.get(job_id)
        if state is None:
            return
        state["node_states"][node_id] = {
            "output": output,
            "status": node_status,
            "error": error,
            "duration_ms": duration_ms,
            "saved_at": "2026-05-21T00:01:00Z",
        }
        state["checkpoint_node"] = node_id

    async def save_context_data(self, job_id, key, value):
        state = self._states.get(job_id)
        if state is None:
            return
        state["context"][key] = value

    async def cleanup_execution_states(self):
        return 0


@pytest.fixture(autouse=True)
def setup_repo():
    """Set up a fake repository for each test."""
    repo = FakeRepository()
    execution_state.set_repository(repo)
    yield repo
    execution_state.set_repository(None)


class TestCreateState:
    """Test execution state creation."""

    @pytest.mark.asyncio
    async def test_create_state_returns_state(self, setup_repo):
        state = await execution_state.create_state("job-1", workflow_id="wf-1")
        assert state is not None
        assert state["job_id"] == "job-1"
        assert state["workflow_id"] == "wf-1"
        assert state["status"] == "running"
        assert state["node_states"] == {}
        assert state["context"] == {}

    @pytest.mark.asyncio
    async def test_create_state_without_repo(self):
        execution_state.set_repository(None)
        state = await execution_state.create_state("job-1")
        assert state is None


class TestNodeOutput:
    """Test saving and retrieving node outputs."""

    @pytest.mark.asyncio
    async def test_save_and_get_node_output(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.save_node_output(
            "job-1", "node-1", {"text": "hello"}, duration_ms=150
        )

        output = await execution_state.get_node_output("job-1", "node-1")
        assert output == {"text": "hello"}

    @pytest.mark.asyncio
    async def test_get_node_output_nonexistent(self, setup_repo):
        await execution_state.create_state("job-1")
        output = await execution_state.get_node_output("job-1", "nonexistent")
        assert output is None

    @pytest.mark.asyncio
    async def test_get_all_node_outputs(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.save_node_output("job-1", "n1", {"a": 1})
        await execution_state.save_node_output("job-1", "n2", {"b": 2})
        await execution_state.save_node_output(
            "job-1", "n3", None, status="failed", error="boom"
        )

        outputs = await execution_state.get_all_node_outputs("job-1")
        assert "n1" in outputs
        assert "n2" in outputs
        assert "n3" not in outputs  # failed nodes excluded

    @pytest.mark.asyncio
    async def test_save_node_output_updates_checkpoint(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.save_node_output("job-1", "node-a", {"x": 1})
        await execution_state.save_node_output("job-1", "node-b", {"y": 2})

        state = await execution_state.get_state("job-1")
        assert state["checkpoint_node"] == "node-b"


class TestContext:
    """Test shared context operations."""

    @pytest.mark.asyncio
    async def test_save_and_get_context(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.save_context("job-1", "doc_type", "invoice")
        await execution_state.save_context("job-1", "confidence", 0.95)

        context = await execution_state.get_context("job-1")
        assert context["doc_type"] == "invoice"
        assert context["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_get_context_empty(self, setup_repo):
        await execution_state.create_state("job-1")
        context = await execution_state.get_context("job-1")
        assert context == {}


class TestLifecycle:
    """Test state lifecycle transitions."""

    @pytest.mark.asyncio
    async def test_mark_completed(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.mark_completed("job-1")

        state = await execution_state.get_state("job-1")
        assert state["status"] == "completed"

    @pytest.mark.asyncio
    async def test_mark_failed_with_checkpoint(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.save_node_output("job-1", "n1", {"ok": True})
        await execution_state.mark_failed("job-1", checkpoint_node="n1")

        state = await execution_state.get_state("job-1")
        assert state["status"] == "failed"
        assert state["checkpoint_node"] == "n1"

    @pytest.mark.asyncio
    async def test_mark_cancelled(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.mark_cancelled("job-1")

        state = await execution_state.get_state("job-1")
        assert state["status"] == "cancelled"


class TestResume:
    """Test resume functionality."""

    @pytest.mark.asyncio
    async def test_set_resume_point(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.set_resume_point("job-1", "node-3")

        state = await execution_state.get_state("job-1")
        assert state["resume_from"] == "node-3"
        assert state["status"] == "resuming"

    @pytest.mark.asyncio
    async def test_get_resume_point(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.set_resume_point("job-1", "node-3")

        point = await execution_state.get_resume_point("job-1")
        assert point == "node-3"

    @pytest.mark.asyncio
    async def test_get_completed_node_ids(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.save_node_output("job-1", "n1", {"a": 1})
        await execution_state.save_node_output("job-1", "n2", {"b": 2})
        await execution_state.save_node_output(
            "job-1", "n3", None, status="failed", error="err"
        )

        completed = await execution_state.get_completed_node_ids("job-1")
        assert "n1" in completed
        assert "n2" in completed
        assert "n3" not in completed

    @pytest.mark.asyncio
    async def test_get_resume_point_from_checkpoint(self, setup_repo):
        await execution_state.create_state("job-1")
        await execution_state.save_node_output("job-1", "n1", {"a": 1})
        await execution_state.mark_failed("job-1", checkpoint_node="n1")

        point = await execution_state.get_resume_point("job-1")
        assert point == "n1"


class TestNoRepository:
    """Test graceful degradation when no repository is configured."""

    @pytest.fixture(autouse=True)
    def no_repo(self):
        execution_state.set_repository(None)
        yield

    @pytest.mark.asyncio
    async def test_get_state_returns_none(self):
        result = await execution_state.get_state("job-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_node_output_no_error(self):
        # Should not raise
        await execution_state.save_node_output("job-1", "n1", {"x": 1})

    @pytest.mark.asyncio
    async def test_get_context_returns_empty(self):
        result = await execution_state.get_context("job-1")
        assert result == {}

    @pytest.mark.asyncio
    async def test_mark_completed_no_error(self):
        await execution_state.mark_completed("job-1")

    @pytest.mark.asyncio
    async def test_cleanup_returns_zero(self):
        result = await execution_state.cleanup_expired_states()
        assert result == 0
