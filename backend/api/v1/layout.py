"""
Layout Recognition API Router.

POST /layout/recognize — Detect document layout structure.
GET /layout/models — Get model info and availability.
"""

import os
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from core.utils import secure_save_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/layout", tags=["Layout Recognition"])

# Allowed file extensions for layout recognition
LAYOUT_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}


@router.post("/recognize")
async def recognize_layout(
    file: UploadFile = File(...),
    threshold: float = Form(0.2),
    scale_factor: int = Form(3),
) -> JSONResponse:
    """
    Detect document layout structure.

    Identifies regions such as text blocks, titles, figures, tables,
    equations, headers, footers, and captions in document images or PDFs.

    Args:
        file: Image (PNG/JPG) or PDF file
        threshold: Confidence threshold (0.0-1.0, default 0.2)
        scale_factor: PDF rendering scale (1-5, default 3)

    Returns:
        JSON with detected layout regions, page count, and summary
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    # Validate file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in LAYOUT_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '.{ext}'. Allowed: {', '.join(LAYOUT_ALLOWED_EXTENSIONS)}",
        )

    # Validate parameters
    threshold = max(0.01, min(1.0, threshold))
    scale_factor = max(1, min(5, scale_factor))

    # Save file temporarily
    upload_folder = os.environ.get("UPLOAD_FOLDER", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        from components.layout_recognizer import LayoutRecognizeComponent

        component = LayoutRecognizeComponent(
            threshold=threshold,
            scale_factor=scale_factor,
        )
        result = component.recognize(file_path)

        if not result.success:
            status_code = 500
            if result.error_type == "validation_error":
                status_code = 400
            elif result.error_type == "model_not_found":
                status_code = 503
            raise HTTPException(status_code=status_code, detail=result.error)

        return JSONResponse(content=result.to_dict())

    finally:
        # Cleanup temp file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass


@router.get("/models")
async def get_layout_models() -> JSONResponse:
    """Get information about available layout recognition models."""
    from deepdoc.model_manager import get_model_info

    info = get_model_info()
    return JSONResponse(content=info)
