"""
M.DocAI MSBE API Gateway.

Single public entry point. Concerns:

* CORS, rate limiting (token bucket per IP), request logging with
  ``X-Request-ID`` response header.
* ``/health``        — same shape as the monolith's ``HealthResponse``.
* ``/health/services`` — aggregated downstream-service status.
* ``/models/check``    — proxied to the orchestrator (which uses the shared
  ``Config``); same response as the monolith.
* ``/tier-config``     — built locally from the shared ``TierConfig``.
* ``/test-logging``    — debug parity endpoint.
* ``/condition/evaluate`` — local evaluator (no remote call needed).
* ``/workflow/execute``   — legacy linear pipeline preserved by walking the
  steps array and calling the workers directly. The new graph-aware
  ``/workflows/run`` and ``/workflows/{id}/run`` are proxied to the
  orchestrator unchanged.
* All other paths are reverse-proxied to the matching downstream service
  via a longest-prefix routing table.

Response shapes are byte-identical to the monolith.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from config import Config, TierConfig
from core.rate_limiter import RateLimiter
from core.utils import check_server_status
from dr_vision_msbe import (
    Condition,
    ConditionEvaluator,
    ConditionOperator,
    ServiceURLs,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

_urls = ServiceURLs.from_env()
_auth_url = os.getenv("AUTH_SERVICE_URL", "http://auth:8006")


# ---------------------------------------------------------------------------
# Routing table — longest prefix wins; longer prefixes must precede shorter.
# ---------------------------------------------------------------------------

ROUTE_TABLE: Tuple[Tuple[str, str, str], ...] = (
    ("/api/v1/auth", "auth", _auth_url),
    ("/api/v1/users", "auth", _auth_url),
    ("/api/v1/admin", "auth", _auth_url),
    ("/workflow-runs", "orchestrator", _urls.orchestrator),
    ("/workflows", "orchestrator", _urls.orchestrator),
    ("/parse", "parser", _urls.parser),
    ("/ocr", "parser", _urls.parser),
    ("/raw-ocr", "parser", _urls.parser),
    ("/parsed", "parser", _urls.parser),
    ("/job", "parser", _urls.parser),
    ("/list-saved-files", "parser", _urls.parser),
    ("/classify-text", "classifier", _urls.classifier),
    ("/classify", "classifier", _urls.classifier),
    ("/extract-text", "extractor", _urls.extractor),
    ("/extract", "extractor", _urls.extractor),
    ("/split", "splitter", _urls.splitter),
    ("/generate-schema", "schema-generator", _urls.schema_generator),
)


def _resolve_service(path: str) -> Optional[Tuple[str, str]]:
    for prefix, name, url in ROUTE_TABLE:
        if path == prefix or path.startswith(prefix + "/"):
            return name, url
    return None


# ---------------------------------------------------------------------------
# App + lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    logger.info("MSBE Gateway ready on port %s", os.getenv("GATEWAY_PORT", "8090"))
    try:
        yield
    finally:
        await app.state.client.aclose()


app = FastAPI(title="M.DocAI MSBE Gateway", version="0.2.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

cors_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Rate limiter — same defaults as the monolith.
# ---------------------------------------------------------------------------

try:
    _rl_cfg: Dict[str, Any] = {}
    try:
        _rl_cfg = Config.load()._config_data.get("rate_limit", {})
    except Exception:
        _rl_cfg = {}
    app.add_middleware(
        RateLimiter,
        enabled=bool(int(os.getenv("RATE_LIMIT_ENABLED", "1") if os.getenv("RATE_LIMIT_ENABLED") else _rl_cfg.get("enabled", True))),
        requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", _rl_cfg.get("requests_per_minute", 30))),
        burst_size=int(os.getenv("RATE_LIMIT_BURST", _rl_cfg.get("burst_size", 10))),
    )
except Exception:
    logger.warning("Failed to enable rate limiter; continuing without one.")


# ---------------------------------------------------------------------------
# Request logging middleware — adds X-Request-ID like the monolith.
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid4().hex
    start = time.time()
    logger.info(
        "request_started request_id=%s method=%s path=%s",
        request_id, request.method, request.url.path,
    )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_errored request_id=%s", request_id)
        raise
    duration_ms = (time.time() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed request_id=%s method=%s path=%s status=%d duration_ms=%.2f",
        request_id, request.method, request.url.path, response.status_code, duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Health: monolith-shaped, plus aggregated view at /health/services
# ---------------------------------------------------------------------------

HEALTH_TARGETS: Tuple[Tuple[str, str], ...] = (
    ("auth", _auth_url),
    ("orchestrator", _urls.orchestrator),
    ("parser", _urls.parser),
    ("classifier", _urls.classifier),
    ("extractor", _urls.extractor),
    ("splitter", _urls.splitter),
    ("schema-generator", _urls.schema_generator),
)


async def _check_health(name: str, base_url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    try:
        response = await client.get(f"{base_url}/health", timeout=5.0)
        return {
            "name": name,
            "url": base_url,
            "status": "healthy" if response.status_code == 200 else "degraded",
            "code": response.status_code,
        }
    except Exception as e:
        return {"name": name, "url": base_url, "status": "unreachable", "error": str(e)}


@app.get("/health")
async def health() -> JSONResponse:
    """Mirror of the monolith's /health (HealthResponse shape)."""
    try:
        config = Config.load()
        available_models = config.get_available_models()
        providers = config.api_providers
        server_running = False
        if providers:
            first_provider = next(iter(providers.values()))
            base_url = first_provider.get("base_url")
            if base_url:
                server_running = bool(check_server_status(base_url).get("running"))
        if server_running and available_models:
            status = "healthy"
        elif available_models:
            status = "degraded"
        else:
            status = "unhealthy"
        return JSONResponse(
            {
                "status": status,
                "server_running": server_running,
                "available_models": available_models,
            }
        )
    except Exception as e:
        return JSONResponse(
            {"status": "unhealthy", "server_running": False, "available_models": [], "error": str(e)},
            status_code=200,
        )


