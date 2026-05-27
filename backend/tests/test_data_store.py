"""Unit tests for the Data Store API (feat-013).

Tests:
1. Create entry — valid tags (Parse, Classify, Extract, Split, WF)
2. Create entry — invalid tag returns 400
3. Create entry — database unavailable returns 503
4. List entries — returns all entries sorted by created_at DESC
5. List entries — filter by tag
6. List entries — pagination (limit/offset)
7. List entries — empty when no DB
8. Get entry by ID — success
9. Get entry by ID — not found returns 404
10. Delete entry — success
11. Delete entry — not found returns 404
12. Result data stored as JSON and deserialized correctly
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

from api.v1.data_store import router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


class FakeConnection:
    """In-memory fake of asyncpg connection for data_store table."""

    def __init__(self, store: list):
        self._store = store

    async def fetch(self, query, *args):
        tag_filter = None
        limit = 200
        offset = 0

        if "WHERE action_tag" in query:
            tag_filter = args[0]
            limit = args[1] if len(args) > 1 else 200
            offset = args[2] if len(args) > 2 else 0
        else:
            limit = args[0] if len(args) > 0 else 200
            offset = args[1] if len(args) > 1 else 0

        filtered = self._store
        if tag_filter:
            filtered = [r for r in filtered if r["action_tag"] == tag_filter]

        # Sort by created_at DESC
        filtered = sorted(filtered, key=lambda r: r["created_at"], reverse=True)
        return filtered[offset : offset + limit]

    async def fetchval(self, query, *args):
        if "WHERE action_tag" in query:
            tag = args[0]
            return len([r for r in self._store if r["action_tag"] == tag])
        return len(self._store)

    async def fetchrow(self, query, *args):
        entry_id = args[0]
        for row in self._store:
            if row["id"] == entry_id:
                return row
        return None

    async def execute(self, query, *args):
        if "INSERT" in query:
            entry_id, filename, action_tag, result_data, model_used, created_at = args
            self._store.append({
                "id": entry_id,
                "filename": filename,
                "action_tag": action_tag,
                "result_data": result_data,
                "model_used": model_used,
                "created_at": created_at,
            })
            return "INSERT 0 1"
        elif "DELETE" in query:
            entry_id = args[0]
            before = len(self._store)
            self._store[:] = [r for r in self._store if r["id"] != entry_id]
            after = len(self._store)
            return f"DELETE {before - after}"
        return "OK"


class FakePool:
    """Fake asyncpg pool that yields FakeConnection."""

    def __init__(self, store: list):
        self._conn = FakeConnection(store)

    def acquire(self):
        return FakePoolContext(self._conn)


class FakePoolContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def make_repo(store: list):
    """Create a mock workflow_repo with a FakePool."""
    repo = MagicMock()
    repo._pool = FakePool(store)
    return repo


def seed_entries(count=3):
    """Create seed data for tests."""
    tags = ["Parse", "Classify", "Extract", "Split", "WF"]
    store = []
    for i in range(count):
        store.append({
            "id": uuid.uuid4(),
            "filename": f"file_{i}.pdf",
            "action_tag": tags[i % len(tags)],
            "result_data": json.dumps({"success": True, "text": f"Result {i}"}),
            "model_used": "gemini-pro" if i % 2 == 0 else None,
            "created_at": datetime(2026, 5, 20, 10, i, 0, tzinfo=timezone.utc),
        })
    return store


# ---------------------------------------------------------------------------
# Tests: Create Entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_entry_parse(client):
    """POST /data-store with valid Parse tag creates entry."""
    store = []
    repo = make_repo(store)

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.post("/api/v1/data-store", json={
                "filename": "invoice.pdf",
                "action_tag": "Parse",
                "result_data": {"success": True, "text": "Hello world"},
                "model_used": "gemini-pro",
            })

    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "invoice.pdf"
    assert body["action_tag"] == "Parse"
    assert body["result_data"] == {"success": True, "text": "Hello world"}
    assert body["model_used"] == "gemini-pro"
    assert "id" in body
    assert "created_at" in body
    assert len(store) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("tag", ["Parse", "Classify", "Extract", "Split", "WF"])
async def test_create_entry_all_valid_tags(client, tag):
    """POST /data-store accepts all valid action tags."""
    store = []
    repo = make_repo(store)

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.post("/api/v1/data-store", json={
                "filename": "test.pdf",
                "action_tag": tag,
                "result_data": {"success": True},
            })

    assert resp.status_code == 200
    assert resp.json()["action_tag"] == tag


@pytest.mark.asyncio
async def test_create_entry_invalid_tag(client):
    """POST /data-store with invalid tag returns 400."""
    store = []
    repo = make_repo(store)

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.post("/api/v1/data-store", json={
                "filename": "test.pdf",
                "action_tag": "InvalidTag",
                "result_data": {"success": True},
            })

    assert resp.status_code == 400
    assert "Invalid action_tag" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_entry_db_unavailable(client):
    """POST /data-store returns 503 when DB is not available."""
    repo = MagicMock()
    repo._pool = None

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.post("/api/v1/data-store", json={
                "filename": "test.pdf",
                "action_tag": "Parse",
                "result_data": {"success": True},
            })

    assert resp.status_code == 503
    assert "Database not available" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: List Entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_entries_all(client):
    """GET /data-store returns all entries."""
    store = seed_entries(5)
    repo = make_repo(store)

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.get("/api/v1/data-store")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["entries"]) == 5


@pytest.mark.asyncio
async def test_list_entries_filter_by_tag(client):
    """GET /data-store?tag=Parse returns only Parse entries."""
    store = seed_entries(5)
    repo = make_repo(store)

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.get("/api/v1/data-store", params={"tag": "Parse"})

    assert resp.status_code == 200
    body = resp.json()
    for entry in body["entries"]:
        assert entry["action_tag"] == "Parse"


@pytest.mark.asyncio
async def test_list_entries_pagination(client):
    """GET /data-store with limit/offset paginates correctly."""
    store = seed_entries(5)
    repo = make_repo(store)

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.get("/api/v1/data-store", params={"limit": 2, "offset": 0})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["entries"]) == 2
    assert body["total"] == 5


@pytest.mark.asyncio
async def test_list_entries_empty_no_db(client):
    """GET /data-store returns empty when DB pool is None."""
    repo = MagicMock()
    repo._pool = None

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.get("/api/v1/data-store")

    assert resp.status_code == 200
    body = resp.json()
    assert body["entries"] == []
    assert body["total"] == 0


# ---------------------------------------------------------------------------
# Tests: Get Entry by ID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_entry_success(client):
    """GET /data-store/{id} returns the entry."""
    store = seed_entries(3)
    repo = make_repo(store)
    target_id = str(store[0]["id"])

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.get(f"/api/v1/data-store/{target_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == target_id
    assert body["filename"] == store[0]["filename"]


@pytest.mark.asyncio
async def test_get_entry_not_found(client):
    """GET /data-store/{id} returns 404 for non-existent entry."""
    store = seed_entries(2)
    repo = make_repo(store)
    fake_id = str(uuid.uuid4())

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.get(f"/api/v1/data-store/{fake_id}")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: Delete Entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_entry_success(client):
    """DELETE /data-store/{id} removes the entry."""
    store = seed_entries(3)
    repo = make_repo(store)
    target_id = str(store[1]["id"])

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.delete(f"/api/v1/data-store/{target_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] is True
    assert body["id"] == target_id
    assert len(store) == 2


@pytest.mark.asyncio
async def test_delete_entry_not_found(client):
    """DELETE /data-store/{id} returns 404 for non-existent entry."""
    store = seed_entries(2)
    repo = make_repo(store)
    fake_id = str(uuid.uuid4())

    with patch("server.workflow_repo", repo):
        async with client:
            resp = await client.delete(f"/api/v1/data-store/{fake_id}")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: JSON serialization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_data_json_roundtrip(client):
    """Result data is stored as JSON and deserialized correctly on retrieval."""
    store = []
    repo = make_repo(store)
    complex_data = {
        "success": True,
        "results": [
            {"category": "Invoice", "confidence": 0.95, "pages": [1, 2]},
            {"category": "Receipt", "confidence": 0.87, "pages": [3]},
        ],
        "metadata": {"total_pages": 3, "processing_time_ms": 1234},
    }

    with patch("server.workflow_repo", repo):
        async with client:
            # Create
            resp = await client.post("/api/v1/data-store", json={
                "filename": "multi-doc.pdf",
                "action_tag": "Classify",
                "result_data": complex_data,
                "model_used": "bedrock-claude",
            })
            assert resp.status_code == 200
            entry_id = resp.json()["id"]

            # Retrieve
            resp2 = await client.get(f"/api/v1/data-store/{entry_id}")
            assert resp2.status_code == 200
            assert resp2.json()["result_data"] == complex_data
