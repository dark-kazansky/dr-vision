"""
Rate limiting middleware using a token-bucket algorithm per client IP.

Configurable via the ``rate_limit`` section in ``settings.yaml``.
Returns HTTP 429 with a ``Retry-After`` header when a client exceeds
the allowed request rate.

Requirements: 20.1, 20.2, 20.3
"""

import logging
import math
import time
from typing import Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


class _TokenBucket:
    """Per-client token bucket that refills at a steady rate."""

    __slots__ = ("tokens", "max_tokens", "refill_rate", "last_refill")

    def __init__(self, max_tokens: float, refill_rate: float) -> None:
        self.tokens = max_tokens
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def retry_after(self) -> int:
        """Seconds until at least one token is available."""
        if self.tokens >= 1.0:
            return 0
        deficit = 1.0 - self.tokens
        return max(1, math.ceil(deficit / self.refill_rate))


class RateLimiter(BaseHTTPMiddleware):
    """Token-bucket rate limiter per client IP.

    Constructor Parameters
    ----------------------
    app : ASGIApp
        The ASGI application to wrap.
    requests_per_minute : int
        Sustained request rate (tokens refill at this rate).
    burst_size : int
        Maximum burst capacity (bucket size).
    enabled : bool
        When ``False`` the middleware passes requests through unchanged.
    """

    def __init__(
        self,
        app,
        *,
        requests_per_minute: int = 30,
        burst_size: int = 10,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self._buckets: Dict[str, _TokenBucket] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from the request."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_bucket(self, client_ip: str) -> _TokenBucket:
        bucket = self._buckets.get(client_ip)
        if bucket is None:
            bucket = _TokenBucket(
                max_tokens=float(self.burst_size),
                refill_rate=self.refill_rate,
            )
            self._buckets[client_ip] = bucket
        return bucket

    # ------------------------------------------------------------------
    # Middleware dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        bucket = self._get_bucket(client_ip)

        if not bucket.consume():
            retry_after = bucket.retry_after()
            logger.warning(
                "rate_limit_exceeded client_ip=%s retry_after=%d",
                client_ip,
                retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
