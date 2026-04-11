"""Tests for RequestLoggingMiddleware."""

import logging
import re

import httpx
import pytest

from fastapi import FastAPI

from core.middleware import RequestLoggingMiddleware


@pytest.fixture
def app():
    """Create a minimal FastAPI app with the logging middleware."""
    _app = FastAPI()
    _app.add_middleware(RequestLoggingMiddleware)

    @_app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    @_app.get("/error")
    async def error_endpoint():
        raise ValueError("boom")

    return _app


@pytest.fixture
def client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class TestRequestLoggingMiddleware:
    """Tests for the RequestLoggingMiddleware class."""

    @pytest.mark.asyncio
    async def test_logs_request_started_and_completed(self, client, caplog):
        """Middleware logs both request_started and request_completed entries."""
        with caplog.at_level(logging.INFO, logger="core.middleware"):
            await client.get("/test")

        messages = [r.message for r in caplog.records]
        assert any("request_started" in m for m in messages)
        assert any("request_completed" in m for m in messages)

    @pytest.mark.asyncio
    async def test_logs_method_and_path(self, client, caplog):
        """Log entries include the HTTP method and request path."""
        with caplog.at_level(logging.INFO, logger="core.middleware"):
            await client.get("/test")

        messages = " ".join(r.message for r in caplog.records)
        assert "method=GET" in messages
        assert "path=/test" in messages

    @pytest.mark.asyncio
    async def test_logs_status_code(self, client, caplog):
        """Completed log entry includes the response status code."""
        with caplog.at_level(logging.INFO, logger="core.middleware"):
            await client.get("/test")

        completed = [r.message for r in caplog.records if "request_completed" in r.message]
        assert len(completed) == 1
        assert "status=200" in completed[0]

    @pytest.mark.asyncio
    async def test_logs_duration(self, client, caplog):
        """Completed log entry includes duration_ms."""
        with caplog.at_level(logging.INFO, logger="core.middleware"):
            await client.get("/test")

        completed = [r.message for r in caplog.records if "request_completed" in r.message]
        assert len(completed) == 1
        assert "duration_ms=" in completed[0]

    @pytest.mark.asyncio
    async def test_generates_unique_request_id(self, client, caplog):
        """Each request gets a unique UUID4 request ID in the log and response header."""
        with caplog.at_level(logging.INFO, logger="core.middleware"):
            resp = await client.get("/test")

        # Check response header
        request_id = resp.headers.get("x-request-id")
        assert request_id is not None
        assert UUID_RE.match(request_id)

        # Check that the same request_id appears in log messages
        messages = " ".join(r.message for r in caplog.records)
        assert request_id in messages

    @pytest.mark.asyncio
    async def test_different_requests_get_different_ids(self, client):
        """Two requests produce different request IDs."""
        resp1 = await client.get("/test")
        resp2 = await client.get("/test")
        assert resp1.headers["x-request-id"] != resp2.headers["x-request-id"]

    @pytest.mark.asyncio
    async def test_logs_on_error_response(self, client, caplog):
        """Middleware still logs completed entry even when the handler raises."""
        with caplog.at_level(logging.INFO, logger="core.middleware"):
            with pytest.raises(ValueError):
                await client.get("/error")

        completed = [r.message for r in caplog.records if "request_completed" in r.message]
        assert len(completed) == 1
        assert "status=500" in completed[0]
