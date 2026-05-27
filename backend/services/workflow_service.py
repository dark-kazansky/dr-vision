"""
Workflow service — multi-step pipeline and condition evaluation logic.

Handles:
- Condition evaluation against previous step results
- Sequential execution of parse / classify / extract / split steps
"""

import asyncio
import json
import logging
from typing import Optional

from agents.factory import AgentFactory
from core.middleware import FileSizeValidator
from core.schemas import ExtractionConfig, ExtractionTarget, FieldType, SchemaField
from core.utils import allowed_file, secure_save_file
from components.classifier import Classifier, ClassificationRule
from components.condition_evaluator import Condition, ConditionEvaluator, ConditionOperator
from components.extractor import Extractor
from components.parser import Parser
from components.splitter import ChunkCategory, Splitter
from config import Config, TierConfig
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

file_size_validator = FileSizeValidator()


def _safe_remove(path: str) -> None:
    import os
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning("Failed to remove temp file %s: %s", path, e)


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

def evaluate_conditions(conditions_json: str, previous_result_json: str, field_name: str) -> dict:
    """
    Evaluate a list of conditions against a previous workflow result.

    Returns a dict with ``success``, ``matched_index``, and ``is_else``.
    """
    try:
        conditions_data = json.loads(conditions_json)
        condition_list = [
            Condition(
                operator=ConditionOperator(cond["operator"]),
                value=cond.get("value"),
                valueMin=cond.get("valueMin"),
                valueMax=cond.get("valueMax"),
            )
            for cond in conditions_data
        ]

        result_data = json.loads(previous_result_json)

        evaluator = ConditionEvaluator()
        eval_result = evaluator.evaluate_from_previous_result(result_data, condition_list, field_name)

        if not eval_result.success:
            raise HTTPException(status_code=500, detail=eval_result.error)

        return {
            "success": True,
            "matched_index": eval_result.matched_index,
            "is_else": eval_result.matched_index is None,
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Condition evaluation failed: {str(e)}")


# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------

async def execute_workflow(file: UploadFile, workflow_json: str, config: Config) -> dict:
    """
    Execute a multi-step workflow pipeline on a single file.

    Returns a dict with ``success``, ``results``, and ``filename``.
    """
    import os

    try:
        workflow_data = json.loads(workflow_json)
        steps = workflow_data.get("steps", [])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid workflow: {str(e)}")

    if not steps:
        raise HTTPException(status_code=400, detail="Workflow must have at least one step")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get("allowed_extensions", []))

    if not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")

    max_size_mb = upload_config.get("max_size_mb", 10)
    await file_size_validator.validate(file, max_size_mb)

    upload_folder = upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    results = []

    try:
        for step in steps:
            step_type = step.get("type")
            step_tier = step.get("tier", "Normal")
            step_config = step.get("config", {})

            if step_type == "parse":
                result = await _run_parse_step(file_path, step_tier, step_config, config)
            elif step_type == "classify":
                result = await _run_classify_step(file_path, step_tier, step_config, config)
            elif step_type == "extract":
                result = await _run_extract_step(file_path, step_tier, step_config, config)
            elif step_type == "split":
                result = await _run_split_step(file_path, step_tier, step_config, config)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown step type: {step_type}")

            results.append({"step": step_type, "tier": step_tier, "result": result})

    except Exception as e:
        return {"success": False, "error": str(e), "completed_steps": results}

    finally:
        _safe_remove(file_path)

    return {"success": True, "results": results, "filename": file.filename}


# ---------------------------------------------------------------------------
# Step helpers (private)
# ---------------------------------------------------------------------------

async def _run_parse_step(file_path: str, tier: str, step_config: dict, config: Config) -> dict:
    model_id = TierConfig.get_parser_model(tier)
    ocr_agent = AgentFactory.create_from_config(config, model_id)
    parser = Parser(ocr_agent=ocr_agent)
    result = await asyncio.to_thread(parser.parse, file_path)

    if not result.success:
        raise Exception(f"Parse failed: {result.error}")

    return {"text": result.text, "file_type": result.file_type, "pages": result.pages}


async def _run_classify_step(file_path: str, tier: str, step_config: dict, config: Config) -> dict:
    parser_model_id = TierConfig.get_parser_model(tier)
    ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
    parser = Parser(ocr_agent=ocr_agent)
    parse_result = await asyncio.to_thread(parser.parse, file_path)

    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")

    classifier_model_id = TierConfig.get_classifier_llm_model(tier)
    llm_agent = AgentFactory.create_llm_agent(classifier_model_id, config=config)
    classifier = Classifier(agent=llm_agent)

    rules = [
        ClassificationRule(doc_type=rule["doc_type"], description=rule["description"])
        for rule in step_config.get("rules", [])
    ]

    classify_result = await asyncio.to_thread(classifier.classify, parse_result.text, rules)

    if not classify_result.success:
        raise Exception(f"Classify failed: {classify_result.error}")

    return {
        "document_type": classify_result.document_type,
        "confidence": classify_result.confidence,
        "reasoning": classify_result.reasoning,
    }


async def _run_extract_step(file_path: str, tier: str, step_config: dict, config: Config) -> dict:
    parser_model_id = TierConfig.get_parser_model(tier)
    ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
    parser = Parser(ocr_agent=ocr_agent)
    parse_result = await asyncio.to_thread(parser.parse, file_path)

    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")

    extractor_model_id = TierConfig.get_extractor_model(tier)
    llm_agent = AgentFactory.create_llm_agent(extractor_model_id, config=config)
    extractor = Extractor(agent=llm_agent)

    schema_data = step_config.get("schema", {})
    extraction_config = ExtractionConfig(
        target=ExtractionTarget(step_config.get("target", "document")),
        fields=[
            SchemaField(
                name=field["name"],
                type=FieldType(field["type"]),
                description=field.get("description", ""),
                required=field.get("required", False),
            )
            for field in schema_data.get("fields", [])
        ],
    )

    extract_result = await asyncio.to_thread(extractor.extract, parse_result.text, extraction_config)

    if not extract_result.success:
        raise Exception(f"Extract failed: {extract_result.error}")

    return {"structured_data": extract_result.structured_data, "field_errors": extract_result.field_errors}


async def _run_split_step(file_path: str, tier: str, step_config: dict, config: Config) -> dict:
    parser_model_id = TierConfig.get_parser_model(tier)
    splitter_model_id = TierConfig.get_splitter_model(tier)

    ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
    parser = Parser(ocr_agent=ocr_agent)
    parse_result = await asyncio.to_thread(parser.parse, file_path)

    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")

    vlm_agent = AgentFactory.create_vlm_agent(splitter_model_id, config=config)
    splitter = Splitter(agent=vlm_agent)

    categories = [
        ChunkCategory(name=cat["name"], description=cat["description"], order=cat.get("order", 0))
        for cat in step_config.get("categories", [])
    ]

    split_result = await asyncio.to_thread(
        splitter.split, file_path, categories,
        allow_uncategorized=step_config.get("allow_uncategorized", True),
    )

    if not split_result.success:
        raise Exception(f"Split failed: {split_result.error}")

    return {
        "chunks": [
            {"content": c.content, "category": c.category, "page_number": c.page_number, "confidence": c.confidence}
            for c in split_result.chunks or []
        ],
        "unknown_chunks": [
            {"content": c.content, "category": c.category, "page_number": c.page_number}
            for c in split_result.unknown_chunks or []
        ],
    }
