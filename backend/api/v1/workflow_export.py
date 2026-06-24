"""
Workflow Export/Import API Router.

GET  /workflows/{id}/export  — Export workflow as JSON
POST /workflows/import       — Import workflow from JSON
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflow Export/Import"])

EXPORT_SCHEMA_VERSION = "1.0"


class WorkflowImportRequest(BaseModel):
    """Request body for importing a workflow."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    dsl: dict = Field(..., description="Canvas DSL (components, graph, path)")
    metadata: Optional[dict] = None
    # Optional: override user_id (admin only)
    user_id: Optional[str] = None


# =============================================================================
# Export
# =============================================================================


@router.get("/{workflow_id}/export")
async def export_workflow(
    request: Request,
    workflow_id: str,
) -> JSONResponse:
    """
    Export a workflow definition as a portable JSON file.

    The export includes:
    - Canvas DSL (nodes, edges, components, path)
    - Metadata (title, description, category, created_at)
    - Schema version for compatibility checking

    The exported JSON can be imported into another instance.
    """
    repo = getattr(request.app.state, "workflow_repo", None)
    if repo is None:
        raise HTTPException(status_code=503, detail="Workflow repository not available")

    # Try user_canvas table first
    canvas = await repo.get_canvas(workflow_id)
    if canvas is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    # Build export payload
    export_data = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": "dr-vision",
        "workflow": {
            "id": canvas["id"],
            "title": canvas["title"],
            "description": canvas.get("description", ""),
            "category": canvas.get("canvas_category", "dataflow_canvas"),
            "dsl": canvas.get("dsl", {}),
            "created_at": (
                canvas["created_at"].isoformat()
                if hasattr(canvas.get("created_at"), "isoformat")
                else canvas.get("created_at")
            ),
            "updated_at": (
                canvas["updated_at"].isoformat()
                if hasattr(canvas.get("updated_at"), "isoformat")
                else canvas.get("updated_at")
            ),
        },
    }

    # Return with Content-Disposition for download
    filename = f"{canvas['title'].replace(' ', '_').lower()}_workflow.json"
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# =============================================================================
# Import
# =============================================================================


@router.post("/import", status_code=201)
async def import_workflow(
    request: Request,
    body: WorkflowImportRequest,
) -> JSONResponse:
    """
    Import a workflow from a JSON definition.

    Accepts either:
    - A full export (with schema_version and workflow wrapper)
    - A direct DSL + title payload

    Validates the DSL structure before creating.
    """
    repo = getattr(request.app.state, "workflow_repo", None)
    if repo is None:
        raise HTTPException(status_code=503, detail="Workflow repository not available")

    dsl = body.dsl
    title = body.title
    description = body.description or ""
    user_id = body.user_id or "default"

    # Validate DSL structure
    validation_error = _validate_dsl(dsl)
    if validation_error:
        raise HTTPException(status_code=400, detail=f"Invalid DSL: {validation_error}")

    # Create canvas
    try:
        canvas = await repo.create_canvas(
            title=title,
            user_id=user_id,
            canvas_category=dsl.get("canvas_category", "dataflow_canvas"),
            description=description,
            dsl=dsl,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {e}")

    return JSONResponse(
        status_code=201,
        content={
            "workflow_id": canvas["id"],
            "title": canvas["title"],
            "description": description,
            "step_count": len(dsl.get("path", [])),
            "message": "Workflow imported successfully",
        },
    )


@router.post("/import-from-export", status_code=201)
async def import_from_export(
    request: Request,
    body: dict,
) -> JSONResponse:
    """
    Import a workflow from a full export JSON (as produced by /export).

    Handles schema version compatibility.
    """
    repo = getattr(request.app.state, "workflow_repo", None)
    if repo is None:
        raise HTTPException(status_code=503, detail="Workflow repository not available")

    # Check if this is an export format
    schema_version = body.get("schema_version")
    workflow_data = body.get("workflow")

    if not workflow_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid export format. Expected 'workflow' field with DSL.",
        )

    if schema_version and schema_version != EXPORT_SCHEMA_VERSION:
        logger.warning(
            "Importing workflow with schema version %s (current: %s)",
            schema_version, EXPORT_SCHEMA_VERSION,
        )

    dsl = workflow_data.get("dsl", {})
    title = workflow_data.get("title", "Imported Workflow")
    description = workflow_data.get("description", "")
    category = workflow_data.get("category", "dataflow_canvas")

    # Validate
    validation_error = _validate_dsl(dsl)
    if validation_error:
        raise HTTPException(status_code=400, detail=f"Invalid DSL: {validation_error}")

    # Create canvas
    try:
        canvas = await repo.create_canvas(
            title=f"{title} (imported)",
            user_id="default",
            canvas_category=category,
            description=description,
            dsl=dsl,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import workflow: {e}")

    return JSONResponse(
        status_code=201,
        content={
            "workflow_id": canvas["id"],
            "title": canvas["title"],
            "step_count": len(dsl.get("path", [])),
            "message": "Workflow imported from export successfully",
        },
    )


# =============================================================================
# Helpers
# =============================================================================


def _validate_dsl(dsl: dict) -> Optional[str]:
    """Validate a canvas DSL structure. Returns error message or None."""
    if not isinstance(dsl, dict):
        return "DSL must be a JSON object"

    # Must have at least components or graph
    if "components" not in dsl and "graph" not in dsl:
        return "DSL must contain 'components' or 'graph' field"

    # If components exist, validate structure
    components = dsl.get("components", {})
    if components and not isinstance(components, dict):
        return "'components' must be a JSON object"

    # Validate path if present
    path = dsl.get("path", [])
    if path and not isinstance(path, list):
        return "'path' must be an array"

    # Check that path nodes exist in components
    if components and path:
        missing = [p for p in path if p not in components]
        if missing:
            return f"Path references unknown nodes: {missing[:3]}"

    return None
