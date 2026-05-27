"""
Document splitting router.

POST /split — split document into categorized chunks or identify document types
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from typing import Optional

from services import split_service
from core.dependencies import get_config
from core.schemas import SplitResponse
from config import Config

router = APIRouter(tags=["Splitting"])


@router.post("/split", response_model=SplitResponse)
async def split_document(
    file: UploadFile = File(...),
    categories: str = Form(...),
    allow_uncategorized: bool = Form(True),
    parser_tier: str = Form("Normal"),
    splitter_tier: str = Form("Normal"),
    split_mode: str = Form("sections"),
    provider: Optional[str] = Form(None),
    config: Config = Depends(get_config),
) -> SplitResponse:
    """
    Split a document into categorized sections or identify document-type boundaries.

    ``split_mode`` accepts ``sections`` (default) or ``document_type``.
    """
    return await split_service.split_document(
        file=file,
        categories=categories,
        allow_uncategorized=allow_uncategorized,
        splitter_tier=splitter_tier,
        split_mode=split_mode,
        provider=provider,
        config=config,
    )
