"""Unit tests for the /split endpoint dual mode support (Task 3.7).

Tests:
1. Default mode (omitted split_mode param) defaults to sections behavior
2. Invalid split_mode returns HTTP 400
3. document_type mode returns document_types field
4. sections mode returns chunks/unknown_chunks with document_types as null
"""

import json
import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from functions.splitter import SplitResult, Chunk, DocumentTypeItem, ChunkCategory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CATEGORIES = json.dumps([
    {"name": "Header", "description": "Document header", "order": 0},
    {"name": "Body", "description": "Document body", "order": 1},
])

SAMPLE_CHUNKS = [
    Chunk(content="Title text", category="Header", page_number=1, confidence=0.95),
    Chunk(content="Body text", category="Body", page_number=1, confidence=0.90),
]

SAMPLE_UNKNOWN_CHUNKS = [
    Chunk(content="Unknown text", category="unknown", page_number=2, confidence=0.3),
]

SAMPLE_DOC_TYPES = [
    DocumentTypeItem(type_name="Header", page_numbers=[1, 2], confidence=0.92),
    DocumentTypeItem(type_name="Body", page_numbers=[3, 4, 5], confidence=0.88),
]


def _sections_split_result():
    return SplitResult(
        success=True,
        chunks=SAMPLE_CHUNKS,
        unknown_chunks=SAMPLE_UNKNOWN_CHUNKS,
    )


def _doc_type_split_result():
    return SplitResult(
        success=True,
        document_types=SAMPLE_DOC_TYPES,
    )


def _make_upload_bytes():
    """Return minimal PDF-like bytes for the upload."""
    return b"%PDF-1.4 fake content"


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
    cfg.upload_config = {"max_size_mb": 10, "folder": "/tmp/test_uploads", "allowed_extensions": [".pdf", ".png"]}
    cfg.models = {"test-model": {"model_id": "test-model", "provider": "test"}}
    return cfg


@pytest.fixture
def app(mock_config):
    """Create a FastAPI app with the router and overridden dependencies."""
    from routes import router
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
# Shared patch context
# ---------------------------------------------------------------------------

def _common_patches(split_return_value):
    """Return a dict of patches needed for every /split request."""
    return {
        "file_size": patch("routes.file_size_validator.validate", new_callable=AsyncMock),
        "secure_save": patch("routes.secure_save_file", new_callable=AsyncMock, return_value="/tmp/fake.pdf"),
        "tier_config": patch("config.tier_config.TierConfig.get_splitter_model", return_value="test-model"),
        "vlm_agent": patch("routes.AgentFactory.create_vlm_agent", return_value=MagicMock()),
        "splitter_split": patch.object(
            __import__("functions.splitter", fromlist=["Splitter"]).Splitter,
            "split",
            return_value=split_return_value,
        ),
        "splitter_split_by_doc_type": patch.object(
            __import__("functions.splitter", fromlist=["Splitter"]).Splitter,
            "split_by_document_type",
            return_value=split_return_value,
        ),
        "safe_remove": patch("routes._safe_remove"),
        "os_makedirs": patch("os.makedirs"),
        "open_file": patch("builtins.open", MagicMock()),
        "os_path_getctime": patch("os.path.getctime", return_value=1234567890.0),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_default_mode_defaults_to_sections(client):
    """Omitting split_mode should default to 'sections' and return chunks."""
    patches = _common_patches(_sections_split_result())
    managers = {k: v for k, v in patches.items()}

    with managers["file_size"], managers["secure_save"], managers["tier_config"], \
         managers["vlm_agent"], managers["splitter_split"], \
         managers["splitter_split_by_doc_type"], managers["safe_remove"], \
         managers["os_makedirs"], managers["open_file"], managers["os_path_getctime"]:

        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": SAMPLE_CATEGORIES,
                    "allow_uncategorized": "true",
                    "splitter_tier": "Normal",
                    # split_mode intentionally omitted
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
async def test_invalid_split_mode_returns_400(client):
    """Providing an invalid split_mode should return HTTP 400."""
    # No need to mock splitter — validation happens before any splitting
    with patch("routes.file_size_validator.validate", new_callable=AsyncMock):
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
    assert "invalid_mode" in body["detail"]
    assert "'sections'" in body["detail"]
    assert "'document_type'" in body["detail"]


@pytest.mark.asyncio
async def test_document_type_mode_returns_document_types(client):
    """split_mode='document_type' should return document_types field."""
    patches = _common_patches(_doc_type_split_result())
    managers = {k: v for k, v in patches.items()}

    with managers["file_size"], managers["secure_save"], managers["tier_config"], \
         managers["vlm_agent"], managers["splitter_split"], \
         managers["splitter_split_by_doc_type"], managers["safe_remove"], \
         managers["os_makedirs"], managers["open_file"], managers["os_path_getctime"]:

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
    assert body["chunks"] == []
    assert body["unknown_chunks"] == []


@pytest.mark.asyncio
async def test_sections_mode_returns_chunks_with_null_document_types(client):
    """Explicit split_mode='sections' should return chunks and document_types=null."""
    patches = _common_patches(_sections_split_result())
    managers = {k: v for k, v in patches.items()}

    with managers["file_size"], managers["secure_save"], managers["tier_config"], \
         managers["vlm_agent"], managers["splitter_split"], \
         managers["splitter_split_by_doc_type"], managers["safe_remove"], \
         managers["os_makedirs"], managers["open_file"], managers["os_path_getctime"]:

        async with client:
            resp = await client.post(
                "/split",
                data={
                    "categories": SAMPLE_CATEGORIES,
                    "split_mode": "sections",
                    "allow_uncategorized": "true",
                    "splitter_tier": "Normal",
                },
                files={"file": ("test.pdf", _make_upload_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["chunks"]) == 2
    assert body["chunks"][0]["category"] == "Header"
    assert body["chunks"][1]["category"] == "Body"
    assert len(body["unknown_chunks"]) == 1
    assert body["document_types"] is None
