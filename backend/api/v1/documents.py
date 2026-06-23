"""
Async Document Processing API — feat-042.

Endpoints:
- POST   /api/v1/documents/process        — Submit a document for async processing
- GET    /api/v1/documents/{job_id}/stream — SSE stream for realtime progress
- GET    /api/v1/documents/{job_id}        — Poll job status
- GET    /api/v1/documents/{job_id}/result — Get completed result payload
- POST   /api/v1/documents/{job_id}/cancel — Cancel a running job
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from auth.dependencies import get_current_user
from services.document_job_runner import (
    DocumentJobConfig,
    DocumentJobStatus,
    DocumentOperation,
    document_job_runner,
)
from services.job_events import job_event_bus, JobEvent, JobEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Document Processing"])


# ---------------------------------------------------------------------------
# POST /process — submit async processing job
# ---------------------------------------------------------------------------


@router.post("/process", dependencies=[Depends(get_current_user)])
async def submit_document_processing(
    file: Optional[UploadFile] = File(None),
    upload_id: Optional[str] = Form(None),
    operation: str = Form("ocr"),
    model_id: str = Form("default"),
    provider: Optional[str] = Form(None),
    tier: str = Form("Normal"),
    force_ocr: bool = Form(False),
    process_all_pages: bool = Form(True),
    # Extraction params
    extraction_schema: Optional[str] = Form(None),
    extraction_target: Optional[str] = Form(None),
    extractor_model: Optional[str] = Form(None),
    # Classify params
    classification_rules: Optional[str] = Form(None),
    classifier_model_id: Optional[str] = Form(None),
    is_multimodal: bool = Form(False),
    max_pages: int = Form(5),
    # Split params
    categories: Optional[str] = Form(None),
    allow_uncategorized: bool = Form(True),
    split_mode: str = Form("sections"),
) -> JSONResponse:
    """
    Submit a document for asynchronous processing.

    Returns 202 Accepted with a job_id. Use the /stream endpoint for
    realtime SSE progress or /status for polling.

    Accepts either a file upload or an upload_id referencing a file
    already stored in MinIO (from /api/v1/uploads).
    """
    # Validate operation
    try:
        op = DocumentOperation(operation)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid operation '{operation}'. Must be one of: ocr, classify, split, extract",
        )

    # Resolve file path
    file_path: Optional[str] = None
    filename: str = "unknown"

    if file and file.filename:
        # Save uploaded file to temp location
        import os
        import tempfile

        from core.storage import UPLOADS_DIR

        os.makedirs(str(UPLOADS_DIR), exist_ok=True)
        suffix = os.path.splitext(file.filename)[1]
        fd, file_path = tempfile.mkstemp(suffix=suffix, dir=str(UPLOADS_DIR))
        os.close(fd)

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        filename = file.filename

    elif upload_id:
        # Resolve from MinIO / local uploads
        file_path = await _resolve_upload_path(upload_id)
        if file_path is None:
            raise HTTPException(
                status_code=404,
                detail=f"Upload not found: {upload_id}",
            )
        filename = os.path.basename(file_path)
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either a file upload or an upload_id",
        )

    # Build config
    config = DocumentJobConfig(
        file_path=file_path,
        filename=filename,
        operation=op,
        model_id=model_id,
        provider=provider,
        tier=tier,
        force_ocr=force_ocr,
        process_all_pages=process_all_pages,
        extraction_schema=extraction_schema,
        extraction_target=extraction_target,
        extractor_model=extractor_model,
        classification_rules=classification_rules,
        classifier_model_id=classifier_model_id,
        is_multimodal=is_multimodal,
        max_pages=max_pages,
        categories=categories,
        allow_uncategorized=allow_uncategorized,
        split_mode=split_mode,
    )

    # Create job and start processing
    job_id = document_job_runner.create_job(config)

    # Emit queued event before kicking off the task
    await job_event_bus.emit_job_queued(job_id)

    # Fire and forget — the runner task processes in the background
    asyncio.create_task(document_job_runner.run(job_id))

    logger.info(
        "Document job %s submitted: operation=%s, file=%s",
        job_id, operation, filename,
    )

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "operation": operation,
            "filename": filename,
            "stream_url": f"/api/v1/documents/{job_id}/stream",
            "poll_url": f"/api/v1/documents/{job_id}",
        },
    )


# ---------------------------------------------------------------------------
# GET /{job_id}/stream — SSE realtime progress
# ---------------------------------------------------------------------------


@router.get("/{job_id}/stream", dependencies=[Depends(get_current_user)])
async def stream_document_progress(job_id: str, request: Request) -> StreamingResponse:
    """
    Server-Sent Events stream for realtime document processing progress.

    Events emitted:
    - connected: Initial state on subscribe
    - stage_changed: Processing moved to a new stage
    - page_progress: Per-page progress update
    - partial_result: Text result for a completed page
    - job_completed: Processing finished successfully
    - job_failed: Processing failed
    - job_cancelled: Processing was cancelled

    The stream closes on terminal events or client disconnect.
    Auth: Bearer token via fetch (not EventSource).
    """
    record = document_job_runner.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # If already terminal, send final event and close
    if record.status in (
        DocumentJobStatus.COMPLETED,
        DocumentJobStatus.FAILED,
        DocumentJobStatus.CANCELLED,
    ):
        async def terminal_stream() -> AsyncGenerator[str, None]:
            event_type = f"job_{record.status.value}"
            data = {
                "event": event_type,
                "job_id": job_id,
                "status": record.status.value,
                "progress": record.progress,
            }
            if record.error:
                data["error"] = record.error
            if record.result:
                data["result"] = record.result
            yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        return StreamingResponse(
            terminal_stream(),
            media_type="text/event-stream",
            headers=_sse_headers(),
        )

    # Live stream
    async def event_stream() -> AsyncGenerator[str, None]:
        queue = await job_event_bus.subscribe(job_id)
        try:
            # Send initial connected event
            initial = {
                "event": "connected",
                "job_id": job_id,
                "status": record.status.value,
                "progress": record.progress,
                "total_pages": record.total_pages,
                "current_page": record.current_page,
                "current_stage": record.current_stage,
            }
            yield f"event: connected\ndata: {json.dumps(initial)}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                try:
                    event: JobEvent = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_data = event.to_sse_dict()
                    event_type = event.event_type.value
                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

                    # Close on terminal events
                    if event.event_type in (
                        JobEventType.JOB_COMPLETED,
                        JobEventType.JOB_FAILED,
                        JobEventType.JOB_CANCELLED,
                    ):
                        break

                except asyncio.TimeoutError:
                    # Keepalive to prevent proxy/gateway timeouts
                    yield ": keepalive\n\n"

        finally:
            await job_event_bus.unsubscribe(job_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


# ---------------------------------------------------------------------------
# GET /{job_id} — poll status
# ---------------------------------------------------------------------------


@router.get("/{job_id}", dependencies=[Depends(get_current_user)])
async def get_document_job_status(job_id: str) -> JSONResponse:
    """
    Poll the status of a document processing job.

    Returns current status, progress, stage, and page counts.
    """
    record = document_job_runner.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JSONResponse({
        "job_id": job_id,
        "status": record.status.value,
        "progress": record.progress,
        "total_pages": record.total_pages,
        "current_page": record.current_page,
        "current_stage": record.current_stage,
        "operation": record.config.operation.value,
        "filename": record.config.filename,
        "created_at": record.created_at,
        "started_at": record.started_at,
        "completed_at": record.completed_at,
        "error": record.error,
    })


# ---------------------------------------------------------------------------
# GET /{job_id}/result — full result payload
# ---------------------------------------------------------------------------


@router.get("/{job_id}/result", dependencies=[Depends(get_current_user)])
async def get_document_job_result(job_id: str) -> JSONResponse:
    """
    Get the full result payload of a completed document job.

    Returns 409 if job is still running.
    """
    record = document_job_runner.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if record.status not in (
        DocumentJobStatus.COMPLETED,
        DocumentJobStatus.FAILED,
        DocumentJobStatus.CANCELLED,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is still {record.status.value}. "
                   f"Poll /api/v1/documents/{job_id} until terminal.",
        )

    return JSONResponse({
        "job_id": job_id,
        "status": record.status.value,
        "result": record.result,
        "error": record.error,
    })


# ---------------------------------------------------------------------------
# POST /{job_id}/cancel — cancel a running job
# ---------------------------------------------------------------------------


@router.post("/{job_id}/cancel", dependencies=[Depends(get_current_user)])
async def cancel_document_job(job_id: str) -> JSONResponse:
    """
    Request cancellation of a running document job.

    Cooperative: the runner checks for cancellation between pages.
    Returns 409 if job is already in a terminal state.
    """
    success = document_job_runner.request_cancel(job_id)
    if not success:
        record = document_job_runner.get_job(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} cannot be cancelled (status: {record.status.value})",
        )

    return JSONResponse({
        "success": True,
        "job_id": job_id,
        "message": "Cancellation requested. Job will stop after current page.",
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sse_headers() -> dict:
    """Standard SSE response headers."""
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


async def _resolve_upload_path(upload_id: str) -> Optional[str]:
    """
    Resolve an upload_id to a local file path.

    Tries:
    1. Download from MinIO via the uploads API
    2. Check local uploads directory
    """
    import os

    from core.storage import UPLOADS_DIR

    # Check local uploads directory for files matching the upload_id
    uploads_dir = str(UPLOADS_DIR)
    if os.path.isdir(uploads_dir):
        for fname in os.listdir(uploads_dir):
            if upload_id in fname:
                return os.path.join(uploads_dir, fname)

    # Try MinIO download
    try:
        from core.minio_client import minio_client


        # Try common MinIO paths
        for prefix in ("uploads/", "jobs/", ""):
            minio_path = f"{prefix}{upload_id}"
            local_path = os.path.join(uploads_dir, f"dl_{upload_id}")
            success = await asyncio.to_thread(
                minio_client.download_file, minio_path, local_path
            )
            if success and os.path.exists(local_path):
                return local_path
    except Exception as e:
        logger.debug("MinIO download failed for upload_id=%s: %s", upload_id, e)

    return None
