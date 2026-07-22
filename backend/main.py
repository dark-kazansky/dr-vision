"""
FastAPI application entry point for OCR Web UI.

This module initializes the FastAPI application, loads configuration,
registers routes, configures CORS, and starts the server.

Requirements: 1.4, 3.1, 7.1, 7.2, 7.3, 9.1, 9.3, 9.5
"""

from pathlib import Path
from dotenv import load_dotenv

# --- Environment variable loading (single, documented sequence) ---
# Load order:
#   1. Backend .env first — contains backend-specific variables (e.g., POE_API_KEY)
#   2. Root .env second — provides additional variables (e.g., GOOGLE_STUDIO_API_KEY)
#      Using override=False so backend .env values take precedence if duplicated.
load_dotenv()  # loads backend/.env (cwd-relative)
root_env_path = Path(__file__).parent.parent / '.env'
if root_env_path.exists():
    load_dotenv(root_env_path, override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)

from routes import router
from routes_workflows import router as workflows_router, runs_router as workflow_runs_router
from core import Config, ConfigurationError
from core.middleware import RequestLoggingMiddleware
from core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.
    
    Handles:
    - Configuration loading and validation on startup
    - Cleanup on shutdown
    """
    # Startup
    logger.info("=" * 70)
    logger.info("OCR Web UI - FastAPI Backend")
    logger.info("=" * 70)
    
    try:
        # Load and validate configuration
        config = Config.load()
        errors = config.validate()
        
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error("  - %s", error)
            logger.error("=" * 70)
            raise RuntimeError(f"Configuration errors: {errors}")
        
        logger.info("Configuration loaded and validated successfully")
        
        # Display configuration summary
        logger.info("Available Models: %s", ", ".join(config.get_available_models()))
        logger.info("Default Model: %s", config.default_model)
        
        fastapi_config = config.fastapi_config
        logger.info("Server: %s:%s", fastapi_config.get('host'), fastapi_config.get('port'))
        logger.info("Debug Mode: %s", fastapi_config.get('debug', False))
        
        logger.info("=" * 70)
        logger.info("Server ready to accept requests")
        logger.info("=" * 70)
        
    except ConfigurationError as e:
        logger.error("Configuration error: %s", e)
        logger.error("=" * 70)
        raise RuntimeError(f"Failed to load configuration: {e}")
    
    yield
    
    # Shutdown
    logger.info("=" * 70)
    logger.info("Shutting down OCR Web UI")
    logger.info("=" * 70)


# Create FastAPI application
app = FastAPI(
    title="OCR Web UI API",
    description="OCR processing API with multiple model support",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS middleware
# Load configuration to get CORS origins
try:
    config = Config.load()
    cors_origins = config.fastapi_config.get('cors_origins', ["*"])
except Exception:
    # Fallback to restrictive CORS if config fails (localhost only)
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

# Register request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Register rate limiting middleware
try:
    _rl_config = Config.load()._config_data.get("rate_limit", {})
    app.add_middleware(
        RateLimiter,
        enabled=_rl_config.get("enabled", True),
        requests_per_minute=_rl_config.get("requests_per_minute", 30),
        burst_size=_rl_config.get("burst_size", 10),
    )
except Exception:
    logging.warning("Failed to load rate_limit config; rate limiter disabled.")

# Register routes
app.include_router(router)
app.include_router(workflows_router)
app.include_router(workflow_runs_router)


# Root endpoint
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
            "docs": "/docs"
        }
    }


# Run with uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn
    
    # Load configuration for server settings
    try:
        config = Config.load()
        fastapi_config = config.fastapi_config
        
        host = fastapi_config.get('host', '0.0.0.0')
        port = fastapi_config.get('port', 8000)
        debug = fastapi_config.get('debug', False)
        
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=debug
        )
    except Exception as e:
        logger.error("Failed to start server: %s", e)
        sys.exit(1)
