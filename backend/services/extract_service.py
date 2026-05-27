"""
Extract service — structured data extraction business logic.

Handles:
- Schema generation via AI
- File-based extraction (OCR + extract)
- Text-based extraction (reusing OCR results)
"""

import asyncio
import json
import logging
import os
from typing import Optional

from agents.factory import AgentFactory
from core.middleware import FileSizeValidator
from core.schemas import ExtractionConfig, ExtractionTarget, FieldType, SchemaField
from core.utils import secure_save_file
from components.extractor import Extractor
from components.parser import Parser
from components.schema_generator import SchemaGenerator
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


def _parse_schema_fields(schema_json: str) -> list[SchemaField]:
    """Parse a JSON schema string into a list of SchemaField objects."""
    try:
        schema_data = json.loads(schema_json)
        return [
            SchemaField(
                name=field["name"],
                type=FieldType(field["type"]),
                description=field.get("description", ""),
                required=field.get("required", False),
            )
            for field in schema_data
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid schema: {str(e)}")


async def generate_schema(
    prompt: str,
    file: Optional[UploadFile],
    tier: str,
    config: Config,
) -> dict:
    """
    Generate an extraction schema from a natural-language prompt.

    Returns a dict with ``success`` and ``schema`` keys.
    """
    sample_text = None
    file_path = None

    try:
        if file and file.filename:
            upload_folder = config.upload_config.get("folder", "uploads")
            file_path = await secure_save_file(file, upload_folder)

            ocr_model_id = config.get_available_models()[0] if config.get_available_models() else None
            if ocr_model_id:
                ocr_agent = AgentFactory.create_from_config(config, ocr_model_id)
                parser = Parser(ocr_agent=ocr_agent)
                parse_result = await asyncio.to_thread(parser.parse, file_path)
                if parse_result.success:
                    sample_text = parse_result.text[:2000]

        model_id = TierConfig.get_extractor_model(tier)
        provider = None
        try:
            model_id, provider = TierConfig.get_extractor_model_spec(tier)
        except Exception:
            pass
        llm_agent = AgentFactory.create_llm_agent(model_id, provider=provider, config=config)
        schema_gen = SchemaGenerator(agent=llm_agent)
        result = await asyncio.to_thread(schema_gen.generate, sample_text or "", prompt)

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        return {
            "success": True,
            "schema": [
                {"name": f.name, "type": f.type.value, "description": f.description, "required": f.required}
                for f in result.fields
            ],
        }

    finally:
        if file_path:
            _safe_remove(file_path)


async def extract_from_file(
    file: UploadFile,
    parser_model_id: str,
    extractor_model_id: str,
    extraction_schema: str,
    extraction_target: str,
    use_generated_schema: bool,
    schema_prompt: Optional[str],
    config: Config,
    provider: Optional[str] = None,
) -> dict:
    """
    OCR a file then extract structured data from it.

    Returns a dict with ``success``, ``structured_data``, ``field_errors``, and ``filename``.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_config = config.upload_config
    max_size_mb = upload_config.get("max_size_mb", 10)
    await file_size_validator.validate(file, max_size_mb)

    upload_folder = upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        ocr_agent = AgentFactory.create_from_config(config, parser_model_id, provider_override=provider)
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = await asyncio.to_thread(parser.parse, file_path)

        if not parse_result.success:
            raise HTTPException(status_code=500, detail=parse_result.error)

        llm_agent = AgentFactory.create_llm_agent(extractor_model_id, config=config, provider=provider)

        if use_generated_schema and schema_prompt:
            schema_gen = SchemaGenerator(agent=llm_agent)
            schema_result = await asyncio.to_thread(schema_gen.generate, parse_result.text, schema_prompt)
            if not schema_result.success:
                raise HTTPException(status_code=500, detail=schema_result.error)
            fields = schema_result.fields
        else:
            fields = _parse_schema_fields(extraction_schema)

        extraction_config = ExtractionConfig(fields=fields, target=ExtractionTarget(extraction_target))
        extractor = Extractor(agent=llm_agent)
        extract_result = await asyncio.to_thread(extractor.extract, parse_result.text, extraction_config)

        if not extract_result.success:
            raise HTTPException(status_code=500, detail=extract_result.error)

        return {
            "success": True,
            "structured_data": extract_result.structured_data,
            "field_errors": extract_result.field_errors,
            "filename": file.filename,
        }

    finally:
        _safe_remove(file_path)


async def extract_from_text(
    text: str,
    extraction_schema: str,
    extraction_target: str,
    extractor_model_id: str,
    extractor: Extractor,
    config: Config,
) -> dict:
    """
    Extract structured data from pre-extracted text.

    Returns a dict with ``success`` and ``extraction`` keys.
    """
    try:
        # Override extractor if an explicit non-default model was provided
        if extractor_model_id != "gemini-2.5-flash":
            llm_agent = AgentFactory.create_llm_agent(extractor_model_id, config=config)
            extractor = Extractor(agent=llm_agent)

        fields = _parse_schema_fields(extraction_schema)
        extraction_config = ExtractionConfig(fields=fields, target=ExtractionTarget(extraction_target))
        extract_result = await asyncio.to_thread(extractor.extract, text, extraction_config)

        if not extract_result.success:
            raise HTTPException(status_code=500, detail=extract_result.error)

        return {
            "success": True,
            "extraction": {
                "success": True,
                "structured_data": extract_result.structured_data,
                "field_errors": extract_result.field_errors,
            },
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid schema JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
