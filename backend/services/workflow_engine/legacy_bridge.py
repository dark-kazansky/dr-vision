"""
Legacy Migration Bridge — Routes legacy job submissions through the durable engine.

When DURABLE_MODE=true, this bridge intercepts workflow execution requests
and routes them to the durable workflow engine instead of the legacy job_queue.

Usage:
    from services.workflow_engine.legacy_bridge import submit_via_durable_engine

    if settings.durable_mode:
        run_id = await submit_via_durable_engine(engine, workflow_data, file_path)
    else:
        job = await job_queue.submit(...)

This ensures backward compatibility: the same API contract is maintained,
but execution uses the durable engine with full replay, retry, and recovery.
"""

import logging
from typing import Any, Dict, List, Optional

from services.workflow_engine.models import (
    ActivityDefinition,
    RetryPolicy,
    WorkflowDefinition,
)

logger = logging.getLogger(__name__)


async def submit_via_durable_engine(
    engine,
    steps: List[Dict[str, Any]],
    file_path: str,
    workflow_id: Optional[str] = None,
    workflow_name: Optional[str] = None,
    max_retries: int = 3,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Submit a legacy workflow execution through the durable engine.

    Converts legacy step definitions to WorkflowDefinition and starts a run.

    Args:
        engine: The WorkflowEngine instance.
        steps: Legacy step list [{"type": "parse", "tier": "Normal", "config": {...}}]
        file_path: Path to the file to process.
        workflow_id: Optional workflow/canvas ID.
        workflow_name: Name for the workflow run.
        max_retries: Max retry attempts per activity.
        metadata: Optional metadata dict.

    Returns:
        The run_id from the durable engine.
    """
    # Convert legacy steps to ActivityDefinitions
    activities = []
    prev_id: Optional[str] = None

    for i, step in enumerate(steps):
        step_type = step.get("type", "parse")
        step_tier = step.get("tier", "Normal")
        step_config = step.get("config", {})
        step_label = step.get("label", step_type.capitalize())
        activity_id = step.get("id", f"node-{i}")

        # Build config with tier
        config = dict(step_config)
        config["tier"] = step_tier

        # Sequential dependency chain
        depends_on = [prev_id] if prev_id else []

        activities.append(ActivityDefinition(
            activity_id=activity_id,
            activity_type=step_type,
            label=step_label,
            config=config,
            timeout_seconds=300,
            retry_policy=RetryPolicy(max_attempts=max_retries),
            queue_name="default",
            depends_on=depends_on,
        ))

        prev_id = activity_id

    # Build definition
    definition = WorkflowDefinition(
        workflow_id=workflow_id or "",
        name=workflow_name or "Legacy Workflow",
        activities=activities,
        timeout_seconds=3600,
    )

    # Start workflow
    run_id = await engine.start_workflow(
        definition=definition,
        input_data={"file_path": file_path},
        metadata=metadata or {},
    )

    logger.info(
        "Legacy job routed to durable engine (run_id=%s, steps=%d, file=%s)",
        run_id, len(steps), file_path,
    )
    return run_id


def is_durable_mode_enabled() -> bool:
    """Check if durable mode is enabled via settings."""
    try:
        from settings import settings
        return settings.durable_mode
    except Exception:
        return False
