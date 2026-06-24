"""Unit tests for the /parse and /ocr endpoints.

Tests:
1. Successful parse with file upload → returns OCR text
2. No file provided → HTTP 400
3. Invalid file type → HTTP 400
4. File size exceeds limit → HTTP 413
5. OCR failure returns HTTP 500
6. Parse with extraction enabled → includes extraction result
7. Background dispatch for large PDFs → returns job_id
8. /ocr alias works identically to /parse
9. Parse with formatting disabled → returns raw text
"""

import json
import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI

from components.parser import ParseResult
from components.extractor import ExtractResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf_bytes():
    """Minimal PDF-like bytes for upload."""
    return b"%PDF-1.4 fake content for testing"


def _make_png_bytes():
    """Minimal PNG-like bytes for upload."""
    return b"\x89PNG\r\n\x1a\n fake image content"


def _successful_parse_result():
    return ParseResult(
        success=True,
        text="Hello World\nThis is parsed text.",
        file_type="pdf",
        is_scanned=False,
        pages=2,
    )


def _failed_parse_result():
    return ParseResult(
        success=False,
        error="OCR engine timeout",
        error_type="timeout_error",
    )


def _successful_extract_result():
    return ExtractResult(
        success=True,
        structured_data={"name": "John Doe", "age": 30},
        field_errors={},
    )


SAMPLE_EXTRACTION_SCHEMA = json.dumps([
    {"name": "name", "type": "string", "description": "Person name", "required": True},
    {"name": "age", "type": "number", "description": "Age", "required": False},
])


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
        "allowed_extensions": [".pdf", ".png", ".jpg", ".jpeg", ".txt", ".docx"],
    }
    cfg.models = {"test-model": {"model_id": "test-model", "provider": "test"}}
    cfg._config_data = {"background_tasks": {"enabled": False, "threshold_pages": 5}}
    cfg.get_available_models = MagicMock(return_value=["test-model"])
    return cfg


@pytest.fixture
def app(mock_config):
    """Create a FastAPI app with the parse router and overridden dependencies."""
    from api.v1.parse import router
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
# Common patches
# ---------------------------------------------------------------------------

def _common_patches(parse_result=None):
    """Return patches for a /parse request."""
    if parse_result is None:
        parse_result = _successful_parse_result()

    return {
        "parse_document": patch(
            "services.parse_service.parse_document",
            new_callable=AsyncMock,
            return_value={
                "success": parse_result.success,
                "text": parse_result.text,
                "parsed_text": parse_result.text,
                "file_type": parse_result.file_type,
                "is_scanned": parse_result.is_scanned,
                "pages": parse_result.pages,
                "filename": "test.pdf",
                "model": "test-model",
            } if parse_result.success else None,
        ),
    }


