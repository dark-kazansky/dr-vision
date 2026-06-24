"""
OCR Results router — CRUD access to stored OCR processing results.

GET  /ocr-results            — list results with pagination
GET  /ocr-results/{id}       — get single result by UUID
GET  /ocr-results/by-filename/{filename} — get latest result for filename
DELETE /ocr-results/{id}     — delete a result
GET  /ocr-results/stats      — summary statistics
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import Optional

router = APIRouter(prefix="/ocr-results", tags=["OCR Results"])


def _get_repo(request: Request):
    """Get OCR result repository from app state or raise 503."""
    repo = getattr(request.app.state, "ocr_result_repo", None)
    if repo is None:
        raise HTTPException(status_code=503, detail="OCR results database not available")
    return repo


@router.get("/stats")
async def get_stats(request: Request) -> JSONResponse:
    """Return summary statistics for stored OCR results."""
    repo = _get_repo(request)
    stats = await repo.get_stats()
    return JSONResponse({"success": True, **stats})


@router.get("/by-filename/{filename:path}")
async def get_by_filename(filename: str, request: Request) -> JSONResponse:
    """Get the most recent OCR result for a given filename."""
    repo = _get_repo(request)
    result = await repo.get_result_by_filename(filename)
    if not result:
        raise HTTPException(status_code=404, detail=f"No OCR result found for filename: {filename}")
    return JSONResponse({"success": True, "result": result})


@router.get("/{result_id}")
async def get_result(result_id: str, request: Request) -> JSONResponse:
    """Get a single OCR result by UUID."""
    repo = _get_repo(request)
    result = await repo.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"OCR result not found: {result_id}")
    return JSONResponse({"success": True, "result": result})


@router.delete("/{result_id}")
async def delete_result(result_id: str, request: Request) -> JSONResponse:
    """Delete an OCR result by UUID."""
    repo = _get_repo(request)
    deleted = await repo.delete_result(result_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"OCR result not found: {result_id}")
    return JSONResponse({"success": True, "message": f"Deleted OCR result: {result_id}"})


@router.get("")
async def list_results(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    filename: Optional[str] = Query(default=None, description="Filter by filename (partial match)"),
) -> JSONResponse:
    """List OCR results with pagination and optional filename search."""
    repo = _get_repo(request)
    results = await repo.list_results(limit=limit, offset=offset, filename_filter=filename)
    return JSONResponse({"success": True, **results})
