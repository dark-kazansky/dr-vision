"""
M.DocAI MSBE Splitter service.

Implements the monolith's ``/split`` endpoint, including the
``split_mode = document_type`` branch and JSON persistence under
``data/splited/``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import Config, TierConfig
from core import ChunkModel, SplitResponse
from core.agent_factory import AgentFactory
from core.middleware import FileSizeValidator
from core.schemas import DocumentTypeResult
from core.utils import secure_save_file
from functions.splitter import ChunkCategory, Splitter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="M.DocAI MSBE Splitter", version="0.2.0")
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
    return JSONResponse({"status": "healthy", "service": "splitter", "version": app.version})


@app.post("/split", response_model=SplitResponse)
async def split_document(
    file: UploadFile = File(...),
    categories: str = Form(...),
    allow_uncategorized: bool = Form(True),
    parser_tier: str = Form("Normal"),
    splitter_tier: str = Form("Normal"),
    split_mode: str = Form("sections"),
    config: Config = Depends(get_config),
) -> SplitResponse:
    if split_mode not in ("sections", "document_type"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid split_mode: '{split_mode}'. Allowed values: 'sections', 'document_type'",
        )
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_config = config.upload_config
    max_size_mb = upload_config.get("max_size_mb", 10)
    await file_size_validator.validate(file, max_size_mb)

    try:
        categories_data: List[Dict[str, Any]] = json.loads(categories)
        chunk_categories = [
            ChunkCategory(
                name=cat["name"],
                description=cat["description"],
                order=cat.get("order", 0),
            )
            for cat in categories_data
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid categories: {e}")

    splitter_model_id = TierConfig.get_splitter_model(splitter_tier)
    upload_folder = upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        vlm_agent = AgentFactory.create_vlm_agent(splitter_model_id, config=config)
        splitter = Splitter(agent=vlm_agent)

        splited_dir = os.path.join(_data_dir(), "splited")
        os.makedirs(splited_dir, exist_ok=True)
        base_filename = os.path.splitext(file.filename)[0]
        split_file_path = os.path.join(splited_dir, f"{base_filename}.json")

        if split_mode == "document_type":
            split_result = await asyncio.to_thread(
                splitter.split_by_document_type, file_path, chunk_categories
            )
            if not split_result.success:
                raise HTTPException(status_code=500, detail=f"Split failed: {split_result.error}")

            document_type_models = [
                DocumentTypeResult(
                    type_name=dt.type_name,
                    page_numbers=dt.page_numbers,
                    confidence=dt.confidence,
                )
                for dt in split_result.document_types or []
            ]
            try:
                with open(split_file_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "filename": file.filename,
                            "splitter_model": splitter_model_id,
                            "splitter_tier": splitter_tier,
                            "split_mode": split_mode,
                            "categories": categories_data,
                            "document_types": [
                                {
                                    "type_name": dt.type_name,
                                    "page_numbers": dt.page_numbers,
                                    "confidence": dt.confidence,
                                }
                                for dt in split_result.document_types or []
                            ],
                            "timestamp": os.path.getctime(file_path) if os.path.exists(file_path) else None,
                        },
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )
            except Exception as e:
                logger.warning("Failed to save split result: %s", e)

            return SplitResponse(
                success=True,
                chunks=[],
                unknown_chunks=[],
                document_types=document_type_models,
                filename=file.filename,
            )

        # sections mode
        split_result = await asyncio.to_thread(
            splitter.split, file_path, chunk_categories, allow_uncategorized
        )
        if not split_result.success:
            raise HTTPException(status_code=500, detail=f"Split failed: {split_result.error}")

        chunk_models = [
            ChunkModel(
                content=chunk.content,
                category=chunk.category,
                page_number=chunk.page_number,
                confidence=chunk.confidence,
            )
            for chunk in split_result.chunks or []
        ]
        unknown_chunk_models = [
            ChunkModel(
                content=chunk.content,
                category=chunk.category,
                page_number=chunk.page_number,
                confidence=chunk.confidence,
            )
            for chunk in split_result.unknown_chunks or []
        ]
        try:
            with open(split_file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
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
                                "confidence": c.confidence,
                            }
                            for c in split_result.chunks or []
                        ],
                        "unknown_chunks": [
                            {
                                "content": c.content,
                                "category": c.category,
                                "page_number": c.page_number,
                                "confidence": c.confidence,
                            }
                            for c in split_result.unknown_chunks or []
                        ],
                        "timestamp": os.path.getctime(file_path) if os.path.exists(file_path) else None,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.warning("Failed to save split result: %s", e)

        return SplitResponse(
            success=True,
            chunks=chunk_models,
            unknown_chunks=unknown_chunk_models,
            document_types=None,
            filename=file.filename,
        )
    finally:
        _safe_remove(file_path)
