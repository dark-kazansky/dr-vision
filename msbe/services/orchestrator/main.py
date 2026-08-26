"""
M.DocAI MSBE Orchestrator service.

Owns saved-workflow CRUD and run execution. Calls the worker services
(parser/classifier/extractor/splitter) over HTTP via shared
``ServiceClient``.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from dr_vision_msbe import (
    RunStore,
    ServiceClient,
    ServiceURLs,
    WorkflowCreateRequest,
    WorkflowStore,
    WorkflowUpdateRequest,
)

from runner import FileBlob, WorkerClients, run_workflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stores + clients
# ---------------------------------------------------------------------------

DATA_DIR = os.getenv("MSBE_DATA_DIR", "./data")
workflow_store = WorkflowStore(os.path.join(DATA_DIR, "workflows"))
run_store = RunStore(os.path.join(DATA_DIR, "runs"))

_urls = ServiceURLs.from_env()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.clients = WorkerClients(
        parser=ServiceClient(service_name="parser", base_url=_urls.parser),
        classifier=ServiceClient(service_name="classifier", base_url=_urls.classifier),
        extractor=ServiceClient(service_name="extractor", base_url=_urls.extractor),
        splitter=ServiceClient(service_name="splitter", base_url=_urls.splitter),
    )
    logger.info("Orchestrator ready (data dir: %s)", DATA_DIR)
    try:
        yield
    finally:
        await app.state.clients.close()


app = FastAPI(title="M.DocAI MSBE Orchestrator", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "orchestrator", "version": app.version})


# ---------------------------------------------------------------------------
# Workflow CRUD
# ---------------------------------------------------------------------------

@app.get("/workflows")
async def list_workflows() -> JSONResponse:
    return JSONResponse({"workflows": workflow_store.list()})


@app.post("/workflows")
async def create_workflow(payload: WorkflowCreateRequest) -> JSONResponse:
    try:
        record = workflow_store.create(
            name=payload.name,
            nodes=[n.model_dump(exclude_none=True) for n in payload.nodes],
            description=payload.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(record, status_code=201)


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str) -> JSONResponse:
    record = workflow_store.get(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return JSONResponse(record)


@app.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, payload: WorkflowUpdateRequest) -> JSONResponse:
    try:
        record = workflow_store.update(
            workflow_id,
            name=payload.name,
            description=payload.description,
            nodes=[n.model_dump(exclude_none=True) for n in payload.nodes] if payload.nodes is not None else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return JSONResponse(record)


@app.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str) -> JSONResponse:
    if not workflow_store.remove(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return JSONResponse({"deleted": workflow_id})


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

async def _read_files(files: List[UploadFile]) -> List[FileBlob]:
    blobs: List[FileBlob] = []
    for f in files:
        if not f.filename:
            raise HTTPException(status_code=400, detail="Uploaded file is missing a name")
        data = await f.read()
        blobs.append(FileBlob(name=f.filename, content_type=f.content_type or "", data=data))
    return blobs


@app.post("/workflows/{workflow_id}/run")
async def run_saved_workflow(workflow_id: str, files: List[UploadFile] = File(...)) -> JSONResponse:
    record = workflow_store.get(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    nodes = record.get("nodes") or []
    if not nodes:
        raise HTTPException(status_code=400, detail="Workflow has no nodes")

    blobs = await _read_files(files)
    result = await run_workflow(
        nodes=nodes,
        files=blobs,
        clients=app.state.clients,
        store=run_store,
        workflow_id=workflow_id,
        workflow_name=record.get("name") or "Workflow",
    )
    return JSONResponse(result)


@app.post("/workflows/run")
async def run_adhoc_workflow(
    files: List[UploadFile] = File(...),
    nodes: str = Form(...),
    workflow_name: str = Form("Ad-hoc workflow"),
) -> JSONResponse:
    try:
        parsed_nodes = json.loads(nodes)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid nodes JSON: {e}")
    if not isinstance(parsed_nodes, list) or not parsed_nodes:
        raise HTTPException(status_code=400, detail="nodes must be a non-empty JSON array")

    blobs = await _read_files(files)
    result = await run_workflow(
        nodes=parsed_nodes,
        files=blobs,
        clients=app.state.clients,
        store=run_store,
        workflow_id=None,
        workflow_name=workflow_name,
    )
    return JSONResponse(result)


@app.get("/workflow-runs")
async def list_runs(status: Optional[str] = None, limit: int = 50, offset: int = 0) -> JSONResponse:
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")
    return JSONResponse(run_store.list(status=status, limit=limit, offset=offset))


@app.get("/workflow-runs/{run_id}")
async def get_run(run_id: str) -> JSONResponse:
    record = run_store.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse(record)


@app.post("/workflow-runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> JSONResponse:
    if not run_store.request_cancel(run_id):
        raise HTTPException(status_code=409, detail="Run is not running")
    return JSONResponse({"run_id": run_id, "cancelRequested": True})


@app.delete("/workflow-runs/{run_id}")
async def delete_run(run_id: str) -> JSONResponse:
    if not run_store.remove(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse({"deleted": run_id})


@app.post("/workflow-runs/clear-finished")
async def clear_finished_runs() -> JSONResponse:
    return JSONResponse({"removed": run_store.remove_finished()})
