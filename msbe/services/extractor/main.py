"""
M.DocAI MSBE Extractor service.

Implements ``/extract`` (file → OCR → optional schema-gen → extract) and
``/extract-text`` (text-only). Response shapes match the monolith exactly.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import Config, TierConfig
from core import (
    ExtractionConfig,
    ExtractionTarget,
    FieldType,
    SchemaField,
)
from core.agent_factory import AgentFactory
from core.middleware import FileSizeValidator
from core.utils import secure_save_file
from functions.extractor import Extractor
from functions.parser import Parser
from functions.schema_generator import SchemaGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="M.DocAI MSBE Extractor", version="0.2.0")
file_size_validator = FileSizeValidator()


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
    return JSONResponse({"status": "healthy", "service": "extractor", "version": app.version})


@app.post("/extract")
async def extract_data(
    file: UploadFile = File(...),
    parser_model_id: str = Form(...),
    extractor_model_id: str = Form("qwen3-max"),
    extraction_schema: str = Form(...),
    extraction_target: str = Form("document"),
    generate_schema: bool = Form(False),
    schema_prompt: Optional[str] = Form(None),
    config: Config = Depends(get_config),
) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_config = config.upload_config
    max_size_mb = upload_config.get("max_size_mb", 10)
    await file_size_validator.validate(file, max_size_mb)
    upload_folder = upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = await asyncio.to_thread(parser.parse, file_path)
        if not parse_result.success:
            raise HTTPException(status_code=500, detail=parse_result.error)

        llm_agent = AgentFactory.create_llm_agent(extractor_model_id, config=config)

        if generate_schema and schema_prompt:
            schema_gen = SchemaGenerator(agent=llm_agent)
            schema_result = await asyncio.to_thread(schema_gen.generate, parse_result.text, schema_prompt)
            if not schema_result.success:
                raise HTTPException(status_code=500, detail=schema_result.error)
            fields = schema_result.fields
        else:
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
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid schema: {e}")

        extraction_config = ExtractionConfig(
            fields=fields, target=ExtractionTarget(extraction_target)
        )
        extractor = Extractor(agent=llm_agent)
        extract_result = await asyncio.to_thread(extractor.extract, parse_result.text, extraction_config)
        if not extract_result.success:
            raise HTTPException(status_code=500, detail=extract_result.error)

        return JSONResponse(
            {
                "success": True,
                "structured_data": extract_result.structured_data,
                "field_errors": extract_result.field_errors,
                "filename": file.filename,
            }
        )
    finally:
        _safe_remove(file_path)


@app.post("/extract-text")
async def extract_text(
    text: str = Form(...),
    extraction_schema: str = Form(...),
    extraction_target: str = Form("document"),
    extractor_model_id: str = Form("gemini-2.5-flash"),
    tier: str = Form("Normal"),
    config: Config = Depends(get_config),
) -> JSONResponse:
    try:
        # Mirror the monolith: tier-resolved DI when caller did not override.
        if extractor_model_id == "gemini-2.5-flash":
            extractor_model_id = TierConfig.get_extractor_model(tier)
        llm_agent = AgentFactory.create_llm_agent(extractor_model_id, config=config)
        extractor = Extractor(agent=llm_agent)

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
            fields=fields, target=ExtractionTarget(extraction_target)
        )
        extract_result = await asyncio.to_thread(extractor.extract, text, extraction_config)
        if not extract_result.success:
            raise HTTPException(status_code=500, detail=extract_result.error)

        return JSONResponse(
            {
                "success": True,
                "extraction": {
                    "success": True,
                    "structured_data": extract_result.structured_data,
                    "field_errors": extract_result.field_errors,
                },
            }
        )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid schema JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")
