"""
Background jobs router.

GET /job/{job_id}/status  — poll job progress
GET /job/{job_id}/result  — retrieve completed job payload
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from services.job_manager import job_manager

router = APIRouter(tags=["Background Jobs"])


@router.get("/job/{job_id}/status")
async def get_job_status(job_id: str) -> JSONResponse:
    """Poll the status of a background processing job."""
    status = job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return JSONResponse(status)


@router.get("/job/{job_id}/result")
async def get_job_result(job_id: str) -> JSONResponse:
    """Retrieve the full result payload of a completed background job."""
    result = job_manager.get_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if result["status"] not in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is still {result['status']}. "
                   f"Poll /job/{job_id}/status until completed.",
        )
    return JSONResponse(result)
