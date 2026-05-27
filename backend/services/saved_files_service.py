"""
Saved-files service — file listing and retrieval logic.
"""

import logging
import os

from fastapi import HTTPException
from fastapi.responses import FileResponse

from core.utils import validate_file_path

logger = logging.getLogger(__name__)

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_DATA_DIR = os.path.join(_BACKEND_DIR, "data")


def list_saved_files() -> dict:
    """Return a sorted list of all saved OCR files with metadata."""
    raw_ocr_dir = os.path.join(_DATA_DIR, "raw_ocr")
    parsed_dir = os.path.join(_DATA_DIR, "parsed")

    files = []

    if os.path.exists(raw_ocr_dir):
        for filename in os.listdir(raw_ocr_dir):
            if filename.endswith(".txt") and filename != ".gitkeep":
                base_name = filename[:-4]
                file_path = os.path.join(raw_ocr_dir, filename)
                docx_path = os.path.join(parsed_dir, f"{base_name}.docx")

                files.append(
                    {
                        "filename": base_name,
                        "raw_ocr": {
                            "exists": True,
                            "path": f"/raw-ocr/{base_name}",
                            "size": os.path.getsize(file_path),
                        },
                        "parsed": {
                            "exists": os.path.exists(docx_path),
                            "path": f"/parsed/{base_name}" if os.path.exists(docx_path) else None,
                            "size": os.path.getsize(docx_path) if os.path.exists(docx_path) else 0,
                        },
                        "created_at": os.path.getctime(file_path),
                    }
                )

    files.sort(key=lambda x: x["created_at"], reverse=True)
    return {"success": True, "count": len(files), "files": files}


def get_raw_ocr(filename: str) -> dict:
    """Read and return the content of a raw OCR text file."""
    raw_ocr_dir = os.path.join(_DATA_DIR, "raw_ocr")
    validate_file_path(f"{filename}.txt", raw_ocr_dir)
    file_path = os.path.join(raw_ocr_dir, f"{filename}.txt")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Raw OCR file not found: {filename}.txt")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "filename": f"{filename}.txt", "content": content, "size": len(content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


def get_parsed_docx(filename: str) -> FileResponse:
    """Return a DOCX file as a download response."""
    parsed_dir = os.path.join(_DATA_DIR, "parsed")
    validate_file_path(f"{filename}.docx", parsed_dir)
    file_path = os.path.join(parsed_dir, f"{filename}.docx")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Parsed DOCX file not found: {filename}.docx")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{filename}.docx",
    )
