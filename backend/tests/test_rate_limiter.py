"""Tests for RateLimiter middleware (Task 9.5).

Validates Requirement 20.1:
- Backend enforces rate limits on processing endpoints
- Returns HTTP 429 with Retry-After header when exceeded
- Rate limit thresholds are configurable
"""

import pytest
import httpx
from fastapi import FastAPI

from core.rate_limiter import RateLimiter


def _create_app(*, requests_per_minute: int = 30, burst_size: int = 3, enabled: bool = True):
    """Create a minimal FastAPI app with the RateLimiter middleware."""
    app = FastAPI()
    app.add_middleware(
        RateLimiter,
        requests_per_minute=requests_per_minute,
        burst_size=burst_size,
        enabled=enabled,
    )

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    return app


@pytest.fixture
def app():
    return _create_app(burst_size=3)


@pytest.fixture
def client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


class TestRateLimiterAllowsRequests:
    """Requests within the burst limit should be allowed."""

    @pytest.mark.asyncio
    async def test_requests_within_burst_return_200(self, client):
        """Requests within the burst_size limit get 200 responses."""
        for _ in range(3):
            resp = await client.get("/test")
            assert resp.status_code == 200


class TestRateLimiterBlocks:
    """Requests exceeding the burst limit should be rejected with 429."""

    @pytest.mark.asyncio
    async def test_exceeding_burst_returns_429(self, client):
        """After exhausting burst tokens, the next request gets 429."""
        # Exhaust the 3-token burst
        for _ in range(3):
            await client.get("/test")

        resp = await client.get("/test")
        assert resp.status_code == 429

    @pytest.mark.asyncio
    async def test_429_includes_retry_after_header(self, client):
        """The 429 response includes a Retry-After header with a positive integer."""
        for _ in range(3):
            await client.get("/test")

        resp = await client.get("/test")
        assert resp.status_code == 429
        retry_after = resp.headers.get("retry-after")
        assert retry_after is not None
        assert int(retry_after) >= 1

    @pytest.mark.asyncio
    async def test_429_body_contains_detail(self, client):
        """The 429 response body contains a descriptive detail message."""
        for _ in range(3):
            await client.get("/test")

        resp = await client.get("/test")
        assert resp.status_code == 429
        assert "rate limit" in resp.json()["detail"].lower()


class TestRateLimiterDisabled:
    """When disabled, the middleware passes all requests through."""

    @pytest.mark.asyncio
    async def test_disabled_allows_all_requests(self):
        """With enabled=False, requests beyond burst_size still get 200."""
        app = _create_app(burst_size=1, enabled=False)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            for _ in range(5):
                resp = await client.get("/test")
                assert resp.status_code == 200


class TestRateLimiterPerClient:
    """Different client IPs should have independent rate limits."""

    @pytest.mark.asyncio
    async def test_different_ips_have_independent_limits(self):
        """Two clients with different IPs each get their own burst budget."""
        app = _create_app(burst_size=2)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Exhaust budget for client A
            for _ in range(2):
                resp = await client.get("/test", headers={"X-Forwarded-For": "10.0.0.1"})
                assert resp.status_code == 200

            # Client A is now rate-limited
            resp = await client.get("/test", headers={"X-Forwarded-For": "10.0.0.1"})
            assert resp.status_code == 429

            # Client B still has full budget
            resp = await client.get("/test", headers={"X-Forwarded-For": "10.0.0.2"})
            assert resp.status_code == 200
