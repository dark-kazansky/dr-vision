"""
Split service — document splitting business logic.

Handles:
- Sections mode: categorized text chunks
- Document-type mode: page-range identification
- Persisting split results to disk
"""

import asyncio
import json
import logging
import os
from typing import Optional

from agents.factory import AgentFactory
from core.middleware import FileSizeValidator
from core.schemas import ChunkModel, DocumentTypeResult, SplitResponse
from core.utils import secure_save_file
from components.splitter import ChunkCategory, Splitter
from config import Config, TierConfig
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

file_size_validator = FileSizeValidator()


def _safe_remove(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning("Failed to remove temp file %s: %s", path, e)


def _parse_categories(categories_json: str) -> tuple[list, list[ChunkCategory]]:
    """Parse categories JSON into raw data and ChunkCategory objects."""
    try:
        categories_data = json.loads(categories_json)
        chunk_categories = [
            ChunkCategory(name=cat["name"], description=cat["description"], order=cat.get("order", 0))
            for cat in categories_data
        ]
        return categories_data, chunk_categories
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid categories: {str(e)}")


def _persist_split_result(payload: dict, base_filename: str) -> None:
    """Save split result to PostgreSQL. Raises if DB unavailable."""
    filename = payload.get("filename", base_filename)

    import asyncio as _aio
    from server import ocr_result_repo

    if not ocr_result_repo or not ocr_result_repo._pool:
        raise RuntimeError("Database unavailable — cannot persist split results")

    loop = _aio.new_event_loop()
    try:
        existing = loop.run_until_complete(ocr_result_repo.get_result_by_filename(filename))
        if existing:
            loop.run_until_complete(ocr_result_repo.update_result_data(
                existing["id"],
                {"split_result": payload},
            ))
        else:
            loop.run_until_complete(ocr_result_repo.store_result(
                filename=filename,
                raw_text="",
                model_id=payload.get("splitter_model"),
                result_data={
                    "type": "split",
                    "split_result": payload,
                },
            ))
    finally:
        loop.close()
    logger.info("Split result persisted to DB: %s", filename)


async def split_document(
    file: UploadFile,
    categories: str,
    allow_uncategorized: bool,
    splitter_tier: str,
    split_mode: str,
    config: Config,
    provider: Optional[str] = None,
) -> SplitResponse:
    """
    Split a document into categorized chunks or identify document-type boundaries.

    Returns a SplitResponse ready to be returned by the router.
    """
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

    categories_data, chunk_categories = _parse_categories(categories)
    splitter_model_id = TierConfig.get_splitter_model(splitter_tier)

    upload_folder = upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        vlm_agent = AgentFactory.create_vlm_agent(splitter_model_id, config=config, provider=provider)
        splitter = Splitter(agent=vlm_agent)
        base_filename = os.path.splitext(file.filename)[0]

        if split_mode == "document_type":
            split_result = await asyncio.to_thread(splitter.split_by_document_type, file_path, chunk_categories)

            if not split_result.success:
                from core.exceptions import raise_agent_error
                raise_agent_error(split_result, prefix="Split failed: ")

            document_type_models = [
                DocumentTypeResult(type_name=dt.type_name, page_numbers=dt.page_numbers, confidence=dt.confidence)
                for dt in split_result.document_types or []
            ]

            _persist_split_result(
                {
                    "filename": file.filename,
                    "splitter_model": splitter_model_id,
                    "splitter_tier": splitter_tier,
                    "split_mode": split_mode,
                    "categories": categories_data,
                    "document_types": [
                        {"type_name": dt.type_name, "page_numbers": dt.page_numbers, "confidence": dt.confidence}
                        for dt in split_result.document_types or []
                    ],
                    "timestamp": os.path.getctime(file_path) if os.path.exists(file_path) else None,
                },
                base_filename,
            )

            return SplitResponse(
                success=True, chunks=[], unknown_chunks=[], document_types=document_type_models, filename=file.filename
            )

        else:
            split_result = await asyncio.to_thread(
                splitter.split, file_path, chunk_categories, allow_uncategorized=allow_uncategorized
            )

            if not split_result.success:
                from core.exceptions import raise_agent_error
                raise_agent_error(split_result, prefix="Split failed: ")

            def _to_chunk_model(chunk) -> ChunkModel:
                return ChunkModel(
                    content=chunk.content,
                    category=chunk.category,
                    page_number=chunk.page_number,
                    confidence=chunk.confidence,
                )

            chunk_models = [_to_chunk_model(c) for c in split_result.chunks or []]
            unknown_chunk_models = [_to_chunk_model(c) for c in split_result.unknown_chunks or []]

            _persist_split_result(
                {
                    "filename": file.filename,
                    "splitter_model": splitter_model_id,
                    "splitter_tier": splitter_tier,
                    "split_mode": split_mode,
                    "categories": categories_data,
                    "allow_uncategorized": allow_uncategorized,
                    "chunks": [
                        {"content": c.content, "category": c.category, "page_number": c.page_number, "confidence": c.confidence}
                        for c in split_result.chunks or []
                    ],
                    "unknown_chunks": [
                        {"content": c.content, "category": c.category, "page_number": c.page_number, "confidence": c.confidence}
                        for c in split_result.unknown_chunks or []
                    ],
                    "timestamp": os.path.getctime(file_path) if os.path.exists(file_path) else None,
                },
                base_filename,
            )

            return SplitResponse(
                success=True,
                chunks=chunk_models,
                unknown_chunks=unknown_chunk_models,
                document_types=None,
                filename=file.filename,
            )

    finally:
        _safe_remove(file_path)