@app.get("/health/services")
async def health_services() -> JSONResponse:
    client: httpx.AsyncClient = app.state.client
    results = await asyncio.gather(*[_check_health(n, u, client) for n, u in HEALTH_TARGETS])
    failed = [r for r in results if r["status"] != "healthy"]
    overall = "healthy" if not failed else "degraded"
    return JSONResponse(
        {"status": overall, "services": results, "failed_services": [r["name"] for r in failed]}
    )


# ---------------------------------------------------------------------------
# /tier-config and /models/check — local; same response as monolith.
# ---------------------------------------------------------------------------

@app.get("/tier-config")
async def get_tier_config() -> JSONResponse:
    return JSONResponse({"success": True, "config": TierConfig.export_to_json()})


@app.get("/models/check")
async def models_check() -> JSONResponse:
    config = Config.load()
    models_info: List[Dict[str, Any]] = []
    for model_id, model_config in config.models.items():
        provider = model_config.get("provider")
        provider_config = config.api_providers.get(provider, {})
        api_key_set = False
        api_key_name = None
        if provider == "google_studio":
            api_key_name = "GOOGLE_STUDIO_API_KEY"
            api_key_set = bool(os.getenv("GOOGLE_STUDIO_API_KEY"))
        elif provider == "poe_api":
            api_key_name = "POE_API_KEY"
            api_key_set = bool(os.getenv("POE_API_KEY"))
        elif provider == "lm_studio":
            api_key_name = "N/A (local)"
            api_key_set = True
        elif provider == "bedrock":
            api_key_name = "AWS credentials"
            api_key_set = bool(os.getenv("AWS_ACCESS_KEY_ID")) or os.path.exists(
                os.path.expanduser("~/.aws/credentials")
            )
        models_info.append(
            {
                "model_id": model_id,
                "name": model_config.get("name", model_id),
                "provider": provider,
                "base_url": provider_config.get("base_url"),
                "api_key_name": api_key_name,
                "api_key_set": api_key_set,
                "available": api_key_set,
            }
        )
    by_provider: Dict[str, List[Dict[str, Any]]] = {}
    for m in models_info:
        by_provider.setdefault(m["provider"], []).append(m)
    return JSONResponse(
        {
            "success": True,
            "models": models_info,
            "by_provider": by_provider,
            "total_models": len(models_info),
            "available_models": len([m for m in models_info if m["available"]]),
        }
    )


