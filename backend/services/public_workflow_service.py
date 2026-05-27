"""
Public Workflow Execution Service.

Handles execution of stored workflows (full pipeline and individual steps).
Delegates to existing component-level services for actual processing.
"""

import asyncio
import logging
import os
import threading
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile

from agents.factory import AgentFactory
from components.classifier import Classifier, ClassificationRule
from components.extractor import Extractor
from components.parser import Parser
from components.splitter import ChunkCategory, Splitter
from core.middleware import FileSizeValidator
from core.schemas import ExtractionConfig, ExtractionTarget, FieldType, SchemaField
from core.utils import allowed_file, secure_save_file
from services.job_manager import job_manager
from services.workflow_store import WorkflowNotFoundError, workflow_store
from settings import settings, TierConfig

logger = logging.getLogger(__name__)

file_size_validator = FileSizeValidator()

_BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))


def _safe_remove(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning("Failed to remove temp file %s: %s", path, e)


def _get_step_by_type(steps: List[Dict[str, Any]], step_type: str) -> Optional[Dict[str, Any]]:
    """Return the first step of the given type from a steps list, or None."""
    for step in steps:
        if step.get("type") == step_type:
            return step
    return None


async def _save_upload(file: UploadFile) -> str:
    """Validate and save an uploaded file. Returns the saved file path."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    upload_config = settings.upload_config
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
        saved_path = await secure_save_file(file, upload_folder)
        # --- Upload copy to MinIO ---
        from core.minio_client import minio_client
        basename = os.path.basename(saved_path)
        await asyncio.to_thread(minio_client.upload_file, saved_path, f"uploads/{basename}")
        return saved_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


# ---------------------------------------------------------------------------
# Individual step runners
# ---------------------------------------------------------------------------

async def _run_parse(file_path: str, tier: str) -> Dict[str, Any]:
    model_id = TierConfig.get_parser_model(tier)
    ocr_agent = AgentFactory.create_from_config(settings, model_id)
    parser = Parser(ocr_agent=ocr_agent)
    result = await asyncio.to_thread(parser.parse, file_path)
    if not result.success:
        raise Exception(f"Parse failed: {result.error}")
    return {
        "text": result.text,
        "file_type": result.file_type,
        "pages": result.pages,
        "is_scanned": result.is_scanned,
    }


async def _run_classify(file_path: str, tier: str, step_config: Dict[str, Any]) -> Dict[str, Any]:
    # Parse first
    parse_result = await _run_parse(file_path, tier)

    rules_data = step_config.get("rules", [])
    if not rules_data:
        raise Exception("classify step requires 'rules' in config")

    rules = [ClassificationRule(doc_type=r["doc_type"], description=r.get("description", "")) for r in rules_data]

    classifier_model_id = TierConfig.get_classifier_llm_model(tier)
    llm_agent = AgentFactory.create_llm_agent(classifier_model_id, config=settings)
    classifier = Classifier(agent=llm_agent)
    classify_result = await asyncio.to_thread(classifier.classify, parse_result["text"], rules)

    if not classify_result.success:
        raise Exception(f"Classify failed: {classify_result.error}")

    return {
        "document_type": classify_result.document_type,
        "confidence": classify_result.confidence,
        "reasoning": classify_result.reasoning,
    }


async def _run_extract(file_path: str, tier: str, step_config: Dict[str, Any]) -> Dict[str, Any]:
    # Parse first
    parse_result = await _run_parse(file_path, tier)

    schema_data = step_config.get("schema", {})
    fields_data = schema_data.get("fields", [])
    if not fields_data:
        raise Exception("extract step requires 'schema.fields' in config")

    fields = [
        SchemaField(
            name=f["name"],
            type=FieldType(f.get("type", "string")),
            description=f.get("description", ""),
            required=f.get("required", False),
        )
        for f in fields_data
    ]
    target = ExtractionTarget(step_config.get("target", "document"))
    extraction_config = ExtractionConfig(fields=fields, target=target)

    extractor_model_id = TierConfig.get_extractor_model(tier)
    llm_agent = AgentFactory.create_llm_agent(extractor_model_id, config=settings)
    extractor = Extractor(agent=llm_agent)
    extract_result = await asyncio.to_thread(extractor.extract, parse_result["text"], extraction_config)

    if not extract_result.success:
        raise Exception(f"Extract failed: {extract_result.error}")

    return {
        "structured_data": extract_result.structured_data,
        "field_errors": extract_result.field_errors,
    }


async def _run_split(file_path: str, tier: str, step_config: Dict[str, Any]) -> Dict[str, Any]:
    categories_data = step_config.get("categories", [])
    if not categories_data:
        raise Exception("split step requires 'categories' in config")

    chunk_categories = [
        ChunkCategory(name=c["name"], description=c.get("description", ""), order=c.get("order", 0))
        for c in categories_data
    ]
    allow_uncategorized = step_config.get("allow_uncategorized", True)

    splitter_model_id = TierConfig.get_splitter_model(tier)
    vlm_agent = AgentFactory.create_vlm_agent(splitter_model_id, config=settings)
    splitter = Splitter(agent=vlm_agent)
    split_result = await asyncio.to_thread(splitter.split, file_path, chunk_categories, allow_uncategorized=allow_uncategorized)

    if not split_result.success:
        raise Exception(f"Split failed: {split_result.error}")

    return {
        "chunks": [
            {"content": c.content, "category": c.category, "page_number": c.page_number, "confidence": c.confidence}
            for c in split_result.chunks or []
        ],
        "unknown_chunks": [
            {"content": c.content, "category": c.category, "page_number": c.page_number, "confidence": c.confidence}
            for c in split_result.unknown_chunks or []
        ],
    }


async def _run_step(step: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """Dispatch a single step to the appropriate runner."""
    step_type = step["type"]
    tier = step.get("tier", "Normal")
    config = step.get("config") or {}

    if step_type == "parse":
        return await _run_parse(file_path, tier)
    elif step_type == "classify":
        return await _run_classify(file_path, tier, config)
    elif step_type == "extract":
        return await _run_extract(file_path, tier, config)
    elif step_type == "split":
        return await _run_split(file_path, tier, config)
    else:
        raise Exception(f"Unknown step type: {step_type}")


# ---------------------------------------------------------------------------
# Full workflow execution
# ---------------------------------------------------------------------------

async def execute_workflow(workflow_id: str, file: UploadFile) -> Dict[str, Any]:
    """
    Execute all steps of a stored workflow on the uploaded file.

    Returns sync result or dispatches to background job for large files.
    """
    try:
        workflow = workflow_store.get(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    file_path = await _save_upload(file)

    try:
        # Check if we should dispatch to background
        bg_config = settings._config_data.get("background_tasks", {}) if hasattr(settings, "_config_data") else {}
        bg_enabled = bg_config.get("enabled", False)
        threshold_pages = bg_config.get("threshold_pages", 5)

        if bg_enabled and file_path.lower().endswith(".pdf"):
            try:
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(file_path)
                try:
                    page_count = len(pdf)
                finally:
                    pdf.close()
                if page_count > threshold_pages:
                    return await _dispatch_background(workflow_id, workflow, file_path, file.filename)
            except Exception:
                pass

        # Synchronous execution
        steps = workflow["steps"]
        completed: List[Dict[str, Any]] = []

        for step in steps:
            try:
                result = await _run_step(step, file_path)
                completed.append({"step": step["type"], "tier": step.get("tier", "Normal"), "result": result})
            except Exception as e:
                return {
                    "success": False,
                    "workflow_id": workflow_id,
                    "filename": file.filename,
                    "error": str(e),
                    "completed_steps": completed,
                }

        final_result = {
            "success": True,
            "workflow_id": workflow_id,
            "filename": file.filename,
            "results": completed,
        }
        
        # Upload result to MinIO
        from core.minio_client import minio_client
        basename = os.path.basename(file_path)
        await asyncio.to_thread(minio_client.upload_json, final_result, f"results/{workflow_id}/{basename}_result.json")
        
        return final_result

    finally:
        _safe_remove(file_path)


async def _dispatch_background(
    workflow_id: str, workflow: Dict[str, Any], file_path: str, filename: str
) -> Dict[str, Any]:
    """Dispatch workflow execution to a background thread."""
    job_id = job_manager.create_job()
    job_manager.update_status(job_id, "processing", progress=0.0)

    steps = workflow["steps"]

    def _worker():
        import asyncio as _asyncio
        loop = _asyncio.new_event_loop()
        try:
            completed = []
            total = len(steps)
            for i, step in enumerate(steps):
                try:
                    result = loop.run_until_complete(_run_step(step, file_path))
                    completed.append({"step": step["type"], "tier": step.get("tier", "Normal"), "result": result})
                    job_manager.update_status(job_id, "processing", progress=(i + 1) / total)
                except Exception as e:
                    job_manager.update_status(
                        job_id, "failed",
                        error=str(e),
                        result={"success": False, "workflow_id": workflow_id, "filename": filename,
                                "error": str(e), "completed_steps": completed},
                    )
                    return
            final_result = {"success": True, "workflow_id": workflow_id, "filename": filename, "results": completed}
            
            # Upload result to MinIO
            try:
                from core.minio_client import minio_client
                basename = os.path.basename(file_path)
                minio_client.upload_json(final_result, f"results/{workflow_id}/{basename}_result.json")
            except Exception as e:
                logger.error("Failed to upload background job result to MinIO: %s", e)
                
            job_manager.update_status(
                job_id, "completed", progress=1.0,
                result=final_result,
            )
        except Exception as exc:
            logger.exception("Background workflow job %s failed", job_id)
            job_manager.update_status(job_id, "failed", error=str(exc))
        finally:
            loop.close()
            _safe_remove(file_path)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    return {
        "job_id": job_id,
        "status": "pending",
        "poll_url": f"/api/v1/jobs/{job_id}/status",
        "message": f"Workflow dispatched to background. Poll {'/api/v1/jobs/' + job_id + '/status'} for updates.",
    }


# ---------------------------------------------------------------------------
# Individual step endpoints
# ---------------------------------------------------------------------------

async def execute_step_parse(workflow_id: str, file: UploadFile, tier_override: Optional[str] = None) -> Dict[str, Any]:
    """Execute only the parse step of a stored workflow."""
    try:
        workflow = workflow_store.get(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    step = _get_step_by_type(workflow["steps"], "parse")
    tier = tier_override or (step["tier"] if step else "Normal")

    file_path = await _save_upload(file)
    try:
        result = await _run_parse(file_path, tier)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _safe_remove(file_path)


async def execute_step_classify(workflow_id: str, file: UploadFile, tier_override: Optional[str] = None) -> Dict[str, Any]:
    """Execute only the classify step of a stored workflow."""
    try:
        workflow = workflow_store.get(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    step = _get_step_by_type(workflow["steps"], "classify")
    if not step:
        raise HTTPException(status_code=400, detail=f"No classify step defined in workflow {workflow_id}")

    tier = tier_override or step.get("tier", "Normal")
    config = step.get("config") or {}

    file_path = await _save_upload(file)
    try:
        result = await _run_classify(file_path, tier, config)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _safe_remove(file_path)


async def execute_step_extract(workflow_id: str, file: UploadFile, tier_override: Optional[str] = None) -> Dict[str, Any]:
    """Execute only the extract step of a stored workflow."""
    try:
        workflow = workflow_store.get(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    step = _get_step_by_type(workflow["steps"], "extract")
    if not step:
        raise HTTPException(status_code=400, detail=f"No extract step defined in workflow {workflow_id}")

    tier = tier_override or step.get("tier", "Normal")
    config = step.get("config") or {}

    file_path = await _save_upload(file)
    try:
        result = await _run_extract(file_path, tier, config)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _safe_remove(file_path)


async def execute_step_split(workflow_id: str, file: UploadFile, tier_override: Optional[str] = None) -> Dict[str, Any]:
    """Execute only the split step of a stored workflow."""
    try:
        workflow = workflow_store.get(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    step = _get_step_by_type(workflow["steps"], "split")
    if not step:
        raise HTTPException(status_code=400, detail=f"No split step defined in workflow {workflow_id}")

    tier = tier_override or step.get("tier", "Normal")
    config = step.get("config") or {}

    file_path = await _save_upload(file)
    try:
        result = await _run_split(file_path, tier, config)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _safe_remove(file_path)
