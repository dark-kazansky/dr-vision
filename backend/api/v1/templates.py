"""
Template Matching API Router.

CRUD:
  POST   /templates           — Create a new template
  GET    /templates           — List templates
  GET    /templates/{id}      — Get template details
  PUT    /templates/{id}      — Update a template
  DELETE /templates/{id}      — Delete a template

Matching:
  POST   /templates/match     — Match document text to best template
  POST   /templates/{id}/extract — Apply template schema to extract from file
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth.dependencies import get_current_user
from services.template_service import template_service
from services.template_matcher import template_matcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Template Matching"])


# =============================================================================
# Request Models
# =============================================================================


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    document_type: str = Field(..., min_length=1)
    description: str = ""
    match_rules: dict = Field(default_factory=dict)
    extraction_schema: dict = Field(default_factory=lambda: {"fields": []})
    processing_config: Optional[dict] = None


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    document_type: Optional[str] = None
    description: Optional[str] = None
    match_rules: Optional[dict] = None
    extraction_schema: Optional[dict] = None
    processing_config: Optional[dict] = None


class TemplateMatchRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Document text to match")
    document_type: Optional[str] = Field(None, description="Pre-classified type (optional)")


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.post("", status_code=201)
async def create_template(
    body: TemplateCreateRequest,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """Create a new extraction template."""
    template = template_service.create(
        name=body.name,
        document_type=body.document_type,
        description=body.description,
        match_rules=body.match_rules,
        extraction_schema=body.extraction_schema,
        processing_config=body.processing_config,
    )
    return JSONResponse(status_code=201, content=template.to_dict())


@router.get("")
async def list_templates(
    document_type: Optional[str] = None,
    include_builtin: bool = True,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """List all templates, optionally filtered by document_type."""
    templates = template_service.list_all(
        document_type=document_type,
        include_builtin=include_builtin,
    )
    return JSONResponse(content={
        "templates": [t.to_dict() for t in templates],
        "total": len(templates),
    })


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """Get a template by ID."""
    template = template_service.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return JSONResponse(content=template.to_dict())


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    body: TemplateUpdateRequest,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """Update an existing template."""
    template = template_service.update(
        template_id=template_id,
        name=body.name,
        description=body.description,
        document_type=body.document_type,
        match_rules=body.match_rules,
        extraction_schema=body.extraction_schema,
        processing_config=body.processing_config,
    )
    if template is None:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_id}' not found or is built-in (cannot modify)",
        )
    return JSONResponse(content=template.to_dict())


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """Delete a template (cannot delete built-ins)."""
    success = template_service.delete(template_id)
    if not success:
        template = template_service.get(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
        raise HTTPException(status_code=403, detail="Cannot delete built-in templates")
    return JSONResponse(content={"deleted": True, "template_id": template_id})


# =============================================================================
# Matching Endpoints
# =============================================================================


@router.post("/match")
async def match_template(
    body: TemplateMatchRequest,
    _user=Depends(get_current_user),
) -> JSONResponse:
    """
    Match document text to the best extraction template.

    Returns ranked matches with confidence scores.
    If document_type is provided (from prior classification), it boosts matching.
    """
    result = template_matcher.match(
        text=body.text,
        document_type=body.document_type,
    )
    return JSONResponse(content=result.to_dict())


@router.post("/{template_id}/extract")
async def extract_with_template(
    request: Request,
    template_id: str,
    file: UploadFile = File(...),
    _user=Depends(get_current_user),
) -> JSONResponse:
    """
    Apply a template's extraction schema to a document.

    Runs: OCR/parse → Extract (using template's schema) → Return structured fields.
    Uses the template's processing_config for tier and language settings.
    """
    from core.utils import secure_save_file

    template = template_service.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Save file
    upload_folder = os.environ.get("UPLOAD_FOLDER", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        from config import Config
        from services.workflow_service import _run_parse_step, _run_extract_step

        config = Config.load()
        proc_config = template.processing_config
        tier = proc_config.get("tier", "Normal")

        # Step 1: Parse (OCR)
        parse_result = await _run_parse_step(file_path, tier, {}, config)
        text = parse_result.get("text", "")

        if not text:
            return JSONResponse(content={
                "success": False,
                "error": "No text could be extracted from document",
                "template_id": template_id,
            })

        # Step 2: Extract using template schema
        extract_config = {
            "schema": template.extraction_schema,
        }
        extract_result = await _run_extract_step(file_path, tier, extract_config, config)

        return JSONResponse(content={
            "success": True,
            "template_id": template_id,
            "template_name": template.name,
            "document_type": template.document_type,
            "extracted_fields": extract_result.get("fields", {}),
            "raw_text_length": len(text),
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass


@router.post("/auto-extract")
async def auto_extract(
    request: Request,
    file: UploadFile = File(...),
    _user=Depends(get_current_user),
) -> JSONResponse:
    """
    Auto-detect document type and extract using the best matching template.

    Pipeline: Parse → Match template → Extract with template schema.
    Returns extracted fields plus the matched template info.
    """
    from core.utils import secure_save_file

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    upload_folder = os.environ.get("UPLOAD_FOLDER", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        from config import Config
        from services.workflow_service import _run_parse_step, _run_extract_step

        config = Config.load()

        # Step 1: Parse
        parse_result = await _run_parse_step(file_path, "Normal", {}, config)
        text = parse_result.get("text", "")

        if not text:
            return JSONResponse(content={
                "success": False,
                "error": "No text extracted from document",
                "matched_template": None,
            })

        # Step 2: Match template
        match_result = template_matcher.match(text=text)

        if not match_result.best_match:
            return JSONResponse(content={
                "success": False,
                "error": "No matching template found",
                "matched_template": None,
                "all_matches": [m.to_dict() for m in match_result.all_matches],
            })

        # Step 3: Extract with matched template
        template = template_service.get(match_result.best_match.template_id)
        if template is None:
            return JSONResponse(content={
                "success": False,
                "error": "Matched template not found",
            })

        tier = template.processing_config.get("tier", "Normal")
        extract_config = {"schema": template.extraction_schema}
        extract_result = await _run_extract_step(file_path, tier, extract_config, config)

        return JSONResponse(content={
            "success": True,
            "matched_template": match_result.best_match.to_dict(),
            "template_name": template.name,
            "document_type": template.document_type,
            "confidence": match_result.best_match.confidence,
            "extracted_fields": extract_result.get("fields", {}),
            "all_matches": [m.to_dict() for m in match_result.all_matches],
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-extraction failed: {e}")

    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
