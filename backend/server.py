"""
FastAPI application factory and lifespan for Doc Intelligence.

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
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from settings import settings
from api.router import router as api_router
from core.middleware import RequestLoggingMiddleware
from core.rate_limiter import RateLimiter
from core.exceptions import register_exception_handlers
from storage.banking_repository import BankingRepository
from storage.ocr_result_repository import OcrResultRepository
from storage.workflow_repository import WorkflowRepository
from services.job_queue import job_queue
from services.job_executor import execute_job
from services import job_persistence
from services import execution_state
from services import observability
from services.workflow_engine import WorkflowEngine
from auth.repository import AuthRepository
from auth.router import router as auth_router
from auth.service import AuthService

logger = logging.getLogger(__name__)

# --- Validate required secrets at startup ---
_missing_secrets = settings.check_required_secrets()
if _missing_secrets:
    logger.warning(
        "Missing required environment variables: %s. "
        "Database and storage features will be unavailable. "
        "See .env.example for configuration reference.",
        ", ".join(_missing_secrets),
    )

# Module-level repository instance — shared with route handlers via app.state
banking_repo = BankingRepository(settings.database_url or "")
ocr_result_repo = OcrResultRepository(settings.database_url or "")
workflow_repo = WorkflowRepository(settings.database_url or "")
auth_repo = AuthRepository()


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
    logger.info("Doc Intelligence — FastAPI Backend")
    logger.info("=" * 70)

    errors = settings.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error("  - %s", error)
        logger.error("=" * 70)
        raise RuntimeError(f"Configuration errors: {errors}")

    # --- Database Migrations (Alembic) ---
    if os.environ.get("AUTO_MIGRATE", "").lower() in ("true", "1", "yes"):
        try:
            from alembic.config import Config as AlembicConfig
            from alembic import command as alembic_command
            from pathlib import Path

            alembic_ini = Path(__file__).parent / "alembic.ini"
            alembic_cfg = AlembicConfig(str(alembic_ini))
            alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url or "")
            alembic_command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations applied (alembic upgrade head)")
        except Exception as e:
            logger.error("Database migration failed: %s", e)
            raise RuntimeError(f"Migration failed: {e}")

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

    # --- OCR Results database ---
    try:
        await ocr_result_repo.connect()
        await ocr_result_repo.init_schema()
        app.state.ocr_result_repo = ocr_result_repo
        logger.info("OCR results database connected and schema initialized")
    except Exception as e:
        logger.error(
            "OCR results database connection FAILED — system cannot operate without DB: %s", e,
        )
        raise RuntimeError(f"OCR results database unavailable: {e}")

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

    # --- Auth database (reuses workflow_repo pool) ---
    try:
        if workflow_repo._pool:
            auth_repo.set_pool(workflow_repo._pool)
            await auth_repo.init_schema()
            app.state.auth_repo = auth_repo
            logger.info("Auth schema initialized")

            # Auto-create admin user on first boot
            if settings.admin_email and settings.admin_password:
                user_count = await auth_repo.count_users()
                if user_count == 0:
                    password_hash = AuthService.hash_password(settings.admin_password)
                    await auth_repo.create_user(
                        email=settings.admin_email,
                        full_name=settings.admin_name,
                        password_hash=password_hash,
                        role="admin",
                    )
                    logger.info(
                        "Admin user created: %s", settings.admin_email,
                    )
        else:
            app.state.auth_repo = auth_repo
            logger.warning("Auth: no DB pool — authentication disabled")
    except Exception as e:
        logger.warning("Auth initialization failed: %s", e)
        app.state.auth_repo = auth_repo

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

        # --- Observability Service (feat-010) ---
        observability.set_repository(app.state.workflow_repo)
        logger.info("Observability service initialized")

    # --- Durable Workflow Engine (feat-050/051) ---
    workflow_engine = None
    if workflow_repo._pool:
        try:
            from services.workflow_engine.definition_store import DefinitionStore

            workflow_engine = WorkflowEngine(
                pool=workflow_repo._pool,
                num_workers=jq_config.get("durable_workers", 2),
                queue_name="default",
            )
            await workflow_engine.start()
            app.state.workflow_engine = workflow_engine

            # Load canvas definitions for recovery
            def_store = DefinitionStore(workflow_repo._pool)
            definitions = await def_store.load_all()
            for defn in definitions.values():
                workflow_engine.scheduler.register_definition(defn)
            app.state.definition_store = def_store

            logger.info(
                "Durable workflow engine started (workers=%d, definitions=%d, durable_mode=%s)",
                workflow_engine._num_workers, len(definitions), settings.durable_mode,
            )
        except Exception as e:
            logger.warning("Durable workflow engine unavailable: %s", e)
            app.state.workflow_engine = None
            app.state.definition_store = None
    else:
        app.state.workflow_engine = None
        app.state.definition_store = None
        logger.info("Durable workflow engine skipped (no DB pool)")

    logger.info("Server ready to accept requests")
    logger.info("=" * 70)

    yield

    # --- Shutdown: stop durable workflow engine ---
    if app.state.workflow_engine:
        try:
            await app.state.workflow_engine.stop()
            logger.info("Durable workflow engine stopped")
        except Exception as e:
            logger.warning("Error stopping workflow engine: %s", e)

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
        await ocr_result_repo.close()
    except Exception as e:
        logger.warning("Error closing OCR results database: %s", e)

    try:
        await workflow_repo.close()
    except Exception as e:
        logger.warning("Error closing workflow database: %s", e)

    logger.info("=" * 70)
    logger.info("Shutting down Doc Intelligence")
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

    # --- CORS (Must be added last to run first and wrap all responses) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Public endpoints (no auth required) ---
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "OCR Web UI API",
            "version": "2.0.0",
            "description": "OCR processing API with multiple model support",
            "endpoints": {
                "health": "/health",
                "auth": "/auth/login (POST)",
                "docs": "/docs",
            },
        }

    @app.get("/health")
    async def public_health():
        """Public health check — no authentication required."""
        from core.dependencies import get_config
        from services import system_service
        config = get_config()
        health = system_service.get_health(config)
        # Add workflow engine status
        engine = getattr(app.state, "workflow_engine", None)
        health.workflow_engine = {
            "status": "running" if engine and engine.is_running else "unavailable",
        }
        return health

    # --- Routers ---
    app.include_router(auth_router)
    app.include_router(api_router)

    return app


# Module-level app instance for uvicorn / ASGI servers
app = create_app()