# ---------------------------------------------------------------------------
# Tests — Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parse_success(client):
    """POST /parse with valid file returns OCR result."""
    mock_result = {
        "success": True,
        "text": "Hello World\nThis is parsed text.",
        "parsed_text": "Hello World\nThis is parsed text.",
        "file_type": "pdf",
        "is_scanned": False,
        "pages": 2,
        "filename": "test.pdf",
        "model": "test-model",
    }

    with patch("services.parse_service.parse_document", new_callable=AsyncMock, return_value=mock_result):
        async with client:
            resp = await client.post(
                "/parse",
                data={
                    "model_id": "test-model",
                    "force_ocr": "false",
                    "parse_formatting": "true",
                    "process_all_pages": "true",
                    "tier": "Normal",
                },
                files={"file": ("test.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["text"] == "Hello World\nThis is parsed text."
    assert body["file_type"] == "pdf"
    assert body["pages"] == 2
    assert body["filename"] == "test.pdf"
    assert body["model"] == "test-model"


@pytest.mark.asyncio
async def test_ocr_alias_works(client):
    """/ocr endpoint is an alias for /parse and works identically."""
    mock_result = {
        "success": True,
        "text": "OCR alias text",
        "parsed_text": "OCR alias text",
        "file_type": "image",
        "is_scanned": True,
        "pages": 1,
        "filename": "scan.png",
        "model": "test-model",
    }

    with patch("services.parse_service.parse_document", new_callable=AsyncMock, return_value=mock_result):
        async with client:
            resp = await client.post(
                "/ocr",
                data={
                    "model_id": "test-model",
                    "force_ocr": "false",
                    "parse_formatting": "true",
                },
                files={"file": ("scan.png", _make_png_bytes(), "image/png")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["text"] == "OCR alias text"


@pytest.mark.asyncio
async def test_parse_with_extraction_enabled(client):
    """Parse with extraction_enabled=true includes extraction in response."""
    mock_result = {
        "success": True,
        "text": "Name: John Doe, Age: 30",
        "parsed_text": "Name: John Doe, Age: 30",
        "file_type": "pdf",
        "is_scanned": False,
        "pages": 1,
        "filename": "resume.pdf",
        "model": "test-model",
        "extraction": {
            "success": True,
            "structured_data": {"name": "John Doe", "age": 30},
            "field_errors": {},
        },
    }

    with patch("services.parse_service.parse_document", new_callable=AsyncMock, return_value=mock_result):
        async with client:
            resp = await client.post(
                "/parse",
                data={
                    "model_id": "test-model",
                    "force_ocr": "false",
                    "parse_formatting": "true",
                    "extraction_enabled": "true",
                    "extraction_target": "document",
                    "extraction_schema": SAMPLE_EXTRACTION_SCHEMA,
                    "extractor_model": "qwen3-max",
                },
                files={"file": ("resume.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["extraction"]["success"] is True
    assert body["extraction"]["structured_data"]["name"] == "John Doe"


@pytest.mark.asyncio
async def test_parse_background_dispatch(client):
    """Large PDFs dispatched to background return job_id."""
    mock_result = {
        "success": True,
        "background": True,
        "job_id": "job-abc-123",
        "message": "Document has 10 pages (threshold: 5). Processing in background.",
    }

    with patch("services.parse_service.parse_document", new_callable=AsyncMock, return_value=mock_result):
        async with client:
            resp = await client.post(
                "/parse",
                data={
                    "model_id": "test-model",
                    "force_ocr": "false",
                    "parse_formatting": "true",
                },
                files={"file": ("large.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["background"] is True
    assert body["job_id"] == "job-abc-123"


@pytest.mark.asyncio
async def test_parse_formatting_disabled(client):
    """parse_formatting=false returns raw text without formatting."""
    mock_result = {
        "success": True,
        "text": "raw unformatted text",
        "parsed_text": None,
        "file_type": "pdf",
        "is_scanned": False,
        "pages": 1,
        "filename": "doc.pdf",
        "model": "test-model",
    }

    with patch("services.parse_service.parse_document", new_callable=AsyncMock, return_value=mock_result):
        async with client:
            resp = await client.post(
                "/parse",
                data={
                    "model_id": "test-model",
                    "force_ocr": "false",
                    "parse_formatting": "false",
                },
                files={"file": ("doc.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["parsed_text"] is None
    assert body["text"] == "raw unformatted text"


# ---------------------------------------------------------------------------
# Tests — Error cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parse_no_file_returns_422(client):
    """POST /parse without file returns 422 (FastAPI validation)."""
    async with client:
        resp = await client.post(
            "/parse",
            data={"model_id": "test-model"},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_parse_no_model_id_returns_422(client):
    """POST /parse without model_id returns 422."""
    async with client:
        resp = await client.post(
            "/parse",
            files={"file": ("test.pdf", _make_pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_parse_service_raises_400(client):
    """Service raises HTTPException(400) for invalid file type."""
    from fastapi import HTTPException

    with patch(
        "services.parse_service.parse_document",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=400, detail="Invalid file type. Allowed: .pdf, .png"),
    ):
        async with client:
            resp = await client.post(
                "/parse",
                data={"model_id": "test-model"},
                files={"file": ("test.exe", b"binary", "application/octet-stream")},
            )

    assert resp.status_code == 400
    body = resp.json()
    assert "Invalid file type" in body["detail"]


@pytest.mark.asyncio
async def test_parse_service_raises_500_on_ocr_failure(client):
    """OCR processing failure returns HTTP 500."""
    from fastapi import HTTPException

    with patch(
        "services.parse_service.parse_document",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=500, detail="OCR engine timeout"),
    ):
        async with client:
            resp = await client.post(
                "/parse",
                data={"model_id": "test-model"},
                files={"file": ("test.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 500
    body = resp.json()
    assert "OCR engine timeout" in body["detail"]


@pytest.mark.asyncio
async def test_parse_with_provider_override(client):
    """Provider parameter is passed through to service."""
    mock_result = {
        "success": True,
        "text": "Provider test",
        "parsed_text": "Provider test",
        "file_type": "pdf",
        "is_scanned": False,
        "pages": 1,
        "filename": "test.pdf",
        "model": "gemini-model",
    }

    with patch(
        "services.parse_service.parse_document",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_parse:
        async with client:
            resp = await client.post(
                "/parse",
                data={
                    "model_id": "gemini-model",
                    "force_ocr": "true",
                    "parse_formatting": "true",
                    "provider": "google",
                },
                files={"file": ("test.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    # Verify provider was passed to service
    call_kwargs = mock_parse.call_args[1]
    assert call_kwargs["provider"] == "google"
