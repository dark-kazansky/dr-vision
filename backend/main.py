"""
FastAPI application entry point for OCR Web UI.

This module initializes the FastAPI application, loads configuration,
registers routes, configures CORS, and starts the server.

Requirements: 1.4, 3.1, 7.1, 7.2, 7.3, 9.1, 9.3, 9.5
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.routes import router
from src.config import Config, ConfigurationError


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
    print("=" * 70)
    print("OCR Web UI - FastAPI Backend")
    print("=" * 70)
    
    try:
        # Load and validate configuration
        config = Config.load()
        errors = config.validate()
        
        if errors:
            print("\n❌ Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            print("\n" + "=" * 70)
            raise RuntimeError(f"Configuration errors: {errors}")
        
        print("\n✅ Configuration loaded and validated successfully")
        
        # Display configuration summary
        print(f"\nAvailable Models: {', '.join(config.get_available_models())}")
        print(f"Default Model: {config.default_model}")
        
        fastapi_config = config.fastapi_config
        print(f"Server: {fastapi_config.get('host')}:{fastapi_config.get('port')}")
        print(f"Debug Mode: {fastapi_config.get('debug', False)}")
        
        print("\n" + "=" * 70)
        print("✅ Server ready to accept requests")
        print("=" * 70 + "\n")
        
    except ConfigurationError as e:
        print(f"\n❌ Configuration error: {e}")
        print("=" * 70 + "\n")
        raise RuntimeError(f"Failed to load configuration: {e}")
    
    yield
    
    # Shutdown
    print("\n" + "=" * 70)
    print("Shutting down OCR Web UI")
    print("=" * 70 + "\n")


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
    # Fallback to permissive CORS if config fails
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)


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
        print(f"Failed to start server: {e}")
        sys.exit(1)
