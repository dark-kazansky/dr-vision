"""Tests for FastAPI dependency injection functions (Task 9.1).

Validates Requirements 18.1, 18.2:
- Backend provides FastAPI dependency functions that create agent instances based on tier and configuration
- Route handlers receive agents via Depends() instead of creating them inline
"""

import pytest
import yaml
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from config.manager import Config
from core.dependencies import get_config, get_parser, get_classifier, get_extractor


SAMPLE_CONFIG = {
    "api_providers": {
        "google_studio": {"base_url": "https://generativelanguage.googleapis.com", "timeout": 60},
        "poe_api": {"base_url": "https://api.poe.com/v1", "timeout": 120},
        "lm_studio": {"base_url": "http://localhost:1234", "timeout": 30},
    },
    "models": {
        "gemini-2.5-flash": {
            "model_id": "gemini-2.5-flash",
            "provider": "google_studio",
            "name": "Gemini 2.5 Flash",
            "base_url": "https://generativelanguage.googleapis.com",
            "max_tokens": 4096,
            "temperature": 0.2,
            "top_p": 0.9,
        },
        "gemini-2.5-flash-lite": {
            "model_id": "gemini-2.5-flash-lite",
            "provider": "google_studio",
            "name": "Gemini 2.5 Flash Lite",
            "base_url": "https://generativelanguage.googleapis.com",
            "max_tokens": 4096,
            "temperature": 0.2,
            "top_p": 0.9,
        },
        "gemini-3-pro-preview": {
            "model_id": "gemini-3-pro-preview",
            "provider": "google_studio",
            "name": "Gemini 3 Pro Preview",
            "base_url": "https://generativelanguage.googleapis.com",
            "max_tokens": 4096,
            "temperature": 0.2,
            "top_p": 0.9,
        },
    },
    "fastapi": {"host": "0.0.0.0", "port": 8000, "debug": False},
    "upload": {
        "folder": "uploads",
        "max_size_mb": 10,
        "allowed_extensions": [".pdf", ".png"],
    },
}


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the Config singleton before each test."""
    Config._instance = None
    yield
    Config._instance = None


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary YAML config file."""
    path = tmp_path / "settings.yaml"
    path.write_text(yaml.dump(SAMPLE_CONFIG))
    return str(path)


@pytest.fixture
def config(config_file):
    """Load a Config instance from the sample config."""
    return Config.load(config_path=config_file)


class TestGetConfig:
    """Test the get_config dependency function."""

    def test_returns_config_instance(self, config_file):
        """get_config returns a valid Config instance."""
        # Pre-load so the singleton is available
        Config.load(config_path=config_file)
        result = get_config()
        assert isinstance(result, Config)

    def test_raises_http_exception_on_config_error(self):
        """get_config raises HTTPException(500) when config cannot be loaded."""
        with patch("core.dependencies.Config.load", side_effect=Exception("bad config")):
            # ConfigurationError is what we catch; simulate it
            from config.manager import ConfigurationError
            with patch("core.dependencies.Config.load", side_effect=ConfigurationError("bad")):
                with pytest.raises(HTTPException) as exc_info:
                    get_config()
                assert exc_info.value.status_code == 500


class TestGetParser:
    """Requirement 18.1: Dependency functions create agent instances based on tier."""

    @patch("core.dependencies.AgentFactory.create_from_config")
    def test_returns_parser_instance(self, mock_create, config):
        """get_parser returns a Parser instance."""
        mock_create.return_value = MagicMock()
        parser = get_parser(config=config, tier="Normal")

        from functions.parser import Parser
        assert isinstance(parser, Parser)

    @patch("core.dependencies.AgentFactory.create_from_config")
    def test_uses_tier_config_for_model(self, mock_create, config):
        """get_parser resolves the model from TierConfig based on tier."""
        mock_create.return_value = MagicMock()
        get_parser(config=config, tier="Rapid")

        # Verify create_from_config was called (model resolved from tier)
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[0][0] is config  # first arg is config

    @patch("core.dependencies.AgentFactory.create_from_config")
    def test_different_tiers_resolve_different_models(self, mock_create, config):
        """Different tiers should resolve to different model IDs."""
        mock_create.return_value = MagicMock()

        get_parser(config=config, tier="Rapid")
        rapid_model = mock_create.call_args[0][1]

        mock_create.reset_mock()
        get_parser(config=config, tier="Normal")
        normal_model = mock_create.call_args[0][1]

        # Rapid and Normal should use different models per tier config
        assert rapid_model != normal_model


class TestGetClassifier:
    """Requirement 18.1: Dependency functions create classifier instances."""

    @patch("core.dependencies.AgentFactory.create_llm_agent")
    def test_returns_classifier_instance(self, mock_create, config):
        """get_classifier returns a Classifier instance."""
        mock_create.return_value = MagicMock()
        classifier = get_classifier(config=config, tier="Normal")

        from functions.classifier import Classifier
        assert isinstance(classifier, Classifier)

    @patch("core.dependencies.AgentFactory.create_llm_agent")
    def test_passes_config_for_provider_resolution(self, mock_create, config):
        """get_classifier passes config to AgentFactory for provider resolution."""
        mock_create.return_value = MagicMock()
        get_classifier(config=config, tier="Normal")

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs.get("config") is config


class TestGetExtractor:
    """Requirement 18.1: Dependency functions create extractor instances."""

    @patch("core.dependencies.AgentFactory.create_llm_agent")
    def test_returns_extractor_instance(self, mock_create, config):
        """get_extractor returns an Extractor instance."""
        mock_create.return_value = MagicMock()
        extractor = get_extractor(config=config, tier="Normal")

        from functions.extractor import Extractor
        assert isinstance(extractor, Extractor)

    @patch("core.dependencies.AgentFactory.create_llm_agent")
    def test_passes_config_for_provider_resolution(self, mock_create, config):
        """get_extractor passes config to AgentFactory for provider resolution."""
        mock_create.return_value = MagicMock()
        get_extractor(config=config, tier="Normal")

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs.get("config") is config

    @patch("core.dependencies.AgentFactory.create_llm_agent")
    def test_uses_extractor_tier_config(self, mock_create, config):
        """get_extractor resolves model from extractor tier config."""
        mock_create.return_value = MagicMock()
        get_extractor(config=config, tier="Rapid")

        call_args = mock_create.call_args
        # Model ID should come from TierConfig extractor mapping
        model_id = call_args[0][0]
        assert model_id  # Should be a non-empty string
