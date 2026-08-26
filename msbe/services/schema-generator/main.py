"""
M.DocAI MSBE Schema Generator service.

Implements ``/generate-schema`` exactly as the monolith does — including
the optional file sample, the tier-driven model selection, and the
flat-list ``schema`` shape returned to the frontend.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import Config, TierConfig
from core.agent_factory import AgentFactory
from core.utils import secure_save_file
from functions.parser import Parser
from functions.schema_generator import SchemaGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="M.DocAI MSBE Schema Generator", version="0.2.0")


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
    return JSONResponse({"status": "healthy", "service": "schema-generator", "version": app.version})


@app.post("/generate-schema")
async def generate_schema(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None),
    tier: str = Form("Normal"),
    config: Config = Depends(get_config),
) -> JSONResponse:
    sample_text: Optional[str] = None
    file_path: Optional[str] = None

    try:
        if file and file.filename:
            upload_folder = config.upload_config.get("folder", "uploads")
            file_path = await secure_save_file(file, upload_folder)
            ocr_model_id = (
                config.get_available_models()[0] if config.get_available_models() else None
            )
            if ocr_model_id:
                ocr_agent = AgentFactory.create_from_config(config, ocr_model_id)
                parser = Parser(ocr_agent=ocr_agent)
                parse_result = await asyncio.to_thread(parser.parse, file_path)
                if parse_result.success:
                    sample_text = parse_result.text[:2000]

        model_id = TierConfig.get_extractor_model(tier)
        llm_agent = AgentFactory.create_llm_agent(model_id, config=config)
        schema_gen = SchemaGenerator(agent=llm_agent)
        result = await asyncio.to_thread(schema_gen.generate, sample_text or "", prompt)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        return JSONResponse(
            {
                "success": True,
                "schema": [
                    {
                        "name": field.name,
                        "type": field.type.value,
                        "description": field.description,
                        "required": field.required,
                    }
                    for field in result.fields
                ],
            }
        )
    finally:
        if file_path:
            _safe_remove(file_path)
