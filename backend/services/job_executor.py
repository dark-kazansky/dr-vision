"""
Job Executor — Executes workflow jobs with per-node retry and cancellation.

This module bridges the JobQueue with the existing workflow_service logic.
It processes each node in sequence, handles retries with exponential backoff,
and checks for cancellation between nodes.

feat-007: Integrates with execution_state service for:
- Persistent state per execution (survives refresh)
- Node output checkpointing (resume from failure)
- Context passing between nodes
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from services.job_queue import JobQueue, JobRecord, NodeStatus

logger = logging.getLogger(__name__)


async def execute_job(job: JobRecord, queue: JobQueue) -> None:
    """
    Execute a workflow job node by node.

    This is the executor function registered with the JobQueue.
    It processes nodes sequentially, retries on failure, and respects cancellation.

    feat-007: Creates execution state on start, saves node outputs as checkpoints,
    and supports resume from failed node.
    """
    from config import Config
    from services import execution_state

    config = Config.load()
    results: List[Dict[str, Any]] = []

    # Get the execution context from the job
    job_context = _get_job_context(job.job_id)
    if job_context is None:
        raise RuntimeError(f"No execution context found for job {job.job_id}")

    file_path = job_context.get("file_path")
    steps = job_context.get("steps", [])
    resume_from_node = job_context.get("resume_from_node")

    if not file_path:
        raise RuntimeError("No file path in job context")

    # Create execution state for this job
    await execution_state.create_state(
        job_id=job.job_id,
        workflow_id=job.workflow_id,
    )

    # Determine which nodes to skip (for resume)
    completed_node_ids: set = set()
    if resume_from_node:
        completed_node_ids = set(
            await execution_state.get_completed_node_ids(job.job_id)
        )
        logger.info(
            "Job %s resuming: skipping %d completed nodes, starting from %s",
            job.job_id, len(completed_node_ids), resume_from_node,
        )

    last_completed_node: Optional[str] = None

    for i, node in enumerate(job.nodes):
        # Check cancellation before each node
        if queue.is_cancelled(job.job_id):
            logger.info("Job %s cancelled before node %s", job.job_id, node.node_id)
            for remaining in job.nodes[i:]:
                await queue.update_node_status(
                    job.job_id, remaining.node_id, NodeStatus.SKIPPED
                )
            await execution_state.mark_cancelled(job.job_id)
            return

        # Skip already-completed nodes during resume
        if node.node_id in completed_node_ids:
            # Load previous output into results for downstream nodes
            prev_output = await execution_state.get_node_output(job.job_id, node.node_id)
            if prev_output is not None:
                step = steps[i] if i < len(steps) else {}
                results.append({
                    "step": step.get("type", "unknown"),
                    "tier": step.get("tier", "Normal"),
                    "result": prev_output,
                })
            await queue.update_node_status(
                job.job_id, node.node_id, NodeStatus.COMPLETED
            )
            last_completed_node = node.node_id
            continue

        # Find the corresponding step definition
        step = steps[i] if i < len(steps) else None
        if step is None:
            await queue.update_node_status(
                job.job_id, node.node_id, NodeStatus.SKIPPED,
                error="No step definition found"
            )
            continue

        # Execute with retry logic
        success = await _execute_node_with_retry(
            queue=queue,
            job=job,
            node_index=i,
            step=step,
            file_path=file_path,
            config=config,
            results=results,
        )

        if success:
            last_completed_node = node.node_id
        else:
            # Node failed after all retries — save checkpoint and fail
            await execution_state.mark_failed(
                job.job_id, checkpoint_node=last_completed_node
            )
            raise RuntimeError(
                f"Node '{node.node_label}' ({node.node_type}) failed after "
                f"{node.retry_count} retries: {node.error}"
            )

    # All nodes completed successfully
    await execution_state.mark_completed(job.job_id)


async def _execute_node_with_retry(
    queue: JobQueue,
    job: JobRecord,
    node_index: int,
    step: Dict[str, Any],
    file_path: str,
    config: Any,
    results: List[Dict[str, Any]],
) -> bool:
    """
    Execute a single node with retry logic.

    Returns True if the node completed successfully, False if it exhausted retries.
    feat-007: Saves node output to execution state on success.
    """
    from services.workflow_service import (
        _run_classify_step,
        _run_extract_step,
        _run_parse_step,
        _run_split_step,
        _run_layout_recognize_step,
        _run_table_recognize_step,
        _run_document_to_markdown_step,
        _run_ocr_postprocess_step,
        _run_template_extract_step,
    )
    from services import execution_state

    node = job.nodes[node_index]
    max_retries = job.max_retries

    for attempt in range(max_retries + 1):
        # Check cancellation
        if queue.is_cancelled(job.job_id):
            await queue.update_node_status(
                job.job_id, node.node_id, NodeStatus.SKIPPED
            )
            return True  # Not a failure, just cancelled

        # Mark as running (or retrying)
        if attempt == 0:
            await queue.update_node_status(
                job.job_id, node.node_id, NodeStatus.RUNNING
            )
        else:
            await queue.update_node_retry(job.job_id, node.node_id)
            # Exponential backoff
            delay = job.retry_delay_base * (2 ** (attempt - 1))
            logger.info(
                "Job %s: retrying node %s (attempt %d/%d, delay %.1fs)",
                job.job_id, node.node_id, attempt + 1, max_retries + 1, delay,
            )
            await asyncio.sleep(delay)
            await queue.update_node_status(
                job.job_id, node.node_id, NodeStatus.RUNNING
            )

        start_time = time.time()

        try:
            step_type = step.get("type")
            step_tier = step.get("tier", "Normal")
            step_config = step.get("config", {})

            if step_type == "parse":
                result = await _run_parse_step(file_path, step_tier, step_config, config)
            elif step_type == "classify":
                result = await _run_classify_step(file_path, step_tier, step_config, config)
            elif step_type == "extract":
                result = await _run_extract_step(file_path, step_tier, step_config, config)
            elif step_type == "split":
                result = await _run_split_step(file_path, step_tier, step_config, config)
            elif step_type == "layout_recognize":
                result = await _run_layout_recognize_step(file_path, step_tier, step_config, config)
            elif step_type == "table_recognize":
                result = await _run_table_recognize_step(file_path, step_tier, step_config, config)
            elif step_type == "document_to_markdown":
                result = await _run_document_to_markdown_step(file_path, step_tier, step_config, config)
            elif step_type == "ocr_postprocess":
                result = await _run_ocr_postprocess_step(file_path, step_tier, step_config, config)
            elif step_type == "template_extract":
                result = await _run_template_extract_step(file_path, step_tier, step_config, config)
            else:
                raise ValueError(f"Unknown step type: {step_type}")

            duration_ms = int((time.time() - start_time) * 1000)

            # Success — update queue status
            await queue.update_node_status(
                job.job_id, node.node_id, NodeStatus.COMPLETED, result=result,
                duration_ms=duration_ms,
            )
            results.append({"step": step_type, "tier": step_tier, "result": result})

            # feat-007: Save node output to execution state (checkpoint)
            await execution_state.save_node_output(
                job_id=job.job_id,
                node_id=node.node_id,
                output=result,
                status="completed",
                duration_ms=duration_ms,
            )

            # Save to shared context for downstream nodes
            await execution_state.save_context(
                job_id=job.job_id,
                key=f"node_{node.node_id}_output",
                value={"type": step_type, "tier": step_tier},
            )

            # Update job results
            async with queue._lock:
                stored_job = queue._jobs.get(job.job_id)
                if stored_job:
                    stored_job.results = list(results)

            return True

        except Exception as e:
            error_msg = str(e)
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "Job %s: node %s failed (attempt %d/%d): %s",
                job.job_id, node.node_id, attempt + 1, max_retries + 1, error_msg,
            )

            if attempt >= max_retries:
                # Exhausted retries — save failure to execution state
                await queue.update_node_status(
                    job.job_id, node.node_id, NodeStatus.FAILED, error=error_msg
                )
                await execution_state.save_node_output(
                    job_id=job.job_id,
                    node_id=node.node_id,
                    output=None,
                    status="failed",
                    error=error_msg,
                    duration_ms=duration_ms,
                )
                return False

    return False


# ---------------------------------------------------------------------------
# Job context store (file paths and step definitions for submitted jobs)
# ---------------------------------------------------------------------------

_job_contexts: Dict[str, Dict[str, Any]] = {}
_context_lock = asyncio.Lock()


async def store_job_context(
    job_id: str,
    file_path: str,
    steps: List[Dict[str, Any]],
    resume_from_node: Optional[str] = None,
) -> None:
    """Store execution context for a job (file path + step definitions + resume info)."""
    async with _context_lock:
        _job_contexts[job_id] = {
            "file_path": file_path,
            "steps": steps,
            "resume_from_node": resume_from_node,
        }


def _get_job_context(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve execution context for a job."""
    return _job_contexts.get(job_id)


async def cleanup_job_context(job_id: str) -> None:
    """Remove execution context after job completes."""
    async with _context_lock:
        _job_contexts.pop(job_id, None)
