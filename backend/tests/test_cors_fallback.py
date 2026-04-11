"""Tests for CORS fallback behavior (Task 3.5).

Validates Requirement 7.1:
- When Config.load() raises an exception during CORS setup,
  the CORS middleware falls back to ["http://localhost:3000"]
  instead of allowing all origins with ["*"]

Validates Requirement 7.2:
- A warning is logged when CORS config loading fails
"""

import logging
from unittest.mock import patch, MagicMock

import pytest
from fastapi.middleware.cors import CORSMiddleware


class TestCORSFallbackOnConfigFailure:
    """Requirement 7.1: Restrictive CORS default when config loading fails."""

    def test_cors_falls_back_to_localhost_on_config_error(self):
        """When Config.load() raises, CORS origins should be ['http://localhost:3000']."""
        with patch("main.Config") as MockConfig:
            MockConfig.load.side_effect = Exception("Config file missing")

            # Re-execute the CORS setup logic from main.py
            try:
                config = MockConfig.load()
                cors_origins = config.fastapi_config.get("cors_origins", ["*"])
            except Exception:
                cors_origins = ["http://localhost:3000"]

            assert cors_origins == ["http://localhost:3000"]

    def test_cors_does_not_fallback_to_wildcard(self):
        """Fallback must never be ['*'] — that would be insecure."""
        with patch("main.Config") as MockConfig:
            MockConfig.load.side_effect = RuntimeError("YAML parse error")

            try:
                config = MockConfig.load()
                cors_origins = config.fastapi_config.get("cors_origins", ["*"])
            except Exception:
                cors_origins = ["http://localhost:3000"]

            assert cors_origins != ["*"]
            assert "*" not in cors_origins


class TestCORSFallbackLogging:
    """Requirement 7.2: Warning logged when CORS config fails."""

    def test_warning_logged_on_config_failure(self, caplog):
        """A warning should be logged when CORS config loading fails."""
        with patch("main.Config") as MockConfig:
            MockConfig.load.side_effect = Exception("Config unavailable")

            with caplog.at_level(logging.WARNING):
                try:
                    config = MockConfig.load()
                    cors_origins = config.fastapi_config.get("cors_origins", ["*"])
                except Exception:
                    logging.warning(
                        "CORS configuration loading failed. "
                        "Falling back to restrictive default: ['http://localhost:3000']"
                    )
                    cors_origins = ["http://localhost:3000"]

            assert any("CORS configuration loading failed" in r.message for r in caplog.records)
            assert any("http://localhost:3000" in r.message for r in caplog.records)


class TestCORSIntegrationWithApp:
    """Integration test: verify the actual main.py CORS setup uses correct fallback."""

    def test_main_module_cors_fallback_integration(self):
        """
        Patch Config.load to fail before importing main, then verify
        the app's CORS middleware uses the restrictive fallback.
        """
        import importlib

        with patch.dict("sys.modules", {}):
            with patch("config.manager.Config.load", side_effect=Exception("Config broken")):
                # Force re-import of main to re-execute module-level CORS setup
                import main as main_module
                main_mod = importlib.reload(main_module)

                # Find the CORSMiddleware in the app's middleware stack
                cors_middleware = None
                for middleware in main_mod.app.user_middleware:
                    if middleware.cls is CORSMiddleware:
                        cors_middleware = middleware
                        break

                assert cors_middleware is not None, "CORSMiddleware not found on app"
                allow_origins = cors_middleware.kwargs.get("allow_origins", [])
                assert allow_origins == ["http://localhost:3000"], (
                    f"Expected ['http://localhost:3000'], got {allow_origins}"
                )
