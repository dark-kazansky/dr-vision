"""Unit tests for /api/v1/documents endpoints — feat-042.

Tests:
1. POST /process with file → 202 + job_id
2. POST /process without file or upload_id → 400
3. POST /process with invalid operation → 400
4. GET /{job_id} status polling → returns status/progress
5. GET /{job_id}/result on completed job → result payload
6. GET /{job_id}/result on running job → 409
7. GET /nonexistent → 404
8. POST /{job_id}/cancel on running job → success
9. POST /{job_id}/cancel on completed job → 409
10. GET /{job_id}/stream → SSE event stream
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from api.v1.documents import router
from services.document_job_runner import (
    DocumentJobConfig,
    DocumentJobRecord,
    DocumentJobStatus,
    DocumentOperation,
)


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create a FastAPI app with the documents router, auth bypassed."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """httpx.AsyncClient for testing."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# Tests: POST /process
# ---------------------------------------------------------------------------


class TestSubmitDocumentProcessing:
    """Test POST /api/v1/documents/process."""

    @pytest.mark.asyncio
    async def test_submit_with_file_returns_202(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                mock_runner.create_job.return_value = "abc123def456"
                mock_runner.run = AsyncMock()

                resp = await client.post(
                    "/api/v1/documents/process",
                    files={"file": ("test.txt", b"Hello World", "text/plain")},
                    data={"operation": "ocr", "model_id": "test-model"},
                )

        assert resp.status_code == 202
        body = resp.json()
        assert body["job_id"] == "abc123def456"
        assert body["status"] == "queued"
        assert body["operation"] == "ocr"

    @pytest.mark.asyncio
    async def test_submit_without_file_or_upload_id_returns_400(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            resp = await client.post(
                "/api/v1/documents/process",
                data={"operation": "ocr"},
            )

        assert resp.status_code == 400
        assert "file upload or an upload_id" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_invalid_operation_returns_400(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            resp = await client.post(
                "/api/v1/documents/process",
                files={"file": ("test.txt", b"content", "text/plain")},
                data={"operation": "invalid_op"},
            )

        assert resp.status_code == 400
        assert "Invalid operation" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: GET /{job_id} (status)
# ---------------------------------------------------------------------------


class TestGetDocumentJobStatus:
    """Test GET /api/v1/documents/{job_id}."""

    @pytest.mark.asyncio
    async def test_get_status_returns_job_info(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                record = DocumentJobRecord(
                    job_id="job123",
                    config=DocumentJobConfig(
                        file_path="/tmp/test.txt",
                        filename="test.txt",
                        operation=DocumentOperation.OCR,
                    ),
                    status=DocumentJobStatus.RUNNING,
                    progress=0.5,
                    total_pages=10,
                    current_page=5,
                    current_stage="parse",
                )
                mock_runner.get_job.return_value = record

                resp = await client.get("/api/v1/documents/job123")

        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == "job123"
        assert body["status"] == "running"
        assert body["progress"] == 0.5
        assert body["total_pages"] == 10
        assert body["current_page"] == 5

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                mock_runner.get_job.return_value = None
                resp = await client.get("/api/v1/documents/nonexistent")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: GET /{job_id}/result
# ---------------------------------------------------------------------------


class TestGetDocumentJobResult:
    """Test GET /api/v1/documents/{job_id}/result."""

    @pytest.mark.asyncio
    async def test_get_result_completed(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                record = DocumentJobRecord(
                    job_id="job123",
                    config=DocumentJobConfig(
                        file_path="/tmp/test.txt",
                        filename="test.txt",
                        operation=DocumentOperation.OCR,
                    ),
                    status=DocumentJobStatus.COMPLETED,
                    result={"success": True, "text": "Extracted text"},
                )
                mock_runner.get_job.return_value = record

                resp = await client.get("/api/v1/documents/job123/result")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["result"]["text"] == "Extracted text"

    @pytest.mark.asyncio
    async def test_get_result_still_running_returns_409(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                record = DocumentJobRecord(
                    job_id="job123",
                    config=DocumentJobConfig(
                        file_path="/tmp/test.txt",
                        filename="test.txt",
                        operation=DocumentOperation.OCR,
                    ),
                    status=DocumentJobStatus.RUNNING,
                )
                mock_runner.get_job.return_value = record

                resp = await client.get("/api/v1/documents/job123/result")

        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Tests: POST /{job_id}/cancel
# ---------------------------------------------------------------------------


class TestCancelDocumentJob:
    """Test POST /api/v1/documents/{job_id}/cancel."""

    @pytest.mark.asyncio
    async def test_cancel_running_job(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                mock_runner.request_cancel.return_value = True
                resp = await client.post("/api/v1/documents/job123/cancel")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

    @pytest.mark.asyncio
    async def test_cancel_completed_job_returns_409(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                mock_runner.request_cancel.return_value = False
                record = DocumentJobRecord(
                    job_id="job123",
                    config=DocumentJobConfig(
                        file_path="/tmp/test.txt",
                        filename="test.txt",
                        operation=DocumentOperation.OCR,
                    ),
                    status=DocumentJobStatus.COMPLETED,
                )
                mock_runner.get_job.return_value = record

                resp = await client.post("/api/v1/documents/job123/cancel")

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_not_found_returns_404(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                mock_runner.request_cancel.return_value = False
                mock_runner.get_job.return_value = None

                resp = await client.post("/api/v1/documents/nonexistent/cancel")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: GET /{job_id}/stream (SSE)
# ---------------------------------------------------------------------------


class TestStreamDocumentProgress:
    """Test GET /api/v1/documents/{job_id}/stream."""

    @pytest.mark.asyncio
    async def test_stream_terminal_job_returns_single_event(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                record = DocumentJobRecord(
                    job_id="job123",
                    config=DocumentJobConfig(
                        file_path="/tmp/test.txt",
                        filename="test.txt",
                        operation=DocumentOperation.OCR,
                    ),
                    status=DocumentJobStatus.COMPLETED,
                    progress=1.0,
                    result={"success": True, "text": "done"},
                )
                mock_runner.get_job.return_value = record

                resp = await client.get("/api/v1/documents/job123/stream")

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "event: job_completed" in body

    @pytest.mark.asyncio
    async def test_stream_not_found_returns_404(self, client):
        with patch("api.v1.documents.get_current_user", return_value="testuser"):
            with patch("api.v1.documents.document_job_runner") as mock_runner:
                mock_runner.get_job.return_value = None
                resp = await client.get("/api/v1/documents/nonexistent/stream")

        assert resp.status_code == 404
