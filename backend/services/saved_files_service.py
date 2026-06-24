"""
Saved-files service — file listing and retrieval logic.

All data is sourced from PostgreSQL (ocr_results table).
Database must be available — raises HTTP 503 if not.
"""

import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def list_saved_files() -> dict:
    """Return a sorted list of all saved OCR results from the database."""
    from server import ocr_result_repo

    if not ocr_result_repo or not ocr_result_repo._pool:
        raise HTTPException(status_code=503, detail="Database unavailable — cannot list saved files")

    result = await ocr_result_repo.list_results(limit=200)
    files = []
    for item in result["items"]:
        raw_text = item.get("raw_text") or ""
        result_data = item.get("result_data") or {}
        files.append({
            "id": item["id"],
            "filename": item["filename"],
            "model_id": item.get("model_id"),
            "raw_ocr": {
                "exists": bool(raw_text),
                "path": f"/ocr-results/{item['id']}",
                "size": len(raw_text),
            },
            "parsed": {
                "exists": "parsed_text" in result_data,
                "path": f"/ocr-results/{item['id']}" if "parsed_text" in result_data else None,
                "size": len(result_data.get("parsed_text") or "") if "parsed_text" in result_data else 0,
            },
            "result_type": result_data.get("type"),
            "created_at": item.get("created_at"),
        })
    return {"success": True, "count": len(files), "files": files}


async def get_raw_ocr(filename: str) -> dict:
    """Read and return OCR text content from the database."""
    from server import ocr_result_repo

    if not ocr_result_repo or not ocr_result_repo._pool:
        raise HTTPException(status_code=503, detail="Database unavailable — cannot retrieve OCR result")

    result = await ocr_result_repo.get_result_by_filename(filename)
    if not result:
        raise HTTPException(status_code=404, detail=f"OCR result not found for: {filename}")

    if not result.get("raw_text"):
        raise HTTPException(status_code=404, detail=f"No raw text available for: {filename}")

    return {
        "success": True,
        "id": result["id"],
        "filename": result["filename"],
        "content": result["raw_text"],
        "size": len(result["raw_text"]),
        "model_id": result.get("model_id"),
        "created_at": result.get("created_at"),
    }
