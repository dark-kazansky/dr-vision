"""Unit tests for the Journey API Trigger endpoint (feat-009).

Tests:
1. Trigger saved workflow successfully (returns 200, uploads file, registers job/upload).
2. Trigger non-existent workflow (returns 404).
3. Trigger workflow with empty steps (returns 400).
4. Trigger workflow with invalid file extension (returns 400).
"""

import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock

import os
# Set dummy AWS credentials before importing any application code that might initialize boto3
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["MINIO_ACCESS_KEY"] = "test"
os.environ["MINIO_SECRET_KEY"] = "test"

from fastapi import FastAPI
from api.v1.journey_jobs import router
import os

@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.upload_config = {
        "max_size_mb": 10,
        "folder": "/tmp/test_uploads",
        "allowed_extensions": ["pdf", "png", "jpg"]
    }
    return cfg

@pytest.fixture
def app(mock_config):
    test_app = FastAPI()
    test_app.include_router(router)
    yield test_app

@pytest.fixture
def client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")

@pytest.mark.asyncio
async def test_trigger_workflow_success(client, mock_config):
    # Mock workflow definition
    mock_workflow = {
        "id": "wf-123",
        "name": "Test Workflow",
        "graph_data": {
            "steps": [
                {"id": "n1", "type": "ocr", "label": "OCR Node"},
                {"id": "n2", "type": "parse", "label": "Parse Node"}
            ]
        }
    }

    # Setup database repository mock
    mock_repo = AsyncMock()
    mock_repo.get_workflow.return_value = mock_workflow
    mock_repo.create_job = AsyncMock()
    mock_repo.update_job = AsyncMock()
    mock_repo.set_job_minio_path = AsyncMock()
    mock_repo.create_upload = AsyncMock()

    # Mock minio client
    mock_minio = MagicMock()
    mock_minio.upload_file.return_value = True

    # Use patches to intercept file handling, MinIO, DB, config loading, and executor context saving
    with patch("server.workflow_repo", mock_repo), \
         patch("config.Config.load", return_value=mock_config), \
         patch("core.utils.secure_save_file", new_callable=AsyncMock, return_value="/tmp/test_uploads/fake.pdf"), \
         patch("core.minio_client.minio_client", mock_minio), \
         patch("services.job_executor.store_job_context", new_callable=AsyncMock), \
         patch("os.path.exists", return_value=True), \
         patch("os.path.getsize", return_value=12345), \
         patch.dict(os.environ, {"WEBHOOK_API_KEY": "test-webhook-key"}):

        async with client:
            resp = await client.post(
                "/api/v1/workflows/wf-123/trigger",
                files={"file": ("test.pdf", b"%PDF-1.4 fake content", "application/pdf")},
                data={"max_retries": 3},
                headers={"X-API-Key": "test-webhook-key"}
            )

            assert resp.status_code == 200
            body = resp.json()
            assert "job_id" in body
            assert body["status"] == "queued"
            assert "poll_url" in body
            assert "queued" in body["message"]

            # Assert correct repo methods were invoked
            mock_repo.get_workflow.assert_called_once_with("wf-123")
            mock_repo.create_job.assert_called_once()
            mock_repo.update_job.assert_called_once()
            mock_repo.set_job_minio_path.assert_called_once()
            mock_repo.create_upload.assert_called_once()

@pytest.mark.asyncio
async def test_trigger_workflow_not_found(client, mock_config):
    # Setup database repository mock to return None
    mock_repo = AsyncMock()
    mock_repo.get_workflow.return_value = None

    with patch("server.workflow_repo", mock_repo), \
         patch("config.Config.load", return_value=mock_config), \
         patch.dict(os.environ, {"WEBHOOK_API_KEY": "test-webhook-key"}):

        async with client:
            resp = await client.post(
                "/api/v1/workflows/wf-999/trigger",
                files={"file": ("test.pdf", b"%PDF-1.4 fake content", "application/pdf")},
                headers={"X-API-Key": "test-webhook-key"}
            )

            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"].lower()
            mock_repo.get_workflow.assert_called_once_with("wf-999")

@pytest.mark.asyncio
async def test_trigger_workflow_empty_steps(client, mock_config):
    # Mock workflow with no steps
    mock_workflow = {
        "id": "wf-empty",
        "name": "Empty Workflow",
        "graph_data": {
            "steps": []
        }
    }

    mock_repo = AsyncMock()
    mock_repo.get_workflow.return_value = mock_workflow

    with patch("server.workflow_repo", mock_repo), \
         patch("config.Config.load", return_value=mock_config), \
         patch.dict(os.environ, {"WEBHOOK_API_KEY": "test-webhook-key"}):

        async with client:
            resp = await client.post(
                "/api/v1/workflows/wf-empty/trigger",
                files={"file": ("test.pdf", b"%PDF-1.4 fake content", "application/pdf")},
                headers={"X-API-Key": "test-webhook-key"}
            )

            assert resp.status_code == 400
            assert "at least one step" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_trigger_workflow_invalid_file_extension(client, mock_config):
    # Setup mock workflow
    mock_workflow = {
        "id": "wf-123",
        "name": "Test Workflow",
        "graph_data": {
            "steps": [{"id": "n1", "type": "ocr"}]
        }
    }

    mock_repo = AsyncMock()
    mock_repo.get_workflow.return_value = mock_workflow

    with patch("server.workflow_repo", mock_repo), \
         patch("config.Config.load", return_value=mock_config), \
         patch.dict(os.environ, {"WEBHOOK_API_KEY": "test-webhook-key"}):

        async with client:
            resp = await client.post(
                "/api/v1/workflows/wf-123/trigger",
                files={"file": ("test.exe", b"fake executable", "application/octet-stream")},
                headers={"X-API-Key": "test-webhook-key"}
            )

            assert resp.status_code == 400
            assert "invalid file type" in resp.json()["detail"].lower()
