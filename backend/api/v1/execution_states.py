"""
Execution State API router (feat-007).

Endpoints:
- GET    /api/v1/jobs/{job_id}/state       — Get execution state for a job
- GET    /api/v1/jobs/{job_id}/state/nodes  — Get all node outputs
- GET    /api/v1/jobs/{job_id}/state/nodes/{node_id} — Get specific node output
- GET    /api/v1/jobs/{job_id}/state/context — Get shared context
- POST   /api/v1/jobs/{job_id}/resume      — Resume a failed job from checkpoint
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services import execution_state
from services.job_queue import job_queue, JobStatus
from services.job_executor import store_job_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Execution State"])


@router.get("/jobs/{job_id}/state")
async def get_execution_state(job_id: str):
    """
    Get the full execution state for a job.

    Returns node outputs, shared context, checkpoint info, and status.
    Use this to display the State Viewer UI.
    """
    state = await execution_state.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"No execution state found for job {job_id}",
        )
    return state


@router.get("/jobs/{job_id}/state/nodes")
async def get_all_node_outputs(job_id: str):
    """
    Get all completed node outputs for a job.

    Returns a dict mapping node_id → output data.
    Only includes nodes that completed successfully.
    """
    outputs = await execution_state.get_all_node_outputs(job_id)
    return {"job_id": job_id, "node_outputs": outputs}


@router.get("/jobs/{job_id}/state/nodes/{node_id}")
async def get_node_output(job_id: str, node_id: str):
    """
    Get a specific node's output from the execution state.

    Returns the full output data for the specified node.
    """
    state = await execution_state.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"No execution state found for job {job_id}",
        )

    node_data = state.get("node_states", {}).get(node_id)
    if node_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No state found for node {node_id} in job {job_id}",
        )

    return {
        "job_id": job_id,
        "node_id": node_id,
        **node_data,
    }


@router.get("/jobs/{job_id}/state/context")
async def get_execution_context(job_id: str):
    """
    Get the shared execution context for a job.

    Context contains metadata shared across all nodes (e.g., document type,
    extracted fields, confidence scores).
    """
    context = await execution_state.get_context(job_id)
    return {"job_id": job_id, "context": context}


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    file: UploadFile = File(...),
    node_id: Optional[str] = Form(None),
):
    """
    Resume a failed job from its checkpoint or a specified node.

    If node_id is provided, execution resumes from that specific node.
    Otherwise, it resumes from the node after the last checkpoint.

    The file must be re-uploaded since the original may have been cleaned up.
    Returns a new job_id for the resumed execution (inherits state from original).
    """
    # Verify original job exists and is in a resumable state
    original_job = await job_queue.get_job(job_id)
    if original_job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if original_job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is not in a resumable state (status: {original_job.status})",
        )

    # Get execution state to determine resume point
    state = await execution_state.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"No execution state found for job {job_id}. Cannot resume.",
        )

    # Determine resume node
    resume_node = node_id or state.get("checkpoint_node")
    if resume_node is None:
        raise HTTPException(
            status_code=400,
            detail="No checkpoint found and no node_id specified. Cannot determine resume point.",
        )

    # Find the index of the resume node to determine which nodes to re-run
    completed_nodes = await execution_state.get_completed_node_ids(job_id)

    # Save uploaded file
    from core.utils import secure_save_file
    from config import Config

    config = Config.load()
    upload_config = config.upload_config

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    upload_folder = upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Reconstruct steps from original job context
    # We need the original steps — get from the execution state context or job nodes
    original_context = _get_original_job_context(job_id)
    if original_context is None:
        # Reconstruct from job nodes
        steps = []
        for node in original_job.nodes:
            steps.append({
                "id": node.node_id,
                "type": node.node_type,
                "label": node.node_label,
            })
    else:
        steps = original_context.get("steps", [])

    # Build node definitions for the new job
    nodes = []
    for node in original_job.nodes:
        nodes.append({
            "id": node.node_id,
            "type": node.node_type,
            "label": node.node_label,
        })

    # Submit new job to queue
    new_job = await job_queue.submit(
        workflow_id=original_job.workflow_id,
        workflow_name=f"{original_job.workflow_name} (resumed)",
        nodes=nodes,
        filename=file.filename,
        file_count=1,
        max_retries=original_job.max_retries,
    )

    # Store context with resume info — the executor will skip completed nodes
    await store_job_context(
        new_job.job_id, file_path, steps, resume_from_node=resume_node
    )

    # Copy execution state from original job to new job
    # so the new job can read outputs from previously completed nodes
    await _copy_execution_state(job_id, new_job.job_id, completed_nodes)

    logger.info(
        "Job %s resumed as %s (from node %s, %d nodes already completed)",
        job_id, new_job.job_id, resume_node, len(completed_nodes),
    )

    return {
        "original_job_id": job_id,
        "new_job_id": new_job.job_id,
        "status": "queued",
        "resume_from_node": resume_node,
        "completed_nodes": completed_nodes,
        "poll_url": f"/api/v1/jobs/{new_job.job_id}",
        "message": f"Job resumed from node '{resume_node}'. {len(completed_nodes)} nodes skipped.",
    }


def _get_original_job_context(job_id: str):
    """Try to get the original job context (may still be in memory)."""
    from services.job_executor import _get_job_context
    return _get_job_context(job_id)


async def _copy_execution_state(
    source_job_id: str,
    target_job_id: str,
    completed_node_ids: list,
) -> None:
    """Copy completed node states from source job to target job's execution state."""
    repo = execution_state.get_repository()
    if repo is None:
        return

    source_state = await execution_state.get_state(source_job_id)
    if source_state is None:
        return

    # Create state for new job
    await execution_state.create_state(
        job_id=target_job_id,
        workflow_id=source_state.get("workflow_id"),
    )

    # Copy completed node outputs
    node_states = source_state.get("node_states", {})
    for node_id in completed_node_ids:
        if node_id in node_states:
            node_data = node_states[node_id]
            await repo.save_node_output(
                job_id=target_job_id,
                node_id=node_id,
                output=node_data.get("output"),
                node_status="completed",
                duration_ms=node_data.get("duration_ms"),
            )

    # Copy context
    context = source_state.get("context", {})
    if context:
        await repo.update_execution_state(
            target_job_id, context=context
        )
