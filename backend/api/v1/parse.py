"""
OCR / document parsing router.

POST /parse  (also aliased as /ocr for backward compatibility)
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from services import parse_service
from core.dependencies import get_config
from config import Config

router = APIRouter(tags=["OCR / Parse"])


@router.post("/ocr")
@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    force_ocr: bool = Form(False),
    parse_formatting: bool = Form(True),
    process_all_pages: bool = Form(True),
    tier: str = Form("Normal"),
    provider: Optional[str] = Form(None),
    extraction_enabled: bool = Form(False),
    extraction_target: Optional[str] = Form(None),
    extraction_schema: Optional[str] = Form(None),
    extractor_model: Optional[str] = Form("qwen3-max"),
    config: Config = Depends(get_config),
) -> JSONResponse:
    """
    Parse a document and extract text, with optional structured extraction.

    Supports both ``/ocr`` (legacy) and ``/parse`` paths.
    For large PDFs (above the configured threshold) the job is dispatched to a
    background thread and a ``job_id`` is returned for polling.
    """
    result = await parse_service.parse_document(
        file=file,
        model_id=model_id,
        force_ocr=force_ocr,
        parse_formatting=parse_formatting,
        extraction_enabled=extraction_enabled,
        extraction_target=extraction_target,
        extraction_schema=extraction_schema,
        extractor_model=extractor_model,
        provider=provider,
        config=config,
    )
    return JSONResponse(result)