@app.get("/test-logging")
async def test_logging() -> JSONResponse:
    logger.info("=" * 50)
    logger.info("TEST LOGGING ENDPOINT CALLED")
    logger.info("=" * 50)
    return JSONResponse(
        {
            "success": True,
            "message": "Check your gateway terminal for log output",
            "python_version": sys.version,
            "cwd": os.getcwd(),
            "stdout_isatty": sys.stdout.isatty(),
        }
    )


# ---------------------------------------------------------------------------
# /condition/evaluate — local evaluation.
# ---------------------------------------------------------------------------

@app.post("/condition/evaluate")
async def evaluate_condition(
    conditions: str = Form(...),
    previous_result: str = Form(...),
    field_name: str = Form("document_type"),
) -> JSONResponse:
    try:
        conditions_data = json.loads(conditions)
        condition_list = [
            Condition(
                operator=ConditionOperator(c["operator"]),
                value=c.get("value"),
                valueMin=c.get("valueMin"),
                valueMax=c.get("valueMax"),
            )
            for c in conditions_data
        ]
        result_data = json.loads(previous_result)
        evaluator = ConditionEvaluator()
        eval_result = evaluator.evaluate_from_previous_result(result_data, condition_list, field_name)
        if not eval_result.success:
            raise HTTPException(status_code=500, detail=eval_result.error)
        return JSONResponse(
            {
                "success": True,
                "matched_index": eval_result.matched_index,
                "is_else": eval_result.matched_index is None,
            }
        )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Condition evaluation failed: {e}")


# ---------------------------------------------------------------------------
# /workflow/execute — legacy linear pipeline preserved at the gateway.
# ---------------------------------------------------------------------------

async def _post_to_service(
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
    *,
    files: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = await client.post(f"{base_url}{path}", files=files, data=data)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Downstream service error at {path}: {response.text}",
        )
    return response.json()


