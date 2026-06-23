"""
Durable Workflow Engine API router.

Endpoints:
- POST   /api/v1/durable/workflows       — Start a durable workflow run
- GET    /api/v1/durable/runs             — List runs (filter by status)
- GET    /api/v1/durable/runs/{run_id}    — Get run state (replayed from events)
- GET    /api/v1/durable/runs/{run_id}/events — Get event history
- POST   /api/v1/durable/runs/{run_id}/cancel — Cancel a running workflow
- GET    /api/v1/durable/runs/{run_id}/stream — SSE real-time event stream
- GET    /api/v1/durable/health           — Engine health summary
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from auth.dependencies import get_current_user
from services.workflow_engine.models import (
    ActivityDefinition,
    RetryPolicy,
    WorkflowDefinition,
    WorkflowRunStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/durable", tags=["Durable Workflows"])


# =============================================================================
# Helpers
# =============================================================================


def _get_engine(request: Request):
    """Get the workflow engine from app state or raise 503."""
    engine = getattr(request.app.state, "workflow_engine", None)
    if engine is None or not engine.is_running:
        raise HTTPException(
            status_code=503,
            detail="Durable workflow engine is not available",
        )
    return engine


# =============================================================================
# POST /workflows — Start a durable workflow run
# =============================================================================


@router.post("/workflows", status_code=202)
async def start_workflow(
    request: Request,
    body: dict,
    _user=Depends(get_current_user),
):
    """
    Start a new durable workflow execution.

    Request body:
    {
        "workflow_id": "optional-id",
        "name": "My Workflow",
        "activities": [
            {"activity_type": "ocr_parse", "label": "Parse PDF", "config": {...}},
            {"activity_type": "ocr_classify", "label": "Classify", "depends_on": ["act-id"]}
        ],
        "input_data": {"file_path": "/uploads/doc.pdf"},
        "timeout_seconds": 3600,
        "metadata": {"user_id": "..."}
    }
    """
    engine = _get_engine(request)

    # Parse activities
    activities_data = body.get("activities", [])
    if not activities_data:
        raise HTTPException(status_code=400, detail="At least one activity is required")

    activities = []
    for i, act_data in enumerate(activities_data):
        activity_type = act_data.get("activity_type") or act_data.get("type")
        if not activity_type:
            raise HTTPException(
                status_code=400,
                detail=f"Activity {i}: 'activity_type' is required",
            )

        # Build retry policy if provided
        retry_data = act_data.get("retry_policy")
        retry_policy = RetryPolicy(**retry_data) if retry_data else RetryPolicy()

        activities.append(ActivityDefinition(
            activity_id=act_data.get("activity_id", f"act-{i}"),
            activity_type=activity_type,
            label=act_data.get("label", activity_type),
            config=act_data.get("config", {}),
            timeout_seconds=act_data.get("timeout_seconds", 300),
            retry_policy=retry_policy,
            queue_name=act_data.get("queue_name", "default"),
            depends_on=act_data.get("depends_on", []),
        ))

    # Build workflow definition
    definition = WorkflowDefinition(
        workflow_id=body.get("workflow_id", ""),
        name=body.get("name", "Untitled Workflow"),
        description=body.get("description", ""),
        activities=activities,
        timeout_seconds=body.get("timeout_seconds", 3600),
        metadata=body.get("metadata", {}),
    )

    # Start workflow
    input_data = body.get("input_data", {})
    metadata = body.get("metadata", {})

    run_id = await engine.start_workflow(
        definition=definition,
        input_data=input_data,
        metadata=metadata,
    )

    return {
        "run_id": run_id,
        "workflow_id": definition.workflow_id,
        "status": "running",
        "message": "Workflow started successfully",
    }


# =============================================================================
# GET /runs — List workflow runs
# =============================================================================


@router.get("/runs")
async def list_runs(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    _user=Depends(get_current_user),
):
    """List durable workflow runs, optionally filtered by status."""
    engine = _get_engine(request)

    valid_statuses = [s.value for s in WorkflowRunStatus]
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid: {valid_statuses}",
        )

    runs = await engine.list_runs(status=status, limit=limit)
    return {
        "runs": runs,
        "total": len(runs),
        "limit": limit,
    }


# =============================================================================
# GET /runs/{run_id} — Get run state (full replay)
# =============================================================================


@router.get("/runs/{run_id}")
async def get_run(
    request: Request,
    run_id: str,
    _user=Depends(get_current_user),
):
    """Get the current state of a workflow run (reconstructed from events)."""
    engine = _get_engine(request)

    run_state = await engine.get_run_state(run_id)
    if run_state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return run_state


# =============================================================================
# GET /runs/{run_id}/events — Get event history
# =============================================================================


@router.get("/runs/{run_id}/events")
async def get_run_events(
    request: Request,
    run_id: str,
    _user=Depends(get_current_user),
):
    """Get the full event history for a workflow run."""
    engine = _get_engine(request)

    # Verify run exists
    run_data = await engine.get_run_status(run_id)
    if run_data is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    events = await engine.get_run_events(run_id)
    return {
        "run_id": run_id,
        "events": [e.model_dump() for e in events],
        "total": len(events),
    }


# =============================================================================
# POST /runs/{run_id}/cancel — Cancel a running workflow
# =============================================================================


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    request: Request,
    run_id: str,
    body: Optional[dict] = None,
    _user=Depends(get_current_user),
):
    """Cancel a running workflow."""
    engine = _get_engine(request)

    # Verify run exists
    run_data = await engine.get_run_status(run_id)
    if run_data is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    reason = (body or {}).get("reason", "Cancelled by user")
    success = await engine.cancel_workflow(run_id, reason=reason)

    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel run '{run_id}' — already in terminal state ({run_data['status']})",
        )

    return {
        "run_id": run_id,
        "status": "cancelled",
        "message": "Workflow cancelled successfully",
    }


# =============================================================================
# GET /runs/{run_id}/stream — SSE real-time event stream
# =============================================================================


@router.get("/runs/{run_id}/stream")
async def stream_run_events(
    request: Request,
    run_id: str,
    _user=Depends(get_current_user),
):
    """
    Server-Sent Events (SSE) stream for real-time workflow progress.

    Streams workflow events as they occur. Closes automatically when
    the workflow reaches a terminal state (completed, failed, cancelled).
    """
    engine = _get_engine(request)

    # Verify run exists
    run_data = await engine.get_run_status(run_id)
    if run_data is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events by polling the event store."""
        last_sequence = 0
        terminal_statuses = {
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLED,
            WorkflowRunStatus.TIMED_OUT,
        }

        # Send initial status
        yield _sse_message("connected", {"run_id": run_id, "status": run_data["status"]})

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Load new events since last check
            try:
                events = await engine.event_store.load_history(run_id, after_sequence=last_sequence)
            except Exception:
                break

            for event in events:
                last_sequence = event.sequence_num
                yield _sse_message(event.event_type, {
                    "sequence": event.sequence_num,
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                    **event.payload,
                })

                # Check if workflow reached terminal state
                if event.event_type in (
                    "workflow_completed",
                    "workflow_failed",
                    "workflow_cancelled",
                    "workflow_timed_out",
                ):
                    yield _sse_message("stream_end", {"reason": event.event_type})
                    return

            # Check run status directly (in case we missed events)
            current_run = await engine.get_run_status(run_id)
            if current_run and current_run["status"] in terminal_statuses:
                yield _sse_message("stream_end", {"reason": current_run["status"]})
                return

            # Poll interval
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# GET /health — Engine health summary
# =============================================================================


@router.get("/health")
async def engine_health(
    request: Request,
    _user=Depends(get_current_user),
):
    """Get durable workflow engine health and stats."""
    engine = _get_engine(request)

    health = await engine.get_health()
    health["engine_status"] = "running" if engine.is_running else "stopped"

    # Add queue stats
    try:
        queue_stats = await engine.task_queue.get_queue_stats()
        health["queue_stats"] = queue_stats
    except Exception:
        health["queue_stats"] = {}

    return health


# =============================================================================
# SSE Helpers
# =============================================================================


def _sse_message(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event message."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"
