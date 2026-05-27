"""
Saved-files router.

GET /list-saved-files      — list all processed files
GET /raw-ocr/{filename}    — read raw OCR text
GET /parsed/{filename}     — download parsed DOCX
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from services import saved_files_service

router = APIRouter(tags=["Saved Files"])


@router.get("/list-saved-files")
async def list_saved_files() -> JSONResponse:
    """Return a list of all saved OCR files with metadata."""
    return JSONResponse(saved_files_service.list_saved_files())


@router.get("/raw-ocr/{filename}")
async def get_raw_ocr(filename: str) -> JSONResponse:
    """Read and return the content of a raw OCR text file."""
    return JSONResponse(saved_files_service.get_raw_ocr(filename))


@router.get("/parsed/{filename}")
async def get_parsed_docx(filename: str) -> FileResponse:
    """Download a parsed DOCX file."""
    return saved_files_service.get_parsed_docx(filename)