@app.post("/workflow/execute")
async def execute_workflow(
    file: UploadFile = File(...),
    workflow: str = Form(...),
) -> JSONResponse:
    """Linear sequential workflow runner (matches monolith /workflow/execute)."""
    try:
        workflow_data = json.loads(workflow)
        steps = workflow_data.get("steps", [])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid workflow: {e}")
    if not steps:
        raise HTTPException(status_code=400, detail="Workflow must have at least one step")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"
    client: httpx.AsyncClient = app.state.client

    results: List[Dict[str, Any]] = []
    parse_text_cache: Dict[str, str] = {}

    async def _parse(tier: str) -> Dict[str, Any]:
        if tier in parse_text_cache:
            return {"text": parse_text_cache[tier]}
        files = {"file": (file.filename, file_bytes, content_type)}
        data = {
            "model_id": TierConfig.get_parser_model(tier),
            "tier": tier,
            "process_all_pages": "true",
            "parse_formatting": "true",
        }
        payload = await _post_to_service(client, _urls.parser, "/parse", files=files, data=data)
        if not payload.get("success"):
            raise HTTPException(status_code=500, detail=payload.get("error") or "Parse failed")
        parse_text_cache[tier] = payload.get("text", "")
        return payload

    try:
        for step in steps:
            step_type = step.get("type")
            step_tier = step.get("tier", "Normal")
            step_config = step.get("config", {})

            if step_type == "parse":
                payload = await _parse(step_tier)
                result = {
                    "text": payload.get("text"),
                    "file_type": payload.get("file_type"),
                    "pages": payload.get("pages"),
                }
            elif step_type == "classify":
                parsed = await _parse(step_tier)
                payload = await _post_to_service(
                    client,
                    _urls.classifier,
                    "/classify-text",
                    data={
                        "text": parsed["text"],
                        "classification_rules": json.dumps(step_config.get("rules", [])),
                        "tier": step_tier,
                    },
                )
                # /classify-text returns ClassifyResponse → flatten to monolith shape
                first = (payload.get("results") or [{}])[0]
                result = {
                    "document_type": first.get("documentType"),
                    "confidence": first.get("confidence"),
                    "reasoning": first.get("reasoning"),
                }
            elif step_type == "extract":
                parsed = await _parse(step_tier)
                payload = await _post_to_service(
                    client,
                    _urls.extractor,
                    "/extract-text",
                    data={
                        "text": parsed["text"],
                        "extraction_schema": json.dumps(
                            (step_config.get("schema") or {}).get("fields", [])
                        ),
                        "extraction_target": step_config.get("target", "document"),
                        "tier": step_tier,
                    },
                )
                ex = payload.get("extraction") or {}
                result = {
                    "structured_data": ex.get("structured_data"),
                    "field_errors": ex.get("field_errors"),
                }
            elif step_type == "split":
                files = {"file": (file.filename, file_bytes, content_type)}
                data = {
                    "categories": json.dumps(step_config.get("categories", [])),
                    "parser_tier": step_tier,
                    "splitter_tier": step_tier,
                    "allow_uncategorized": str(step_config.get("allow_uncategorized", True)).lower(),
                }
                payload = await _post_to_service(client, _urls.splitter, "/split", files=files, data=data)
                if not payload.get("success"):
                    raise HTTPException(
                        status_code=500, detail=payload.get("error") or "Split failed"
                    )
                result = {
                    "chunks": payload.get("chunks", []),
                    "unknown_chunks": payload.get("unknown_chunks", []),
                }
            else:
                raise HTTPException(status_code=400, detail=f"Unknown step type: {step_type}")

            results.append({"step": step_type, "tier": step_tier, "result": result})
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code if e.status_code >= 500 else 500,
            content={"success": False, "error": e.detail, "completed_steps": results},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "completed_steps": results},
        )

    return JSONResponse({"success": True, "results": results, "filename": file.filename})


# ---------------------------------------------------------------------------
# Reverse proxy
# ---------------------------------------------------------------------------

_HOP_BY_HOP = frozenset(
    {
        "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
        "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
    }
)


def _filter_headers(items: Iterable[Tuple[bytes, bytes]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in items:
        key = k.decode("latin-1") if isinstance(k, (bytes, bytearray)) else str(k)
        if key.lower() in _HOP_BY_HOP:
            continue
        out[key] = v.decode("latin-1") if isinstance(v, (bytes, bytearray)) else str(v)
    return out


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    include_in_schema=False,
)
async def proxy(path: str, request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(status_code=200)
    full_path = "/" + path
    resolved = _resolve_service(full_path)
    if resolved is None:
        return JSONResponse({"error": f"No service handles {full_path}"}, status_code=404)
    service_name, base_url = resolved

    body = await request.body()
    target_url = f"{base_url}{full_path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    client: httpx.AsyncClient = app.state.client
    try:
        upstream = await client.request(
            request.method,
            target_url,
            content=body,
            headers=_filter_headers(request.headers.raw),
        )
    except httpx.ConnectError:
        return JSONResponse(
            {"error": f"{service_name} is unreachable at {base_url}", "service": service_name},
            status_code=503,
        )
    except httpx.RequestError as e:
        return JSONResponse(
            {"error": f"{service_name} request failed: {e}", "service": service_name},
            status_code=502,
        )
    headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP}
    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers)
