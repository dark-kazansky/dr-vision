"""
Workflow service — multi-step pipeline and condition evaluation logic.

Handles:
- Condition evaluation against previous step results
- Sequential execution of parse / classify / extract / split steps
"""

import asyncio
import json
import logging

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
            elif step_type == "layout_recognize":
                result = await _run_layout_recognize_step(file_path, step_tier, step_config, config)
            elif step_type == "table_recognize":
                result = await _run_table_recognize_step(file_path, step_tier, step_config, config)
            elif step_type == "document_to_markdown":
                result = await _run_document_to_markdown_step(file_path, step_tier, step_config, config)
            elif step_type == "ocr_postprocess":
                result = await _run_ocr_postprocess_step(file_path, step_tier, step_config, config)
            elif step_type == "template_extract":
                result = await _run_template_extract_step(file_path, step_tier, step_config, config)
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


async def _run_layout_recognize_step(file_path: str, tier: str, step_config: dict, config: Config) -> dict:
    """Run layout recognition step in workflow pipeline."""
    from components.layout_recognizer import LayoutRecognizeComponent

    threshold = step_config.get("threshold", 0.2)
    scale_factor = step_config.get("scale_factor", 3)

    component = LayoutRecognizeComponent(
        threshold=threshold,
        scale_factor=scale_factor,
    )
    result = await asyncio.to_thread(component.recognize, file_path)

    if not result.success:
        raise Exception(f"Layout recognize failed: {result.error}")

    return result.to_dict()


async def _run_table_recognize_step(file_path: str, tier: str, step_config: dict, config: Config) -> dict:
    """Run table structure recognition step in workflow pipeline."""
    from components.table_recognizer import TableRecognizeComponent

    method = step_config.get("method", "auto")
    threshold = step_config.get("threshold", 0.3)
    scale_factor = step_config.get("scale_factor", 3)
    output_format = step_config.get("output_format", "json")
    use_layout_detection = step_config.get("use_layout_detection", True)

    # Route based on method
    if method == "markitdown":
        # Use MarkItDown for native files (XLSX, DOCX, CSV, HTML)
        from components.markdown_converter import MarkdownConverter, extract_markdown_tables

        converter = MarkdownConverter()
        md_result = await asyncio.to_thread(converter.convert, file_path)
        if not md_result.success:
            raise Exception(f"MarkItDown conversion failed: {md_result.error}")

        tables = extract_markdown_tables(md_result.markdown)
        return {
            "success": True,
            "method": "markitdown",
            "tables": [{"markdown": t, "index": i} for i, t in enumerate(tables)],
            "table_count": len(tables),
            "markdown": tables,
            "full_markdown": md_result.markdown,
        }

    elif method == "llm":
        # Use LLM-based extraction for table data
        from pathlib import Path
        ext = Path(file_path).suffix.lower()

        # Parse first to get text
        parse_result = await _run_parse_step(file_path, tier, {}, config)
        text = parse_result.get("text", "")
        if not text:
            raise Exception("No text extracted for LLM table processing")

        # Use extract step with table-specific prompt
        extract_config = {
            "schema": step_config.get("schema", {
                "fields": [
                    {"field_name": "tables", "field_type": "text", "description": "Extract all tables as structured data"},
                ]
            }),
        }
        extract_result = await _run_extract_step(file_path, tier, extract_config, config)
        return {
            "success": True,
            "method": "llm",
            "extracted": extract_result,
        }

    else:
        # Default: DeepDoc TSR (auto or deepdoc)
        # For native files, try MarkItDown first if method is "auto"
        if method == "auto":
            from pathlib import Path
            ext = Path(file_path).suffix.lower()
            if ext in (".xlsx", ".xls", ".csv", ".docx", ".html", ".htm"):
                # Native file — use MarkItDown
                from components.markdown_converter import MarkdownConverter, extract_markdown_tables

                converter = MarkdownConverter()
                md_result = await asyncio.to_thread(converter.convert, file_path)
                if md_result.success and md_result.markdown:
                    tables = extract_markdown_tables(md_result.markdown)
                    if tables:
                        return {
                            "success": True,
                            "method": "markitdown",
                            "tables": [{"markdown": t, "index": i} for i, t in enumerate(tables)],
                            "table_count": len(tables),
                            "markdown": tables,
                        }

        # Fall through to DeepDoc TSR for images/PDFs
        component = TableRecognizeComponent(
            threshold=threshold,
            scale_factor=scale_factor,
            use_layout_detection=use_layout_detection,
        )
        result = await asyncio.to_thread(component.recognize, file_path)

        if not result.success:
            raise Exception(f"Table recognize failed: {result.error}")

        output = result.to_dict()
        output["method"] = "deepdoc"

        # Add formatted output based on config
        if output_format in ("csv", "all"):
            output["csv"] = [t.to_csv() for t in result.tables]
        if output_format in ("markdown", "all"):
            output["markdown"] = [t.to_markdown() for t in result.tables]
        if output_format in ("html", "all"):
            output["html"] = [t.to_html() for t in result.tables]

        return output


