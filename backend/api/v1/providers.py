"""
Provider configuration endpoints.

GET  /providers              — list all providers with status and models
GET  /providers/{id}         — get a single provider detail
POST /providers/{id}/test    — test connection to a provider
POST /providers/{id}/config  — save provider config (API key, base URL, RPM)
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import Config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Providers"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ModelInfo(BaseModel):
    model_id: str
    name: str
    provider: str


# ---------------------------------------------------------------------------
# In-memory store for test connection results (survives until restart)
# ---------------------------------------------------------------------------
# status values: "not_configured" | "configured" | "ready" | "timeout" | "error"
_provider_status: Dict[str, str] = {}  # provider_id -> status string


class ProviderInfo(BaseModel):
    id: str = Field(..., description="Provider identifier (e.g. google_studio, poe_api)")
    name: str = Field(..., description="Human-readable provider name")
    type: str = Field(..., description="cloud or local")
    base_url: Optional[str] = None
    configured: bool = Field(..., description="True if required credentials are set")
    credential_key: Optional[str] = Field(None, description="Name of the env var holding the API key")
    credential_set: bool = Field(False, description="True if the credential env var is non-empty")
    credential_preview: Optional[str] = Field(None, description="Masked preview of the API key, e.g. sk-...••••3abc")
    key_placeholder: Optional[str] = Field(None, description="Placeholder hint for the API key input")
    models: List[ModelInfo] = Field(default_factory=list)
    description: str = ""
    rpm: Optional[int] = Field(None, description="Requests per minute limit")
    ready: bool = Field(False, description="True if last Test Connection succeeded")
    status: str = Field("not_configured", description="not_configured | configured | ready | timeout | error")


class ProviderListResponse(BaseModel):
    success: bool = True
    providers: List[ProviderInfo]


class TestConnectionResponse(BaseModel):
    success: bool
    provider: str
    message: str
    latency_ms: Optional[float] = None


class ProviderConfigRequest(BaseModel):
    api_key: Optional[str] = Field(None, description="API key value to save")
    base_url: Optional[str] = Field(None, description="Base URL override for local providers")
    rpm: Optional[int] = Field(None, description="Requests per minute limit")


class ProviderConfigResponse(BaseModel):
    success: bool
    provider: str
    message: str


# ---------------------------------------------------------------------------
# Provider metadata (static, augmented with runtime status)
# ---------------------------------------------------------------------------
_PROVIDER_META: Dict[str, Dict[str, Any]] = {
    "google_studio": {
        "name": "Google Studio (Gemini)",
        "type": "cloud",
        "credential_key": "GOOGLE_STUDIO_API_KEY",
        "key_placeholder": "AIzaSy...",
        "description": "Google Gemini API — supports VLM (vision) and LLM tasks. Best for OCR and classification.",
        "default_rpm": 15,   # Gemini free tier: 15 RPM; paid: up to 1000 RPM
    },
    "poe_api": {
        "name": "POE API",
        "type": "cloud",
        "credential_key": "POE_API_KEY",
        "key_placeholder": "poe-...",
        "description": "POE API — access to Claude, Gemini, Qwen and other models via POE platform.",
        "default_rpm": 60,   # POE API: ~60 RPM depending on subscription
    },
    "lm_studio": {
        "name": "LM Studio (Local)",
        "type": "local",
        "credential_key": None,
        "key_placeholder": "No API key required",
        "description": "Local LM Studio server — run models on your own hardware. No API key required.",
        "default_rpm": 10,   # Local default: 10 RPM (hardware-limited)
    },
    "bedrock": {
        "name": "AWS Bedrock",
        "type": "cloud",
        "credential_key": "AWS_ACCESS_KEY_ID",
        "key_placeholder": "AKIAIOSFODNN7EXAMPLE",
        "description": "AWS Bedrock — Claude Haiku and Sonnet via AWS infrastructure. Requires AWS credentials.",
        "default_rpm": 60,   # Bedrock default quota: 60 RPM per model
    },
    "ollama": {
        "name": "Ollama (Local)",
        "type": "local",
        "credential_key": None,
        "key_placeholder": "No API key required",
        "description": "Local Ollama server — run open-source models locally. No API key required.",
        "default_rpm": 10,   # Local default: 10 RPM (hardware-limited)
    },
}


def _mask_api_key(key: str) -> str:
    """Return a masked preview: first 6 chars + •••• + last 4 chars."""
    if not key:
        return ""
    key = key.strip()
    n = len(key)
    if n <= 10:
        # Too short — show only last 3 chars
        return "••••" + key[-3:]
    prefix = key[:6]
    suffix = key[-4:]
    return f"{prefix}••••{suffix}"


def _build_provider_info(provider_id: str, config: Config) -> ProviderInfo:
    """Build a ProviderInfo object for a given provider ID."""
    meta = _PROVIDER_META.get(provider_id, {
        "name": provider_id,
        "type": "cloud",
        "credential_key": None,
        "description": "",
    })

    provider_cfg = config.api_providers.get(provider_id, {})
    base_url = provider_cfg.get("base_url")

    credential_key = meta.get("credential_key")
    credential_value = os.getenv(credential_key) if credential_key else None
    credential_set = bool(credential_value) if credential_key else True  # local = always set
    credential_preview = _mask_api_key(credential_value) if credential_value else None

    # Collect models belonging to this provider
    models = [
        ModelInfo(
            model_id=mid,
            name=mcfg.get("name", mid),
            provider=provider_id,
        )
        for mid, mcfg in config.models.items()
        if mcfg.get("provider") == provider_id
    ]

    configured = credential_set and bool(base_url or meta["type"] == "local")

    # Read RPM from env var (e.g. GOOGLE_STUDIO_RPM)
    rpm_key = f"{provider_id.upper()}_RPM"
    rpm_val = os.getenv(rpm_key)
    rpm = int(rpm_val) if rpm_val and rpm_val.isdigit() else meta.get("default_rpm")

    # Determine status
    if provider_id in _provider_status:
        status = _provider_status[provider_id]
    elif configured:
        status = "configured"
    else:
        status = "not_configured"

    return ProviderInfo(
        id=provider_id,
        name=meta["name"],
        type=meta["type"],
        base_url=base_url,
        configured=configured,
        credential_key=credential_key,
        credential_set=credential_set,
        credential_preview=credential_preview,
        key_placeholder=meta.get("key_placeholder"),
        models=models,
        description=meta["description"],
        rpm=rpm,
        ready=status == "ready",
        status=status,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/providers",
    response_model=ProviderListResponse,
    summary="List all providers",
    description=(
        "Return all configured AI providers with their status, models, and credential info. "
        "Use this to populate the provider configuration UI."
    ),
)
async def list_providers() -> ProviderListResponse:
    try:
        config = Config.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {str(e)}")

    # Collect all provider IDs from settings.yaml + known providers
    provider_ids = set(config.api_providers.keys()) | set(_PROVIDER_META.keys())

    providers = [_build_provider_info(pid, config) for pid in sorted(provider_ids)]
    return ProviderListResponse(providers=providers)


@router.get(
    "/providers/{provider_id}",
    response_model=ProviderInfo,
    summary="Get provider details",
    description="Return details for a single provider including its models and credential status.",
    responses={404: {"description": "Provider not found"}},
)
async def get_provider(provider_id: str) -> ProviderInfo:
    try:
        config = Config.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {str(e)}")

    known_ids = set(config.api_providers.keys()) | set(_PROVIDER_META.keys())
    if provider_id not in known_ids:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_id}")

    return _build_provider_info(provider_id, config)


@router.post(
    "/providers/{provider_id}/test",
    response_model=TestConnectionResponse,
    summary="Test provider connection",
    description=(
        "Attempt a lightweight connection test to verify the provider is reachable "
        "and credentials are valid. Returns latency in milliseconds on success."
    ),
)
async def test_provider(provider_id: str) -> TestConnectionResponse:
    import time

    def _record(result: TestConnectionResponse) -> TestConnectionResponse:
        """Persist test outcome and return the result unchanged."""
        if result.success:
            _provider_status[provider_id] = "ready"
        else:
            # Distinguish timeout from other errors
            msg = result.message.lower()
            if "timeout" in msg or "timed out" in msg:
                _provider_status[provider_id] = "timeout"
            else:
                _provider_status[provider_id] = "error"
        return result

    try:
        config = Config.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {str(e)}")

    known_ids = set(config.api_providers.keys()) | set(_PROVIDER_META.keys())
    if provider_id not in known_ids:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_id}")

    provider_cfg = config.api_providers.get(provider_id, {})
    base_url = provider_cfg.get("base_url", "")
    meta = _PROVIDER_META.get(provider_id, {})
    credential_key = meta.get("credential_key")

    # Check credentials first
    if credential_key and not os.getenv(credential_key):
        return _record(TestConnectionResponse(
            success=False,
            provider=provider_id,
            message=f"Missing credential: {credential_key} environment variable is not set.",
        ))

    # Attempt connection
    start = time.monotonic()
    try:
        if provider_id == "google_studio":
            # Send a real minimal inference request using the google-genai SDK
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_STUDIO_API_KEY", "")
            genai.configure(api_key=api_key)
            # Try models in order until one succeeds (quota varies per model)
            test_models = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
            last_error = "No models available"
            for model_name in test_models:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        "Reply with the single word: ok",
                        generation_config={"max_output_tokens": 5},
                    )
                    latency = (time.monotonic() - start) * 1000
                    reply = response.text.strip() if response.text else "(no text)"
                    return _record(TestConnectionResponse(
                        success=True,
                        provider=provider_id,
                        message=f"Connected via {model_name}. Model replied: \"{reply}\"",
                        latency_ms=round(latency, 1),
                    ))
                except Exception as model_err:
                    last_error = str(model_err)
                    continue
            latency = (time.monotonic() - start) * 1000
            return _record(TestConnectionResponse(
                success=False,
                provider=provider_id,
                message=f"All test models failed. Last error: {last_error[:300]}",
                latency_ms=round(latency, 1),
            ))

        elif provider_id == "poe_api":
            # Send a real chat completion request via POE API
            import httpx
            api_key = os.getenv("POE_API_KEY", "")
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.poe.com/bot/GPT-3.5-Turbo",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"query": [{"role": "user", "content": "Reply with the single word: ok"}]},
                )
            latency = (time.monotonic() - start) * 1000
            if resp.status_code < 400:
                return _record(TestConnectionResponse(
                    success=True,
                    provider=provider_id,
                    message=f"Connected to POE API successfully. HTTP {resp.status_code}.",
                    latency_ms=round(latency, 1),
                ))
            return _record(TestConnectionResponse(
                success=False,
                provider=provider_id,
                message=f"POE API returned HTTP {resp.status_code}: {resp.text[:200]}",
            ))

        elif provider_id in ("lm_studio", "ollama"):
            # Send a real chat completion request to the local server
            import httpx
            if provider_id == "lm_studio":
                endpoint = (base_url or "http://localhost:1234").rstrip("/") + "/v1/chat/completions"
                payload = {
                    "model": "local-model",
                    "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
                    "max_tokens": 5,
                }
            else:
                endpoint = (base_url or "http://localhost:11434").rstrip("/") + "/api/generate"
                payload = {
                    "model": "llama3",
                    "prompt": "Reply with the single word: ok",
                    "stream": False,
                    "options": {"num_predict": 5},
                }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(endpoint, json=payload)
            latency = (time.monotonic() - start) * 1000
            if resp.status_code < 400:
                return _record(TestConnectionResponse(
                    success=True,
                    provider=provider_id,
                    message=f"Connected to {meta.get('name', provider_id)} at {endpoint}. HTTP {resp.status_code}.",
                    latency_ms=round(latency, 1),
                ))
            return _record(TestConnectionResponse(
                success=False,
                provider=provider_id,
                message=f"{meta.get('name', provider_id)} returned HTTP {resp.status_code}: {resp.text[:200]}",
            ))

        elif provider_id == "bedrock":
            # Send a real InvokeModel request to Bedrock
            import boto3, json as _json
            region = os.getenv("BEDROCK_REGION", "ap-southeast-2")
            model_arn = os.getenv("CLAUDE_HAIKU_ID", "anthropic.claude-3-haiku-20240307-v1:0")
            client = boto3.client("bedrock-runtime", region_name=region)
            body = _json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
            })
            response = client.invoke_model(modelId=model_arn, body=body)
            result = _json.loads(response["body"].read())
            latency = (time.monotonic() - start) * 1000
            reply = result.get("content", [{}])[0].get("text", "(no text)").strip()
            return _record(TestConnectionResponse(
                success=True,
                provider=provider_id,
                message=f"Connected to AWS Bedrock successfully. Model replied: \"{reply}\"",
                latency_ms=round(latency, 1),
            ))

        else:
            return _record(TestConnectionResponse(
                success=False,
                provider=provider_id,
                message=f"Connection test not implemented for provider: {provider_id}",
            ))

    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        logger.warning("Provider test failed for %s: %s", provider_id, e)
        msg = str(e)
        is_timeout = "timeout" in msg.lower() or "timed out" in msg.lower()
        _provider_status[provider_id] = "timeout" if is_timeout else "error"
        return TestConnectionResponse(
            success=False,
            provider=provider_id,
            message=msg,
            latency_ms=round(latency, 1),
        )


@router.post(
    "/providers/{provider_id}/config",
    response_model=ProviderConfigResponse,
    summary="Save provider configuration",
    description=(
        "Persist API key, base URL, and RPM settings for a provider. "
        "Values are written to the backend .env file so they survive restarts."
    ),
)
async def save_provider_config(
    provider_id: str,
    body: ProviderConfigRequest,
) -> ProviderConfigResponse:
    """Write provider settings (API key, base URL, RPM) to backend/.env."""
    known_ids = set(_PROVIDER_META.keys())
    if provider_id not in known_ids:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_id}")

    meta = _PROVIDER_META[provider_id]

    # Locate backend/.env (same directory as this file's package root)
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"

    # Read existing lines
    existing: Dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()

    updated: List[str] = []

    # API key
    if body.api_key is not None and meta.get("credential_key"):
        key_name = meta["credential_key"]
        if body.api_key.strip():
            existing[key_name] = body.api_key.strip()
            os.environ[key_name] = body.api_key.strip()
        # empty string = clear the key
        elif key_name in existing:
            del existing[key_name]
            os.environ.pop(key_name, None)

    # Base URL (for local providers)
    if body.base_url is not None:
        url_key = f"{provider_id.upper()}_BASE_URL"
        if body.base_url.strip():
            existing[url_key] = body.base_url.strip()
            os.environ[url_key] = body.base_url.strip()
        elif url_key in existing:
            del existing[url_key]
            os.environ.pop(url_key, None)

    # RPM
    if body.rpm is not None:
        rpm_key = f"{provider_id.upper()}_RPM"
        existing[rpm_key] = str(body.rpm)
        os.environ[rpm_key] = str(body.rpm)

    # Write back
    try:
        lines = [f"{k}={v}" for k, v in existing.items()]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env: {e}")

    # Reset status to "configured" when credentials are updated
    if body.api_key is not None and body.api_key.strip():
        _provider_status[provider_id] = "configured"

    return ProviderConfigResponse(
        success=True,
        provider=provider_id,
        message="Configuration saved successfully.",
    )


class AddProviderRequest(BaseModel):
    name: str = Field(..., description="Human-readable display name")
    type: str = Field("cloud", description="cloud or local")
    api_key: Optional[str] = Field(None, description="API key value")
    base_url: Optional[str] = Field(None, description="Base URL for the provider")
    rpm: Optional[int] = Field(None, description="Requests per minute limit")


@router.post(
    "/providers/{provider_id}/add",
    response_model=ProviderConfigResponse,
    summary="Add a new custom provider",
    description="Register a new AI provider by writing its metadata to _PROVIDER_META and credentials to .env.",
)
async def add_provider(
    provider_id: str,
    body: AddProviderRequest,
) -> ProviderConfigResponse:
    """Add a new provider entry to the runtime registry and persist credentials."""
    # Sanitize provider_id: lowercase, underscores only
    safe_id = provider_id.strip().lower().replace("-", "_").replace(" ", "_")
    if not safe_id or not safe_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid provider ID. Use lowercase letters, numbers, and underscores only.")

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"

    # Read existing .env
    existing: Dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()

    # Determine credential key name
    credential_key = f"{safe_id.upper()}_API_KEY" if body.type == "cloud" else None

    # Register in runtime metadata (survives until process restart)
    _PROVIDER_META[safe_id] = {
        "name": body.name.strip(),
        "type": body.type,
        "credential_key": credential_key,
        "description": f"Custom provider: {body.name.strip()}",
        "default_rpm": body.rpm,
    }

    # Persist API key
    if body.api_key and credential_key:
        existing[credential_key] = body.api_key.strip()
        os.environ[credential_key] = body.api_key.strip()

    # Persist base URL
    if body.base_url:
        url_key = f"{safe_id.upper()}_BASE_URL"
        existing[url_key] = body.base_url.strip()
        os.environ[url_key] = body.base_url.strip()

    # Persist RPM
    if body.rpm:
        rpm_key = f"{safe_id.upper()}_RPM"
        existing[rpm_key] = str(body.rpm)
        os.environ[rpm_key] = str(body.rpm)

    # Write .env
    try:
        lines = [f"{k}={v}" for k, v in existing.items()]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env: {e}")

    return ProviderConfigResponse(
        success=True,
        provider=safe_id,
        message=f"Provider '{body.name}' added successfully.",
    )
