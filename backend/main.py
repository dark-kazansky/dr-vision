"""
FastAPI application entry point for Dr.Vision.

This module is the ASGI entry point used by uvicorn. All application
setup (middleware, routers, exception handlers, lifespan) lives in server.py.

This file only handles:
  1. Environment variable loading (.env files)
  2. Logging configuration
  3. Importing the ``app`` object from ``server.py``
  4. Running uvicorn when executed directly
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# --- Environment variable loading (single, documented sequence) ---
# Load order:
#   1. Backend .env first — contains backend-specific variables (e.g., POE_API_KEY)
#   2. Root .env second — provides additional variables (e.g., GOOGLE_STUDIO_API_KEY)
#      Using override=False so backend .env values take precedence if duplicated.
load_dotenv()  # loads backend/.env (cwd-relative)
root_env_path = Path(__file__).parent.parent / ".env"
if root_env_path.exists():
    load_dotenv(root_env_path, override=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)

# Import the app object created by the application factory.
# All middleware, routers, and exception handlers are registered in server.py.
from server import app  # noqa: E402  (import after env setup is intentional)

logger = logging.getLogger(__name__)

# Run with uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn
    from settings import settings

    try:
        uvicorn.run(
            "main:app",
            host=settings.fastapi_host,
            port=settings.fastapi_port,
            reload=settings.fastapi_debug,
        )
    except Exception as e:
        logger.error("Failed to start server: %s", e)
        sys.exit(1)
