"""
Parse service — OCR and document text extraction business logic.

Handles:
- File validation and upload
- Background job dispatch for large PDFs
- Synchronous OCR + text formatting
- Optional inline extraction
- Saving raw OCR and DOCX artefacts
"""

import asyncio
import json
import logging
import os
import threading
from typing import Optional

from agents.factory import AgentFactory
from services.job_manager import job_manager
from core.middleware import FileSizeValidator
from core.schemas import ExtractionConfig, ExtractionTarget, FieldType, SchemaField
from core.storage import UPLOADS_DIR
from core.utils import allowed_file, secure_save_file
from components.extractor import Extractor
from components.parser import Parser
from components.text_parser import TextParser
from config import Config
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

file_size_validator = FileSizeValidator()


def _safe_remove(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning("Failed to remove temp file %s: %s", path, e)


def _build_extraction_fields(schema_data: list) -> list:
    return [
        SchemaField(
            name=field["name"],
            type=FieldType(field["type"]),
            description=field.get("description", ""),
            required=field.get("required", False),
        )
        for field in schema_data
    ]


def _run_extraction_sync(text: str, extraction_schema: str, extraction_target: str, extractor_model: str, config: Config) -> dict:
    """Run extraction synchronously (used inside background thread)."""
    try:
        schema_data = json.loads(extraction_schema)
        fields = _build_extraction_fields(schema_data)
        extraction_config = ExtractionConfig(
            fields=fields,
            target=ExtractionTarget(extraction_target or "document"),
        )
        llm_agent = AgentFactory.create_llm_agent(extractor_model, config=config)
        extractor = Extractor(agent=llm_agent)
        result = extractor.extract(text, extraction_config)
        if result.success:
            return {"success": True, "structured_data": result.structured_data, "field_errors": result.field_errors}
        return {"success": False, "error": result.error}
    except Exception as e:
        return {"success": False, "error": f"Extraction failed: {str(e)}"}


def _background_parse_worker(
    file_path: str,
    filename: str,
    model_id: str,
    force_ocr: bool,
    parse_formatting: bool,
    extraction_enabled: bool,
    extraction_target: Optional[str],
    extraction_schema: Optional[str],
    extractor_model: Optional[str],
    config: Config,
    job_id: str,
    provider: Optional[str] = None,
) -> None:
    """Worker function executed in a background thread for large PDFs."""
    try:
        ocr_agent = AgentFactory.create_from_config(config, model_id, provider_override=provider)
        parser = Parser(ocr_agent=ocr_agent)
        result = parser.parse(file_path, force_ocr)

        if not result.success:
            job_manager.update_status(job_id, "failed", error=result.error)
            return

        job_manager.update_status(job_id, "processing", progress=0.5)

        text = result.text
        if parse_formatting:
            text = TextParser.auto_parse(text)

        # Persist to PostgreSQL (mandatory)
        import asyncio as _aio
        from server import ocr_result_repo
        if not ocr_result_repo or not ocr_result_repo._pool:
            job_manager.update_status(job_id, "failed", error="Database unavailable — cannot persist OCR results")
            return

        loop = _aio.new_event_loop()
        try:
            loop.run_until_complete(ocr_result_repo.store_result(
                filename=filename,
                raw_text=result.text,
                model_id=model_id,
                provider=provider,
                result_data={
                    "type": "parse",
                    "parsed_text": text if parse_formatting else None,
                    "file_type": result.file_type,
                    "is_scanned": result.is_scanned,
                    "pages": result.pages,
                },
            ))
            logger.info("BG job %s: OCR result persisted to DB", job_id)
        finally:
            loop.close()

        response_data: dict = {
            "success": True,
            "text": text,
            "parsed_text": text if parse_formatting else None,
            "file_type": result.file_type,
            "is_scanned": result.is_scanned,
            "pages": result.pages,
            "filename": filename,
            "model": model_id,
        }

        if extraction_enabled and extraction_schema:
            response_data["extraction"] = _run_extraction_sync(
                text, extraction_schema, extraction_target or "document", extractor_model or "qwen3-max", config
            )

        job_manager.update_status(job_id, "completed", progress=1.0, result=response_data)

    except Exception as exc:
        logger.exception("Background job %s failed", job_id)
        job_manager.update_status(job_id, "failed", error=str(exc))
    finally:
        _safe_remove(file_path)


def _get_pdf_page_count(file_path: str) -> Optional[int]:
    """Return page count for a PDF, or None on failure."""
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(file_path)
        try:
            return len(pdf)
        finally:
            pdf.close()
    except Exception:
        return None


async def parse_document(
    file: UploadFile,
    model_id: str,
    force_ocr: bool,
    parse_formatting: bool,
    extraction_enabled: bool,
    extraction_target: Optional[str],
    extraction_schema: Optional[str],
    extractor_model: Optional[str],
    config: Config,
    provider: Optional[str] = None,
) -> dict:
    """
    Validate, save, and OCR a document.

    Returns a response dict ready to be serialised by the router.
    Dispatches to a background thread for large PDFs when configured.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get("allowed_extensions", []))

    if not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")

    max_size_mb = upload_config.get("max_size_mb", 10)
    await file_size_validator.validate(file, max_size_mb)

    upload_folder = str(UPLOADS_DIR)
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        # --- Background dispatch for large PDFs ---
        bg_config = config._config_data.get("background_tasks", {})
        bg_enabled = bg_config.get("enabled", False)
        threshold_pages = bg_config.get("threshold_pages", 5)

        if bg_enabled and file_path.lower().endswith(".pdf"):
            page_count = _get_pdf_page_count(file_path)
            if page_count is not None and page_count > threshold_pages:
                job_id = job_manager.create_job()
                job_manager.update_status(job_id, "processing", progress=0.0)

                thread = threading.Thread(
                    target=_background_parse_worker,
                    args=(
                        file_path, file.filename, model_id, force_ocr, parse_formatting,
                        extraction_enabled, extraction_target, extraction_schema,
                        extractor_model, config, job_id, provider,
                    ),
                    daemon=True,
                )
                thread.start()

                return {
                    "success": True,
                    "background": True,
                    "job_id": job_id,
                    "message": f"Document has {page_count} pages (threshold: {threshold_pages}). Processing in background.",
                }

        # --- Synchronous path ---
        ocr_agent = AgentFactory.create_from_config(config, model_id, provider_override=provider)
        parser = Parser(ocr_agent=ocr_agent)
        result = await asyncio.to_thread(parser.parse, file_path, force_ocr)

        if not result.success:
            from core.exceptions import raise_agent_error
            raise_agent_error(result)

        text = result.text
        if parse_formatting:
            text = await asyncio.to_thread(TextParser.auto_parse, text)

        # Persist to PostgreSQL (mandatory)
        from server import ocr_result_repo
        if not ocr_result_repo or not ocr_result_repo._pool:
            raise HTTPException(status_code=503, detail="Database unavailable — cannot persist OCR results")

        await ocr_result_repo.store_result(
            filename=file.filename,
            raw_text=result.text,
            model_id=model_id,
            provider=provider,
            result_data={
                "type": "parse",
                "parsed_text": text if parse_formatting else None,
                "file_type": result.file_type,
                "is_scanned": result.is_scanned,
                "pages": result.pages,
            },
        )
        logger.info("OCR result persisted to DB: %s", file.filename)

        response_data: dict = {
            "success": True,
            "text": text,
            "parsed_text": text if parse_formatting else None,
            "file_type": result.file_type,
            "is_scanned": result.is_scanned,
            "pages": result.pages,
            "filename": file.filename,
            "model": model_id,
        }

        if extraction_enabled and extraction_schema:
            try:
                schema_data = json.loads(extraction_schema)
                fields = _build_extraction_fields(schema_data)
                extraction_config = ExtractionConfig(
                    fields=fields,
                    target=ExtractionTarget(extraction_target or "document"),
                )
                llm_agent = AgentFactory.create_llm_agent(extractor_model, config=config)
                extractor = Extractor(agent=llm_agent)
                extract_result = await asyncio.to_thread(extractor.extract, text, extraction_config)

                if extract_result.success:
                    # Persist extraction result to DB
                    from server import ocr_result_repo
                    if ocr_result_repo and ocr_result_repo._pool:
                        result_by_file = await ocr_result_repo.get_result_by_filename(file.filename)
                        if result_by_file:
                            await ocr_result_repo.update_result_data(
                                result_by_file["id"],
                                {
                                    "extraction": {
                                        "model": extractor_model,
                                        "target": extraction_target or "document",
                                        "schema": schema_data,
                                        "structured_data": extract_result.structured_data,
                                        "field_errors": extract_result.field_errors,
                                    }
                                },
                            )

                    response_data["extraction"] = {
                        "success": True,
                        "structured_data": extract_result.structured_data,
                        "field_errors": extract_result.field_errors,
                    }
                else:
                    response_data["extraction"] = {"success": False, "error": extract_result.error}
            except Exception as e:
                response_data["extraction"] = {"success": False, "error": f"Extraction failed: {str(e)}"}

        return response_data

    finally:
        _safe_remove(file_path)
