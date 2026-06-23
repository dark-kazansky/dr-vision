"""Unit tests for the /extract, /extract-text, and /generate-schema endpoints.

Tests:
1. POST /extract — successful file extraction
2. POST /extract — no file returns 422
3. POST /extract — invalid schema returns 400
4. POST /extract — OCR failure returns 500
5. POST /extract-text — successful text extraction
6. POST /extract-text — empty text returns extraction error
7. POST /extract-text — invalid schema JSON returns 400
8. POST /generate-schema — successful schema generation
9. POST /generate-schema — with sample file
10. POST /generate-schema — service failure returns 500
"""

import json
import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf_bytes():
    """Minimal PDF-like bytes for upload."""
    return b"%PDF-1.4 fake content for testing"


SAMPLE_SCHEMA = json.dumps([
    {"name": "company_name", "type": "string", "description": "Company name", "required": True},
    {"name": "revenue", "type": "number", "description": "Annual revenue", "required": True},
    {"name": "date", "type": "date", "description": "Report date", "required": False},
])

INVALID_SCHEMA = "not valid json at all"

GENERATED_SCHEMA = [
    {"name": "invoice_number", "type": "string", "description": "Invoice number", "required": True},
    {"name": "total_amount", "type": "number", "description": "Total amount", "required": True},
]


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
        "allowed_extensions": [".pdf", ".png", ".jpg"],
    }
    cfg.models = {"test-model": {"model_id": "test-model", "provider": "test"}}
    cfg.get_available_models = MagicMock(return_value=["test-model"])
    return cfg


@pytest.fixture
def mock_extractor():
    ext = MagicMock()
    return ext


