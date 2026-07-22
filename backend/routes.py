"""
FastAPI route handlers for Dr.Vision.

New agent-based architecture:
Input → Backend API → Functions + Config → Agents → Output → Frontend
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List
import asyncio
import logging
import os
import json
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

from core import Config, ConfigurationError
from config.tier_config import TierConfig
from core.utils import allowed_file, secure_save_file, validate_file_path
from core.agent_factory import AgentFactory
from core.middleware import FileSizeValidator
from core.docx_generator import DocxGenerator
from core.dependencies import get_config, get_parser, get_classifier, get_extractor
from core.background_tasks import job_manager
from core import (
    OCRResponse, HealthResponse, ClassifyResponse,
    SplitResponse, ChunkModel, ChunkCategoryModel,
    ExtractionConfig, SchemaField, FieldType, ExtractionTarget
)
from core.schemas import DocumentTypeResult
from functions.parser import Parser
from functions.extractor import Extractor
from functions.classifier import Classifier, ClassificationRule
from functions.schema_generator import SchemaGenerator
from functions.splitter import Splitter, ChunkCategory, DocumentTypeItem
from functions.text_parser import TextParser
from functions.condition_evaluator import ConditionEvaluator, Condition, ConditionOperator


# Create API router
router = APIRouter()

# File size validator instance
file_size_validator = FileSizeValidator()


def _safe_remove(path: str) -> None:
    """Remove a file safely, logging a warning on failure instead of raising."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning("Failed to remove temp file %s: %s", path, e)


# Dependency injection functions are imported from core.dependencies
# (get_config, get_parser, get_classifier, get_extractor)


@router.get("/job/{job_id}/status")
async def get_job_status(job_id: str) -> JSONResponse:
    """
    Poll the status of a background processing job.

    Args:
        job_id: The unique job identifier returned by a background request.

    Returns:
        JSON with job_id, status, progress, created_at, completed_at.
    """
    status = job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return JSONResponse(status)


@router.get("/job/{job_id}/result")
async def get_job_result(job_id: str) -> JSONResponse:
    """
    Retrieve the result of a completed background job.

    Args:
        job_id: The unique job identifier.

    Returns:
        Full job payload including result or error.
    """
    result = job_manager.get_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if result["status"] not in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is still {result['status']}. Poll /job/{job_id}/status until completed.",
        )
    return JSONResponse(result)


