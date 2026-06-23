"""
Custom exception handlers for the Doc Intelligence FastAPI application.

Registers application-wide error handlers that return consistent JSON
error responses for common failure modes.

Usage (in server.py):
    from core.exceptions import register_exception_handlers, raise_agent_error
    register_exception_handlers(app)
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def raise_agent_error(result, prefix: str = "") -> None:
    """Raise an appropriate HTTP exception based on agent error_type.

    Maps common agent error types to HTTP status codes:
      - quota_error    → 429
      - auth_error     → 401
      - timeout_error  → 504
      - validation_error / content_blocked / safety_blocked → 400
      - anything else  → 500

    Args:
        result: Agent result object with .error and .error_type attributes.
        prefix: Optional string prepended to the error message.

    Raises:
        StarletteHTTPException with structured detail payload.
    """
    status_code = 500
    if result.error_type == "quota_error":
        status_code = 429
    elif result.error_type == "auth_error":
        status_code = 401
    elif result.error_type == "timeout_error":
        status_code = 504
    elif result.error_type in ("validation_error", "content_blocked", "safety_blocked"):
        status_code = 400

    error_msg = f"{prefix}{result.error}" if prefix else result.error

    raise StarletteHTTPException(
        status_code=status_code,
        detail={"message": error_msg, "error_type": result.error_type or "processing_error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app instance."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Return a structured JSON body for HTTP errors (4xx / 5xx)."""
        detail = exc.detail
        error_msg = str(detail)
        error_type = "http_error"
        if isinstance(detail, dict) and "message" in detail:
            error_msg = detail["message"]
            error_type = detail.get("error_type", "http_error")

        logger.warning(
            "http_error status=%d path=%s detail=%s error_type=%s",
            exc.status_code,
            request.url.path,
            error_msg,
            error_type,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": error_msg, "error_type": error_type},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return a 422 JSON body with field-level validation details."""
        errors = exc.errors()
        logger.warning(
            "validation_error path=%s errors=%s",
            request.url.path,
            errors,
        )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "Request validation failed",
                "error_type": "validation_error",
                "details": errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all handler for unexpected server errors."""
        logger.exception(
            "unhandled_exception path=%s error=%s",
            request.url.path,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "An unexpected server error occurred.",
                "error_type": "internal_error",
            },
        )
