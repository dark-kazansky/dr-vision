"""
M.DocAI MSBE Parser service.

Implements the same surface as ``backend/routes.py`` for parser-owned
endpoints by calling the shared monolith code directly. Specifically:

* ``POST /parse`` and ``POST /ocr`` — synchronous parse with optional
  structured extraction; for PDFs above ``background_tasks.threshold_pages``
  the request is accepted and processed in the shared ``JobManager``.
* ``GET  /job/{job_id}/status`` — poll a background job.
* ``GET  /job/{job_id}/result`` — fetch the final payload.
* ``GET  /raw-ocr/{filename}`` — raw OCR text persisted to ``data/raw_ocr``.
* ``GET  /parsed/{filename}`` — generated DOCX persisted to ``data/parsed``.
* ``GET  /list-saved-files`` — index of the two folders above.
* ``GET  /health`` — same shape as the monolith's ``HealthResponse``.

Response shapes are byte-identical to the monolith.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from config import Config, TierConfig
from core import (
    ExtractionConfig,
    ExtractionTarget,
    FieldType,
    HealthResponse,
    SchemaField,
)
from core.agent_factory import AgentFactory
from core.background_tasks import job_manager
from core.docx_generator import DocxGenerator
from core.middleware import FileSizeValidator
from core.utils import (
    allowed_file,
    check_server_status,
    secure_save_file,
    validate_file_path,
)
from functions.extractor import Extractor
from functions.parser import Parser
from functions.text_parser import TextParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="M.DocAI MSBE Parser", version="0.2.0")
file_size_validator = FileSizeValidator()


def _data_dir() -> str:
    """Single shared data root, configurable for the container layout."""
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
    except Exception as e:  # pragma: no cover — surfaced via 500
        raise HTTPException(status_code=500, detail=f"Configuration error: {e}")


# ---------------------------------------------------------------------------
# Health (matches monolith HealthResponse)
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health(config: Config = Depends(get_config)) -> HealthResponse:
    available_models = config.get_available_models()
    server_running = False
    providers = config.api_providers
    if providers:
        first_provider = next(iter(providers.values()))
        base_url = first_provider.get("base_url")
        if base_url:
            status = check_server_status(base_url)
            server_running = bool(status.get("running"))

    if server_running and available_models:
        status = "healthy"
    elif available_models:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status, server_running=server_running, available_models=available_models
    )


# ---------------------------------------------------------------------------
# Background-job polling
# ---------------------------------------------------------------------------

@app.get("/job/{job_id}/status")
async def get_job_status(job_id: str) -> JSONResponse:
    status = job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return JSONResponse(status)


@app.get("/job/{job_id}/result")
async def get_job_result(job_id: str) -> JSONResponse:
    result = job_manager.get_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if result["status"] not in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is still {result['status']}. "
            f"Poll /job/{job_id}/status until completed.",
        )
    return JSONResponse(result)


# ---------------------------------------------------------------------------
# /parse (and /ocr alias)
# ---------------------------------------------------------------------------

@app.post("/parse")
@app.post("/ocr")
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
    config: Config = Depends(get_config),
) -> JSONResponse:
    """Mirror of the monolith's parse_document — same params, same response."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get("allowed_extensions", []))
    if not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
        )

    max_size_mb = upload_config.get("max_size_mb", 10)
    await file_size_validator.validate(file, max_size_mb)

    upload_folder = upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        # Background offload for large PDFs (matches the monolith).
        bg_config = config._config_data.get("background_tasks", {})
        bg_enabled = bg_config.get("enabled", False)
        threshold_pages = bg_config.get("threshold_pages", 5)

        page_count = None
        if bg_enabled and file_path.lower().endswith(".pdf"):
            try:
                import pypdfium2 as pdfium  # type: ignore

                _pdf = pdfium.PdfDocument(file_path)
                try:
                    page_count = len(_pdf)
                finally:
                    _pdf.close()
            except Exception:
                page_count = None

        if bg_enabled and page_count is not None and page_count > threshold_pages:
            job_id = job_manager.create_job()
            job_manager.update_status(job_id, "processing", progress=0.0)

            def _bg(_path, _filename, _model_id, _force, _fmt,
                   _ext_enabled, _ext_target, _ext_schema, _ext_model, _cfg, _job_id):
                try:
                    ocr_agent = AgentFactory.create_from_config(_cfg, _model_id)
                    parser = Parser(ocr_agent=ocr_agent)
                    result = parser.parse(_path, _force)
                    if not result.success:
                        job_manager.update_status(_job_id, "failed", error=result.error)
                        return
                    job_manager.update_status(_job_id, "processing", progress=0.5)

                    text = result.text
                    if _fmt:
                        text = TextParser.auto_parse(text)

                    raw_ocr_dir = os.path.join(_data_dir(), "raw_ocr")
                    parsed_dir = os.path.join(_data_dir(), "parsed")
                    os.makedirs(raw_ocr_dir, exist_ok=True)
                    os.makedirs(parsed_dir, exist_ok=True)
                    base_fn = os.path.splitext(_filename)[0]
                    try:
                        with open(os.path.join(raw_ocr_dir, f"{base_fn}.txt"), "w", encoding="utf-8") as f:
                            f.write(result.text)
                    except Exception as e:
                        logger.warning("BG job %s raw OCR save failed: %s", _job_id, e)
                    try:
                        DocxGenerator().generate(
                            text=text,
                            filename=_filename,
                            model_id=_model_id,
                            pages=result.pages or 1,
                            file_type=result.file_type,
                            output_path=os.path.join(parsed_dir, f"{base_fn}.docx"),
                        )
                    except Exception as e:
                        logger.warning("BG job %s DOCX failed: %s", _job_id, e)

                    response_data = {
                        "success": True,
                        "text": text,
                        "parsed_text": text if _fmt else None,
                        "file_type": result.file_type,
                        "is_scanned": result.is_scanned,
                        "pages": result.pages,
                        "filename": _filename,
                        "model": _model_id,
                    }
                    if _ext_enabled and _ext_schema:
                        try:
                            schema_data = json.loads(_ext_schema)
                            fields = [
                                SchemaField(
                                    name=f["name"],
                                    type=FieldType(f["type"]),
                                    description=f.get("description", ""),
                                    required=f.get("required", False),
                                )
                                for f in schema_data
                            ]
                            extraction_config = ExtractionConfig(
                                fields=fields,
                                target=ExtractionTarget(_ext_target or "document"),
                            )
                            llm_agent = AgentFactory.create_llm_agent(_ext_model, config=_cfg)
                            extractor = Extractor(agent=llm_agent)
                            ex = extractor.extract(text, extraction_config)
                            if ex.success:
                                response_data["extraction"] = {
                                    "success": True,
                                    "structured_data": ex.structured_data,
                                    "field_errors": ex.field_errors,
                                }
                            else:
                                response_data["extraction"] = {"success": False, "error": ex.error}
                        except Exception as e:
                            response_data["extraction"] = {
                                "success": False,
                                "error": f"Extraction failed: {e}",
                            }
                    job_manager.update_status(_job_id, "completed", progress=1.0, result=response_data)
                except Exception as exc:
                    logger.exception("Background job %s failed", _job_id)
                    job_manager.update_status(_job_id, "failed", error=str(exc))
                finally:
                    _safe_remove(_path)

            threading.Thread(
                target=_bg,
                args=(
                    file_path, file.filename, model_id, force_ocr, parse_formatting,
                    extraction_enabled, extraction_target, extraction_schema,
                    extractor_model, config, job_id,
                ),
                daemon=True,
            ).start()

            return JSONResponse(
                {
                    "success": True,
                    "background": True,
                    "job_id": job_id,
                    "message": (
                        f"Document has {page_count} pages (threshold: {threshold_pages}). "
                        f"Processing in background."
                    ),
                }
            )

        # --- Synchronous path
        ocr_agent = AgentFactory.create_from_config(config, model_id)
        parser = Parser(ocr_agent=ocr_agent)
        result = await asyncio.to_thread(parser.parse, file_path, force_ocr)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        text = result.text
        if parse_formatting:
            text = await asyncio.to_thread(TextParser.auto_parse, text)

        raw_ocr_dir = os.path.join(_data_dir(), "raw_ocr")
        parsed_dir = os.path.join(_data_dir(), "parsed")
        os.makedirs(raw_ocr_dir, exist_ok=True)
        os.makedirs(parsed_dir, exist_ok=True)
        base_filename = os.path.splitext(file.filename)[0]
        try:
            with open(os.path.join(raw_ocr_dir, f"{base_filename}.txt"), "w", encoding="utf-8") as f:
                f.write(result.text)
        except Exception as e:
            logger.warning("Failed to save raw OCR: %s", e)
        try:
            DocxGenerator().generate(
                text=text,
                filename=file.filename,
                model_id=model_id,
                pages=result.pages or 1,
                file_type=result.file_type,
                output_path=os.path.join(parsed_dir, f"{base_filename}.docx"),
            )
        except Exception as e:
            logger.warning("Failed to create DOCX: %s", e)

        response_data = {
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
                fields = [
                    SchemaField(
                        name=f["name"],
                        type=FieldType(f["type"]),
                        description=f.get("description", ""),
                        required=f.get("required", False),
                    )
                    for f in schema_data
                ]
                extraction_config = ExtractionConfig(
                    fields=fields,
                    target=ExtractionTarget(extraction_target or "document"),
                )
                llm_agent = AgentFactory.create_llm_agent(extractor_model, config=config)
                extractor = Extractor(agent=llm_agent)
                ex = await asyncio.to_thread(extractor.extract, text, extraction_config)
                if ex.success:
                    response_data["extraction"] = {
                        "success": True,
                        "structured_data": ex.structured_data,
                        "field_errors": ex.field_errors,
                    }
                else:
                    response_data["extraction"] = {"success": False, "error": ex.error}
            except Exception as e:
                response_data["extraction"] = {"success": False, "error": f"Extraction failed: {e}"}

        return JSONResponse(response_data)
    finally:
        _safe_remove(file_path)


# ---------------------------------------------------------------------------
# Saved-file accessors
# ---------------------------------------------------------------------------

@app.get("/raw-ocr/{filename}")
async def get_raw_ocr(filename: str) -> JSONResponse:
    raw_ocr_dir = os.path.join(_data_dir(), "raw_ocr")
    validate_file_path(f"{filename}.txt", raw_ocr_dir)
    file_path = os.path.join(raw_ocr_dir, f"{filename}.txt")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Raw OCR file not found: {filename}.txt")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return JSONResponse(
            {
                "success": True,
                "filename": f"{filename}.txt",
                "content": content,
                "size": len(content),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")


@app.get("/parsed/{filename}")
async def get_parsed_docx(filename: str):
    parsed_dir = os.path.join(_data_dir(), "parsed")
    validate_file_path(f"{filename}.docx", parsed_dir)
    file_path = os.path.join(parsed_dir, f"{filename}.docx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Parsed DOCX file not found: {filename}.docx")
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{filename}.docx",
    )


@app.get("/list-saved-files")
async def list_saved_files() -> JSONResponse:
    raw_ocr_dir = os.path.join(_data_dir(), "raw_ocr")
    parsed_dir = os.path.join(_data_dir(), "parsed")
    files: list = []
    if os.path.exists(raw_ocr_dir):
        for filename in os.listdir(raw_ocr_dir):
            if filename.endswith(".txt") and filename != ".gitkeep":
                base_name = filename[:-4]
                file_path = os.path.join(raw_ocr_dir, filename)
                docx_path = os.path.join(parsed_dir, f"{base_name}.docx")
                files.append(
                    {
                        "filename": base_name,
                        "raw_ocr": {
                            "exists": True,
                            "path": f"/raw-ocr/{base_name}",
                            "size": os.path.getsize(file_path),
                        },
                        "parsed": {
                            "exists": os.path.exists(docx_path),
                            "path": f"/parsed/{base_name}" if os.path.exists(docx_path) else None,
                            "size": os.path.getsize(docx_path) if os.path.exists(docx_path) else 0,
                        },
                        "created_at": os.path.getctime(file_path),
                    }
                )
    files.sort(key=lambda x: x["created_at"], reverse=True)
    return JSONResponse({"success": True, "count": len(files), "files": files})
