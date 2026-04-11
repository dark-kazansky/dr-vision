"""Tests for config-based model resolution in Agent Factory (Task 5.3).

Validates Requirements 10.1, 10.2, 10.3:
- create_llm_agent looks up provider from config when no explicit provider given
- Raises ValueError with available models when model ID not found in config
- Accepts optional config parameter for provider resolution
"""

import pytest
import yaml
from unittest.mock import patch, MagicMock
from config.manager import Config


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
        },
        "assistant": {
            "model_id": "assistant",
            "provider": "poe_api",
            "name": "POE Assistant",
        },
        "deepseek-ocr": {
            "model_id": "deepseek-ocr",
            "provider": "lm_studio",
            "name": "DeepSeek OCR",
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


class TestConfigBasedProviderResolution:
    """Requirement 10.1: Look up provider from config when no explicit provider."""

    @patch("core.agent_factory.GoogleLLMAgent")
    def test_resolves_google_provider_from_config(self, mock_cls, config):
        from core.agent_factory import AgentFactory

        mock_cls.return_value = MagicMock()
        agent = AgentFactory.create_llm_agent("gemini-2.5-flash", config=config)
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args
        assert call_kwargs[1]["model_id"] == "gemini-2.5-flash"

    @patch("core.agent_factory.POELLMAgent")
    def test_resolves_poe_provider_from_config(self, mock_cls, config):
        from core.agent_factory import AgentFactory

        mock_cls.return_value = MagicMock()
        agent = AgentFactory.create_llm_agent("assistant", config=config)
        mock_cls.assert_called_once()
        assert mock_cls.call_args[1]["model_id"] == "assistant"

    @patch("core.agent_factory.LMStudioLLMAgent")
    def test_resolves_lmstudio_provider_from_config(self, mock_cls, config):
        from core.agent_factory import AgentFactory

        mock_cls.return_value = MagicMock()
        agent = AgentFactory.create_llm_agent("deepseek-ocr", config=config)
        mock_cls.assert_called_once()
        assert mock_cls.call_args[1]["model_id"] == "deepseek-ocr"


class TestModelNotFoundError:
    """Requirement 10.2: Raise ValueError when model not in config."""

    def test_raises_value_error_for_unknown_model(self, config):
        from core.agent_factory import AgentFactory

        with pytest.raises(ValueError) as exc_info:
            AgentFactory.create_llm_agent("nonexistent-model", config=config)

        error_msg = str(exc_info.value)
        assert "nonexistent-model" in error_msg
        assert "not found in configuration" in error_msg

    def test_error_lists_available_models(self, config):
        from core.agent_factory import AgentFactory

        with pytest.raises(ValueError) as exc_info:
            AgentFactory.create_llm_agent("nonexistent-model", config=config)

        error_msg = str(exc_info.value)
        assert "gemini-2.5-flash" in error_msg
        assert "assistant" in error_msg
        assert "deepseek-ocr" in error_msg


class TestConfigParameterAcceptance:
    """Requirement 10.3: Accepts optional config parameter."""

    @patch("core.agent_factory.POELLMAgent")
    def test_explicit_provider_overrides_config(self, mock_cls, config):
        """When provider is explicitly given, config lookup is skipped."""
        from core.agent_factory import AgentFactory

        mock_cls.return_value = MagicMock()
        agent = AgentFactory.create_llm_agent(
            "gemini-2.5-flash", provider="poe", config=config
        )
        # Should use POE even though config says google_studio
        mock_cls.assert_called_once()

    @patch("core.agent_factory.POELLMAgent")
    def test_legacy_fallback_when_no_config(self, mock_cls):
        """When config is None, falls back to hardcoded auto-detect."""
        from core.agent_factory import AgentFactory

        mock_cls.return_value = MagicMock()
        agent = AgentFactory.create_llm_agent("assistant")
        # 'assistant' is in the hardcoded poe list
        mock_cls.assert_called_once()

    @patch("core.agent_factory.LMStudioLLMAgent")
    def test_legacy_fallback_default_lmstudio(self, mock_cls):
        """Unknown model with no config defaults to lmstudio (legacy)."""
        from core.agent_factory import AgentFactory

        mock_cls.return_value = MagicMock()
        agent = AgentFactory.create_llm_agent("some-unknown-model")
        mock_cls.assert_called_once()
