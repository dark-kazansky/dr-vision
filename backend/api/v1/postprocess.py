"""
OCR Post-processing API Router.

POST /postprocess — Post-process raw OCR text (correction + confidence scoring)
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/postprocess", tags=["OCR Post-processing"])


class PostProcessRequest(BaseModel):
    """Request body for OCR post-processing."""

    text: str = Field(..., description="Raw OCR text to post-process")
    language: str = Field(default="vi", description="Primary language (vi/en)")
    confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Words below this confidence are flagged",
    )
    enable_number_correction: bool = Field(default=True)
    enable_diacritics_correction: bool = Field(default=True)
    enable_currency_normalization: bool = Field(default=True)
    custom_rules: Optional[List[List[str]]] = Field(
        default=None,
        description="Additional [pattern, replacement] rules",
    )


@router.post("")
async def postprocess_text(body: PostProcessRequest) -> JSONResponse:
    """
    Post-process raw OCR text.

    Applies:
    - Unicode normalization
    - Whitespace cleanup
    - Number correction (O→0, l→1 in numeric contexts)
    - Vietnamese diacritics correction
    - Currency/unit normalization
    - Per-word confidence scoring

    Returns corrected text, per-word confidence scores, and list of corrections made.
    """
    from components.ocr_postprocessor import OCRPostProcessor

    # Convert custom rules from list of lists to list of tuples
    custom_rules: List[Tuple[str, str]] = []
    if body.custom_rules:
        for rule in body.custom_rules:
            if len(rule) >= 2:
                custom_rules.append((rule[0], rule[1]))

    processor = OCRPostProcessor(
        language=body.language,
        confidence_threshold=body.confidence_threshold,
        enable_number_correction=body.enable_number_correction,
        enable_diacritics_correction=body.enable_diacritics_correction,
        enable_currency_normalization=body.enable_currency_normalization,
        custom_rules=custom_rules,
    )

    result = processor.process(body.text)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return JSONResponse(content=result.to_dict())
