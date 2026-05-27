"""
Public Workflow Execution API — v1 router.

Endpoints:
  POST   /api/v1/workflows                              Create workflow
  GET    /api/v1/workflows                              List workflows
  GET    /api/v1/workflows/{workflow_id}                Get workflow
  PUT    /api/v1/workflows/{workflow_id}                Update workflow
  DELETE /api/v1/workflows/{workflow_id}                Delete workflow

  POST   /api/v1/workflows/{workflow_id}/execute        Execute full workflow
  POST   /api/v1/workflows/{workflow_id}/steps/parse    Execute parse step
  POST   /api/v1/workflows/{workflow_id}/steps/classify Execute classify step
  POST   /api/v1/workflows/{workflow_id}/steps/extract  Execute extract step
  POST   /api/v1/workflows/{workflow_id}/steps/split    Execute split step

  GET    /api/v1/jobs/{job_id}/status                   Poll job status
  GET    /api/v1/jobs/{job_id}/result                   Get job result
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import JSONResponse

from api.v1.schemas.workflow import (
    AsyncJobResponse,
    ClassifyStepResponse,
    ErrorResponse,
    ExtractStepResponse,
    JobStatusResponse,
    ParseStepResponse,
    SplitStepResponse,
    WorkflowCreate,
    WorkflowExecuteResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from services.job_manager import job_manager
from services.public_workflow_service import (
    execute_step_classify,
    execute_step_extract,
    execute_step_parse,
    execute_step_split,
    execute_workflow,
)
from services.workflow_store import WorkflowNotFoundError, workflow_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Public Workflow API v1"])


# ---------------------------------------------------------------------------
# Workflow CRUD
# ---------------------------------------------------------------------------

@router.post(
    "/workflows",
    response_model=WorkflowResponse,
    status_code=201,
    summary="Create a new workflow",
    description=(
        "Create and store a workflow definition with optional graph_data. "
        "Returns a `workflow_id` that can be used to execute the workflow later."
    ),
)
async def create_workflow(body: WorkflowCreate, request: Request) -> WorkflowResponse:
    steps = [s.model_dump() for s in body.steps] if body.steps else []
    graph_data = body.graph_data or {"nodes": [], "edges": [], "steps": steps}

    if "steps" not in graph_data:
        graph_data["steps"] = steps

    repo = getattr(request.app.state, "workflow_repo", None)
    if repo:
        # Build DSL from graph_data (new user_canvas schema)
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        components = {}
        path = []
        for n in nodes:
            nid = n.get("id", "")
            path.append(nid)
            connections = n.get("connections") or []
            downstream = [c.get("targetId", "") for c in connections] if connections else []
            components[nid] = {
                "obj": {
                    "component_name": f"{n.get('type', 'parse').capitalize()}Processor",
                    "params": {"tier": n.get("tier", "Normal"), **(n.get("config") or {})},
                },
                "downstream": downstream,
                "upstream": [],
                "parent_id": None,
            }

        for nid, comp in components.items():
            for ds in comp["downstream"]:
                if ds in components:
                    components[ds]["upstream"].append(nid)

        dsl = {
            "components": components,
            "graph": {
                "nodes": [{"id": n.get("id"), "type": n.get("type"), "position": {"x": n.get("x", 100), "y": n.get("y", 200)}, "data": {"label": n.get("label", ""), "name": f"{n.get('type', '').capitalize()}Processor", "form": n.get("config") or {}}} for n in nodes],
                "edges": edges,
            },
            "globals": {"sys.query": "", "sys.conversation_turns": 0, "sys.files": [], "sys.history": []},
            "path": path,
            "history": [],
            "variables": {},
        }

        canvas = await repo.create_canvas(
            title=body.name,
            user_id="default",
            canvas_category="dataflow_canvas",
            description=body.description,
            dsl=dsl,
        )

        return WorkflowResponse(
            workflow_id=canvas["id"],
            name=canvas["title"],
            description=canvas.get("description"),
            steps=steps,
            graph_data=graph_data,
            status="draft",
            created_at=canvas["created_at"],
            updated_at=canvas["updated_at"],
        )
    else:
        record = workflow_store.create(
            name=body.name,
            description=body.description,
            steps=steps,
        )
        record["graph_data"] = graph_data
        record["status"] = "draft"
        return WorkflowResponse(**record)


@router.get(
    "/workflows",
    response_model=WorkflowListResponse,
    summary="List all workflows",
    description="Return a list of all stored workflow definitions (from user_canvas table).",
)
async def list_workflows(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = None,
) -> WorkflowListResponse:
    repo = getattr(request.app.state, "workflow_repo", None)
    if repo:
        # Try new user_canvas table first
        try:
            result = await repo.list_canvases(
                user_id=user_id, limit=limit, offset=offset,
            )
            items = [
                {
                    "workflow_id": r["id"],
                    "name": r["title"],
                    "description": r.get("description"),
                    "step_count": len(r.get("dsl", {}).get("path", [])),
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                }
                for r in result["canvases"]
            ]
            return WorkflowListResponse(total=result["total"], workflows=items)
        except Exception as e:
            logger.debug("user_canvas query failed, falling back to workflows: %s", e)

        # Fallback to legacy workflows table
        result = await repo.list_workflows(limit=limit, offset=offset)
        items = [
            {
                "workflow_id": r["workflow_id"],
                "name": r["name"],
                "description": r.get("description"),
                "step_count": len(r.get("graph_data", {}).get("steps", [])),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in result["workflows"]
        ]
        return WorkflowListResponse(total=result.get("total", len(items)), workflows=items)
    else:
        records = workflow_store.list_all()
        items = [
            {
                "workflow_id": r["workflow_id"],
                "name": r["name"],
                "description": r.get("description"),
                "step_count": len(r["steps"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in records
        ]
        return WorkflowListResponse(total=len(items), workflows=items)


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Get a workflow by ID",
    description="Return the full definition of a stored workflow including graph_data.",
    responses={404: {"model": ErrorResponse}},
)
async def get_workflow(workflow_id: str, request: Request) -> WorkflowResponse:
    repo = getattr(request.app.state, "workflow_repo", None)
    if repo:
        # Try user_canvas first (new schema)
        try:
            canvas = await repo.get_canvas(workflow_id)
            if canvas:
                # Convert DSL to graph_data format that frontend expects
                dsl = canvas.get("dsl", {})
                graph_nodes = dsl.get("graph", {}).get("nodes", [])
                graph_edges = dsl.get("graph", {}).get("edges", [])
                components = dsl.get("components", {})

                # Convert to frontend format (x, y, type, label, config, connections)
                frontend_nodes = []
                for gn in graph_nodes:
                    nid = gn["id"]
                    comp = components.get(nid, {})
                    params = comp.get("obj", {}).get("params", {})
                    pos = gn.get("position", {})
                    downstream = comp.get("downstream", [])

                    frontend_nodes.append({
                        "id": nid,
                        "type": gn.get("type", "parse"),
                        "label": gn.get("data", {}).get("label", "Node"),
                        "x": pos.get("x", 100),
                        "y": pos.get("y", 200),
                        "tier": params.get("tier", "Normal"),
                        "config": {k: v for k, v in params.items() if k != "tier"},
                        "connections": [{"targetId": d} for d in downstream] if downstream else [],
                    })

                graph_data = {
                    "nodes": frontend_nodes,
                    "edges": graph_edges,
                    "steps": [
                        {"type": n["type"], "tier": n.get("tier", "Normal"),
                         "config": n.get("config")}
                        for n in frontend_nodes
                    ],
                }

                return WorkflowResponse(
                    workflow_id=canvas["id"],
                    name=canvas["title"],
                    description=canvas.get("description"),
                    steps=graph_data["steps"],
                    graph_data=graph_data,
                    status="published" if canvas.get("release") else "draft",
                    created_at=canvas["created_at"],
                    updated_at=canvas["updated_at"],
                )
        except Exception as e:
            logger.debug("Canvas lookup failed for %s: %s", workflow_id, e)

        # Fallback to legacy workflows table
        record = await repo.get_workflow(workflow_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
        record["steps"] = record.get("graph_data", {}).get("steps", [])
        return WorkflowResponse(**record)
    else:
        try:
            record = workflow_store.get(workflow_id)
        except WorkflowNotFoundError:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
        record["graph_data"] = None
        record["status"] = "draft"
        return WorkflowResponse(**record)


@router.put(
    "/workflows/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Update a workflow",
    description="Update the name, description, steps, or graph_data of an existing workflow.",
    responses={404: {"model": ErrorResponse}},
)
async def update_workflow(workflow_id: str, body: WorkflowUpdate, request: Request) -> WorkflowResponse:
    repo = getattr(request.app.state, "workflow_repo", None)
    if repo:
        # Try user_canvas first (new schema)
        try:
            canvas = await repo.get_canvas(workflow_id)
            if canvas:
                # Convert body to canvas update format
                dsl = canvas.get("dsl", {})
                if body.graph_data:
                    # Update graph in DSL from frontend graph_data
                    nodes = body.graph_data.get("nodes", [])
                    edges = body.graph_data.get("edges", [])
                    steps = body.graph_data.get("steps", [])

                    # Rebuild components from nodes
                    components = {}
                    path = []
                    for n in nodes:
                        nid = n.get("id", "")
                        path.append(nid)
                        components[nid] = {
                            "obj": {
                                "component_name": f"{n.get('type', 'parse').capitalize()}Processor",
                                "params": {
                                    "tier": n.get("tier", "Normal"),
                                    **(n.get("config") or {}),
                                },
                            },
                            "downstream": [c.get("targetId", "") for c in (n.get("connections") or [])],
                            "upstream": [],
                            "parent_id": None,
                        }

                    # Rebuild upstream from downstream
                    for nid, comp in components.items():
                        for ds in comp["downstream"]:
                            if ds in components:
                                components[ds]["upstream"].append(nid)

                    dsl["components"] = components
                    dsl["graph"] = {
                        "nodes": [{"id": n.get("id"), "type": n.get("type"), "position": {"x": n.get("x", 100), "y": n.get("y", 200)}, "data": {"label": n.get("label", ""), "name": f"{n.get('type', '').capitalize()}Processor", "form": n.get("config") or {}}} for n in nodes],
                        "edges": edges,
                    }
                    dsl["path"] = path

                updated = await repo.update_canvas(
                    canvas_id=workflow_id,
                    title=body.name,
                    description=body.description,
                    dsl=dsl,
                )
                if updated:
                    return WorkflowResponse(
                        workflow_id=updated["id"],
                        name=updated["title"],
                        description=updated.get("description"),
                        steps=body.graph_data.get("steps", []) if body.graph_data else [],
                        graph_data=body.graph_data,
                        status="published" if updated.get("release") else "draft",
                        created_at=updated["created_at"],
                        updated_at=updated["updated_at"],
                    )
        except Exception as e:
            logger.debug("Canvas update failed for %s: %s", workflow_id, e)

        # Fallback to legacy workflows table
        graph_data = body.graph_data
        if body.steps and graph_data:
            graph_data["steps"] = [s.model_dump() for s in body.steps]
        elif body.steps and not graph_data:
            graph_data = {"steps": [s.model_dump() for s in body.steps]}

        record = await repo.update_workflow(
            workflow_id=workflow_id,
            name=body.name,
            description=body.description,
            graph_data=graph_data,
        )
        if record is None:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
        record["steps"] = record.get("graph_data", {}).get("steps", [])
        return WorkflowResponse(**record)
    else:
        try:
            steps = [s.model_dump() for s in body.steps] if body.steps is not None else None
            record = workflow_store.update(
                workflow_id=workflow_id,
                name=body.name,
                description=body.description,
                steps=steps,
            )
        except WorkflowNotFoundError:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
        record["graph_data"] = body.graph_data
        record["status"] = "draft"
        return WorkflowResponse(**record)


@router.delete(
    "/workflows/{workflow_id}",
    status_code=204,
    summary="Delete a workflow",
    description="Remove a workflow definition from the store.",
    responses={404: {"model": ErrorResponse}},
)
async def delete_workflow(workflow_id: str, request: Request) -> None:
    repo = getattr(request.app.state, "workflow_repo", None)
    if repo:
        # Try user_canvas first (new schema)
        try:
            deleted = await repo.delete_canvas(workflow_id)
            if deleted:
                return
        except Exception:
            pass

        # Fallback to legacy workflows table
        deleted = await repo.delete_workflow(workflow_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
    else:
        try:
            workflow_store.delete(workflow_id)
        except WorkflowNotFoundError:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")


# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------

@router.post(
    "/workflows/{workflow_id}/execute",
    summary="Execute a workflow",
    description=(
        "Upload a file and execute all steps of the stored workflow sequentially. "
        "For small files, returns results synchronously. "
        "For large PDFs (above the configured threshold), dispatches to a background job "
        "and returns a `job_id` for polling."
    ),
    responses={
        200: {"model": WorkflowExecuteResponse, "description": "Synchronous execution result"},
        202: {"model": AsyncJobResponse, "description": "Dispatched to background job"},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def execute_workflow_endpoint(
    workflow_id: str,
    file: UploadFile = File(..., description="Document file to process (PDF, PNG, JPG, JPEG)."),
) -> JSONResponse:
    result = await execute_workflow(workflow_id, file)

    # Async dispatch returns job_id
    if "job_id" in result:
        return JSONResponse(content=result, status_code=202)

    status_code = 200 if result.get("success") else 500
    return JSONResponse(content=result, status_code=status_code)


# ---------------------------------------------------------------------------
# Individual step endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/workflows/{workflow_id}/steps/parse",
    response_model=ParseStepResponse,
    summary="Execute parse step",
    description=(
        "Run only the parse (OCR) step of the stored workflow on the uploaded file. "
        "Uses the tier configured in the workflow's parse step, or 'Normal' if not defined."
    ),
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def step_parse(
    workflow_id: str,
    file: UploadFile = File(..., description="Document file to OCR."),
    tier: Optional[str] = Form(default=None, description="Override the tier from the workflow definition."),
) -> ParseStepResponse:
    result = await execute_step_parse(workflow_id, file, tier_override=tier)
    return ParseStepResponse(**result)


@router.post(
    "/workflows/{workflow_id}/steps/classify",
    response_model=ClassifyStepResponse,
    summary="Execute classify step",
    description=(
        "Run only the classify step of the stored workflow on the uploaded file. "
        "Uses the classification rules stored in the workflow's classify step config."
    ),
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def step_classify(
    workflow_id: str,
    file: UploadFile = File(..., description="Document file to classify."),
    tier: Optional[str] = Form(default=None, description="Override the tier from the workflow definition."),
) -> ClassifyStepResponse:
    result = await execute_step_classify(workflow_id, file, tier_override=tier)
    return ClassifyStepResponse(**result)


@router.post(
    "/workflows/{workflow_id}/steps/extract",
    response_model=ExtractStepResponse,
    summary="Execute extract step",
    description=(
        "Run only the extract step of the stored workflow on the uploaded file. "
        "Uses the extraction schema stored in the workflow's extract step config."
    ),
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def step_extract(
    workflow_id: str,
    file: UploadFile = File(..., description="Document file to extract data from."),
    tier: Optional[str] = Form(default=None, description="Override the tier from the workflow definition."),
) -> ExtractStepResponse:
    result = await execute_step_extract(workflow_id, file, tier_override=tier)
    return ExtractStepResponse(**result)


@router.post(
    "/workflows/{workflow_id}/steps/split",
    response_model=SplitStepResponse,
    summary="Execute split step",
    description=(
        "Run only the split step of the stored workflow on the uploaded file. "
        "Uses the categories stored in the workflow's split step config."
    ),
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def step_split(
    workflow_id: str,
    file: UploadFile = File(..., description="Document file to split."),
    tier: Optional[str] = Form(default=None, description="Override the tier from the workflow definition."),
) -> SplitStepResponse:
    result = await execute_step_split(workflow_id, file, tier_override=tier)
    return SplitStepResponse(**result)


# ---------------------------------------------------------------------------
# Job polling
# ---------------------------------------------------------------------------

@router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Poll job status",
    description="Check the status and progress of a background workflow execution job.",
    responses={404: {"model": ErrorResponse}},
)
async def get_job_status(job_id: str) -> JobStatusResponse:
    status = job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return JobStatusResponse(**status)


@router.get(
    "/jobs/{job_id}/result",
    summary="Get job result",
    description=(
        "Retrieve the full result of a completed background workflow job. "
        "Returns 409 if the job is still running."
    ),
    responses={
        200: {"description": "Full workflow execution result"},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def get_job_result(job_id: str) -> JSONResponse:
    result = job_manager.get_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if result["status"] not in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is still {result['status']}. Poll /api/v1/jobs/{job_id}/status until completed.",
        )
    return JSONResponse(result.get("result", result))
