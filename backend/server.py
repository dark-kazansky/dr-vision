"""
FastAPI application factory and lifespan for Dr.Vision.

This module owns:
- Lifespan context manager (startup / shutdown)
- App factory (create_app)
- Middleware registration
- Router registration
- Exception handler registration

Usage:
    from server import app          # for uvicorn
    from server import create_app   # for testing
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from settings import settings
from api.router import router as api_router
from core.middleware import RequestLoggingMiddleware
from core.rate_limiter import RateLimiter
from core.exceptions import register_exception_handlers
from storage.banking_repository import BankingRepository
from storage.workflow_repository import WorkflowRepository
from services.job_queue import job_queue
from services.job_executor import execute_job
from services import job_persistence
from services import execution_state

logger = logging.getLogger(__name__)

# Module-level repository instance — shared with route handlers via app.state
banking_repo = BankingRepository(settings.database_url)
workflow_repo = WorkflowRepository(settings.database_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — runs on startup and shutdown.

    Startup:
    - Validates settings
    - Connects to PostgreSQL and initializes banking schema
    - Logs available models and server info

    Shutdown:
    - Closes database connection pool
    - Logs shutdown message
    """
    logger.info("=" * 70)
    logger.info("Dr.Vision — FastAPI Backend")
    logger.info("=" * 70)

    errors = settings.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error("  - %s", error)
        logger.error("=" * 70)
        raise RuntimeError(f"Configuration errors: {errors}")

    # --- Banking database ---
    try:
        await banking_repo.connect()
        await banking_repo.init_schema()
        app.state.banking_repo = banking_repo
        logger.info("Banking database connected and schema initialized")
    except Exception as e:
        logger.warning(
            "Banking database unavailable — storage features disabled: %s", e,
        )
        app.state.banking_repo = None

    # --- Workflow database ---
    try:
        await workflow_repo.connect()
        await workflow_repo.init_schema()
        app.state.workflow_repo = workflow_repo
        logger.info("Workflow database connected and schema initialized")
    except Exception as e:
        logger.warning(
            "Workflow database unavailable — persistence disabled: %s", e,
        )
        app.state.workflow_repo = None

    logger.info("Configuration loaded and validated successfully")
    logger.info("Available Models: %s", ", ".join(settings.get_available_models()))
    logger.info("Default Model: %s", settings.default_model)
    logger.info("Server: %s:%s", settings.fastapi_host, settings.fastapi_port)
    logger.info("Debug Mode: %s", settings.fastapi_debug)
    logger.info("=" * 70)

    # --- Job Queue ---
    try:
        import yaml
        from pathlib import Path
        config_path = Path("config/settings.yaml")
        if config_path.exists():
            with open(config_path) as f:
                yaml_config = yaml.safe_load(f) or {}
            jq_config = yaml_config.get("job_queue", {})
        else:
            jq_config = {}
    except Exception:
        jq_config = {}

    max_concurrent = jq_config.get("max_concurrent", 2)
    job_queue._max_concurrent = max_concurrent
    job_queue.set_executor(execute_job)
    await job_queue.start()
    logger.info("Job queue started (max_concurrent=%d)", job_queue.max_concurrent)

    # --- Job Persistence & Cleanup ---
    if app.state.workflow_repo:
        job_persistence.set_repository(app.state.workflow_repo)
        await job_persistence.start_persistence()
        logger.info("Job persistence and cleanup scheduler started")

        # --- Execution State Service (feat-007) ---
        execution_state.set_repository(app.state.workflow_repo)
        logger.info("Execution state service initialized")

    logger.info("Server ready to accept requests")
    logger.info("=" * 70)

    yield

    # --- Shutdown: stop persistence ---
    await job_persistence.stop_persistence()

    # --- Shutdown: stop job queue ---
    await job_queue.stop()
    logger.info("Job queue stopped")

    # --- Shutdown: close DB pools ---
    try:
        await banking_repo.close()
    except Exception as e:
        logger.warning("Error closing banking database: %s", e)

    try:
        await workflow_repo.close()
    except Exception as e:
        logger.warning("Error closing workflow database: %s", e)

    logger.info("=" * 70)
    logger.info("Shutting down Dr.Vision")
    logger.info("=" * 70)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title="OCR Web UI API",
        description="OCR processing API with multiple model support",
        version="2.0.0",
        lifespan=lifespan,
    )

    # --- Exception handlers ---
    register_exception_handlers(app)

    # --- CORS ---
    try:
        cors_origins = settings.cors_origins
    except Exception:
        logging.warning(
            "CORS configuration loading failed. "
            "Falling back to restrictive default: ['http://localhost:3000']"
        )
        cors_origins = ["http://localhost:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Request logging ---
    app.add_middleware(RequestLoggingMiddleware)

    # --- Rate limiting ---
    try:
        app.add_middleware(
            RateLimiter,
            enabled=settings.rate_limit_enabled,
            requests_per_minute=settings.rate_limit_requests_per_minute,
            burst_size=settings.rate_limit_burst_size,
        )
    except Exception:
        logging.warning("Failed to configure rate limiter; rate limiting disabled.")

    # --- Routers ---
    app.include_router(api_router)

    # --- Root endpoint ---
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "OCR Web UI API",
            "version": "2.0.0",
            "description": "OCR processing API with multiple model support",
            "endpoints": {
                "health": "/health",
                "ocr": "/ocr (POST)",
                "docs": "/docs",
            },
        }

    return app


# Module-level app instance for uvicorn / ASGI servers
app = create_app()
