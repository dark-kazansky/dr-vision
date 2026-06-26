"""
Tests for feat-070: Full-text Document Search.

Covers:
- API endpoint GET /api/v1/search (success, empty, no-match, date filter, 503)
- Repository OcrResultRepository.search_text (SQL/param construction, empty
  query short-circuit, date filters, no pool)
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI

from api.v1.search import router
from storage.ocr_result_repository import OcrResultRepository


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_repo():
    """A mock OcrResultRepository injected via app.state."""
    return AsyncMock()


@pytest.fixture
def app(mock_repo):
    """Minimal FastAPI app with only the search router + injected repo."""
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.state.ocr_result_repo = mock_repo
    return test_app


@pytest.fixture
def client(app):
    """httpx AsyncClient bound to the test app."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# =============================================================================
# API tests
# =============================================================================


@pytest.mark.asyncio
async def test_search_returns_results(client, mock_repo):
    """GET /api/v1/search?q=invoice → 200 with items, total, snippet."""
    mock_repo.search_text.return_value = {
        "items": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "filename": "invoice-001.pdf",
                "model_id": "gemini-1.5-pro",
                "provider": "gemini",
                "tier": "Normal",
                "created_at": "2026-06-01T00:00:00+00:00",
                "rank": 0.45,
                "snippet": "\x01invoice\x02 total: 1,000,000 VND",
            }
        ],
        "total": 1,
        "limit": 20,
        "offset": 0,
        "query": "invoice",
    }

    resp = await client.get("/api/v1/search", params={"q": "invoice"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["filename"] == "invoice-001.pdf"
    assert "\x01" in body["items"][0]["snippet"]
    mock_repo.search_text.assert_awaited_once()
    call_kwargs = mock_repo.search_text.call_args.kwargs
    assert call_kwargs["query"] == "invoice"
    assert call_kwargs["limit"] == 20
    assert call_kwargs["offset"] == 0


@pytest.mark.asyncio
async def test_search_no_matches_returns_empty(client, mock_repo):
    """Search with a term that matches nothing → 200 with empty items."""
    mock_repo.search_text.return_value = {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
        "query": "nonexistentterm",
    }

    resp = await client.get(
        "/api/v1/search", params={"q": "nonexistentterm"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    # No error — empty results, not an error state.
    assert body["success"] is True


@pytest.mark.asyncio
async def test_search_empty_query_returns_empty(client, mock_repo):
    """Empty q → 200 with empty items (not an error)."""
    mock_repo.search_text.return_value = {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
        "query": "",
    }

    resp = await client.get("/api/v1/search", params={"q": ""})

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_search_missing_q_defaults_to_empty(client, mock_repo):
    """No q param → defaults to empty string → empty results."""
    mock_repo.search_text.return_value = {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
        "query": "",
    }

    resp = await client.get("/api/v1/search")

    assert resp.status_code == 200
    mock_repo.search_text.assert_awaited_once()
    assert mock_repo.search_text.call_args.kwargs["query"] == ""


@pytest.mark.asyncio
async def test_search_with_date_range_filter(client, mock_repo):
    """date_from and date_to are forwarded to the repository."""
    mock_repo.search_text.return_value = {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
        "query": "hóa đơn",
    }

    resp = await client.get(
        "/api/v1/search",
        params={
            "q": "hóa đơn",
            "date_from": "2026-01-01T00:00:00Z",
            "date_to": "2026-06-30T23:59:59Z",
        },
    )

    assert resp.status_code == 200
    call_kwargs = mock_repo.search_text.call_args.kwargs
    assert call_kwargs["date_from"] == "2026-01-01T00:00:00Z"
    assert call_kwargs["date_to"] == "2026-06-30T23:59:59Z"


@pytest.mark.asyncio
async def test_search_pagination_params_forwarded(client, mock_repo):
    """limit and offset are forwarded and clamped by FastAPI validation."""
    mock_repo.search_text.return_value = {
        "items": [],
        "total": 0,
        "limit": 50,
        "offset": 100,
        "query": "test",
    }

    resp = await client.get(
        "/api/v1/search", params={"q": "test", "limit": 50, "offset": 100}
    )

    assert resp.status_code == 200
    call_kwargs = mock_repo.search_text.call_args.kwargs
    assert call_kwargs["limit"] == 50
    assert call_kwargs["offset"] == 100


@pytest.mark.asyncio
async def test_search_limit_above_max_rejected(client):
    """limit > 200 → 422 validation error."""
    resp = await client.get(
        "/api/v1/search", params={"q": "test", "limit": 201}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_limit_below_min_rejected(client):
    """limit < 1 → 422 validation error."""
    resp = await client.get(
        "/api/v1/search", params={"q": "test", "limit": 0}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_offset_negative_rejected(client):
    """offset < 0 → 422 validation error."""
    resp = await client.get(
        "/api/v1/search", params={"q": "test", "offset": -1}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_repo_unavailable_returns_503(app, mock_repo):
    """When app.state.ocr_result_repo is None → 503."""
    app.state.ocr_result_repo = None
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as c:
        resp = await c.get("/api/v1/search", params={"q": "test"})
    assert resp.status_code == 503


# =============================================================================
# Repository unit tests — OcrResultRepository.search_text
# =============================================================================


def _make_repo_with_mock_pool():
    """Build a repo with a mocked asyncpg pool that captures SQL + params.

    Returns (repo, fetch_calls, fetchval_calls) where fetch/fetchval record
    the SQL string and params they were called with.
    """
    from datetime import datetime, timezone

    class FakeRecord:
        """asyncpg.Record-like object returning values by key."""

        def __init__(self, data: dict):
            self._data = data

        def __getitem__(self, key):
            return self._data[key]

    fake_created_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    fake_row = FakeRecord(
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "filename": "doc1.pdf",
            "model_id": "m1",
            "provider": "gemini",
            "tier": "Normal",
            "created_at": fake_created_at,
            "rank": 0.5,
            "snippet": "\x01hit\x02 text",
        }
    )

    repo = OcrResultRepository("postgres://test")
    fetch_calls = []
    fetchval_calls = []

    async def fake_fetch(sql, *params):
        fetch_calls.append((sql, params))
        return [fake_row]

    async def fake_fetchval(sql, *params):
        fetchval_calls.append((sql, params))
        return 1

    conn = MagicMock()
    conn.fetch = fake_fetch
    conn.fetchval = fake_fetchval

    class _Ctx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, exc_type, exc, tb):
            return None

    pool = MagicMock()
    pool.acquire.return_value = _Ctx()
    repo._pool = pool
    return repo, fetch_calls, fetchval_calls


@pytest.mark.asyncio
async def test_repo_search_text_empty_query_short_circuits():
    """Empty query returns empty result without hitting the DB."""
    repo = OcrResultRepository("postgres://test")
    repo._pool = MagicMock()  # pool exists but must NOT be acquired

    result = await repo.search_text("   ", limit=10, offset=0)

    assert result["items"] == []
    assert result["total"] == 0
    assert result["query"] == "   "
    repo._pool.acquire.assert_not_called()


@pytest.mark.asyncio
async def test_repo_search_text_no_pool_raises():
    """search_text without a connected pool raises RuntimeError."""
    repo = OcrResultRepository("postgres://test")
    repo._pool = None

    with pytest.raises(RuntimeError, match="Not connected"):
        await repo.search_text("query", limit=10, offset=0)


@pytest.mark.asyncio
async def test_repo_search_text_query_only_builds_correct_params():
    """A query with no date filters passes (query, limit, offset) to fetch."""
    repo, fetch_calls, fetchval_calls = _make_repo_with_mock_pool()

    await repo.search_text("hóa đơn", limit=15, offset=5)

    assert len(fetch_calls) == 1
    sql, params = fetch_calls[0]
    # $1 = query, $2 = limit, $3 = offset (no date filters).
    assert "websearch_to_tsquery('simple', $1)" in sql
    assert "LIMIT $2 OFFSET $3" in sql
    assert params == ("hóa đơn", 15, 5)

    assert len(fetchval_calls) == 1
    count_sql, count_params = fetchval_calls[0]
    assert "COUNT(*)" in count_sql
    assert count_params == ("hóa đơn",)


@pytest.mark.asyncio
async def test_repo_search_text_with_date_from_only():
    """date_from only → $2 = date_from, $3 = limit, $4 = offset."""
    repo, fetch_calls, _ = _make_repo_with_mock_pool()

    await repo.search_text(
        "invoice", limit=10, offset=0, date_from="2026-01-01T00:00:00Z"
    )

    sql, params = fetch_calls[0]
    assert "created_at >= $2" in sql
    assert "LIMIT $3 OFFSET $4" in sql
    assert params == ("invoice", "2026-01-01T00:00:00Z", 10, 0)


@pytest.mark.asyncio
async def test_repo_search_text_with_both_date_filters():
    """date_from + date_to → $2 = from, $3 = to, $4 = limit, $5 = offset."""
    repo, fetch_calls, _ = _make_repo_with_mock_pool()

    await repo.search_text(
        "invoice",
        limit=10,
        offset=0,
        date_from="2026-01-01T00:00:00Z",
        date_to="2026-06-30T23:59:59Z",
    )

    sql, params = fetch_calls[0]
    assert "created_at >= $2" in sql
    assert "created_at <= $3" in sql
    assert "LIMIT $4 OFFSET $5" in sql
    assert params == (
        "invoice",
        "2026-01-01T00:00:00Z",
        "2026-06-30T23:59:59Z",
        10,
        0,
    )


@pytest.mark.asyncio
async def test_repo_search_text_returns_serialized_items():
    """Returned items have id as string, created_at as ISO, rank as float."""
    repo, _, _ = _make_repo_with_mock_pool()

    result = await repo.search_text("hit", limit=10, offset=0)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert isinstance(item["id"], str)
    assert item["id"] == "11111111-1111-1111-1111-111111111111"
    assert item["filename"] == "doc1.pdf"
    assert item["created_at"] == "2026-06-01T00:00:00+00:00"
    assert isinstance(item["rank"], float)
    assert "\x01" in item["snippet"]
