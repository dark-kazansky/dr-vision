"""
Classify service — document classification business logic.

Handles:
- File upload, deduplication, and temp storage
- OCR + classification pipeline
- Text-only classification (reusing OCR results)
- Persisting classification results
"""

import asyncio
import hashlib
import json
import logging
import os
import secrets
from typing import Optional

from agents.factory import AgentFactory
from core.middleware import FileSizeValidator
from core.schemas import ClassificationResult, ClassifyResponse
from core.storage import UPLOADS_DIR, ensure_dirs
from components.classifier import Classifier, ClassificationRule
from components.parser import Parser
from config import Config, TierConfig
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

file_size_validator = FileSizeValidator()

ensure_dirs()


def _safe_remove(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning("Failed to remove temp file %s: %s", path, e)


def _parse_rules(classification_rules: str) -> list[ClassificationRule]:
    """Parse and validate classification rules JSON."""
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

        return rules

    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid classification rules JSON: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error parsing rules: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid classification rules: {str(e)}")


def _persist_classification_result(filename: str, document_type: str, model_id: Optional[str] = None) -> None:
    """Save classification result to PostgreSQL. Raises if DB unavailable."""
    import asyncio as _aio
    from server import ocr_result_repo

    if not ocr_result_repo or not ocr_result_repo._pool:
        raise RuntimeError("Database unavailable — cannot persist classification results")

    loop = _aio.new_event_loop()
    try:
        existing = loop.run_until_complete(ocr_result_repo.get_result_by_filename(filename))
        if existing:
            loop.run_until_complete(ocr_result_repo.update_result_data(
                existing["id"],
                {"classification": {"document_type": document_type, "model": model_id}},
            ))
        else:
            loop.run_until_complete(ocr_result_repo.store_result(
                filename=filename,
                raw_text="",
                model_id=model_id,
                result_data={
                    "type": "classify",
                    "classification": {"document_type": document_type, "model": model_id},
                },
            ))
    finally:
        loop.close()
    logger.info("Classification result persisted to DB: %s → %s", filename, document_type)


async def classify_document(
    file: UploadFile,
    parser_model_id: str,
    classifier_model_id: Optional[str],
    classification_rules: str,
    tier: str,
    config: Config,
    provider: Optional[str] = None,
) -> ClassifyResponse:
    """
    Classify a document file (OCR + classify).

    Returns a ClassifyResponse ready to be returned by the router.
    """
    logger.info("=== CLASSIFY REQUEST ===")
    logger.info("File: %s", file.filename if file else "None")
    logger.info("Parser Model: %s", parser_model_id)
    logger.info("Classifier Model: %s", classifier_model_id)
    logger.info("Tier: %s", tier)
    logger.info("========================")

    # Resolve classifier model from tier config if not provided
    if not classifier_model_id:
        classifier_model_id = TierConfig.get_classifier_llm_model(tier)
        logger.info("Using classifier model from tier config: %s for tier: %s", classifier_model_id, tier)
    else:
        logger.info("Using provided classifier model: %s", classifier_model_id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_config = config.upload_config
    max_size_mb = upload_config.get("max_size_mb", 10)
    await file_size_validator.validate(file, max_size_mb)

    rules = _parse_rules(classification_rules)
    logger.info("Loaded %d classification rules: %s", len(rules), [r.doc_type for r in rules])

    # Setup directories
    uploaded_dir = str(UPLOADS_DIR)
    os.makedirs(uploaded_dir, exist_ok=True)

    # Read file content and check for duplicates
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    saved_file_path = os.path.join(uploaded_dir, file.filename)
    is_duplicate = False

    if os.path.exists(saved_file_path):
        with open(saved_file_path, "rb") as existing_file:
            existing_hash = hashlib.sha256(existing_file.read()).hexdigest()
            if existing_hash == file_hash:
                is_duplicate = True
                logger.info("Duplicate file detected: %s (hash: %s...)", file.filename, file_hash[:8])

    if not is_duplicate:
        try:
            with open(saved_file_path, "wb") as f:
                f.write(file_content)
            logger.info("File saved: %s", saved_file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    else:
        logger.info("Skipping duplicate file: %s", file.filename)

    # Save to temp folder for processing
    upload_folder = upload_config.get("folder", "uploads")
    try:
        os.makedirs(upload_folder, exist_ok=True)
        random_hex = secrets.token_hex(16)
        safe_filename = file.filename.replace("/", "_").replace("\\", "_")
        temp_filename = f"{random_hex}_{safe_filename}"
        file_path = os.path.join(upload_folder, temp_filename)

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info("Temp file created for processing: %s", file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temp file: {str(e)}")

    try:
        logger.info("Parsing document with model: %s", parser_model_id)

        if parser_model_id not in config.models:
            raise HTTPException(
                status_code=400,
                detail=f"Parser model '{parser_model_id}' not found in configuration. "
                       f"Available models: {', '.join(config.models.keys())}",
            )

        ocr_agent = AgentFactory.create_from_config(config, parser_model_id, provider_override=provider)
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = await asyncio.to_thread(parser.parse, file_path)

        if not parse_result.success:
            from core.exceptions import raise_agent_error
            raise_agent_error(parse_result, prefix="Parse failed: ")

        logger.info("Parse successful, text length: %d", len(parse_result.text))
        logger.info("Classifying with model: %s, rules: %d", classifier_model_id, len(rules))

        if classifier_model_id not in config.models:
            raise HTTPException(
                status_code=400,
                detail=f"Classifier model '{classifier_model_id}' not found in configuration. "
                       f"Available models: {', '.join(config.models.keys())}",
            )

        llm_agent = AgentFactory.create_llm_agent(classifier_model_id, config=config, provider=provider)
        classifier = Classifier(agent=llm_agent)
        classify_result = await asyncio.to_thread(classifier.classify, parse_result.text, rules)

        if not classify_result.success:
            from core.exceptions import raise_agent_error
            raise_agent_error(classify_result, prefix="Classification failed: ")

        logger.info("Classification successful: %s", classify_result.document_type)

        classification_result = ClassificationResult(
            fileName=file.filename,
            documentType=classify_result.document_type,
            confidence=classify_result.confidence,
            reasoning=classify_result.reasoning,
        )

        _persist_classification_result(file.filename, classify_result.document_type, model_id=classifier_model_id)

        return ClassifyResponse(success=True, results=[classification_result], error=None, error_type=None)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Classification error: {str(e)}")

    finally:
        _safe_remove(file_path)
        _safe_remove(saved_file_path)


async def classify_text(
    text: str,
    classification_rules: str,
    classifier_model_id: Optional[str],
    tier: str,
    classifier: Classifier,
    config: Config,
) -> ClassifyResponse:
    """
    Classify text directly without OCR (for reusing OCR results).

    Returns a ClassifyResponse ready to be returned by the router.
    """
    if classifier_model_id:
        logger.info("Using provided classifier model: %s", classifier_model_id)
        llm_agent = AgentFactory.create_llm_agent(classifier_model_id, config=config)
        classifier = Classifier(agent=llm_agent)

    rules = _parse_rules(classification_rules)

    try:
        classify_result = await asyncio.to_thread(classifier.classify, text, rules)

        if not classify_result.success:
            from core.exceptions import raise_agent_error
            raise_agent_error(classify_result)

        classification_result = ClassificationResult(
            fileName="text_input",
            documentType=classify_result.document_type,
            confidence=classify_result.confidence,
            reasoning=classify_result.reasoning,
        )

        return ClassifyResponse(success=True, results=[classification_result], error=None, error_type=None)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")
