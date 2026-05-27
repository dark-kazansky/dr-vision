"""
Uploads API router (feat-012).

Endpoints:
- POST /api/v1/uploads              — Upload file to MinIO
- GET  /api/v1/uploads              — List all uploads
- GET  /api/v1/uploads/{id}         — Get upload metadata
- GET  /api/v1/uploads/{id}/download — Download file from MinIO
- DELETE /api/v1/uploads/{id}       — Delete upload
- GET  /api/v1/jobs/{job_id}/uploads — Get uploads for a specific job
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Uploads"])


@router.post("/uploads")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to MinIO and create a metadata record in PostgreSQL.
    
    Returns the upload metadata including the upload_id for future reference.
    """
    try:
        from server import workflow_repo
        from core.minio_client import minio_client

        if not workflow_repo or not workflow_repo._pool:
            raise HTTPException(status_code=503, detail="Database not available")

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Determine MIME type
        mime_type = file.content_type or "application/octet-stream"

        # Generate unique MinIO path
        upload_id = uuid.uuid4()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        object_name = f"uploads/{timestamp}_{upload_id.hex[:8]}/{file.filename}"

        # Upload to MinIO
        success = await asyncio.to_thread(
            minio_client.upload_bytes, content, object_name, mime_type
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")

        # Create DB record
        record = await workflow_repo.create_upload(
            job_id=None,
            filename=file.filename or "unknown",
            minio_path=object_name,
            size_bytes=file_size,
            mime_type=mime_type,
        )

        return record

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.get("/uploads")
async def list_uploads(limit: int = 50, offset: int = 0):
    """List uploaded files that actually exist in MinIO (path starts with 'uploads/')."""
    try:
        from server import workflow_repo
        if workflow_repo and workflow_repo._pool:
            async with workflow_repo._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM uploads
                    WHERE minio_path LIKE 'uploads/%'
                    ORDER BY uploaded_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    min(limit, 100), max(offset, 0),
                )
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM uploads WHERE minio_path LIKE 'uploads/%'"
                )

            uploads = [
                {
                    "upload_id": str(row["id"]),
                    "job_id": str(row["job_id"]) if row["job_id"] else None,
                    "filename": row["filename"],
                    "minio_path": row["minio_path"],
                    "size_bytes": row["size_bytes"],
                    "mime_type": row["mime_type"],
                    "uploaded_at": row["uploaded_at"].isoformat() if row["uploaded_at"] else None,
                }
                for row in rows
            ]
            return {"uploads": uploads, "total": count, "limit": limit, "offset": offset}
    except Exception as e:
        logger.warning("Failed to list uploads: %s", e)

    return {"uploads": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/uploads/{upload_id}")
async def get_upload(upload_id: str):
    """Get upload metadata by ID."""
    try:
        from server import workflow_repo
        if workflow_repo and workflow_repo._pool:
            upload = await workflow_repo.get_upload(upload_id)
            if upload is None:
                raise HTTPException(status_code=404, detail=f"Upload not found: {upload_id}")
            return upload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get upload: {e}")


@router.get("/uploads/{upload_id}/download")
async def download_upload(upload_id: str):
    """
    Download a file from MinIO by upload ID.

    Streams the file content directly from MinIO.
    """
    try:
        from server import workflow_repo
        if not workflow_repo or not workflow_repo._pool:
            raise HTTPException(status_code=503, detail="Database not available")

        upload = await workflow_repo.get_upload(upload_id)
        if upload is None:
            raise HTTPException(status_code=404, detail=f"Upload not found: {upload_id}")

        minio_path = upload.get("minio_path")
        if not minio_path or minio_path.startswith("local/"):
            raise HTTPException(
                status_code=404,
                detail="File not available in MinIO (local-only upload)",
            )

        # Stream from MinIO
        import asyncio
        from core.minio_client import minio_client

        try:
            response = await asyncio.to_thread(
                minio_client.s3_client.get_object,
                Bucket=minio_client.bucket_name,
                Key=minio_path,
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"File not found in MinIO: {e}")

        filename = upload.get("filename", "download")
        content_type = upload.get("mime_type") or "application/octet-stream"

        # Use RFC 5987 encoding for Unicode filenames
        from urllib.parse import quote
        encoded_filename = quote(filename)

        return StreamingResponse(
            response["Body"],
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {e}")


@router.get("/jobs/{job_id}/uploads")
async def get_job_uploads(job_id: str):
    """Get all uploads associated with a specific job."""
    try:
        from server import workflow_repo
        if workflow_repo and workflow_repo._pool:
            uploads = await workflow_repo.get_uploads_for_job(job_id)
            return {"job_id": job_id, "uploads": uploads}
    except Exception as e:
        logger.warning("Failed to get uploads for job %s: %s", job_id, e)

    return {"job_id": job_id, "uploads": []}


@router.delete("/uploads/{upload_id}")
async def delete_upload(upload_id: str):
    """Delete an upload from MinIO and PostgreSQL."""
    try:
        from server import workflow_repo
        from core.minio_client import minio_client

        if not workflow_repo or not workflow_repo._pool:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get upload metadata
        upload = await workflow_repo.get_upload(upload_id)
        if upload is None:
            raise HTTPException(status_code=404, detail=f"Upload not found: {upload_id}")

        # Delete from MinIO
        minio_path = upload.get("minio_path")
        if minio_path and not minio_path.startswith("local/"):
            await asyncio.to_thread(minio_client.delete_object, minio_path)

        # Delete from DB
        async with workflow_repo._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM uploads WHERE id = $1", uuid.UUID(upload_id)
            )

        return {"deleted": True, "upload_id": upload_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
