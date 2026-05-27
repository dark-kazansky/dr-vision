"""
Journey Job Manager API router.

Endpoints:
- POST   /api/v1/jobs           — Submit a new workflow execution job
- GET    /api/v1/jobs           — List jobs with filtering
- GET    /api/v1/jobs/{job_id}  — Get job details + progress
- POST   /api/v1/jobs/{job_id}/cancel — Cancel a running/queued job
- GET    /api/v1/jobs/{job_id}/stream — SSE stream for real-time progress
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from api.v1.schemas.jobs import (
    JobCancelResponse,
    JobListResponse,
    JobResponse,
    JobSubmitResponse,
    NodeProgressResponse,
)
from services.job_queue import JobRecord, JobStatus, job_queue
from services.job_events import job_event_bus, JobEvent, JobEventType
from services.job_executor import store_job_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Journey Jobs"])


def _job_to_response(job: JobRecord) -> JobResponse:
    """Convert a JobRecord to a JobResponse."""
    return JobResponse(
        job_id=job.job_id,
        workflow_id=job.workflow_id,
        workflow_name=job.workflow_name,
        status=job.status,
        progress=job.progress,
        nodes=[
            NodeProgressResponse(
                node_id=n.node_id,
                node_type=n.node_type,
                node_label=n.node_label,
                status=n.status,
                retry_count=n.retry_count,
                started_at=n.started_at,
                completed_at=n.completed_at,
                error=n.error,
            )
            for n in job.nodes
        ],
        filename=job.filename,
        file_count=job.file_count,
        max_retries=job.max_retries,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        cancelled_at=job.cancelled_at,
        error=job.error,
        results=job.results,
    )


@router.post("/jobs", response_model=JobSubmitResponse)
async def submit_job(
    file: UploadFile = File(...),
    workflow: str = Form(...),
    workflow_id: Optional[str] = Form(None),
    workflow_name: Optional[str] = Form(None),
    max_retries: int = Form(3),
) -> JobSubmitResponse:
    """
    Submit a new workflow execution job.

    The job is queued and processed asynchronously.
    Returns immediately with a job_id for polling.

    feat-012: DB-first — writes job to PostgreSQL immediately,
    uploads file to MinIO, and stores minio_path in DB.
    """
    import json
    import os

    from core.utils import allowed_file, secure_save_file
    from config import Config

    # Parse workflow JSON
    try:
        workflow_data = json.loads(workflow)
        steps = workflow_data.get("steps", [])
    except (json.JSONDecodeError, AttributeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid workflow JSON: {e}")

    if not steps:
        raise HTTPException(status_code=400, detail="Workflow must have at least one step")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file
    config = Config.load()
    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get("allowed_extensions", []))

    if allowed_extensions and not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
        )

    # Save file locally for processing
    upload_folder = upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Upload to MinIO
    minio_path: Optional[str] = None
    try:
        import asyncio
        from core.minio_client import minio_client

        basename = os.path.basename(file_path)
        minio_object = f"jobs/{basename}"
        success = await asyncio.to_thread(minio_client.upload_file, file_path, minio_object)
        if success:
            minio_path = minio_object
    except Exception as e:
        logger.warning("Failed to upload to MinIO (job will still proceed): %s", e)

    # Build node definitions for the queue
    nodes = []
    for i, step in enumerate(steps):
        nodes.append({
            "id": step.get("id", f"node-{i}"),
            "type": step.get("type", "unknown"),
            "label": step.get("label", step.get("type", "Unknown")),
        })

    # Submit to queue (writes to in-memory queue)
    job = await job_queue.submit(
        workflow_id=workflow_id,
        workflow_name=workflow_name or f"Job for {file.filename}",
        nodes=nodes,
        filename=file.filename,
        file_count=1,
        max_retries=max_retries,
    )

    # feat-012: Write job to DB immediately (DB-first)
    try:
        from server import workflow_repo
        if workflow_repo and workflow_repo._pool:
            nodes_data = [
                {"node_id": n["id"], "node_type": n["type"], "node_label": n["label"],
                 "status": "pending", "retry_count": 0, "error": None,
                 "config": steps[i].get("config") if i < len(steps) else None,
                 "tier": steps[i].get("tier", "Normal") if i < len(steps) else "Normal"}
                for i, n in enumerate(nodes)
            ]
            await workflow_repo.create_job(
                workflow_id=workflow_id,
                workflow_name=workflow_name or f"Job for {file.filename}",
                nodes_data=nodes_data,
                steps_data=steps,
                filename=file.filename,
                file_count=1,
                max_retries=max_retries,
            )
            # Update with the correct job_id (match in-memory)
            await workflow_repo.update_job(
                job_id=job.job_id,
                status="queued",
                progress=0.0,
            )
            # Store minio_path
            if minio_path:
                await workflow_repo.set_job_minio_path(job.job_id, minio_path)

            # Create upload record
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
            await workflow_repo.create_upload(
                job_id=job.job_id,
                filename=file.filename,
                minio_path=minio_path or f"local/{os.path.basename(file_path)}",
                size_bytes=file_size,
                mime_type=file.content_type,
            )
    except Exception as e:
        logger.warning("Failed to persist job to DB (will sync later): %s", e)

    # Store execution context (file path + steps) for the executor
    await store_job_context(job.job_id, file_path, steps)

    logger.info("Job %s submitted for file %s (%d steps, minio=%s)",
                job.job_id, file.filename, len(steps), minio_path)

    return JobSubmitResponse(
        job_id=job.job_id,
        status="queued",
        poll_url=f"/api/v1/jobs/{job.job_id}",
        message=f"Job queued with {len(steps)} steps",
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = None,
    workflow_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> JobListResponse:
    """
    List jobs with optional filtering.

    feat-012: Queries from PostgreSQL (DB-first) with fallback to in-memory queue.

    Query params:
    - status: Filter by job status (queued, running, completed, failed, cancelled)
    - workflow_id: Filter by workflow ID
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    # Validate status if provided
    if status:
        valid_statuses = [s.value for s in JobStatus]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            )

    # Try DB first (feat-012)
    try:
        from server import workflow_repo
        if workflow_repo and workflow_repo._pool:
            db_result = await workflow_repo.list_jobs(
                status=status,
                workflow_id=workflow_id,
                limit=min(limit, 100),
                offset=max(offset, 0),
            )
            # Convert DB records to JobResponse format
            jobs_response = []
            for db_job in db_result["jobs"]:
                nodes = db_job.get("nodes") or []
                node_responses = [
                    NodeProgressResponse(
                        node_id=n.get("node_id", ""),
                        node_type=n.get("node_type", ""),
                        node_label=n.get("node_label", ""),
                        status=n.get("status", "pending"),
                        retry_count=n.get("retry_count", 0),
                        started_at=None,
                        completed_at=None,
                        error=n.get("error"),
                    )
                    for n in (nodes if isinstance(nodes, list) else [])
                ]
                jobs_response.append(JobResponse(
                    job_id=db_job["job_id"],
                    workflow_id=db_job.get("workflow_id"),
                    workflow_name=db_job.get("workflow_name"),
                    status=db_job.get("status", "queued"),
                    progress=db_job.get("progress", 0.0),
                    nodes=node_responses,
                    filename=db_job.get("filename"),
                    file_count=db_job.get("file_count", 0),
                    max_retries=db_job.get("max_retries", 3),
                    created_at=db_job["created_at"],
                    started_at=db_job.get("started_at"),
                    completed_at=db_job.get("completed_at"),
                    cancelled_at=db_job.get("cancelled_at"),
                    error=db_job.get("error"),
                    results=db_job.get("results"),
                ))
            return JobListResponse(
                jobs=jobs_response,
                total=db_result["total"],
                limit=db_result["limit"],
                offset=db_result["offset"],
            )
    except Exception as e:
        logger.debug("DB query failed, falling back to in-memory: %s", e)

    # Fallback: in-memory queue
    result = await job_queue.list_jobs(
        status=status,
        workflow_id=workflow_id,
        limit=min(limit, 100),
        offset=max(offset, 0),
    )

    return JobListResponse(
        jobs=[_job_to_response(j) for j in result["jobs"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """
    Get full job details including per-node progress.

    Use this endpoint to poll job status and see which nodes
    have completed, are running, or have failed.
    """
    job = await job_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return _job_to_response(job)


@router.post("/jobs/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job(job_id: str) -> JobCancelResponse:
    """
    Cancel a queued or running job.

    If the job is queued, it will be cancelled immediately.
    If the job is running, it will be cancelled after the current node completes.
    Already completed/failed/cancelled jobs cannot be cancelled.
    """
    success = await job_queue.cancel(job_id)
    if not success:
        job = await job_queue.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} cannot be cancelled (status: {job.status})",
        )

    return JobCancelResponse(
        success=True,
        job_id=job_id,
        message="Cancellation requested. Job will stop after current node completes.",
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str, request: Request) -> StreamingResponse:
    """
    Server-Sent Events (SSE) stream for real-time job progress.

    Streams events as they occur:
    - job_started: Job picked up by worker
    - job_progress: Overall progress updated
    - node_started: A node began processing
    - node_completed: A node finished successfully
    - node_failed: A node failed
    - node_retrying: A node is being retried
    - node_skipped: A node was skipped
    - job_completed: Job finished successfully
    - job_failed: Job failed
    - job_cancelled: Job was cancelled

    The stream closes automatically when the job reaches a terminal state
    (completed, failed, cancelled) or when the client disconnects.

    Usage (JavaScript):
        const es = new EventSource('/api/v1/jobs/{job_id}/stream');
        es.onmessage = (e) => { const data = JSON.parse(e.data); ... };
        es.addEventListener('job_completed', (e) => { es.close(); });
    """
    # Verify job exists
    job = await job_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # If job is already in terminal state, send final event and close
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        async def terminal_stream() -> AsyncGenerator[str, None]:
            status_value = job.status if isinstance(job.status, str) else job.status.value
            event_type = f"job_{status_value}"
            data = {
                "event": event_type,
                "job_id": job_id,
                "status": status_value,
                "progress": job.progress,
            }
            if job.error:
                data["error"] = job.error
            yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        return StreamingResponse(
            terminal_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Subscribe to events for this job
    async def event_stream() -> AsyncGenerator[str, None]:
        queue = await job_event_bus.subscribe(job_id)
        try:
            # Send initial state as first event
            initial_data = {
                "event": "connected",
                "job_id": job_id,
                "status": job.status if isinstance(job.status, str) else job.status.value,
                "progress": job.progress,
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "node_type": n.node_type,
                        "node_label": n.node_label,
                        "status": n.status if isinstance(n.status, str) else n.status.value,
                    }
                    for n in job.nodes
                ],
            }
            yield f"event: connected\ndata: {json.dumps(initial_data)}\n\n"

            # Stream events until job completes or client disconnects
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    # Wait for next event with timeout (for keepalive)
                    event: JobEvent = await asyncio.wait_for(
                        queue.get(), timeout=30.0
                    )

                    # Format as SSE
                    event_data = event.to_sse_dict()
                    event_type = event.event_type.value
                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

                    # Close stream on terminal events
                    if event.event_type in (
                        JobEventType.JOB_COMPLETED,
                        JobEventType.JOB_FAILED,
                        JobEventType.JOB_CANCELLED,
                    ):
                        break

                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection timeout
                    yield ": keepalive\n\n"

        finally:
            await job_event_bus.unsubscribe(job_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/workflows/{workflow_id}/trigger", response_model=JobSubmitResponse)
async def trigger_workflow_by_id(
    workflow_id: str,
    file: UploadFile = File(...),
    max_retries: int = Form(3),
) -> JobSubmitResponse:
    """
    Trigger a saved workflow by its ID using an uploaded file.

    1. Fetches the workflow definition from the database.
    2. Extracts steps from graph_data.
    3. Saves the file locally and uploads to MinIO.
    4. Creates a job record and triggers asynchronous execution.
    """
    import os
    from core.utils import allowed_file, secure_save_file
    from config import Config
    from server import workflow_repo

    if not workflow_repo:
        raise HTTPException(
            status_code=500,
            detail="Workflow repository is not configured",
        )

    # 1. Fetch workflow definition
    try:
        workflow_record = await workflow_repo.get_workflow(workflow_id)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workflow ID format or database error: {e}",
        )

    if not workflow_record:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow not found: {workflow_id}",
        )

    # 2. Extract steps
    graph_data = workflow_record.get("graph_data") or {}
    steps = graph_data.get("steps") or []
    if not steps:
        raise HTTPException(
            status_code=400,
            detail="Workflow must have at least one step in its graph_data",
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # 3. Validate file
    config = Config.load()
    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get("allowed_extensions", []))

    if allowed_extensions and not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
        )

    # Save file locally for processing
    upload_folder = upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Upload to MinIO
    minio_path: Optional[str] = None
    try:
        from core.minio_client import minio_client

        basename = os.path.basename(file_path)
        minio_object = f"jobs/{basename}"
        success = await asyncio.to_thread(minio_client.upload_file, file_path, minio_object)
        if success:
            minio_path = minio_object
    except Exception as e:
        logger.warning("Failed to upload to MinIO (job will still proceed): %s", e)

    # Build node definitions for the queue
    nodes = []
    for i, step in enumerate(steps):
        nodes.append({
            "id": step.get("id", f"node-{i}"),
            "type": step.get("type", "unknown"),
            "label": step.get("label", step.get("type", "Unknown")),
        })

    # Submit to queue (writes to in-memory queue)
    job = await job_queue.submit(
        workflow_id=workflow_id,
        workflow_name=workflow_record.get("name") or f"Job for {file.filename}",
        nodes=nodes,
        filename=file.filename,
        file_count=1,
        max_retries=max_retries,
    )

    # Write job to DB immediately (DB-first)
    try:
        nodes_data = [
            {"node_id": n["id"], "node_type": n["type"], "node_label": n["label"],
             "status": "pending", "retry_count": 0, "error": None,
             "config": steps[i].get("config") if i < len(steps) else None,
             "tier": steps[i].get("tier", "Normal") if i < len(steps) else "Normal"}
            for i, n in enumerate(nodes)
        ]
        await workflow_repo.create_job(
            workflow_id=workflow_id,
            workflow_name=workflow_record.get("name") or f"Job for {file.filename}",
            nodes_data=nodes_data,
            steps_data=steps,
            filename=file.filename,
            file_count=1,
            max_retries=max_retries,
        )
        # Update with the correct job_id (match in-memory)
        await workflow_repo.update_job(
            job_id=job.job_id,
            status="queued",
            progress=0.0,
        )
        # Store minio_path
        if minio_path:
            await workflow_repo.set_job_minio_path(job.job_id, minio_path)

        # Create upload record
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
        await workflow_repo.create_upload(
            job_id=job.job_id,
            filename=file.filename,
            minio_path=minio_path or f"local/{os.path.basename(file_path)}",
            size_bytes=file_size,
            mime_type=file.content_type,
        )
    except Exception as e:
        logger.warning("Failed to persist job to DB (will sync later): %s", e)

    # Store execution context (file path + steps) for the executor
    await store_job_context(job.job_id, file_path, steps)

    logger.info("Job %s submitted via workflow trigger for file %s (%d steps, minio=%s)",
                job.job_id, file.filename, len(steps), minio_path)

    return JobSubmitResponse(
        job_id=job.job_id,
        status="queued",
        poll_url=f"/api/v1/jobs/{job.job_id}",
        message=f"Job queued with {len(steps)} steps",
    )
