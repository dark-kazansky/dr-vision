"""
Observability API router — feat-010.

Endpoints:
- GET /api/v1/observability/timeline/{job_id}  — Execution timeline per job
- GET /api/v1/observability/metrics            — Performance metrics (aggregated)
- GET /api/v1/observability/errors             — Error analytics
- GET /api/v1/observability/audit              — Audit log
- GET /api/v1/observability/dashboard          — Dashboard summary
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services import observability

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/observability", tags=["Observability"])


@router.get("/timeline/{job_id}")
async def get_timeline(job_id: str):
    """
    Get execution timeline for a specific job.

    Returns per-node timing with duration_ms, status, and error info.
    Useful for visualizing which nodes took longest and where failures occurred.
    """
    timeline = await observability.get_execution_timeline(job_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return timeline


@router.get("/metrics")
async def get_metrics(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    days: int = Query(7, ge=1, le=90, description="Time period in days"),
):
    """
    Get aggregated performance metrics.

    Returns:
    - Overall: total jobs, success rate, avg/min/max duration
    - Per node_type: execution count, failure rate, avg duration

    Query params:
    - workflow_id: filter metrics for a specific workflow
    - days: lookback period (default 7, max 90)
    """
    result = await observability.get_performance_metrics(
        workflow_id=workflow_id,
        days=days,
    )
    if "error" in result and "summary" not in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.get("/errors")
async def get_errors(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    days: int = Query(7, ge=1, le=90, description="Time period in days"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
):
    """
    Get error analytics.

    Returns:
    - Top errors: grouped by node_type + error message with occurrence count
    - Failure rates: per node_type success/failure breakdown

    Use this to identify which node types are most problematic
    and what errors occur most frequently.
    """
    result = await observability.get_error_analytics(
        workflow_id=workflow_id,
        days=days,
        limit=limit,
    )
    if "error" in result and "top_errors" not in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.get("/audit")
async def get_audit(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    days: int = Query(7, ge=1, le=90, description="Time period in days"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    Get audit log entries.

    Returns job-level audit trail: who ran what workflow, when,
    with what file, and what was the result.

    Supports pagination via limit/offset.
    """
    result = await observability.get_audit_log(
        workflow_id=workflow_id,
        days=days,
        limit=limit,
        offset=offset,
    )
    return result


@router.get("/dashboard")
async def get_dashboard(
    days: int = Query(7, ge=1, le=90, description="Time period in days"),
):
    """
    Get dashboard summary.

    Returns:
    - System health: overall success rate, active jobs, health status
    - Per-workflow breakdown: jobs count, success rate, health indicator

    Health levels:
    - healthy: failure rate < 10%
    - warning: failure rate 10-30%
    - critical: failure rate > 30%
    """
    result = await observability.get_dashboard_summary(days=days)
    if "error" in result and "system" not in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result