async def _run_document_to_markdown_step(file_path: str, tier: str, step_config: dict, config: Config) -> dict:
    """Run document-to-markdown conversion step using Microsoft MarkItDown."""
    from components.markdown_converter import MarkdownConverter

    converter = MarkdownConverter()
    result = await asyncio.to_thread(converter.convert, file_path)

    if not result.success:
        raise Exception(f"Document to markdown conversion failed: {result.error}")

    output = result.to_dict()

    # Also extract tables separately for downstream processing
    from components.markdown_converter import extract_markdown_tables
    output["tables"] = extract_markdown_tables(result.markdown)

    return output


async def _run_ocr_postprocess_step(file_path: str, tier: str, step_config: dict, config: Config) -> dict:
    """Run OCR post-processing step — correct and score text from upstream parse."""
    from components.ocr_postprocessor import OCRPostProcessor

    # Get text from step_config (passed from upstream node) or read file
    text = step_config.get("text", "")
    if not text and file_path:
        # Try reading file as text
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            pass

    if not text:
        return {"success": True, "processed_text": "", "corrections": [], "stats": {"word_count": 0}}

    language = step_config.get("language", "vi")
    threshold = step_config.get("confidence_threshold", 0.7)

    processor = OCRPostProcessor(
        language=language,
        confidence_threshold=threshold,
    )
    result = processor.process(text)

    if not result.success:
        raise Exception(f"OCR post-processing failed: {result.error}")

    return result.to_dict()


async def _run_template_extract_step(file_path: str, tier: str, step_config: dict, config: Config) -> dict:
    """
    Run template-based extraction step.

    If template_id provided: use that template directly.
    Otherwise: auto-match based on parsed text.
    """
    from services.template_service import template_service
    from services.template_matcher import template_matcher

    template_id = step_config.get("template_id")

    # Step 1: Parse document
    parse_result = await _run_parse_step(file_path, tier, {}, config)
    text = parse_result.get("text", "")

    if not text:
        raise Exception("No text extracted from document")

    # Step 2: Get template (direct or auto-match)
    template = None
    match_info = None

    if template_id:
        template = template_service.get(template_id)
        if template is None:
            raise Exception(f"Template '{template_id}' not found")
    else:
        # Auto-match
        match_result = template_matcher.match(text=text)
        if match_result.best_match:
            template = template_service.get(match_result.best_match.template_id)
            match_info = match_result.best_match.to_dict()

    if template is None:
        return {
            "success": False,
            "error": "No matching template found",
            "text_length": len(text),
        }

    # Step 3: Extract using template schema
    extract_tier = template.processing_config.get("tier", tier)
    extract_config = {"schema": template.extraction_schema}
    extract_result = await _run_extract_step(file_path, extract_tier, extract_config, config)

    return {
        "success": True,
        "template_id": template.template_id,
        "template_name": template.name,
        "document_type": template.document_type,
        "match_info": match_info,
        "extracted_fields": extract_result.get("fields", {}),
    }
