"""
Full-text Search router — search across stored OCR document content.

GET /api/v1/search?q=...           — full-text search over OCR raw_text
    Query params:
        q          — free-text query (supports quoted phrases, OR, -negation)
        limit      — page size (1..200, default 20)
        offset     — pagination offset (default 0)
        date_from  — ISO 8601 timestamp, inclusive lower bound on created_at
        date_to    — ISO 8601 timestamp, inclusive upper bound on created_at

    Response:
        {
            "success": true,
            "items": [{ id, filename, model_id, provider, tier,
                        created_at, rank, snippet }],
            "total": <int>,
            "limit": <int>,
            "offset": <int>,
            "query": <str>
        }

    The ``snippet`` field contains highlight markers using control characters
    ``\\x01`` / ``\\x02`` so the frontend can HTML-escape first, then convert
    the markers to ``<mark>`` tags (XSS-safe).
"""

from typing import Optional

import logging
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


def _get_repo(request: Request):
    """Get OCR result repository from app state or raise 503."""
    repo = getattr(request.app.state, "ocr_result_repo", None)
    if repo is None:
        raise HTTPException(
            status_code=503, detail="Search database not available"
        )
    return repo


@router.get("")
async def search(
    request: Request,
    q: str = Query(default="", description="Full-text search query"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    date_from: Optional[str] = Query(
        default=None,
        description="ISO 8601 timestamp — inclusive lower bound on created_at",
    ),
    date_to: Optional[str] = Query(
        default=None,
        description="ISO 8601 timestamp — inclusive upper bound on created_at",
    ),
) -> JSONResponse:
    """Full-text search across OCR document content (feat-070)."""
    repo = _get_repo(request)
    try:
        results = await repo.search_text(
            query=q,
            limit=limit,
            offset=offset,
            date_from=date_from,
            date_to=date_to,
        )
        return JSONResponse({"success": True, **results})
    except Exception as exc:
        logger.exception("search_endpoint_failed q=%r err=%r", q, exc)
        raise