@router.post("/ocr")
@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    force_ocr: bool = Form(False),
    parse_formatting: bool = Form(True),
    process_all_pages: bool = Form(True),
    tier: str = Form("Normal"),
    extraction_enabled: bool = Form(False),
    extraction_target: Optional[str] = Form(None),
    extraction_schema: Optional[str] = Form(None),
    extractor_model: Optional[str] = Form("qwen3-max"),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Parse document and extract text (with optional structured extraction).
    
    This endpoint supports both /ocr (legacy) and /parse paths.
    
    Args:
        file: Uploaded file
        model_id: OCR model ID
        force_ocr: Force OCR even for text-based PDFs
        parse_formatting: Parse markdown/HTML to plain text
        process_all_pages: Process all pages (for PDFs)
        tier: Processing tier (Rapid, Normal, Advance)
        extraction_enabled: Enable structured data extraction
        extraction_target: Extraction scope (document, page, table_row)
        extraction_schema: JSON string with extraction schema
        extractor_model: LLM model for extraction
        config: Configuration instance
        
    Returns:
        JSON response with parsed text, metadata, and optional structured data
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get('allowed_extensions', []))
    
    if not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size
    max_size_mb = upload_config.get('max_size_mb', 10)
    await file_size_validator.validate(file, max_size_mb)
    
    # Save file
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    try:
        # --- Background task check: get page count for PDFs quickly ---
        bg_config = config._config_data.get("background_tasks", {})
        bg_enabled = bg_config.get("enabled", False)
        threshold_pages = bg_config.get("threshold_pages", 5)

        page_count = None
        if bg_enabled and file_path.lower().endswith(".pdf"):
            try:
                import pypdfium2 as pdfium
                _pdf = pdfium.PdfDocument(file_path)
                try:
                    page_count = len(_pdf)
                finally:
                    _pdf.close()
            except Exception:
                page_count = None

        if bg_enabled and page_count is not None and page_count > threshold_pages:
            # Offload heavy processing to a background thread and return job ID
            job_id = job_manager.create_job()
            job_manager.update_status(job_id, "processing", progress=0.0)

            def _run_parse_in_background(
                _file_path, _filename, _model_id, _force_ocr, _parse_formatting,
                _extraction_enabled, _extraction_target, _extraction_schema,
                _extractor_model, _config, _job_id,
            ):
                try:
                    from config.tier_config import TierConfig as _TC
                    _bm, _bp = _TC.get_parser_model_spec("Normal")
                    ocr_agent = AgentFactory.create_ocr_from_spec(_bm, _bp, _config)
                    parser = Parser(ocr_agent=ocr_agent)
                    result = parser.parse(_file_path, _force_ocr)

                    if not result.success:
                        job_manager.update_status(_job_id, "failed", error=result.error)
                        return

                    job_manager.update_status(_job_id, "processing", progress=0.5)

                    text = result.text
                    if _parse_formatting:
                        text = TextParser.auto_parse(text)

                    # Save raw OCR + DOCX
                    data_dir = os.path.join(os.path.dirname(__file__), 'data')
                    raw_ocr_dir = os.path.join(data_dir, 'raw_ocr')
                    parsed_dir = os.path.join(data_dir, 'parsed')
                    os.makedirs(raw_ocr_dir, exist_ok=True)
                    os.makedirs(parsed_dir, exist_ok=True)
                    base_fn = os.path.splitext(_filename)[0]

                    try:
                        with open(os.path.join(raw_ocr_dir, f"{base_fn}.txt"), 'w', encoding='utf-8') as f:
                            f.write(result.text)
                    except Exception as e:
                        logger.warning("BG job %s: failed to save raw OCR: %s", _job_id, e)

                    try:
                        DocxGenerator().generate(
                            text=text, filename=_filename, model_id=_model_id,
                            pages=result.pages or 1, file_type=result.file_type,
                            output_path=os.path.join(parsed_dir, f"{base_fn}.docx"),
                        )
                    except Exception as e:
                        logger.warning("BG job %s: failed to create DOCX: %s", _job_id, e)

                    response_data = {
                        "success": True,
                        "text": text,
                        "parsed_text": text if _parse_formatting else None,
                        "file_type": result.file_type,
                        "is_scanned": result.is_scanned,
                        "pages": result.pages,
                        "filename": _filename,
                        "model": _model_id,
                    }

                    # Optional extraction
                    if _extraction_enabled and _extraction_schema:
                        try:
                            schema_data = json.loads(_extraction_schema)
                            fields = [
                                SchemaField(
                                    name=field['name'],
                                    type=FieldType(field['type']),
                                    description=field.get('description', ''),
                                    required=field.get('required', False),
                                )
                                for field in schema_data
                            ]
                            extraction_config = ExtractionConfig(
                                fields=fields,
                                target=ExtractionTarget(_extraction_target or "document"),
                            )
                            from config.tier_config import TierConfig as _TC
                            _em2, _ep2 = _TC.get_extractor_model_spec("Normal")
                            llm_agent = AgentFactory.create_llm_from_spec(_em2, _ep2, _config)
                            extractor = Extractor(agent=llm_agent)
                            extract_result = extractor.extract(text, extraction_config)
                            if extract_result.success:
                                response_data["extraction"] = {
                                    "success": True,
                                    "structured_data": extract_result.structured_data,
                                    "field_errors": extract_result.field_errors,
                                }
                            else:
                                response_data["extraction"] = {
                                    "success": False,
                                    "error": extract_result.error,
                                }
                        except Exception as e:
                            response_data["extraction"] = {
                                "success": False,
                                "error": f"Extraction failed: {str(e)}",
                            }

                    job_manager.update_status(_job_id, "completed", progress=1.0, result=response_data)
                except Exception as exc:
                    logger.exception("Background job %s failed", _job_id)
                    job_manager.update_status(_job_id, "failed", error=str(exc))
                finally:
                    _safe_remove(_file_path)

            thread = threading.Thread(
                target=_run_parse_in_background,
                args=(
                    file_path, file.filename, model_id, force_ocr, parse_formatting,
                    extraction_enabled, extraction_target, extraction_schema,
                    extractor_model, config, job_id,
                ),
                daemon=True,
            )
            thread.start()

            return JSONResponse({
                "success": True,
                "background": True,
                "job_id": job_id,
                "message": f"Document has {page_count} pages (threshold: {threshold_pages}). Processing in background.",
            })

        # --- Standard synchronous path (below threshold or non-PDF) ---
        # Create OCR agent
        _parser_model_id, _parser_provider = TierConfig.get_parser_model_spec(tier)
        ocr_agent = AgentFactory.create_ocr_from_spec(_parser_model_id, _parser_provider, config)
        
        # Create parser
        parser = Parser(ocr_agent=ocr_agent)
        
        # Parse file (non-blocking)
        result = await asyncio.to_thread(parser.parse, file_path, force_ocr)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Parse formatting if requested
        text = result.text
        if parse_formatting:
            text = await asyncio.to_thread(TextParser.auto_parse, text)
        
        # Save raw OCR result and create DOCX
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        raw_ocr_dir = os.path.join(data_dir, 'raw_ocr')
        parsed_dir = os.path.join(data_dir, 'parsed')
        os.makedirs(raw_ocr_dir, exist_ok=True)
        os.makedirs(parsed_dir, exist_ok=True)
        
        # Generate base filename (without extension)
        base_filename = os.path.splitext(file.filename)[0]
        
        # Save raw OCR result as text file
        raw_ocr_path = os.path.join(raw_ocr_dir, f"{base_filename}.txt")
        try:
            with open(raw_ocr_path, 'w', encoding='utf-8') as f:
                f.write(result.text)
            logger.info("Raw OCR saved: %s", raw_ocr_path)
        except Exception as e:
            logger.warning("Failed to save raw OCR: %s", e)
        
        # Convert to DOCX and save
        docx_path = os.path.join(parsed_dir, f"{base_filename}.docx")
        try:
            DocxGenerator().generate(
                text=text,
                filename=file.filename,
                model_id=model_id,
                pages=result.pages if result.pages else 1,
                file_type=result.file_type,
                output_path=docx_path,
            )
            logger.info("DOCX saved: %s", docx_path)
        except Exception as e:
            logger.warning("Failed to create DOCX: %s", e)
            import traceback
            logger.debug("DOCX creation traceback: %s", traceback.format_exc())
        
        response_data = {
            "success": True,
            "text": text,
            "parsed_text": text if parse_formatting else None,
            "file_type": result.file_type,
            "is_scanned": result.is_scanned,
            "pages": result.pages,
            "filename": file.filename,
            "model": model_id
        }
        
        # Perform extraction if enabled
        if extraction_enabled and extraction_schema:
            try:
                # Parse schema
                schema_data = json.loads(extraction_schema)
                fields = [
                    SchemaField(
                        name=field['name'],
                        type=FieldType(field['type']),
                        description=field.get('description', ''),
                        required=field.get('required', False)
                    )
                    for field in schema_data
                ]
                
                # Create extraction config
                extraction_config = ExtractionConfig(
                    fields=fields,
                    target=ExtractionTarget(extraction_target or "document")
                )
                
                # Extract data
                _ext_model, _ext_provider = TierConfig.get_extractor_model_spec(tier)
                llm_agent = AgentFactory.create_llm_from_spec(_ext_model, _ext_provider, config)
                extractor = Extractor(agent=llm_agent)
                extract_result = await asyncio.to_thread(extractor.extract, text, extraction_config)
                
                if extract_result.success:
                    # Save extraction result to file
                    extracted_dir = os.path.join(data_dir, 'extracted')
                    os.makedirs(extracted_dir, exist_ok=True)
                    
                    # Generate filename (without extension)
                    base_filename = os.path.splitext(file.filename)[0]
                    extracted_file_path = os.path.join(extracted_dir, f"{base_filename}.json")
                    
                    try:
                        extraction_output = {
                            "filename": file.filename,
                            "model": extractor_model,
                            "extraction_target": extraction_target or "document",
                            "schema": schema_data,
                            "structured_data": extract_result.structured_data,
                            "field_errors": extract_result.field_errors,
                            "timestamp": os.path.getctime(file_path) if os.path.exists(file_path) else None
                        }
                        
                        with open(extracted_file_path, 'w', encoding='utf-8') as f:
                            json.dump(extraction_output, f, indent=2, ensure_ascii=False)
                        
                        logger.info("Extraction result saved: %s", extracted_file_path)
                    except Exception as e:
                        logger.warning("Failed to save extraction result: %s", e)
                    
                    response_data["extraction"] = {
                        "success": True,
                        "structured_data": extract_result.structured_data,
                        "field_errors": extract_result.field_errors
                    }
                else:
                    response_data["extraction"] = {
                        "success": False,
                        "error": extract_result.error
                    }
            except Exception as e:
                response_data["extraction"] = {
                    "success": False,
                    "error": f"Extraction failed: {str(e)}"
                }
        
        return JSONResponse(response_data)
        
    finally:
        _safe_remove(file_path)