@pytest.fixture
def app(mock_config, mock_extractor):
    """Create a FastAPI app with the extract router and overridden dependencies."""
    from api.v1.extract import router
    from core.dependencies import get_config, get_extractor

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_config] = lambda: mock_config
    test_app.dependency_overrides[get_extractor] = lambda: mock_extractor
    yield test_app
    test_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# Tests — POST /extract (file-based extraction)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_file_success(client):
    """POST /extract with valid file and schema returns structured data."""
    mock_result = {
        "success": True,
        "structured_data": {"company_name": "Acme Corp", "revenue": 1000000},
        "field_errors": {},
        "filename": "report.pdf",
    }

    with patch("services.extract_service.extract_from_file", new_callable=AsyncMock, return_value=mock_result):
        async with client:
            resp = await client.post(
                "/extract",
                data={
                    "parser_model_id": "test-model",
                    "extractor_model_id": "qwen3-max",
                    "extraction_schema": SAMPLE_SCHEMA,
                    "extraction_target": "document",
                },
                files={"file": ("report.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["structured_data"]["company_name"] == "Acme Corp"
    assert body["structured_data"]["revenue"] == 1000000
    assert body["filename"] == "report.pdf"


@pytest.mark.asyncio
async def test_extract_file_no_file_returns_422(client):
    """POST /extract without file returns 422."""
    async with client:
        resp = await client.post(
            "/extract",
            data={
                "parser_model_id": "test-model",
                "extraction_schema": SAMPLE_SCHEMA,
                "extraction_target": "document",
            },
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_file_missing_schema_returns_422(client):
    """POST /extract without extraction_schema returns 422."""
    async with client:
        resp = await client.post(
            "/extract",
            data={
                "parser_model_id": "test-model",
                "extraction_target": "document",
            },
            files={"file": ("report.pdf", _make_pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_file_invalid_schema_returns_400(client):
    """POST /extract with invalid schema JSON returns 400."""
    from fastapi import HTTPException

    with patch(
        "services.extract_service.extract_from_file",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=400, detail="Invalid schema: Expecting value"),
    ):
        async with client:
            resp = await client.post(
                "/extract",
                data={
                    "parser_model_id": "test-model",
                    "extractor_model_id": "qwen3-max",
                    "extraction_schema": INVALID_SCHEMA,
                    "extraction_target": "document",
                },
                files={"file": ("report.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 400
    assert "Invalid schema" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_extract_file_ocr_failure_returns_500(client):
    """POST /extract when OCR fails returns 500."""
    from fastapi import HTTPException

    with patch(
        "services.extract_service.extract_from_file",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=500, detail="OCR processing failed"),
    ):
        async with client:
            resp = await client.post(
                "/extract",
                data={
                    "parser_model_id": "test-model",
                    "extractor_model_id": "qwen3-max",
                    "extraction_schema": SAMPLE_SCHEMA,
                    "extraction_target": "document",
                },
                files={"file": ("report.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 500
    assert "OCR processing failed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_extract_file_with_generated_schema(client):
    """POST /extract with generate_schema=true uses AI schema."""
    mock_result = {
        "success": True,
        "structured_data": {"invoice_number": "INV-001", "total_amount": 5000},
        "field_errors": {},
        "filename": "invoice.pdf",
    }

    with patch(
        "services.extract_service.extract_from_file",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_extract:
        async with client:
            resp = await client.post(
                "/extract",
                data={
                    "parser_model_id": "test-model",
                    "extractor_model_id": "qwen3-max",
                    "extraction_schema": SAMPLE_SCHEMA,
                    "extraction_target": "document",
                    "generate_schema": "true",
                    "schema_prompt": "Extract invoice fields",
                },
                files={"file": ("invoice.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # Verify generate_schema and schema_prompt were passed through
    call_kwargs = mock_extract.call_args[1]
    assert call_kwargs["use_generated_schema"] is True
    assert call_kwargs["schema_prompt"] == "Extract invoice fields"


@pytest.mark.asyncio
async def test_extract_file_with_provider(client):
    """POST /extract passes provider to service."""
    mock_result = {
        "success": True,
        "structured_data": {"company_name": "Test"},
        "field_errors": {},
        "filename": "report.pdf",
    }

    with patch(
        "services.extract_service.extract_from_file",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_extract:
        async with client:
            resp = await client.post(
                "/extract",
                data={
                    "parser_model_id": "test-model",
                    "extractor_model_id": "gemini-2.5-flash",
                    "extraction_schema": SAMPLE_SCHEMA,
                    "extraction_target": "document",
                    "provider": "google",
                },
                files={"file": ("report.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    call_kwargs = mock_extract.call_args[1]
    assert call_kwargs["provider"] == "google"


# ---------------------------------------------------------------------------
# Tests — POST /extract-text (text-based extraction)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_text_success(client):
    """POST /extract-text with valid text and schema returns extraction."""
    mock_result = {
        "success": True,
        "extraction": {
            "success": True,
            "structured_data": {"company_name": "Acme Corp", "revenue": 500000},
            "field_errors": {},
        },
    }

    with patch("services.extract_service.extract_from_text", new_callable=AsyncMock, return_value=mock_result):
        async with client:
            resp = await client.post(
                "/extract-text",
                data={
                    "text": "Acme Corp reported revenue of $500,000 this year.",
                    "extraction_schema": SAMPLE_SCHEMA,
                    "extraction_target": "document",
                    "extractor_model_id": "gemini-2.5-flash",
                    "tier": "Normal",
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["extraction"]["structured_data"]["company_name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_extract_text_missing_text_returns_422(client):
    """POST /extract-text without text field returns 422."""
    async with client:
        resp = await client.post(
            "/extract-text",
            data={
                "extraction_schema": SAMPLE_SCHEMA,
                "extraction_target": "document",
            },
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_text_missing_schema_returns_422(client):
    """POST /extract-text without extraction_schema returns 422."""
    async with client:
        resp = await client.post(
            "/extract-text",
            data={
                "text": "Some document text",
                "extraction_target": "document",
            },
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_text_invalid_schema_returns_error(client):
    """POST /extract-text with invalid JSON schema returns error."""
    from fastapi import HTTPException

    with patch(
        "services.extract_service.extract_from_text",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=400, detail="Invalid schema JSON: Expecting value"),
    ):
        async with client:
            resp = await client.post(
                "/extract-text",
                data={
                    "text": "Some document text",
                    "extraction_schema": INVALID_SCHEMA,
                    "extraction_target": "document",
                },
            )

    assert resp.status_code == 400
    assert "Invalid schema" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_extract_text_with_custom_model(client):
    """POST /extract-text with custom extractor_model_id passes it to service."""
    mock_result = {
        "success": True,
        "extraction": {
            "success": True,
            "structured_data": {"company_name": "Test"},
            "field_errors": {},
        },
    }

    with patch(
        "services.extract_service.extract_from_text",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_extract:
        async with client:
            resp = await client.post(
                "/extract-text",
                data={
                    "text": "Test document content",
                    "extraction_schema": SAMPLE_SCHEMA,
                    "extraction_target": "document",
                    "extractor_model_id": "qwen3-max",
                    "tier": "Advance",
                },
            )

    assert resp.status_code == 200
    call_kwargs = mock_extract.call_args[1]
    assert call_kwargs["extractor_model_id"] == "qwen3-max"


@pytest.mark.asyncio
async def test_extract_text_page_target(client):
    """POST /extract-text with extraction_target=page works correctly."""
    mock_result = {
        "success": True,
        "extraction": {
            "success": True,
            "structured_data": [
                {"company_name": "Page 1 Corp", "revenue": 100},
                {"company_name": "Page 2 Corp", "revenue": 200},
            ],
            "field_errors": {},
        },
    }

    with patch(
        "services.extract_service.extract_from_text",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        async with client:
            resp = await client.post(
                "/extract-text",
                data={
                    "text": "Page 1: Page 1 Corp revenue 100\nPage 2: Page 2 Corp revenue 200",
                    "extraction_schema": SAMPLE_SCHEMA,
                    "extraction_target": "page",
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["extraction"]["structured_data"]) == 2


# ---------------------------------------------------------------------------
# Tests — POST /generate-schema
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_schema_success(client):
    """POST /generate-schema returns AI-generated schema."""
    mock_result = {
        "success": True,
        "schema": GENERATED_SCHEMA,
    }

    with patch("services.extract_service.generate_schema", new_callable=AsyncMock, return_value=mock_result):
        async with client:
            resp = await client.post(
                "/generate-schema",
                data={
                    "prompt": "Generate schema for invoice extraction",
                    "tier": "Normal",
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["schema"]) == 2
    assert body["schema"][0]["name"] == "invoice_number"
    assert body["schema"][1]["name"] == "total_amount"


@pytest.mark.asyncio
async def test_generate_schema_with_sample_file(client):
    """POST /generate-schema with file provides sample context."""
    mock_result = {
        "success": True,
        "schema": GENERATED_SCHEMA,
    }

    with patch(
        "services.extract_service.generate_schema",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_gen:
        async with client:
            resp = await client.post(
                "/generate-schema",
                data={
                    "prompt": "Extract invoice data",
                    "tier": "Normal",
                },
                files={"file": ("sample.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # Verify file was passed to service
    call_kwargs = mock_gen.call_args[1]
    assert call_kwargs["file"] is not None


@pytest.mark.asyncio
async def test_generate_schema_missing_prompt_returns_422(client):
    """POST /generate-schema without prompt returns 422."""
    async with client:
        resp = await client.post(
            "/generate-schema",
            data={"tier": "Normal"},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_generate_schema_failure_returns_500(client):
    """POST /generate-schema when AI fails returns 500."""
    from fastapi import HTTPException

    with patch(
        "services.extract_service.generate_schema",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=500, detail="LLM generation failed"),
    ):
        async with client:
            resp = await client.post(
                "/generate-schema",
                data={
                    "prompt": "Generate schema",
                    "tier": "Normal",
                },
            )

    assert resp.status_code == 500
    assert "LLM generation failed" in resp.json()["detail"]
