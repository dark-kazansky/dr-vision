"""
Data Store API router (feat-013).

Endpoints:
- GET    /api/v1/data-store           — List all data store entries
- POST   /api/v1/data-store           — Create a new entry
- GET    /api/v1/data-store/{id}      — Get entry by ID
- DELETE /api/v1/data-store/{id}      — Delete entry
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["DataStore"])


class DataStoreCreateRequest(BaseModel):
    filename: str = Field(..., description="Source filename")
    action_tag: str = Field(..., description="Action tag: Parse, Classify, Extract, Split, WF")
    result_data: Any = Field(..., description="The processing result data")
    model_used: Optional[str] = Field(None, description="Model used for processing")


@router.get("/data-store")
async def list_data_store(
    tag: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List data store entries with optional tag filter."""
    try:
        from server import workflow_repo

        if not workflow_repo or not workflow_repo._pool:
            return {"entries": [], "total": 0, "limit": limit, "offset": offset}

        async with workflow_repo._pool.acquire() as conn:
            if tag:
                rows = await conn.fetch(
                    """
                    SELECT * FROM data_store
                    WHERE action_tag = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    tag, min(limit, 200), max(offset, 0),
                )
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM data_store WHERE action_tag = $1", tag
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM data_store
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    min(limit, 200), max(offset, 0),
                )
                count = await conn.fetchval("SELECT COUNT(*) FROM data_store")

        entries = [
            {
                "id": str(row["id"]),
                "filename": row["filename"],
                "action_tag": row["action_tag"],
                "result_data": json.loads(row["result_data"]) if row["result_data"] else None,
                "model_used": row["model_used"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]

        return {"entries": entries, "total": count, "limit": limit, "offset": offset}

    except Exception as e:
        logger.error("Failed to list data store: %s", e)
        return {"entries": [], "total": 0, "limit": limit, "offset": offset}


@router.post("/data-store")
async def create_data_store_entry(request: DataStoreCreateRequest):
    """Create a new data store entry."""
    try:
        from server import workflow_repo

        if not workflow_repo or not workflow_repo._pool:
            raise HTTPException(status_code=503, detail="Database not available")

        # Validate action_tag
        valid_tags = {"Parse", "Classify", "Extract", "Split", "WF"}
        if request.action_tag not in valid_tags:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action_tag. Must be one of: {', '.join(valid_tags)}",
            )

        entry_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        result_json = json.dumps(request.result_data, ensure_ascii=False)

        async with workflow_repo._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO data_store (id, filename, action_tag, result_data, model_used, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                entry_id,
                request.filename,
                request.action_tag,
                result_json,
                request.model_used,
                now,
            )

        return {
            "id": str(entry_id),
            "filename": request.filename,
            "action_tag": request.action_tag,
            "result_data": request.result_data,
            "model_used": request.model_used,
            "created_at": now.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create data store entry: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save entry: {e}")


@router.get("/data-store/{entry_id}")
async def get_data_store_entry(entry_id: str):
    """Get a data store entry by ID."""
    try:
        from server import workflow_repo

        if not workflow_repo or not workflow_repo._pool:
            raise HTTPException(status_code=503, detail="Database not available")

        async with workflow_repo._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM data_store WHERE id = $1", uuid.UUID(entry_id)
            )

        if row is None:
            raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")

        return {
            "id": str(row["id"]),
            "filename": row["filename"],
            "action_tag": row["action_tag"],
            "result_data": json.loads(row["result_data"]) if row["result_data"] else None,
            "model_used": row["model_used"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get entry: {e}")


@router.delete("/data-store/{entry_id}")
async def delete_data_store_entry(entry_id: str):
    """Delete a data store entry."""
    try:
        from server import workflow_repo

        if not workflow_repo or not workflow_repo._pool:
            raise HTTPException(status_code=503, detail="Database not available")

        async with workflow_repo._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM data_store WHERE id = $1", uuid.UUID(entry_id)
            )

        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")

        return {"deleted": True, "id": entry_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete entry: {e}")
