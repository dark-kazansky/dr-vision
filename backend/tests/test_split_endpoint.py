"""Unit tests for the /split endpoint.

Tests:
1. Default mode (omitted split_mode) defaults to 'sections' → returns chunks
2. Invalid split_mode returns HTTP 400
3. document_type mode returns document_types field
4. sections mode returns chunks with document_types=null
5. No file provided returns 422
6. No categories returns 422
7. Invalid categories JSON returns 400
8. Split failure returns 500
9. allow_uncategorized=false filters unknown chunks
10. Provider parameter is passed to service
"""

import json
import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI

from core.schemas import ChunkModel, DocumentTypeResult, SplitResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CATEGORIES = json.dumps([
    {"name": "Header", "description": "Document header", "order": 0},
    {"name": "Body", "description": "Document body", "order": 1},
])

INVALID_CATEGORIES = "not valid json"


def _make_upload_bytes():
    """Return minimal PDF-like bytes for the upload."""
    return b"%PDF-1.4 fake content"


def _sections_split_response():
    """SplitResponse for sections mode."""
    return SplitResponse(
        success=True,
        chunks=[
            ChunkModel(content="Title text", category="Header", page_number=1, confidence=0.95),
            ChunkModel(content="Body text", category="Body", page_number=1, confidence=0.90),
        ],
        unknown_chunks=[
            ChunkModel(content="Unknown text", category="unknown", page_number=2, confidence=0.3),
        ],
        document_types=None,
        filename="test.pdf",
    )


def _doc_type_split_response():
    """SplitResponse for document_type mode."""
    return SplitResponse(
        success=True,
        chunks=[],
        unknown_chunks=[],
        document_types=[
            DocumentTypeResult(type_name="Header", page_numbers=[1, 2], confidence=0.92),
            DocumentTypeResult(type_name="Body", page_numbers=[3, 4, 5], confidence=0.88),
        ],
        filename="test.pdf",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_config_singleton():
    """Reset Config singleton before/after each test."""
    from config.manager import Config
    Config._instance = None
    yield
    Config._instance = None


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.upload_config = {
        "max_size_mb": 10,
        "folder": "/tmp/test_uploads",
        "allowed_extensions": [".pdf", ".png"],
    }
    cfg.models = {"test-model": {"model_id": "test-model", "provider": "test"}}
    return cfg


@pytest.fixture
def app(mock_config):
    """Create a FastAPI app with the split router and overridden dependencies."""
    from api.v1.split import router
    from core.dependencies import get_config

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_config] = lambda: mock_config
    yield test_app
    test_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# Tests — Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_default_mode_defaults_to_sections(client):
    """Omitting split_mode should default to 'sections' and return chunks."""
    with patch(
        "services.split_service.split_document",
        new_callable=AsyncMock,
        return_value=_sections_split_response(),
    ):
        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": SAMPLE_CATEGORIES,
                    "allow_uncategorized": "true",
                    "splitter_tier": "Normal",
                    # split_mode intentionally omitted — defaults to "sections"
                },
                files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["chunks"]) == 2
    assert len(body["unknown_chunks"]) == 1
    assert body["document_types"] is None


@pytest.mark.asyncio
async def test_sections_mode_returns_chunks(client):
    """Explicit split_mode='sections' returns chunks and document_types=null."""
    with patch(
        "services.split_service.split_document",
        new_callable=AsyncMock,
        return_value=_sections_split_response(),
    ):
        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": SAMPLE_CATEGORIES,
                    "allow_uncategorized": "true",
                    "split_mode": "sections",
                    "splitter_tier": "Normal",
                },
                files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["chunks"]) == 2
    assert body["chunks"][0]["category"] == "Header"
    assert body["chunks"][0]["content"] == "Title text"
    assert body["chunks"][1]["category"] == "Body"
    assert len(body["unknown_chunks"]) == 1
    assert body["unknown_chunks"][0]["category"] == "unknown"
    assert body["document_types"] is None
    assert body["filename"] == "test.pdf"


