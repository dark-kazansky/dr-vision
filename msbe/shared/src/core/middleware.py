"""
Middleware components for the M.DocAI backend.

Provides cross-cutting concerns like file size validation
and request logging.
"""

import logging
import time
from uuid import uuid4

from fastapi import UploadFile, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request method, path, status code, response time, and a unique request ID for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid4())
        start_time = time.time()

        logger.info(
            "request_started request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )

        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "request_completed request_id=%s method=%s path=%s status=%d duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                500,
                duration_ms,
            )
            raise

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "request_completed request_id=%s method=%s path=%s status=%d duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response


class FileSizeValidator:
    """Validates uploaded file sizes against configured limits.

    Reads the file content to determine actual size, then resets
    the file position so downstream handlers can read it normally.
    """

    async def validate(self, file: UploadFile, max_size_mb: float) -> None:
        """
        Check that an uploaded file does not exceed the size limit.

        Args:
            file: The uploaded file to validate.
            max_size_mb: Maximum allowed file size in megabytes.

        Raises:
            HTTPException: 413 if the file exceeds the configured limit.
        """
        max_size_bytes = int(max_size_mb * 1024 * 1024)

        content = await file.read()
        size = len(content)

        # Always reset file position so the file can be read again downstream
        await file.seek(0)

        if size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File size ({size / (1024 * 1024):.2f} MB) exceeds "
                    f"the maximum allowed size of {max_size_mb} MB"
                ),
            )
