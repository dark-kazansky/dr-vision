"""
End-to-end smoke tests that boot the orchestrator FastAPI app via
httpx.ASGITransport — no docker / network required.

Verifies:
- /health
- /workflows CRUD round-trip
- /workflow-runs returns an empty list
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx
import pytest

# Make `main` and shared importable.
HERE = os.path.dirname(os.path.abspath(__file__))
ORCHESTRATOR = os.path.join(os.path.dirname(HERE), "services", "orchestrator")
SHARED_SRC = os.path.join(os.path.dirname(HERE), "shared", "src")
for path in (ORCHESTRATOR, SHARED_SRC):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("MSBE_DATA_DIR", str(tmp_path))
    # Drop any previously-imported `main` (gateway tests may have loaded the
    # gateway's main.py first) before importing the orchestrator's main.py.
    for mod_name in ("main", "runner", "graph"):
        sys.modules.pop(mod_name, None)
    # Make sure orchestrator dir wins on the path.
    if ORCHESTRATOR in sys.path:
        sys.path.remove(ORCHESTRATOR)
    sys.path.insert(0, ORCHESTRATOR)
    import main  # type: ignore
    return main.app


@pytest.mark.asyncio
async def test_orchestrator_endpoints(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")
        assert r.status_code == 200
        assert r.json()["service"] == "orchestrator"

        r = await c.get("/workflows")
        assert r.status_code == 200
        assert r.json() == {"workflows": []}

        r = await c.post("/workflows", json={"name": "demo", "nodes": []})
        assert r.status_code == 201
        wf_id = r.json()["id"]

        r = await c.get(f"/workflows/{wf_id}")
        assert r.status_code == 200
        assert r.json()["name"] == "demo"

        r = await c.delete(f"/workflows/{wf_id}")
        assert r.status_code == 200

        r = await c.get("/workflow-runs")
        assert r.status_code == 200
        assert r.json()["total"] == 0
