"""
Execution State Service — Persistent state management for workflow executions.

Provides:
- Create/read/update execution state per job
- Save per-node outputs (checkpoint after each node)
- Context passing between nodes (shared metadata)
- Resume from last checkpoint
- State cleanup based on retention policy

This is the core service for feat-007 (Journey Stateful Execution).
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Reference to the workflow repository (set during startup)
_repo = None


def set_repository(repo) -> None:
    """Set the workflow repository. Called during app startup."""
    global _repo
    _repo = repo


def get_repository():
    """Get the workflow repository."""
    return _repo


async def create_state(
    job_id: str,
    workflow_id: Optional[str] = None,
    retention_hours: int = 72,
) -> Optional[Dict[str, Any]]:
    """
    Create a new execution state for a job.

    Called when a job starts executing. The state persists node outputs
    and shared context throughout the execution lifecycle.
    """
    if _repo is None:
        logger.debug("No repository configured, execution state disabled")
        return None

    try:
        state = await _repo.create_execution_state(
            job_id=job_id,
            workflow_id=workflow_id,
            retention_hours=retention_hours,
        )
        logger.debug("Created execution state for job %s", job_id)
        return state
    except Exception as e:
        logger.warning("Failed to create execution state for job %s: %s", job_id, e)
        return None


async def get_state(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the execution state for a job.

    Returns the full state including all node outputs and shared context.
    """
    if _repo is None:
        return None

    try:
        return await _repo.get_execution_state(job_id)
    except Exception as e:
        logger.warning("Failed to get execution state for job %s: %s", job_id, e)
        return None


async def save_node_output(
    job_id: str,
    node_id: str,
    output: Any,
    status: str = "completed",
    error: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> None:
    """
    Save a node's output to the execution state (checkpoint).

    This is called after each node completes successfully or fails.
    Subsequent nodes can read this output via get_node_output().
    """
    if _repo is None:
        return

    try:
        await _repo.save_node_output(
            job_id=job_id,
            node_id=node_id,
            output=output,
            node_status=status,
            error=error,
            duration_ms=duration_ms,
        )
        logger.debug("Saved output for node %s in job %s", node_id, job_id)
    except Exception as e:
        logger.warning(
            "Failed to save node output for %s in job %s: %s", node_id, job_id, e
        )


async def get_node_output(job_id: str, node_id: str) -> Optional[Any]:
    """
    Get a specific node's output from the execution state.

    Used by subsequent nodes to read upstream outputs (context passing).
    """
    state = await get_state(job_id)
    if state is None:
        return None

    node_data = state.get("node_states", {}).get(node_id)
    if node_data is None:
        return None

    return node_data.get("output")


async def get_all_node_outputs(job_id: str) -> Dict[str, Any]:
    """
    Get all node outputs for a job.

    Returns a dict mapping node_id → output data.
    """
    state = await get_state(job_id)
    if state is None:
        return {}

    node_states = state.get("node_states", {})
    return {
        node_id: data.get("output")
        for node_id, data in node_states.items()
        if data.get("status") == "completed"
    }


async def save_context(job_id: str, key: str, value: Any) -> None:
    """
    Save a key-value pair to the shared execution context.

    Context is shared across all nodes in the execution.
    Use for metadata like extracted document type, confidence scores, etc.
    """
    if _repo is None:
        return

    try:
        await _repo.save_context_data(job_id, key, value)
    except Exception as e:
        logger.warning("Failed to save context for job %s: %s", job_id, e)


async def get_context(job_id: str) -> Dict[str, Any]:
    """Get the shared execution context for a job."""
    state = await get_state(job_id)
    if state is None:
        return {}
    return state.get("context", {})


async def mark_completed(job_id: str) -> None:
    """Mark execution state as completed."""
    if _repo is None:
        return
    try:
        await _repo.update_execution_state(job_id, status="completed")
    except Exception as e:
        logger.warning("Failed to mark state completed for job %s: %s", job_id, e)


async def mark_failed(job_id: str, checkpoint_node: Optional[str] = None) -> None:
    """
    Mark execution state as failed, recording the checkpoint node.

    The checkpoint_node is the last node that completed successfully,
    enabling resume from the next node.
    """
    if _repo is None:
        return
    try:
        await _repo.update_execution_state(
            job_id, status="failed", checkpoint_node=checkpoint_node
        )
    except Exception as e:
        logger.warning("Failed to mark state failed for job %s: %s", job_id, e)


async def mark_cancelled(job_id: str) -> None:
    """Mark execution state as cancelled."""
    if _repo is None:
        return
    try:
        await _repo.update_execution_state(job_id, status="cancelled")
    except Exception as e:
        logger.warning("Failed to mark state cancelled for job %s: %s", job_id, e)


async def set_resume_point(job_id: str, node_id: str) -> None:
    """
    Set the resume point for a failed job.

    When resume is triggered, execution will start from this node.
    """
    if _repo is None:
        return
    try:
        await _repo.update_execution_state(job_id, resume_from=node_id, status="resuming")
    except Exception as e:
        logger.warning("Failed to set resume point for job %s: %s", job_id, e)


async def get_resume_point(job_id: str) -> Optional[str]:
    """
    Get the node ID to resume from.

    Returns the node_id where execution should restart, or None.
    """
    state = await get_state(job_id)
    if state is None:
        return None

    # If explicitly set, use resume_from
    if state.get("resume_from"):
        return state["resume_from"]

    # Otherwise, find the first failed/pending node after checkpoint
    checkpoint = state.get("checkpoint_node")
    if checkpoint is None:
        return None

    # The resume point is the node AFTER the checkpoint
    # (caller needs to determine this from the workflow graph)
    return checkpoint


async def get_completed_node_ids(job_id: str) -> List[str]:
    """
    Get list of node IDs that completed successfully.

    Used during resume to skip already-completed nodes.
    """
    state = await get_state(job_id)
    if state is None:
        return []

    node_states = state.get("node_states", {})
    return [
        node_id
        for node_id, data in node_states.items()
        if data.get("status") == "completed"
    ]


async def cleanup_expired_states() -> int:
    """Clean up execution states past their retention period."""
    if _repo is None:
        return 0
    try:
        return await _repo.cleanup_execution_states()
    except Exception as e:
        logger.warning("Failed to cleanup execution states: %s", e)
        return 0
