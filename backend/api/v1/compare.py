"""
Document Comparison API Router.

POST /compare — Compare two documents (text or files)
"""

import logging
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compare", tags=["Document Comparison"])


class TextCompareRequest(BaseModel):
    """Request body for text-based comparison."""

    text_a: str = Field(..., description="First document text")
    text_b: str = Field(..., description="Second document text")
    mode: str = Field(default="line", description="Comparison mode: line, word, paragraph")
    ignore_whitespace: bool = Field(default=False)
    ignore_case: bool = Field(default=False)


@router.post("/text")
async def compare_texts(
    body: TextCompareRequest,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """
    Compare two text strings and return diff analysis.

    Use this when you already have extracted text from both documents.
    """
    from components.document_comparator import DocumentComparator

    comparator = DocumentComparator(
        mode=body.mode,
        ignore_whitespace=body.ignore_whitespace,
        ignore_case=body.ignore_case,
    )
    result = comparator.compare(body.text_a, body.text_b)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return JSONResponse(content=result.to_dict())


@router.post("/files")
async def compare_files(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    mode: str = Form("line"),
    ignore_whitespace: bool = Form(False),
    ignore_case: bool = Form(False),
    _user=Depends(get_current_user),
) -> JSONResponse:
    """
    Compare two uploaded documents.

    Pipeline: OCR/parse both files → compute diff → return analysis.
    Supports: PDF, images (PNG/JPG), text files, DOCX.
    """
    import asyncio
    from core.utils import secure_save_file

    if not file_a.filename or not file_b.filename:
        raise HTTPException(status_code=400, detail="Both files are required")

    upload_folder = os.environ.get("UPLOAD_FOLDER", "uploads")

    try:
        path_a = await secure_save_file(file_a, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file A: {e}")

    try:
        path_b = await secure_save_file(file_b, upload_folder)
    except Exception as e:
        _cleanup(path_a)
        raise HTTPException(status_code=500, detail=f"Failed to save file B: {e}")

    try:
        from components.document_comparator import DocumentComparator
        from config import Config
        from services.workflow_service import _run_parse_step

        config = Config.load()

        # Parse both documents in parallel
        text_a_task = _run_parse_step(path_a, "Normal", {}, config)
        text_b_task = _run_parse_step(path_b, "Normal", {}, config)

        result_a, result_b = await asyncio.gather(text_a_task, text_b_task)

        text_a = result_a.get("text", "")
        text_b = result_b.get("text", "")

        if not text_a:
            raise HTTPException(status_code=400, detail="Could not extract text from file A")
        if not text_b:
            raise HTTPException(status_code=400, detail="Could not extract text from file B")

        # Compare
        comparator = DocumentComparator(
            mode=mode,
            ignore_whitespace=ignore_whitespace,
            ignore_case=ignore_case,
        )
        result = comparator.compare(text_a, text_b)

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        response = result.to_dict()
        response["file_a"] = file_a.filename
        response["file_b"] = file_b.filename

        return JSONResponse(content=response)

    finally:
        _cleanup(path_a)
        _cleanup(path_b)


def _cleanup(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