@router.post("/classify", response_model=ClassifyResponse)
async def classify_document(
    file: UploadFile = File(...),
    parser_model_id: str = Form(...),
    classifier_model_id: str = Form(None),  # Make optional, will use tier config if not provided
    classification_rules: str = Form(...),
    tier: str = Form("Normal"),
    max_pages: int = Form(5),
    is_multimodal: bool = Form(False),
    config: Config = Depends(get_config)
) -> ClassifyResponse:
    """
    Classify document based on rules.
    
    Args:
        file: Uploaded file
        parser_model_id: OCR model ID
        classifier_model_id: LLM model ID for classification (optional, uses tier config if not provided)
        classification_rules: JSON string with classification rules
        tier: Processing tier (Rapid, Normal, Advance)
        max_pages: Maximum number of pages to process
        is_multimodal: Whether to use multimodal processing
        config: Configuration instance
        
    Returns:
        ClassifyResponse with classification results
    """
    try:
        logger.info("=== CLASSIFY REQUEST ===")
        logger.info("File: %s", file.filename if file else "None")
        logger.info("Parser Model: %s", parser_model_id)
        logger.info("Classifier Model: %s", classifier_model_id)
        logger.info("Tier: %s", tier)
        logger.info("Rules: %s", classification_rules[:100] + "..." if len(classification_rules) > 100 else classification_rules)
        logger.info("========================")
    except Exception as e:
        logger.warning("Error logging request: %s", e)
    
    # Use tier config if classifier_model_id not provided
    if not classifier_model_id:
        from config import TierConfig
        classifier_model_id, _clf_provider = TierConfig.get_classifier_llm_model_spec(tier)
        logger.info("Using classifier model from tier config: %s for tier: %s", classifier_model_id, tier)
    else:
        _clf_provider = None
        logger.info("Using provided classifier model: %s", classifier_model_id)
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Validate file size
    upload_config = config.upload_config
    max_size_mb = upload_config.get('max_size_mb', 10)
    await file_size_validator.validate(file, max_size_mb)
    
    logger.info("Processing file: %s", file.filename)
    
    # Parse classification rules
    try:
        rules_data = json.loads(classification_rules)
        if not rules_data or len(rules_data) == 0:
            raise HTTPException(status_code=400, detail="Classification rules cannot be empty. Please add rules in node settings.")
        
        rules = [
            ClassificationRule(
                doc_type=rule.get('type', rule.get('doc_type', '')),
                description=rule.get('description', '')
            )
            for rule in rules_data
        ]
        
        # Validate that rules have doc_type
        for i, rule in enumerate(rules):
            if not rule.doc_type:
                raise HTTPException(status_code=400, detail=f"Rule {i+1} is missing doc_type. Please fill in all rule fields.")
        
        logger.info("Loaded %d classification rules: %s", len(rules), [r.doc_type for r in rules])
        
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid classification rules JSON: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error parsing rules: %s", e)
        import traceback
        logger.debug("Rules parsing traceback: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Invalid classification rules: {str(e)}")
    
    # Setup directories
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    uploaded_dir = os.path.join(data_dir, 'uploaded')
    classified_dir = os.path.join(data_dir, 'classified')
    os.makedirs(uploaded_dir, exist_ok=True)
    os.makedirs(classified_dir, exist_ok=True)
    
    # Read file content
    file_content = await file.read()
    
    # Calculate file hash for duplicate detection
    import hashlib
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check for duplicate file
    saved_file_path = os.path.join(uploaded_dir, file.filename)
    is_duplicate = False
    
    if os.path.exists(saved_file_path):
        # File with same name exists, check content hash
        with open(saved_file_path, 'rb') as existing_file:
            existing_hash = hashlib.sha256(existing_file.read()).hexdigest()
            if existing_hash == file_hash:
                is_duplicate = True
                logger.info("Duplicate file detected: %s (hash: %s...)", file.filename, file_hash[:8])
    
    # Save file only if not duplicate
    if not is_duplicate:
        try:
            with open(saved_file_path, 'wb') as f:
                f.write(file_content)
            logger.info("File saved: %s", saved_file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    else:
        logger.info("Skipping duplicate file: %s", file.filename)
    
    # Save to temp folder for processing (using already-read content)
    upload_config = config.upload_config
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        # Create upload folder if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate secure temp filename
        import secrets
        random_hex = secrets.token_hex(16)
        safe_filename = file.filename.replace('/', '_').replace('\\', '_')
        temp_filename = f"{random_hex}_{safe_filename}"
        file_path = os.path.join(upload_folder, temp_filename)
        
        # Write the already-read content to temp file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info("Temp file created for processing: %s", file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temp file: {str(e)}")
    
    try:
        # Step 1: Parse document
        logger.info("Parsing document with model: %s", parser_model_id)
        
        _p_model, _p_provider = TierConfig.get_parser_model_spec(tier)
        ocr_agent = AgentFactory.create_ocr_from_spec(_p_model, _p_provider, config)
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = await asyncio.to_thread(parser.parse, file_path)

        if not parse_result.success:
            raise HTTPException(status_code=500, detail=f"Parse failed: {parse_result.error}")

        logger.info("Parse successful, text length: %d", len(parse_result.text))

        # Step 2: Classify
        logger.info("Classifying with model: %s, rules: %d", classifier_model_id, len(rules))

        llm_agent = AgentFactory.create_llm_from_spec(classifier_model_id, _clf_provider, config)
        classifier = Classifier(agent=llm_agent)
        classify_result = await asyncio.to_thread(classifier.classify, parse_result.text, rules)
        
        if not classify_result.success:
            raise HTTPException(status_code=500, detail=f"Classification failed: {classify_result.error}")
        
        logger.info("Classification successful: %s", classify_result.document_type)
        
        # Import ClassificationResult from core.schemas
        from core.schemas import ClassificationResult
        
        # Create classification result
        classification_result = ClassificationResult(
            fileName=file.filename,
            documentType=classify_result.document_type,
            confidence=classify_result.confidence,
            reasoning=classify_result.reasoning
        )
        
        # Save result to classified/result.json
        result_file_path = os.path.join(classified_dir, 'result.json')
        try:
            # Load existing results
            if os.path.exists(result_file_path):
                with open(result_file_path, 'r', encoding='utf-8') as f:
                    results_data = json.load(f)
            else:
                results_data = {}
            
            # Add new result (or update if duplicate)
            results_data[file.filename] = classify_result.document_type
            
            # Save updated results
            with open(result_file_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Result saved to: %s", result_file_path)
        except Exception as e:
            logger.warning("Failed to save result to result.json: %s", e)
        
        return ClassifyResponse(
            success=True,
            results=[classification_result],
            error=None,
            error_type=None
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Classification error: {str(e)}")
        
    finally:
        _safe_remove(file_path)
        # Clean up the copy saved to data/uploaded/ to avoid accumulating files
        _safe_remove(saved_file_path)


@router.post("/classify-text", response_model=ClassifyResponse)
async def classify_text(
    text: str = Form(...),
    classification_rules: str = Form(...),
    classifier_model_id: str = Form(None),  # Make optional
    tier: str = Form("Normal"),  # Add tier parameter
    classifier: Classifier = Depends(get_classifier),
    config: Config = Depends(get_config)
) -> ClassifyResponse:
    """
    Classify text directly without OCR (for reusing OCR results).
    
    Args:
        text: Text content to classify
        classification_rules: JSON string with classification rules
        classifier_model_id: LLM model ID for classification (optional, uses tier config if not provided)
        tier: Processing tier (Rapid, Normal, Advance)
        classifier: Classifier instance (injected via DI based on tier)
        config: Configuration instance
        
    Returns:
        ClassifyResponse with classification results
    """
    # If an explicit model was provided, create a custom classifier instead of using the injected one
    if classifier_model_id:
        logger.info("Using provided classifier model: %s", classifier_model_id)
        _cm, _cp = TierConfig.get_classifier_llm_model_spec(tier)
        llm_agent = AgentFactory.create_llm_from_spec(_cm, _cp, config)
        classifier = Classifier(agent=llm_agent)
    
    # Parse classification rules
    try:
        rules_data = json.loads(classification_rules)
        rules = [
            ClassificationRule(
                doc_type=rule.get('type', rule.get('doc_type', '')),
                description=rule.get('description', '')
            )
            for rule in rules_data
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid classification rules: {str(e)}")
    
    try:
        # Classify text directly using injected or overridden classifier
        classify_result = await asyncio.to_thread(classifier.classify, text, rules)
        
        if not classify_result.success:
            raise HTTPException(status_code=500, detail=classify_result.error)
        
        # Import ClassificationResult from core.schemas
        from core.schemas import ClassificationResult
        
        # Create classification result
        classification_result = ClassificationResult(
            fileName="text_input",
            documentType=classify_result.document_type,
            confidence=classify_result.confidence,
            reasoning=classify_result.reasoning
        )
        
        return ClassifyResponse(
            success=True,
            results=[classification_result],
            error=None,
            error_type=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post("/generate-schema")
async def generate_schema(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None),
    tier: str = Form("Normal"),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Generate extraction schema using AI.
    
    Args:
        prompt: Description of what to extract
        file: Optional sample document
        tier: Processing tier (Rapid, Normal, Advance) - uses extractor tier config
        config: Configuration instance
        
    Returns:
        JSON response with generated schema
    """
    sample_text = None
    file_path = None
    
    try:
        # If file provided, extract text
        if file and file.filename:
            upload_config = config.upload_config
            upload_folder = upload_config.get('folder', 'uploads')
            file_path = await secure_save_file(file, upload_folder)
            
            # Parse file to get sample text
            from config import TierConfig as _TC2
            _sgm, _sgp = _TC2.get_parser_model_spec(tier)
            if _sgm:
                ocr_agent = AgentFactory.create_ocr_from_spec(_sgm, _sgp, config)
                parser = Parser(ocr_agent=ocr_agent)
                parse_result = await asyncio.to_thread(parser.parse, file_path)
                
                if parse_result.success:
                    sample_text = parse_result.text[:2000]  # Limit to 2000 chars
        
        # Get model from extractor tier configuration
        from config import TierConfig
        model_id, _ext_prov = TierConfig.get_extractor_model_spec(tier)

        # Generate schema (non-blocking)
        llm_agent = AgentFactory.create_llm_from_spec(model_id, _ext_prov, config)
        schema_gen = SchemaGenerator(agent=llm_agent)
        result = await asyncio.to_thread(schema_gen.generate, sample_text or "", prompt)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Convert to dict
        schema_dicts = [
            {
                "name": field.name,
                "type": field.type.value,
                "description": field.description,
                "required": field.required
            }
            for field in result.fields
        ]
        
        return JSONResponse({
            "success": True,
            "schema": schema_dicts
        })
        
    finally:
        if file_path:
            _safe_remove(file_path)


@router.post("/extract")
async def extract_data(
    file: UploadFile = File(...),
    parser_model_id: str = Form(...),
    extractor_model_id: str = Form("qwen3-max"),
    extraction_schema: str = Form(...),
    extraction_target: str = Form("document"),
    generate_schema: bool = Form(False),
    schema_prompt: Optional[str] = Form(None),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Extract structured data from document.
    
    Args:
        file: Uploaded file
        parser_model_id: OCR model ID
        extractor_model_id: LLM model ID for extraction
        extraction_schema: JSON string with schema
        extraction_target: Target scope (document, page, table_row)
        generate_schema: Whether to generate schema first
        schema_prompt: Prompt for schema generation
        config: Configuration instance
        
    Returns:
        JSON response with extracted data
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Validate file size
    upload_config = config.upload_config
    max_size_mb = upload_config.get('max_size_mb', 10)
    await file_size_validator.validate(file, max_size_mb)
    
    # Save file
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    try:
        # Step 1: Parse document (non-blocking)
        _pm, _pp = TierConfig.get_parser_model_spec("Normal")
        ocr_agent = AgentFactory.create_ocr_from_spec(_pm, _pp, config)
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = await asyncio.to_thread(parser.parse, file_path)

        if not parse_result.success:
            raise HTTPException(status_code=500, detail=parse_result.error)

        _em, _ep = TierConfig.get_extractor_model_spec("Normal")
        llm_agent = AgentFactory.create_llm_from_spec(_em, _ep, config)
        
        # Step 2: Generate schema if requested (non-blocking)
        if generate_schema and schema_prompt:
            schema_gen = SchemaGenerator(agent=llm_agent)
            schema_result = await asyncio.to_thread(schema_gen.generate, parse_result.text, schema_prompt)
            
            if not schema_result.success:
                raise HTTPException(status_code=500, detail=schema_result.error)
            
            fields = schema_result.fields
        else:
            # Parse provided schema
            try:
                schema_data = json.loads(extraction_schema)
                fields = [
                    SchemaField(
                        name=field['name'],
                        type=FieldType(field['type']),
                        description=field.get('description', ''),
                        required=field.get('required', False)
                    )
                    for field in schema_data
                ]
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid schema: {str(e)}")
        
        # Step 3: Extract data
        extraction_config = ExtractionConfig(
            fields=fields,
            target=ExtractionTarget(extraction_target)
        )
        
        extractor = Extractor(agent=llm_agent)
        extract_result = await asyncio.to_thread(extractor.extract, parse_result.text, extraction_config)
        
        if not extract_result.success:
            raise HTTPException(status_code=500, detail=extract_result.error)
        
        return JSONResponse({
            "success": True,
            "structured_data": extract_result.structured_data,
            "field_errors": extract_result.field_errors,
            "filename": file.filename
        })
        
    finally:
        _safe_remove(file_path)


@router.post("/extract-text")
async def extract_text(
    text: str = Form(...),
    extraction_schema: str = Form(...),
    extraction_target: str = Form("document"),
    extractor_model_id: str = Form("gemini-2.5-flash"),
    tier: str = Form("Normal"),
    extractor: Extractor = Depends(get_extractor),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Extract structured data from text directly without OCR (for reusing OCR results).
    
    Args:
        text: Text content to extract from
        extraction_schema: JSON string with schema
        extraction_target: Target scope (document, page, table_row)
        extractor_model_id: LLM model ID for extraction (optional override)
        tier: Processing tier (Rapid, Normal, Advance)
        extractor: Extractor instance (injected via DI based on tier)
        config: Configuration instance
        
    Returns:
        JSON response with extracted data
    """
    try:
        # Always use tier-based extractor
        _etm, _etp = TierConfig.get_extractor_model_spec(tier)
        llm_agent = AgentFactory.create_llm_from_spec(_etm, _etp, config)
        extractor = Extractor(agent=llm_agent)

        # Parse schema
        schema_data = json.loads(extraction_schema)
        fields = [
            SchemaField(
                name=field['name'],
                type=FieldType(field['type']),
                description=field.get('description', ''),
                required=field.get('required', False)
            )
            for field in schema_data
        ]
        
        # Create extraction config
        extraction_config = ExtractionConfig(
            fields=fields,
            target=ExtractionTarget(extraction_target)
        )
        
        # Extract data using injected or overridden extractor
        extract_result = await asyncio.to_thread(extractor.extract, text, extraction_config)
        
        if not extract_result.success:
            raise HTTPException(status_code=500, detail=extract_result.error)
        
        return JSONResponse({
            "success": True,
            "extraction": {
                "success": True,
                "structured_data": extract_result.structured_data,
                "field_errors": extract_result.field_errors
            }
        })
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid schema JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/split", response_model=SplitResponse)
async def split_document(
    file: UploadFile = File(...),
    categories: str = Form(...),
    allow_uncategorized: bool = Form(True),
    parser_tier: str = Form("Normal"),
    splitter_tier: str = Form("Normal"),
    split_mode: str = Form("sections"),
    config: Config = Depends(get_config)
) -> SplitResponse:
    """
    Split document into categorized chunks using VLM-based Splitter.
    
    This endpoint uses the Splitter class to analyze the document image
    and categorize content into user-defined categories. Supports two modes:
    - "sections": splits into categorized text chunks (default)
    - "document_type": identifies document type boundaries and page ranges
    
    Args:
        file: Uploaded file
        categories: JSON string with categories
        allow_uncategorized: Whether to include unknown chunks
        parser_tier: OCR processing tier (kept for backward compatibility)
        splitter_tier: Splitting processing tier (Rapid, Normal, Advance)
        split_mode: Splitting mode - "sections" or "document_type"
        config: Configuration instance
        
    Returns:
        SplitResponse with categorized chunks or document type results
    """
    # Validate split_mode
    if split_mode not in ("sections", "document_type"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid split_mode: '{split_mode}'. Allowed values: 'sections', 'document_type'"
        )
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Validate file size
    upload_config = config.upload_config
    max_size_mb = upload_config.get('max_size_mb', 10)
    await file_size_validator.validate(file, max_size_mb)
    
    # Parse categories
    try:
        categories_data = json.loads(categories)
        chunk_categories = [
            ChunkCategory(
                name=cat['name'],
                description=cat['description'],
                order=cat.get('order', 0)
            )
            for cat in categories_data
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid categories: {str(e)}")
    
    # Get splitter model from tier configuration
    from config import TierConfig
    splitter_model_id, _spl_prov = TierConfig.get_splitter_model_spec(splitter_tier)

    # Save file
    upload_config = config.upload_config
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        # Use Splitter class for consistent splitting approach
        vlm_agent = AgentFactory.create_vlm_from_spec(splitter_model_id, _spl_prov, config)
        splitter = Splitter(agent=vlm_agent)
        
        if split_mode == "document_type":
            # Document type mode: identify document boundaries and page ranges
            split_result = await asyncio.to_thread(
                splitter.split_by_document_type,
                file_path,
                chunk_categories
            )
            
            if not split_result.success:
                raise HTTPException(status_code=500, detail=f"Split failed: {split_result.error}")
            
            # Map DocumentTypeItem objects to DocumentTypeResult schema objects
            document_type_models = [
                DocumentTypeResult(
                    type_name=dt.type_name,
                    page_numbers=dt.page_numbers,
                    confidence=dt.confidence
                )
                for dt in split_result.document_types or []
            ]
            
            # Save split result to file
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
            splited_dir = os.path.join(data_dir, 'splited')
            os.makedirs(splited_dir, exist_ok=True)
            
            base_filename = os.path.splitext(file.filename)[0]
            split_file_path = os.path.join(splited_dir, f"{base_filename}.json")
            
            try:
                split_output = {
                    "filename": file.filename,
                    "splitter_model": splitter_model_id,
                    "splitter_tier": splitter_tier,
                    "split_mode": split_mode,
                    "categories": categories_data,
                    "document_types": [
                        {
                            "type_name": dt.type_name,
                            "page_numbers": dt.page_numbers,
                            "confidence": dt.confidence
                        }
                        for dt in split_result.document_types or []
                    ],
                    "timestamp": os.path.getctime(file_path) if os.path.exists(file_path) else None
                }
                
                with open(split_file_path, 'w', encoding='utf-8') as f:
                    json.dump(split_output, f, indent=2, ensure_ascii=False)
                
                logger.info("Split result saved: %s", split_file_path)
            except Exception as e:
                logger.warning("Failed to save split result: %s", e)
            
            return SplitResponse(
                success=True,
                chunks=[],
                unknown_chunks=[],
                document_types=document_type_models,
                filename=file.filename
            )
        else:
            # Sections mode: existing behavior unchanged
            split_result = await asyncio.to_thread(
                splitter.split,
                file_path,
                chunk_categories,
                allow_uncategorized=allow_uncategorized
            )
            
            if not split_result.success:
                raise HTTPException(status_code=500, detail=f"Split failed: {split_result.error}")
            
            # Convert to response models
            chunk_models = [
                ChunkModel(
                    content=chunk.content,
                    category=chunk.category,
                    page_number=chunk.page_number,
                    confidence=chunk.confidence
                )
                for chunk in split_result.chunks or []
            ]
            
            unknown_chunk_models = [
                ChunkModel(
                    content=chunk.content,
                    category=chunk.category,
                    page_number=chunk.page_number,
                    confidence=chunk.confidence
                )
                for chunk in split_result.unknown_chunks or []
            ]
            
            # Save split result to file
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
            splited_dir = os.path.join(data_dir, 'splited')
            os.makedirs(splited_dir, exist_ok=True)
            
            base_filename = os.path.splitext(file.filename)[0]
            split_file_path = os.path.join(splited_dir, f"{base_filename}.json")
            
            try:
                split_output = {
                    "filename": file.filename,
                    "splitter_model": splitter_model_id,
                    "splitter_tier": splitter_tier,
                    "split_mode": split_mode,
                    "categories": categories_data,
                    "allow_uncategorized": allow_uncategorized,
                    "chunks": [
                        {
                            "content": c.content,
                            "category": c.category,
                            "page_number": c.page_number,
                            "confidence": c.confidence
                        }
                        for c in split_result.chunks or []
                    ],
                    "unknown_chunks": [
                        {
                            "content": c.content,
                            "category": c.category,
                            "page_number": c.page_number,
                            "confidence": c.confidence
                        }
                        for c in split_result.unknown_chunks or []
                    ],
                    "timestamp": os.path.getctime(file_path) if os.path.exists(file_path) else None
                }
                
                with open(split_file_path, 'w', encoding='utf-8') as f:
                    json.dump(split_output, f, indent=2, ensure_ascii=False)
                
                logger.info("Split result saved: %s", split_file_path)
            except Exception as e:
                logger.warning("Failed to save split result: %s", e)
            
            return SplitResponse(
                success=True,
                chunks=chunk_models,
                unknown_chunks=unknown_chunk_models,
                document_types=None,
                filename=file.filename
            )
        
    finally:
        _safe_remove(file_path)


@router.get("/health", response_model=HealthResponse)
async def health_check(config: Config = Depends(get_config)) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with status and available models
    """
    available_models = config.get_available_models()
    
    # Check if any server is running
    server_running = False
    providers = config.api_providers
    
    if providers:
        first_provider = list(providers.values())[0]
        base_url = first_provider.get('base_url')
        
        if base_url:
            from core.utils import check_server_status
            status = check_server_status(base_url)
            server_running = status.get('running', False)
    
    # Determine status
    if server_running and available_models:
        status = "healthy"
    elif available_models:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        server_running=server_running,
        available_models=available_models
    )


@router.get("/models/check")
async def check_models(config: Config = Depends(get_config)) -> JSONResponse:
    """
    Check which models are configured and available.
    
    Returns detailed information about model availability and configuration.
    """
    import os
    
    logger.info("=== MODEL CHECK REQUEST ===")
    
    models_info = []
    
    # Check each model in config
    for model_id, model_config in config.models.items():
        provider = model_config.get('provider')
        provider_config = config.api_providers.get(provider, {})
        
        # Check if API key is set for this provider
        api_key_set = False
        api_key_name = None
        if provider == 'google_studio':
            api_key_name = 'GOOGLE_STUDIO_API_KEY'
            api_key_set = bool(os.getenv('GOOGLE_STUDIO_API_KEY'))
        elif provider == 'poe_api':
            api_key_name = 'POE_API_KEY'
            api_key_set = bool(os.getenv('POE_API_KEY'))
        elif provider == 'lm_studio':
            api_key_name = 'N/A (local)'
            api_key_set = True  # Local, no API key needed
        
        models_info.append({
            'model_id': model_id,
            'name': model_config.get('name', model_id),
            'provider': provider,
            'base_url': provider_config.get('base_url'),
            'api_key_name': api_key_name,
            'api_key_set': api_key_set,
            'available': api_key_set
        })
        
        logger.info("  %s: provider=%s, api_key=%s, available=%s", model_id, provider, api_key_name, api_key_set)
    
    # Group by provider
    by_provider = {}
    for model in models_info:
        provider = model['provider']
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model)
    
    logger.info("Total models: %d, Available: %d", len(models_info), len([m for m in models_info if m['available']]))
    logger.info("===========================")
    
    return JSONResponse({
        'success': True,
        'models': models_info,
        'by_provider': by_provider,
        'total_models': len(models_info),
        'available_models': len([m for m in models_info if m['available']])
    })


@router.get("/test-logging")
async def test_logging() -> JSONResponse:
    """Test endpoint to verify logging is working."""
    logger.info("=" * 50)
    logger.info("TEST LOGGING ENDPOINT CALLED")
    logger.info("If you can see this in your terminal, logging is working!")
    logger.info("=" * 50)
    
    import sys
    import os
    
    return JSONResponse({
        'success': True,
        'message': 'Check your backend terminal for log output',
        'python_version': sys.version,
        'cwd': os.getcwd(),
        'stdout_isatty': sys.stdout.isatty()
    })


@router.get("/tier-config")
async def get_tier_config() -> JSONResponse:
    """
    Get tier configuration mappings.
    
    Returns tier-to-model mappings for all features.
    This allows the frontend to dynamically use the correct models for each tier.
    
    Returns:
        JSON response with tier configuration
    """
    from config import TierConfig
    
    return JSONResponse({
        "success": True,
        "config": TierConfig.export_to_json()
    })


@router.get("/raw-ocr/{filename}")
async def get_raw_ocr(filename: str) -> JSONResponse:
    """
    Get raw OCR text file.
    
    Args:
        filename: Name of the file (without .txt extension)
        
    Returns:
        JSON response with raw OCR text
    """
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    raw_ocr_dir = os.path.join(data_dir, 'raw_ocr')
    validate_file_path(f"{filename}.txt", raw_ocr_dir)
    file_path = os.path.join(raw_ocr_dir, f"{filename}.txt")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Raw OCR file not found: {filename}.txt")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return JSONResponse({
            "success": True,
            "filename": f"{filename}.txt",
            "content": content,
            "size": len(content)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.get("/parsed/{filename}")
async def get_parsed_docx(filename: str):
    """
    Get parsed DOCX file.
    
    Args:
        filename: Name of the file (without .docx extension)
        
    Returns:
        DOCX file as download
    """
    from fastapi.responses import FileResponse
    
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    parsed_dir = os.path.join(data_dir, 'parsed')
    validate_file_path(f"{filename}.docx", parsed_dir)
    file_path = os.path.join(parsed_dir, f"{filename}.docx")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Parsed DOCX file not found: {filename}.docx")
    
    return FileResponse(
        path=file_path,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=f"{filename}.docx"
    )


@router.get("/list-saved-files")
async def list_saved_files() -> JSONResponse:
    """
    List all saved OCR files.
    
    Returns:
        JSON response with list of available files
    """
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    raw_ocr_dir = os.path.join(data_dir, 'raw_ocr')
    parsed_dir = os.path.join(data_dir, 'parsed')
    
    files = []
    
    # List raw OCR files
    if os.path.exists(raw_ocr_dir):
        for filename in os.listdir(raw_ocr_dir):
            if filename.endswith('.txt') and filename != '.gitkeep':
                base_name = filename[:-4]  # Remove .txt extension
                file_path = os.path.join(raw_ocr_dir, filename)
                docx_path = os.path.join(parsed_dir, f"{base_name}.docx")
                
                file_info = {
                    "filename": base_name,
                    "raw_ocr": {
                        "exists": True,
                        "path": f"/raw-ocr/{base_name}",
                        "size": os.path.getsize(file_path)
                    },
                    "parsed": {
                        "exists": os.path.exists(docx_path),
                        "path": f"/parsed/{base_name}" if os.path.exists(docx_path) else None,
                        "size": os.path.getsize(docx_path) if os.path.exists(docx_path) else 0
                    },
                    "created_at": os.path.getctime(file_path)
                }
                files.append(file_info)
    
    # Sort by creation time (newest first)
    files.sort(key=lambda x: x['created_at'], reverse=True)
    
    return JSONResponse({
        "success": True,
        "count": len(files),
        "files": files
    })


@router.post("/condition/evaluate")
async def evaluate_condition(
    conditions: str = Form(...),
    previous_result: str = Form(...),
    field_name: str = Form("document_type")
) -> JSONResponse:
    """
    Evaluate conditions against previous workflow result.
    
    This endpoint determines which output path to take based on conditions.
    
    Args:
        conditions: JSON string with condition definitions
        previous_result: JSON string with previous node result
        field_name: Field name to evaluate (default: document_type)
        
    Returns:
        JSON response with matched condition index (or null for else)
    """
    try:
        # Parse conditions
        conditions_data = json.loads(conditions)
        condition_list = [
            Condition(
                operator=ConditionOperator(cond['operator']),
                value=cond.get('value'),
                valueMin=cond.get('valueMin'),
                valueMax=cond.get('valueMax')
            )
            for cond in conditions_data
        ]
        
        # Parse previous result
        result_data = json.loads(previous_result)
        
        # Evaluate conditions
        evaluator = ConditionEvaluator()
        eval_result = evaluator.evaluate_from_previous_result(
            result_data,
            condition_list,
            field_name
        )
        
        if not eval_result.success:
            raise HTTPException(status_code=500, detail=eval_result.error)
        
        return JSONResponse({
            "success": True,
            "matched_index": eval_result.matched_index,
            "is_else": eval_result.matched_index is None
        })
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Condition evaluation failed: {str(e)}")


@router.post("/workflow/execute")
async def execute_workflow(
    file: UploadFile = File(...),
    workflow: str = Form(...),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Execute a workflow pipeline.
    
    This endpoint processes a file through multiple steps defined in the workflow.
    Each step can be: parse, classify, extract, or split.
    
    Args:
        file: Uploaded file
        workflow: JSON string with workflow definition
        config: Configuration instance
        
    Returns:
        JSON response with results from each workflow step
    """
    # Parse workflow
    try:
        workflow_data = json.loads(workflow)
        steps = workflow_data.get('steps', [])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid workflow: {str(e)}")
    
    if not steps:
        raise HTTPException(status_code=400, detail="Workflow must have at least one step")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get('allowed_extensions', []))
    
    if not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size
    max_size_mb = upload_config.get('max_size_mb', 10)
    await file_size_validator.validate(file, max_size_mb)
    
    # Save file
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Execute workflow steps
    results = []
    previous_result = None
    
    try:
        for step in steps:
            step_type = step.get('type')
            step_tier = step.get('tier', 'Normal')
            step_config = step.get('config', {})
            
            if step_type == 'parse':
                result = await execute_parse_step(file_path, step_tier, step_config, config)
            elif step_type == 'classify':
                result = await execute_classify_step(file_path, step_tier, step_config, config)
            elif step_type == 'extract':
                result = await execute_extract_step(file_path, step_tier, step_config, config)
            elif step_type == 'split':
                result = await execute_split_step(file_path, step_tier, step_config, config)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown step type: {step_type}")
            
            results.append({
                'step': step_type,
                'tier': step_tier,
                'result': result
            })
            
            previous_result = result
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'completed_steps': results
            }
        )
    
    finally:
        _safe_remove(file_path)
    
    return JSONResponse(content={
        'success': True,
        'results': results,
        'filename': file.filename
    })


async def execute_parse_step(file_path: str, tier: str, step_config: dict, config: Config):
    """Execute parse step."""
    from config import TierConfig
    model_id, provider = TierConfig.get_parser_model_spec(tier)

    ocr_agent = AgentFactory.create_ocr_from_spec(model_id, provider, config)
    parser = Parser(ocr_agent=ocr_agent)
    
    parse_result = await asyncio.to_thread(parser.parse, file_path)
    
    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")
    
    return {
        'text': parse_result.text,
        'file_type': parse_result.file_type,
        'pages': parse_result.pages
    }


async def execute_classify_step(file_path: str, tier: str, step_config: dict, config: Config):
    """Execute classify step."""
    from config import TierConfig

    # Parse document first
    parser_model_id, parser_provider = TierConfig.get_parser_model_spec(tier)
    ocr_agent = AgentFactory.create_ocr_from_spec(parser_model_id, parser_provider, config)
    parser = Parser(ocr_agent=ocr_agent)
    parse_result = await asyncio.to_thread(parser.parse, file_path)

    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")

    # Classify
    classifier_model_id, clf_provider = TierConfig.get_classifier_llm_model_spec(tier)
    llm_agent = AgentFactory.create_llm_from_spec(classifier_model_id, clf_provider, config)
    classifier = Classifier(agent=llm_agent)
    
    rules = [
        ClassificationRule(
            doc_type=rule['doc_type'],
            description=rule['description']
        )
        for rule in step_config.get('rules', [])
    ]
    
    classify_result = await asyncio.to_thread(classifier.classify, parse_result.text, rules)
    
    if not classify_result.success:
        raise Exception(f"Classify failed: {classify_result.error}")
    
    return {
        'document_type': classify_result.document_type,
        'confidence': classify_result.confidence,
        'reasoning': classify_result.reasoning
    }


async def execute_extract_step(file_path: str, tier: str, step_config: dict, config: Config):
    """Execute extract step."""
    from config import TierConfig

    # Parse document first
    parser_model_id, parser_provider = TierConfig.get_parser_model_spec(tier)
    ocr_agent = AgentFactory.create_ocr_from_spec(parser_model_id, parser_provider, config)
    parser = Parser(ocr_agent=ocr_agent)
    parse_result = await asyncio.to_thread(parser.parse, file_path)

    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")

    # Extract
    extractor_model_id, ext_provider = TierConfig.get_extractor_model_spec(tier)
    llm_agent = AgentFactory.create_llm_from_spec(extractor_model_id, ext_provider, config)
    extractor = Extractor(agent=llm_agent)
    
    # Build extraction config
    schema_data = step_config.get('schema', {})
    extraction_config = ExtractionConfig(
        target=ExtractionTarget(step_config.get('target', 'document')),
        fields=[
            SchemaField(
                name=field['name'],
                type=FieldType(field['type']),
                description=field.get('description', ''),
                required=field.get('required', False)
            )
            for field in schema_data.get('fields', [])
        ]
    )
    
    extract_result = await asyncio.to_thread(extractor.extract, parse_result.text, extraction_config)
    
    if not extract_result.success:
        raise Exception(f"Extract failed: {extract_result.error}")
    
    return {
        'structured_data': extract_result.structured_data,
        'field_errors': extract_result.field_errors
    }


async def execute_split_step(file_path: str, tier: str, step_config: dict, config: Config):
    """Execute split step."""
    from config import TierConfig

    # Get models
    parser_model_id, parser_provider = TierConfig.get_parser_model_spec(tier)
    splitter_model_id, spl_provider = TierConfig.get_splitter_model_spec(tier)

    # Parse document
    ocr_agent = AgentFactory.create_ocr_from_spec(parser_model_id, parser_provider, config)
    parser = Parser(ocr_agent=ocr_agent)
    parse_result = await asyncio.to_thread(parser.parse, file_path)

    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")

    # Split
    vlm_agent = AgentFactory.create_vlm_from_spec(splitter_model_id, spl_provider, config)
    splitter = Splitter(agent=vlm_agent)
    
    categories = [
        ChunkCategory(
            name=cat['name'],
            description=cat['description'],
            order=cat.get('order', 0)
        )
        for cat in step_config.get('categories', [])
    ]
    
    split_result = await asyncio.to_thread(
        splitter.split,
        file_path,
        categories,
        allow_uncategorized=step_config.get('allow_uncategorized', True)
    )
    
    if not split_result.success:
        raise Exception(f"Split failed: {split_result.error}")
    
    return {
        'chunks': [
            {
                'content': chunk.content,
                'category': chunk.category,
                'page_number': chunk.page_number,
                'confidence': chunk.confidence
            }
            for chunk in split_result.chunks or []
        ],
        'unknown_chunks': [
            {
                'content': chunk.content,
                'category': chunk.category,
                'page_number': chunk.page_number
            }
            for chunk in split_result.unknown_chunks or []
        ]
    }


from pydantic import BaseModel

class BedrockTokenRequest(BaseModel):
    bearer_token: str
    region: str = "ap-southeast-1"

@router.post("/api/config/update-bedrock-token")
async def update_bedrock_token(body: BedrockTokenRequest) -> JSONResponse:
    """
    Update AWS Bedrock token and region in environment variables.

    Args:
        bearer_token: AWS Bedrock API bearer token
        region: AWS region (default: ap-southeast-1)

    Returns:
        Success confirmation
    """
    bearer_token = body.bearer_token
    region = body.region
    try:
        # Update environment variables immediately (affects all new requests)
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = bearer_token.strip()
        os.environ["AWS_REGION"] = region
        os.environ["BEDROCK_REGION"] = region

        # Also try to update .env file if it exists
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            try:
                # Read existing .env content
                with open(env_path, 'r') as f:
                    lines = f.readlines()

                # Update or add the token and region lines
                updated_lines = []
                token_found = False
                region_found = False
                bedrock_region_found = False
                for line in lines:
                    if line.startswith("AWS_BEARER_TOKEN_BEDROCK="):
                        updated_lines.append(f"AWS_BEARER_TOKEN_BEDROCK={bearer_token.strip()}\n")
                        token_found = True
                    elif line.startswith("AWS_REGION="):
                        updated_lines.append(f"AWS_REGION={region}\n")
                        region_found = True
                    elif line.startswith("BEDROCK_REGION="):
                        updated_lines.append(f"BEDROCK_REGION={region}\n")
                        bedrock_region_found = True
                    else:
                        updated_lines.append(line)

                # Add lines if they weren't found
                if not token_found:
                    updated_lines.append(f"AWS_BEARER_TOKEN_BEDROCK={bearer_token.strip()}\n")
                if not region_found:
                    updated_lines.append(f"AWS_REGION={region}\n")
                if not bedrock_region_found:
                    updated_lines.append(f"BEDROCK_REGION={region}\n")

                # Write back to .env
                with open(env_path, 'w') as f:
                    f.writelines(updated_lines)

                logger.info("Successfully updated AWS Bedrock credentials in .env file")
            except Exception as e:
                logger.warning("Failed to update .env file: %s", e)
                # Continue anyway - environment variables are updated

        return JSONResponse({
            "success": True,
            "message": "AWS Bedrock token updated successfully",
            "region": region
        })

    except Exception as e:
        logger.error("Failed to update Bedrock token: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update AWS credentials: {str(e)}"
        )
