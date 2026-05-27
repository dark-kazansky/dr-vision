"""
Structured data extraction router.

POST /extract           — extract from a file (OCR + extract)
POST /extract-text      — extract from pre-extracted text
POST /generate-schema   — AI-generated extraction schema
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from services import extract_service
from core.dependencies import get_config, get_extractor
from components.extractor import Extractor
from config import Config

router = APIRouter(tags=["Extraction"])


@router.post("/generate-schema")
async def generate_schema(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None),
    tier: str = Form("Normal"),
    config: Config = Depends(get_config),
) -> JSONResponse:
    """Generate an extraction schema from a natural-language description."""
    result = await extract_service.generate_schema(
        prompt=prompt,
        file=file,
        tier=tier,
        config=config,
    )
    return JSONResponse(result)


@router.post("/extract")
async def extract_data(
    file: UploadFile = File(...),
    parser_model_id: str = Form(...),
    extractor_model_id: str = Form("qwen3-max"),
    extraction_schema: str = Form(...),
    extraction_target: str = Form("document"),
    generate_schema: bool = Form(False),
    schema_prompt: Optional[str] = Form(None),
    provider: Optional[str] = Form(None),
    config: Config = Depends(get_config),
) -> JSONResponse:
    """OCR a document then extract structured data according to a schema."""
    result = await extract_service.extract_from_file(
        file=file,
        parser_model_id=parser_model_id,
        extractor_model_id=extractor_model_id,
        extraction_schema=extraction_schema,
        extraction_target=extraction_target,
        use_generated_schema=generate_schema,
        schema_prompt=schema_prompt,
        provider=provider,
        config=config,
    )
    return JSONResponse(result)


@router.post("/extract-text")
async def extract_text(
    text: str = Form(...),
    extraction_schema: str = Form(...),
    extraction_target: str = Form("document"),
    extractor_model_id: str = Form("gemini-2.5-flash"),
    tier: str = Form("Normal"),
    extractor: Extractor = Depends(get_extractor),
    config: Config = Depends(get_config),
) -> JSONResponse:
    """Extract structured data from pre-extracted text without running OCR."""
    result = await extract_service.extract_from_text(
        text=text,
        extraction_schema=extraction_schema,
        extraction_target=extraction_target,
        extractor_model_id=extractor_model_id,
        extractor=extractor,
        config=config,
    )
    return JSONResponse(result)
