"""
System / health router.

GET /health          — health check
GET /models/check    — model availability details
GET /tier-config     — tier-to-model mapping
PUT /tier-config     — update tier-to-model mapping
GET /test-logging    — logging smoke test
"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services import system_service
from core.dependencies import get_config
from core.schemas import HealthResponse
from config import Config

router = APIRouter(tags=["System"])


class TierModelUpdate(BaseModel):
    """Single cell update: feature + tier → provider + model."""
    feature: str          # parser | extractor | classifier_llm | splitter
    tier: str             # Rapid | Normal | Advance | Multimodal
    provider: str         # google_studio | poe_api | bedrock | lm_studio | ollama
    model: str            # model_id from settings.yaml


class TierConfigUpdateRequest(BaseModel):
    updates: list[TierModelUpdate]


@router.get("/health", response_model=HealthResponse)
async def health_check(config: Config = Depends(get_config)) -> HealthResponse:
    """Return server health status and list of available models."""
    return system_service.get_health(config)


@router.get("/models/check")
async def check_models(config: Config = Depends(get_config)) -> JSONResponse:
    """Return detailed availability info for every configured model."""
    return JSONResponse(system_service.get_models_info(config))


@router.get("/tier-config")
async def get_tier_config() -> JSONResponse:
    """Return tier-to-model mappings for all processing features."""
    return JSONResponse(system_service.get_tier_config())


@router.put("/tier-config")
async def update_tier_config(body: TierConfigUpdateRequest) -> JSONResponse:
    """Update tier-to-model mappings at runtime and persist to tier_config.py."""
    result = system_service.update_tier_config(body.updates)
    return JSONResponse(result)


@router.get("/test-logging")
async def test_logging() -> JSONResponse:
    """Smoke-test endpoint — emits log lines and returns runtime info."""
    return JSONResponse(system_service.get_logging_info())


# ---------------------------------------------------------------------------
# Job Queue Configuration (feat-012)
# ---------------------------------------------------------------------------

class JobQueueConfigUpdate(BaseModel):
    max_concurrent: Optional[int] = None
    default_timeout: Optional[int] = None
    default_max_retries: Optional[int] = None
    retry_delay_base: Optional[float] = None


@router.get("/api/v1/system/config/job-queue")
async def get_job_queue_config() -> JSONResponse:
    """Return current job queue configuration from settings.yaml."""
    import yaml
    from pathlib import Path

    config_path = Path("config/settings.yaml")
    jq_config = {"max_concurrent": 2, "default_timeout": 300, "default_max_retries": 3, "retry_delay_base": 1.0}

    try:
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            jq = data.get("job_queue", {})
            jq_config.update({k: v for k, v in jq.items() if v is not None})
    except Exception:
        pass

    return JSONResponse(jq_config)


@router.put("/api/v1/system/config/job-queue")
async def update_job_queue_config(body: JobQueueConfigUpdate) -> JSONResponse:
    """Update job queue configuration in settings.yaml. Requires server restart."""
    import yaml
    from pathlib import Path

    config_path = Path("config/settings.yaml")

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        if "job_queue" not in data:
            data["job_queue"] = {}

        if body.max_concurrent is not None:
            data["job_queue"]["max_concurrent"] = max(1, min(10, body.max_concurrent))
        if body.default_timeout is not None:
            data["job_queue"]["default_timeout"] = max(60, min(3600, body.default_timeout))
        if body.default_max_retries is not None:
            data["job_queue"]["default_max_retries"] = max(0, min(10, body.default_max_retries))
        if body.retry_delay_base is not None:
            data["job_queue"]["retry_delay_base"] = max(0.5, min(10.0, body.retry_delay_base))

        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return JSONResponse({"success": True, "message": "Job queue config saved. Restart server to apply.", "config": data["job_queue"]})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
