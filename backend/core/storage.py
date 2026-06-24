"""
Centralized storage paths for Doc Intelligence.

Only temporary upload storage remains on the filesystem.
All processing results are stored in PostgreSQL.
"""

from pathlib import Path

# Root of the repository (two levels up from backend/core/)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Temporary upload directory — files are removed after processing
UPLOADS_DIR = _REPO_ROOT / "backend" / "data" / "uploaded"


def ensure_dirs() -> None:
    """Create the uploads directory if it doesn't exist."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
