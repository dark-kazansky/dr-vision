"""
Batch Processing API Router.

POST /batch/process         — Submit multiple files for batch processing
GET  /batch                 — List batch jobs
GET  /batch/{batch_id}      — Get batch status and per-file progress
GET  /batch/{batch_id}/stream — SSE stream for real-time progress
POST /batch/{batch_id}/cancel — Cancel a running batch
GET  /batch/{batch_id}/results — Get aggregated results
"""

import asyncio
import json
import logging
import os
from typing import AsyncGenerator, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from auth.dependencies import get_current_user
from core.utils import secure_save_file
from services.batch_processor import (
    BatchProcessor,
    BatchStatus,
    batch_processor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["Batch Processing"])


def _get_processor(request: Request) -> BatchProcessor:
    """Get batch processor, configure file_processor if needed."""
    if batch_processor._file_processor is None:
        # Wire up the default file processor (uses workflow_service)
        async def process_file(file_path: str, steps: List[dict]) -> dict:
            from config import Config
            from services.workflow_service import (
                _run_classify_step,
                _run_extract_step,
                _run_parse_step,
                _run_split_step,
                _run_layout_recognize_step,
                _run_table_recognize_step,
                _run_document_to_markdown_step,
                _run_ocr_postprocess_step,
            )

            config = Config.load()
            results = []

            for step in steps:
                step_type = step.get("type", "parse")
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
                else:
                    raise ValueError(f"Unknown step type: {step_type}")

                results.append({"step": step_type, "tier": step_tier, "result": result})

            return {"success": True, "results": results}

        batch_processor._file_processor = process_file

    return batch_processor


# =============================================================================
# POST /batch/process — Submit batch
# =============================================================================


@router.post("/process", status_code=202)
async def submit_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    workflow: str = Form('{"steps": [{"type": "parse", "tier": "Normal"}]}'),
    max_concurrency: int = Form(3),
    _user=Depends(get_current_user),
) -> JSONResponse:
    """
    Submit multiple files for batch processing.

    Accepts:
    - Multiple file uploads (multipart)
    - A single zip archive (auto-extracted)
    - Workflow definition (same format as journey jobs)

    Returns immediately with batch_id for polling/streaming.
    """
    processor = _get_processor(request)

    # Parse workflow
    try:
        workflow_data = json.loads(workflow)
        steps = workflow_data.get("steps", [{"type": "parse", "tier": "Normal"}])
    except (json.JSONDecodeError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid workflow JSON")

    if not steps:
        raise HTTPException(status_code=400, detail="Workflow must have at least one step")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    max_concurrency = max(1, min(10, max_concurrency))

    # Save files and collect paths
    upload_folder = os.environ.get("UPLOAD_FOLDER", "uploads")
    file_paths: List[str] = []

    for upload_file in files:
        if not upload_file.filename:
            continue

        try:
            file_path = await secure_save_file(upload_file, upload_folder)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

        # Check if it's a zip — extract
        if upload_file.filename.lower().endswith(".zip"):
            try:
                extracted = processor.extract_zip(file_path)
                file_paths.extend(extracted)
                # Remove the zip itself
                os.remove(file_path)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            file_paths.append(file_path)

    if not file_paths:
        raise HTTPException(status_code=400, detail="No valid files found")

    # Create and start batch
    batch_id = processor.create_batch(
        file_paths=file_paths,
        workflow_steps=steps,
        max_concurrency=max_concurrency,
    )
    await processor.start_batch(batch_id)

    return JSONResponse(
        status_code=202,
        content={
            "batch_id": batch_id,
            "total_files": len(file_paths),
            "max_concurrency": max_concurrency,
            "status": "processing",
            "message": f"Batch started with {len(file_paths)} files",
        },
    )


# =============================================================================
# GET /batch — List batches
# =============================================================================


@router.get("")
async def list_batches(
    request: Request,
    limit: int = 50,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """List recent batch jobs."""
    processor = _get_processor(request)
    batches = processor.list_batches(limit=limit)
    return JSONResponse(content={"batches": batches, "total": len(batches)})


# =============================================================================
# GET /batch/{batch_id} — Get batch status
# =============================================================================


@router.get("/{batch_id}")
async def get_batch(
    request: Request,
    batch_id: str,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """Get batch status with per-file progress."""
    processor = _get_processor(request)
    batch = processor.get_batch(batch_id)

    if batch is None:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    return JSONResponse(content=batch.to_dict())


# =============================================================================
# GET /batch/{batch_id}/stream — SSE progress stream
# =============================================================================


@router.get("/{batch_id}/stream")
async def stream_batch(
    request: Request,
    batch_id: str,
    _user=Depends(get_current_user),
) -> StreamingResponse:
    """SSE stream for real-time batch progress events."""
    processor = _get_processor(request)
    batch = processor.get_batch(batch_id)

    if batch is None:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    queue = processor.subscribe(batch_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send initial status
            yield _sse("connected", {"batch_id": batch_id, "status": batch.status.value})

            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield _sse(event.event_type, event.to_sse_dict())

                    # End stream when batch completes
                    if event.event_type in ("batch_completed", "batch_cancelled"):
                        yield _sse("stream_end", {"reason": event.event_type})
                        break

                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"

        finally:
            processor.unsubscribe(batch_id, queue)

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
# POST /batch/{batch_id}/cancel — Cancel batch
# =============================================================================


@router.post("/{batch_id}/cancel")
async def cancel_batch(
    request: Request,
    batch_id: str,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """Cancel a running batch."""
    processor = _get_processor(request)
    success = await processor.cancel_batch(batch_id)

    if not success:
        batch = processor.get_batch(batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel batch in state '{batch.status.value}'",
        )

    return JSONResponse(content={"batch_id": batch_id, "status": "cancelled"})


# =============================================================================
# GET /batch/{batch_id}/results — Get aggregated results
# =============================================================================


@router.get("/{batch_id}/results")
async def get_batch_results(
    request: Request,
    batch_id: str,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """Get aggregated results for a completed batch."""
    processor = _get_processor(request)
    batch = processor.get_batch(batch_id)

    if batch is None:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    if batch.status in (BatchStatus.PENDING, BatchStatus.PROCESSING):
        raise HTTPException(
            status_code=409,
            detail="Batch is still processing. Wait for completion or stream events.",
        )

    results = []
    for f in batch.files:
        results.append({
            "file_id": f.file_id,
            "filename": f.filename,
            "status": f.status.value,
            "result": f.result,
            "error": f.error,
            "duration_ms": f.duration_ms,
        })

    return JSONResponse(content={
        "batch_id": batch_id,
        "status": batch.status.value,
        "total": batch.total,
        "completed": batch.completed_count,
        "failed": batch.failed_count,
        "results": results,
    })


# =============================================================================
# SSE Helper
# =============================================================================


def _sse(event_type: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"
