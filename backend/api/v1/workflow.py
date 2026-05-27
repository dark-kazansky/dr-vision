"""
Workflow router.

POST /workflow/execute   — execute a multi-step pipeline
POST /condition/evaluate — evaluate branching conditions
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from services import workflow_service
from core.dependencies import get_config
from config import Config

router = APIRouter(tags=["Workflow"])


@router.post("/condition/evaluate")
async def evaluate_condition(
    conditions: str = Form(...),
    previous_result: str = Form(...),
    field_name: str = Form("document_type"),
) -> JSONResponse:
    """
    Evaluate a list of conditions against the result of a previous workflow step.

    Returns the index of the first matching condition, or ``null`` for the else branch.
    """
    result = workflow_service.evaluate_conditions(
        conditions_json=conditions,
        previous_result_json=previous_result,
        field_name=field_name,
    )
    return JSONResponse(result)


@router.post("/workflow/execute")
async def execute_workflow(
    file: UploadFile = File(...),
    workflow: str = Form(...),
    config: Config = Depends(get_config),
) -> JSONResponse:
    """
    Execute a sequential pipeline of steps (parse → classify → extract → split).

    Returns results for each completed step, or an error with partial results.
    """
    result = await workflow_service.execute_workflow(
        file=file,
        workflow_json=workflow,
        config=config,
    )
    status_code = 200 if result.get("success") else 500
    return JSONResponse(content=result, status_code=status_code)
