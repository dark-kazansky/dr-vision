"""
Table Recognition API Router.

POST /table/recognize — Detect table structure and extract cells.
GET  /table/models    — Get model info and availability.
"""

import os
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from core.utils import secure_save_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/table", tags=["Table Recognition"])

# Allowed file extensions
TABLE_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}


@router.post("/recognize")
async def recognize_table(
    file: UploadFile = File(...),
    threshold: float = Form(0.3),
    scale_factor: int = Form(3),
    output_format: str = Form("json"),
    use_layout_detection: bool = Form(True),
) -> JSONResponse:
    """
    Detect table structure and extract cells from a document.

    Identifies table regions, then detects rows, columns, headers,
    and spanning cells within each table.

    Args:
        file: Image (PNG/JPG) or PDF file containing tables
        threshold: Confidence threshold (0.0-1.0, default 0.3)
        scale_factor: PDF rendering scale (1-5, default 3)
        output_format: Output format — json, csv, markdown, html (default json)
        use_layout_detection: Whether to auto-detect table regions (default True)

    Returns:
        JSON with detected tables, cells, and optional formatted output
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    # Validate file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in TABLE_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '.{ext}'. Allowed: {', '.join(TABLE_ALLOWED_EXTENSIONS)}",
        )

    # Validate parameters
    threshold = max(0.05, min(1.0, threshold))
    scale_factor = max(1, min(5, scale_factor))
    valid_formats = {"json", "csv", "markdown", "html", "all"}
    if output_format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid output_format. Valid: {', '.join(valid_formats)}",
        )

    # Save file temporarily
    upload_folder = os.environ.get("UPLOAD_FOLDER", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        from components.table_recognizer import TableRecognizeComponent

        component = TableRecognizeComponent(
            threshold=threshold,
            scale_factor=scale_factor,
            use_layout_detection=use_layout_detection,
        )
        result = component.recognize(file_path)

        if not result.success:
            status_code = 500
            if result.error_type == "validation_error":
                status_code = 400
            elif result.error_type == "model_not_found":
                status_code = 503
            raise HTTPException(status_code=status_code, detail=result.error)

        # Build response based on output format
        response = result.to_dict()

        # Add formatted output
        if output_format in ("csv", "all"):
            response["csv"] = [t.to_csv() for t in result.tables]
        if output_format in ("markdown", "all"):
            response["markdown"] = [t.to_markdown() for t in result.tables]
        if output_format in ("html", "all"):
            response["html"] = [t.to_html() for t in result.tables]

        return JSONResponse(content=response)

    finally:
        # Cleanup temp file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass


@router.post("/recognize/csv")
async def recognize_table_csv(
    file: UploadFile = File(...),
    threshold: float = Form(0.3),
    scale_factor: int = Form(3),
    table_index: int = Form(0),
) -> PlainTextResponse:
    """
    Detect table and return as CSV directly.

    Convenience endpoint that returns the first (or specified) table as CSV text.
    Useful for direct integration with spreadsheet tools.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in TABLE_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type '.{ext}'")

    upload_folder = os.environ.get("UPLOAD_FOLDER", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        from components.table_recognizer import TableRecognizeComponent

        component = TableRecognizeComponent(
            threshold=threshold,
            scale_factor=scale_factor,
        )
        result = component.recognize(file_path)

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        if not result.tables:
            raise HTTPException(status_code=404, detail="No tables detected in document")

        if table_index >= len(result.tables):
            raise HTTPException(
                status_code=400,
                detail=f"table_index {table_index} out of range (found {len(result.tables)} tables)",
            )

        csv_content = result.tables[table_index].to_csv()
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=table_{table_index}.csv"},
        )

    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass


@router.get("/models")
async def get_table_models() -> JSONResponse:
    """Get information about available table recognition models."""
    from deepdoc.model_manager import get_model_info, is_model_available

    info = get_model_info()
    info["table_model_available"] = is_model_available("tsr.onnx")
    return JSONResponse(content=info)


@router.post("/convert-markdown")
async def convert_to_markdown(
    file: UploadFile = File(...),
) -> JSONResponse:
    """
    Convert a document with tables to Markdown using Microsoft MarkItDown.

    Best for native-format files (XLSX, DOCX, CSV, HTML) where table structure
    is embedded in the file format. For scanned documents, use /table/recognize instead.

    Supported: XLSX, DOCX, PPTX, CSV, HTML, PDF (text-based), and more.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_folder = os.environ.get("UPLOAD_FOLDER", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        from components.markdown_converter import MarkdownConverter

        converter = MarkdownConverter()
        result = converter.convert(file_path)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        return JSONResponse(content=result.to_dict())

    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
