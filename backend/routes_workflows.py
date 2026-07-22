"""
Workflow management & orchestration routes.

Provides:

* ``GET    /workflows``                  — list saved workflows
* ``POST   /workflows``                  — save a new workflow graph
* ``GET    /workflows/{id}``             — fetch one workflow
* ``PUT    /workflows/{id}``             — update an existing workflow
* ``DELETE /workflows/{id}``             — delete a workflow
* ``POST   /workflows/{id}/run``         — run a saved workflow with files
* ``POST   /workflows/run``              — run an ad-hoc graph (no save)
* ``GET    /workflows/runs``             — list run history (paginated)
* ``GET    /workflows/runs/{run_id}``    — full run record (status, nodes, logs)
* ``POST   /workflows/runs/{run_id}/cancel`` — cooperative cancellation
* ``DELETE /workflows/runs/{run_id}``    — delete a run from history

All endpoints share the authentication / rate-limiting middleware
already applied to the main router.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core import Config
from core.dependencies import get_config
from core.middleware import FileSizeValidator
from core.run_store import run_store
from core.utils import secure_save_file
from core.workflow_orchestrator import run_workflow
from core.workflow_store import workflow_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])
runs_router = APIRouter(prefix="/workflow-runs", tags=["workflow-runs"])

_file_size_validator = FileSizeValidator()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    nodes: Optional[List[Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("")
async def list_workflows() -> JSONResponse:
    return JSONResponse({"workflows": workflow_store.list()})


@router.post("")
async def create_workflow(payload: WorkflowCreateRequest) -> JSONResponse:
    try:
        record = workflow_store.create(
            name=payload.name,
            nodes=payload.nodes,
            description=payload.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(record, status_code=201)


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> JSONResponse:
    record = workflow_store.get(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return JSONResponse(record)


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, payload: WorkflowUpdateRequest) -> JSONResponse:
    try:
        record = workflow_store.update(
            workflow_id,
            name=payload.name,
            description=payload.description,
            nodes=payload.nodes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return JSONResponse(record)


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str) -> JSONResponse:
    if not workflow_store.remove(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return JSONResponse({"deleted": workflow_id})


# ---------------------------------------------------------------------------
# Run execution
# ---------------------------------------------------------------------------

async def _save_uploaded_files(
    files: List[UploadFile], upload_folder: str, max_size_mb: int
) -> List[Dict[str, str]]:
    """
    Persist all uploaded files to a temporary location and return their
    paths plus original names.
    """
    saved: List[Dict[str, str]] = []
    for f in files:
        if not f.filename:
            raise HTTPException(status_code=400, detail="One of the uploaded files is missing a name")
        await _file_size_validator.validate(f, max_size_mb)
        path = await secure_save_file(f, upload_folder)
        saved.append({"path": path, "name": f.filename})
    return saved


def _cleanup_paths(paths: List[str]) -> None:
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception as e:
            logger.warning("Failed to clean up temp file %s: %s", p, e)


def _parse_nodes_form(nodes_json: Optional[str], fallback: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if nodes_json:
        try:
            parsed = json.loads(nodes_json)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid nodes JSON: {e}")
        if not isinstance(parsed, list):
            raise HTTPException(status_code=400, detail="nodes must be a JSON array")
        return parsed
    if fallback is None:
        raise HTTPException(status_code=400, detail="No workflow nodes provided")
    return fallback


@router.post("/{workflow_id}/run")
async def run_saved_workflow(
    workflow_id: str,
    files: List[UploadFile] = File(...),
    config: Config = Depends(get_config),
) -> JSONResponse:
    """Execute a saved workflow against one or more uploaded files."""
    record = workflow_store.get(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    nodes = record.get("nodes") or []
    if not nodes:
        raise HTTPException(status_code=400, detail="Workflow has no nodes")

    upload_cfg = config.upload_config
    upload_folder = upload_cfg.get("folder", "uploads")
    max_size_mb = upload_cfg.get("max_size_mb", 10)

    saved = await _save_uploaded_files(files, upload_folder, max_size_mb)
    paths = [s["path"] for s in saved]
    names = [s["name"] for s in saved]

    try:
        result = await run_workflow(
            nodes=nodes,
            file_paths=paths,
            file_names=names,
            config=config,
            workflow_id=workflow_id,
            workflow_name=record.get("name") or "Workflow",
        )
        return JSONResponse(result)
    finally:
        _cleanup_paths(paths)


@router.post("/run")
async def run_adhoc_workflow(
    files: List[UploadFile] = File(...),
    nodes: str = Form(...),
    workflow_name: str = Form("Ad-hoc workflow"),
    config: Config = Depends(get_config),
) -> JSONResponse:
    """Execute a workflow graph passed inline (no save)."""
    parsed_nodes = _parse_nodes_form(nodes, None)
    if not parsed_nodes:
        raise HTTPException(status_code=400, detail="No workflow nodes provided")

    upload_cfg = config.upload_config
    upload_folder = upload_cfg.get("folder", "uploads")
    max_size_mb = upload_cfg.get("max_size_mb", 10)

    saved = await _save_uploaded_files(files, upload_folder, max_size_mb)
    paths = [s["path"] for s in saved]
    names = [s["name"] for s in saved]

    try:
        result = await run_workflow(
            nodes=parsed_nodes,
            file_paths=paths,
            file_names=names,
            config=config,
            workflow_id=None,
            workflow_name=workflow_name,
        )
        return JSONResponse(result)
    finally:
        _cleanup_paths(paths)


# ---------------------------------------------------------------------------
# Runs (history)
# ---------------------------------------------------------------------------

@runs_router.get("")
async def list_runs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> JSONResponse:
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")
    return JSONResponse(run_store.list(status=status, limit=limit, offset=offset))


@runs_router.get("/{run_id}")
async def get_run(run_id: str) -> JSONResponse:
    record = run_store.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse(record)


@runs_router.post("/{run_id}/cancel")
async def cancel_run(run_id: str) -> JSONResponse:
    if not run_store.request_cancel(run_id):
        raise HTTPException(status_code=409, detail="Run is not running")
    return JSONResponse({"run_id": run_id, "cancelRequested": True})


@runs_router.delete("/{run_id}")
async def delete_run(run_id: str) -> JSONResponse:
    if not run_store.remove(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse({"deleted": run_id})


@runs_router.post("/clear-finished")
async def clear_finished_runs() -> JSONResponse:
    removed = run_store.remove_finished()
    return JSONResponse({"removed": removed})
