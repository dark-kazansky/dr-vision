"""
Custom exception handlers for the Dr.Vision FastAPI application.

Registers application-wide error handlers that return consistent JSON
error responses for common failure modes.

Usage (in server.py):
    from core.exceptions import register_exception_handlers
    register_exception_handlers(app)
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app instance."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Return a structured JSON body for HTTP errors (4xx / 5xx)."""
        logger.warning(
            "http_error status=%d path=%s detail=%s",
            exc.status_code,
            request.url.path,
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": str(exc.detail), "error_type": "http_error"},
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
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
