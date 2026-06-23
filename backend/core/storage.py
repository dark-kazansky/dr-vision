"""
Centralized storage paths for Doc Intelligence.

All uploaded files and processing results are stored under a single
root directory: ``dataResult/`` (sibling of the backend folder).

Structure:
    dataResult/
    ├── uploads/          ← temp files during processing (auto-cleaned)
    ├── raw_ocr/          ← raw OCR text output (.txt)
    ├── parsed/           ← formatted DOCX output
    ├── extracted/        ← structured extraction JSON
    ├── classified/       ← classification result JSON
    └── splited/          ← split result JSON
"""

import os
from pathlib import Path

# Root of the repository (two levels up from backend/core/)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Single top-level data directory
DATA_ROOT = _REPO_ROOT / "dataResult"

# Sub-directories
UPLOADS_DIR   = DATA_ROOT / "uploads"
RAW_OCR_DIR   = DATA_ROOT / "raw_ocr"
PARSED_DIR    = DATA_ROOT / "parsed"
EXTRACTED_DIR = DATA_ROOT / "extracted"
CLASSIFIED_DIR = DATA_ROOT / "classified"
SPLITED_DIR   = DATA_ROOT / "splited"


def ensure_dirs() -> None:
    """Create all storage directories if they don't exist."""
    for d in (UPLOADS_DIR, RAW_OCR_DIR, PARSED_DIR, EXTRACTED_DIR, CLASSIFIED_DIR, SPLITED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def str_path(p: Path) -> str:
    """Return path as string (convenience helper)."""
    return str(p)
