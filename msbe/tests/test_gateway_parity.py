"""
Parity tests between the monolith and the MSBE gateway.

These tests assert the gateway returns the same JSON shapes the monolith
returns for the endpoints that don't require live LLM calls. Downstream
service traffic is intercepted via httpx ``MockTransport`` so tests run
without docker.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from typing import Any, Dict

import httpx
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GATEWAY_DIR = os.path.join(os.path.dirname(HERE), "gateway")
SHARED_SRC = os.path.join(os.path.dirname(HERE), "shared", "src")
for path in (SHARED_SRC,):
    if path not in sys.path:
        sys.path.insert(0, path)


def _load_gateway_app(monkeypatch):
    """Load gateway/main.py under a unique module name for each test."""
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
    # Disable rate limiter for tests so multiple calls don't 429.
    monkeypatch.setenv("RATE_LIMIT_RPM", "10000")
    monkeypatch.setenv("RATE_LIMIT_BURST", "10000")

    spec = importlib.util.spec_from_file_location(
        "msbe_gateway_main_app", os.path.join(GATEWAY_DIR, "main.py")
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Local routes that don't need downstream services
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_matches_monolith_shape(monkeypatch):
    gw = _load_gateway_app(monkeypatch)
    transport = httpx.ASGITransport(app=gw.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # Trigger lifespan to set up app.state.client.
        async with httpx.AsyncClient(transport=transport, base_url="http://test"):
            pass
        r = await c.get("/health")
    assert r.status_code == 200
    body = r.json()
    # Monolith HealthResponse contract.
    assert set(body.keys()) >= {"status", "server_running", "available_models"}
    assert isinstance(body["server_running"], bool)
    assert isinstance(body["available_models"], list)


@pytest.mark.asyncio
async def test_tier_config_returns_full_dict(monkeypatch):
    gw = _load_gateway_app(monkeypatch)
    transport = httpx.ASGITransport(app=gw.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/tier-config")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    cfg = body["config"]
    for key in ("parser", "extractor", "classifier_llm", "splitter", "tiers"):
        assert key in cfg


@pytest.mark.asyncio
async def test_models_check_lists_models(monkeypatch):
    gw = _load_gateway_app(monkeypatch)
    transport = httpx.ASGITransport(app=gw.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/models/check")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "models" in body and isinstance(body["models"], list)
    assert "by_provider" in body
    if body["models"]:
        m = body["models"][0]
        assert {"model_id", "name", "provider", "available"} <= set(m.keys())


@pytest.mark.asyncio
async def test_test_logging_is_proxied_locally(monkeypatch):
    gw = _load_gateway_app(monkeypatch)
    transport = httpx.ASGITransport(app=gw.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/test-logging")
    assert r.status_code == 200
    assert r.json()["success"] is True


@pytest.mark.asyncio
async def test_condition_evaluate_matches_monolith(monkeypatch):
    gw = _load_gateway_app(monkeypatch)
    transport = httpx.ASGITransport(app=gw.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/condition/evaluate",
            data={
                "conditions": json.dumps([{"operator": "equals", "value": "Invoice"}]),
                "previous_result": json.dumps({"document_type": "Invoice"}),
                "field_name": "document_type",
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body == {"success": True, "matched_index": 0, "is_else": False}


@pytest.mark.asyncio
async def test_condition_evaluate_else_branch(monkeypatch):
    gw = _load_gateway_app(monkeypatch)
    transport = httpx.ASGITransport(app=gw.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/condition/evaluate",
            data={
                "conditions": json.dumps([{"operator": "equals", "value": "Invoice"}]),
                "previous_result": json.dumps({"document_type": "Other"}),
            },
        )
    assert r.status_code == 200
    assert r.json() == {"success": True, "matched_index": None, "is_else": True}


@pytest.mark.asyncio
async def test_request_id_header_set(monkeypatch):
    gw = _load_gateway_app(monkeypatch)
    transport = httpx.ASGITransport(app=gw.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/tier-config")
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) >= 16
