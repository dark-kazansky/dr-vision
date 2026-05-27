"""
Document classification router.

POST /classify       — classify a file (OCR + classify)
POST /classify-text  — classify pre-extracted text
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from services import classify_service
from core.dependencies import get_config, get_classifier
from core.schemas import ClassifyResponse
from components.classifier import Classifier
from config import Config

router = APIRouter(tags=["Classification"])


@router.post("/classify", response_model=ClassifyResponse)
async def classify_document(
    file: UploadFile = File(...),
    parser_model_id: str = Form(...),
    classifier_model_id: Optional[str] = Form(None),
    classification_rules: str = Form(...),
    tier: str = Form("Normal"),
    max_pages: int = Form(5),
    is_multimodal: bool = Form(False),
    provider: Optional[str] = Form(None),
    config: Config = Depends(get_config),
) -> ClassifyResponse:
    """Classify a document file using OCR then an LLM classifier."""
    return await classify_service.classify_document(
        file=file,
        parser_model_id=parser_model_id,
        classifier_model_id=classifier_model_id,
        classification_rules=classification_rules,
        tier=tier,
        provider=provider,
        config=config,
    )


@router.post("/classify-text", response_model=ClassifyResponse)
async def classify_text(
    text: str = Form(...),
    classification_rules: str = Form(...),
    classifier_model_id: Optional[str] = Form(None),
    tier: str = Form("Normal"),
    classifier: Classifier = Depends(get_classifier),
    config: Config = Depends(get_config),
) -> ClassifyResponse:
    """Classify pre-extracted text without running OCR again."""
    return await classify_service.classify_text(
        text=text,
        classification_rules=classification_rules,
        classifier_model_id=classifier_model_id,
        tier=tier,
        classifier=classifier,
        config=config,
    )