@pytest.mark.asyncio
async def test_document_type_mode_returns_document_types(client):
    """split_mode='document_type' returns document_types field."""
    with patch(
        "services.split_service.split_document",
        new_callable=AsyncMock,
        return_value=_doc_type_split_response(),
    ):
        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": SAMPLE_CATEGORIES,
                    "split_mode": "document_type",
                    "splitter_tier": "Normal",
                },
                files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["document_types"] is not None
    assert len(body["document_types"]) == 2
    assert body["document_types"][0]["type_name"] == "Header"
    assert body["document_types"][0]["page_numbers"] == [1, 2]
    assert body["document_types"][1]["type_name"] == "Body"
    assert body["document_types"][1]["page_numbers"] == [3, 4, 5]
    assert body["chunks"] == []
    assert body["unknown_chunks"] == []


@pytest.mark.asyncio
async def test_split_with_provider(client):
    """Provider parameter is passed through to service."""
    with patch(
        "services.split_service.split_document",
        new_callable=AsyncMock,
        return_value=_sections_split_response(),
    ) as mock_split:
        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": SAMPLE_CATEGORIES,
                    "split_mode": "sections",
                    "splitter_tier": "Normal",
                    "provider": "google",
                },
                files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    call_kwargs = mock_split.call_args[1]
    assert call_kwargs["provider"] == "google"


# ---------------------------------------------------------------------------
# Tests — Error cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_split_mode_returns_400(client):
    """Providing an invalid split_mode returns HTTP 400."""
    from fastapi import HTTPException

    with patch(
        "services.split_service.split_document",
        new_callable=AsyncMock,
        side_effect=HTTPException(
            status_code=400,
            detail="Invalid split_mode: 'invalid_mode'. Allowed values: 'sections', 'document_type'",
        ),
    ):
        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": SAMPLE_CATEGORIES,
                    "split_mode": "invalid_mode",
                },
                files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
            )

    assert resp.status_code == 400
    body = resp.json()
    assert "Invalid split_mode" in body["detail"]


@pytest.mark.asyncio
async def test_split_no_file_returns_422(client):
    """POST /split without file returns 422."""
    async with client:
        resp = await client.post(
            "/split",
            data={
                "categories": SAMPLE_CATEGORIES,
                "split_mode": "sections",
            },
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_split_no_categories_returns_422(client):
    """POST /split without categories returns 422."""
    async with client:
        resp = await client.post(
            "/split",
            data={"split_mode": "sections"},
            files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_split_invalid_categories_returns_400(client):
    """POST /split with invalid categories JSON returns 400."""
    from fastapi import HTTPException

    with patch(
        "services.split_service.split_document",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=400, detail="Invalid categories: Expecting value"),
    ):
        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": INVALID_CATEGORIES,
                    "split_mode": "sections",
                },
                files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
            )

    assert resp.status_code == 400
    assert "Invalid categories" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_split_service_failure_returns_500(client):
    """Split service internal error returns 500."""
    from fastapi import HTTPException

    with patch(
        "services.split_service.split_document",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=500, detail="Split failed: VLM agent timeout"),
    ):
        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": SAMPLE_CATEGORIES,
                    "split_mode": "sections",
                    "splitter_tier": "Normal",
                },
                files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
            )

    assert resp.status_code == 500
    assert "Split failed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_split_allow_uncategorized_false(client):
    """allow_uncategorized=false returns no unknown_chunks."""
    response = SplitResponse(
        success=True,
        chunks=[
            ChunkModel(content="Title text", category="Header", page_number=1, confidence=0.95),
        ],
        unknown_chunks=[],
        document_types=None,
        filename="test.pdf",
    )

    with patch(
        "services.split_service.split_document",
        new_callable=AsyncMock,
        return_value=response,
    ):
        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": SAMPLE_CATEGORIES,
                    "allow_uncategorized": "false",
                    "split_mode": "sections",
                    "splitter_tier": "Normal",
                },
                files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["chunks"]) == 1
    assert body["unknown_chunks"] == []
