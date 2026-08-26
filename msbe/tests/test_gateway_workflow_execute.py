"""
Verify the legacy /workflow/execute pipeline at the gateway proxies to
worker services and reshapes their JSON to match the monolith.

Worker traffic is intercepted via httpx ``MockTransport`` so we never
hit the real services.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import httpx
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GATEWAY_DIR = os.path.join(os.path.dirname(HERE), "gateway")
SHARED_SRC = os.path.join(os.path.dirname(HERE), "shared", "src")
if SHARED_SRC not in sys.path:
    sys.path.insert(0, SHARED_SRC)


def _load_app(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_RPM", "10000")
    monkeypatch.setenv("RATE_LIMIT_BURST", "10000")
    spec = importlib.util.spec_from_file_location(
        "msbe_gateway_main_wf", os.path.join(GATEWAY_DIR, "main.py")
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _mock_workers(request: httpx.Request) -> httpx.Response:
    """Stub the worker services with deterministic responses."""
    path = request.url.path
    if path == "/parse":
        return httpx.Response(
            200,
            json={
                "success": True,
                "text": "STUB TEXT",
                "parsed_text": "STUB TEXT",
                "file_type": "pdf",
                "is_scanned": False,
                "pages": 1,
                "filename": "doc.pdf",
                "model": "stub",
            },
        )
    if path == "/classify-text":
        return httpx.Response(
            200,
            json={
                "success": True,
                "results": [
                    {"fileName": "text_input", "documentType": "Invoice", "confidence": 0.9}
                ],
            },
        )
    if path == "/extract-text":
        return httpx.Response(
            200,
            json={
                "success": True,
                "extraction": {
                    "success": True,
                    "structured_data": {"vendor_name": "Acme"},
                    "field_errors": {},
                },
            },
        )
    if path == "/split":
        return httpx.Response(
            200,
            json={
                "success": True,
                "filename": "doc.pdf",
                "chunks": [{"content": "x", "category": "Header", "page_number": 1, "confidence": 0.9}],
                "unknown_chunks": [],
            },
        )
    return httpx.Response(404, json={"error": f"unmocked path {path}"})


@pytest.mark.asyncio
async def test_workflow_execute_chains_classify_extract(monkeypatch):
    gw = _load_app(monkeypatch)

    transport = httpx.ASGITransport(app=gw.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # Replace the gateway's outbound httpx client with a MockTransport
        # so any /parse, /classify-text, /extract-text, /split calls return
        # our deterministic stubs.
        await c.get("/tier-config")  # ensure lifespan ran
        gw.app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_workers))

        files = {"file": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")}
        workflow = {
            "steps": [
                {"type": "parse", "tier": "Normal"},
                {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "Invoice", "description": "x"}]}},
                {
                    "type": "extract",
                    "tier": "Normal",
                    "config": {
                        "schema": {"fields": [{"name": "vendor_name", "type": "string"}]},
                        "target": "document",
                    },
                },
            ]
        }
        r = await c.post(
            "/workflow/execute",
            files=files,
            data={"workflow": json.dumps(workflow)},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["filename"] == "doc.pdf"
    steps = body["results"]
    assert [s["step"] for s in steps] == ["parse", "classify", "extract"]
    assert steps[1]["result"]["document_type"] == "Invoice"
    assert steps[2]["result"]["structured_data"] == {"vendor_name": "Acme"}


@pytest.mark.asyncio
async def test_workflow_execute_rejects_unknown_step(monkeypatch):
    gw = _load_app(monkeypatch)
    transport = httpx.ASGITransport(app=gw.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        await c.get("/tier-config")
        gw.app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_workers))
        r = await c.post(
            "/workflow/execute",
            files={"file": ("doc.pdf", b"x", "application/pdf")},
            data={"workflow": json.dumps({"steps": [{"type": "noop"}]})},
        )
    assert r.status_code == 500
    body = r.json()
    assert body["success"] is False
    assert "Unknown step type" in body["error"]
    assert body["completed_steps"] == []
