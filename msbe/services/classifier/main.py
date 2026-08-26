"""
M.DocAI MSBE Classifier service.

Implements ``/classify`` (file → OCR → classify) and ``/classify-text``
(text-only) using the monolith's Parser, Classifier and AgentFactory so
the JSON response shape matches ``ClassifyResponse`` exactly.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import secrets
import sys
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import Config, TierConfig
from core import ClassifyResponse, HealthResponse
from core.agent_factory import AgentFactory
from core.middleware import FileSizeValidator
from core.schemas import ClassificationResult
from core.utils import secure_save_file
from functions.classifier import Classifier, ClassificationRule
from functions.parser import Parser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="M.DocAI MSBE Classifier", version="0.2.0")
file_size_validator = FileSizeValidator()


def _data_dir() -> str:
    return os.getenv("MSBE_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))


def _safe_remove(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning("Failed to remove temp file %s: %s", path, e)


def get_config() -> Config:
    try:
        return Config.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {e}")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "classifier", "version": app.version})


@app.post("/classify", response_model=ClassifyResponse)
async def classify_document(
    file: UploadFile = File(...),
    parser_model_id: str = Form(...),
    classifier_model_id: Optional[str] = Form(None),
    classification_rules: str = Form(...),
    tier: str = Form("Normal"),
    max_pages: int = Form(5),
    is_multimodal: bool = Form(False),
    config: Config = Depends(get_config),
) -> ClassifyResponse:
    if not classifier_model_id:
        classifier_model_id = TierConfig.get_classifier_llm_model(tier)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_config = config.upload_config
    max_size_mb = upload_config.get("max_size_mb", 10)
    await file_size_validator.validate(file, max_size_mb)

    try:
        rules_data = json.loads(classification_rules)
        if not rules_data:
            raise HTTPException(
                status_code=400,
                detail="Classification rules cannot be empty. Please add rules in node settings.",
            )
        rules = [
            ClassificationRule(
                doc_type=rule.get("type", rule.get("doc_type", "")),
                description=rule.get("description", ""),
            )
            for rule in rules_data
        ]
        for i, rule in enumerate(rules):
            if not rule.doc_type:
                raise HTTPException(
                    status_code=400,
                    detail=f"Rule {i + 1} is missing doc_type. Please fill in all rule fields.",
                )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid classification rules JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid classification rules: {e}")

    data_dir = _data_dir()
    uploaded_dir = os.path.join(data_dir, "uploaded")
    classified_dir = os.path.join(data_dir, "classified")
    os.makedirs(uploaded_dir, exist_ok=True)
    os.makedirs(classified_dir, exist_ok=True)

    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    saved_file_path = os.path.join(uploaded_dir, file.filename)
    is_duplicate = False
    if os.path.exists(saved_file_path):
        with open(saved_file_path, "rb") as existing_file:
            existing_hash = hashlib.sha256(existing_file.read()).hexdigest()
            if existing_hash == file_hash:
                is_duplicate = True

    if not is_duplicate:
        try:
            with open(saved_file_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    upload_folder = upload_config.get("folder", "uploads")
    os.makedirs(upload_folder, exist_ok=True)
    random_hex = secrets.token_hex(16)
    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    file_path = os.path.join(upload_folder, f"{random_hex}_{safe_filename}")
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temp file: {e}")

    try:
        if parser_model_id not in config.models:
            raise HTTPException(
                status_code=400,
                detail=f"Parser model '{parser_model_id}' not found in configuration. "
                f"Available models: {', '.join(config.models.keys())}",
            )
        ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = await asyncio.to_thread(parser.parse, file_path)
        if not parse_result.success:
            raise HTTPException(status_code=500, detail=f"Parse failed: {parse_result.error}")

        if classifier_model_id not in config.models:
            raise HTTPException(
                status_code=400,
                detail=f"Classifier model '{classifier_model_id}' not found in configuration. "
                f"Available models: {', '.join(config.models.keys())}",
            )
        llm_agent = AgentFactory.create_llm_agent(classifier_model_id, config=config)
        classifier = Classifier(agent=llm_agent)
        classify_result = await asyncio.to_thread(classifier.classify, parse_result.text, rules)
        if not classify_result.success:
            raise HTTPException(status_code=500, detail=f"Classification failed: {classify_result.error}")

        classification_result = ClassificationResult(
            fileName=file.filename,
            documentType=classify_result.document_type,
            confidence=classify_result.confidence,
            reasoning=classify_result.reasoning,
        )

        result_file_path = os.path.join(classified_dir, "result.json")
        try:
            if os.path.exists(result_file_path):
                with open(result_file_path, "r", encoding="utf-8") as f:
                    results_data = json.load(f)
            else:
                results_data = {}
            results_data[file.filename] = classify_result.document_type
            with open(result_file_path, "w", encoding="utf-8") as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Failed to save result to result.json: %s", e)

        return ClassifyResponse(
            success=True, results=[classification_result], error=None, error_type=None
        )
    finally:
        _safe_remove(file_path)
        _safe_remove(saved_file_path)


@app.post("/classify-text", response_model=ClassifyResponse)
async def classify_text(
    text: str = Form(...),
    classification_rules: str = Form(...),
    classifier_model_id: Optional[str] = Form(None),
    tier: str = Form("Normal"),
    config: Config = Depends(get_config),
) -> ClassifyResponse:
    if not classifier_model_id:
        classifier_model_id = TierConfig.get_classifier_llm_model(tier)
    try:
        rules_data = json.loads(classification_rules)
        rules = [
            ClassificationRule(
                doc_type=rule.get("type", rule.get("doc_type", "")),
                description=rule.get("description", ""),
            )
            for rule in rules_data
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid classification rules: {e}")

    try:
        llm_agent = AgentFactory.create_llm_agent(classifier_model_id, config=config)
        classifier = Classifier(agent=llm_agent)
        classify_result = await asyncio.to_thread(classifier.classify, text, rules)
        if not classify_result.success:
            raise HTTPException(status_code=500, detail=classify_result.error)

        classification_result = ClassificationResult(
            fileName="text_input",
            documentType=classify_result.document_type,
            confidence=classify_result.confidence,
            reasoning=classify_result.reasoning,
        )
        return ClassifyResponse(
            success=True, results=[classification_result], error=None, error_type=None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {e}")
