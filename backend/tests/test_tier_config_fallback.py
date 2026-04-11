"""Tests for tier config model reference validation and fallback logic."""

import logging
from unittest.mock import patch, MagicMock

from config.tier_config import TierConfig, Tier


class TestMultimodalModelReference:
    """Verify the Multimodal tier references a valid model ID."""

    def test_multimodal_classifier_model_is_valid(self):
        """The Multimodal classifier tier should reference claude-sonnet."""
        model_spec = TierConfig.CLASSIFIER_LLM_TIER_TO_MODEL[Tier.MULTIMODAL]
        model_id, _ = TierConfig._resolve_model_spec(model_spec)
        assert model_id == "claude-sonnet"


class TestTierFallbackLogic:
    """Verify fallback to Normal tier when a model doesn't exist in config."""

    def _mock_config(self, available_models):
        """Create a mock Config with the given available models."""
        mock_config = MagicMock()
        mock_config.get_available_models.return_value = available_models
        return mock_config

    @patch("backend.config.manager.Config.load")
    def test_fallback_on_invalid_model(self, mock_load, caplog):
        """When a tier references a non-existent model, fall back to Normal and log a warning."""
        mock_load.return_value = self._mock_config(["gemini-2.5-flash"])

        # Create a tier map where ADVANCE references a non-existent model
        tier_map = {
            Tier.NORMAL: {"model": "gemini-2.5-flash", "provider": "google"},
            Tier.ADVANCE: {"model": "nonexistent-model", "provider": "google"},
        }

        with caplog.at_level(logging.WARNING):
            result = TierConfig._get_model_spec_with_fallback(tier_map, Tier.ADVANCE, "test")

        model_id, _ = TierConfig._resolve_model_spec(result)
        assert model_id == "gemini-2.5-flash"
        assert "non-existent model" in caplog.text
        assert "nonexistent-model" in caplog.text

    @patch("backend.config.manager.Config.load")
    def test_no_fallback_on_valid_model(self, mock_load, caplog):
        """When a tier references a valid model, return it without fallback."""
        mock_load.return_value = self._mock_config(["gemini-2.5-flash", "gemini-3-pro-preview"])

        tier_map = {
            Tier.NORMAL: {"model": "gemini-2.5-flash", "provider": "google"},
            Tier.ADVANCE: {"model": "gemini-3-pro-preview", "provider": "google"},
        }

        with caplog.at_level(logging.WARNING):
            result = TierConfig._get_model_spec_with_fallback(tier_map, Tier.ADVANCE, "test")

        model_id, _ = TierConfig._resolve_model_spec(result)
        assert model_id == "gemini-3-pro-preview"
        assert caplog.text == ""

    @patch("backend.config.manager.Config.load", side_effect=Exception("Config not loaded"))
    def test_graceful_when_config_unavailable(self, mock_load):
        """When Config.load() fails, return the original spec without crashing."""
        tier_map = {
            Tier.NORMAL: {"model": "gemini-2.5-flash", "provider": "google"},
            Tier.ADVANCE: {"model": "some-model", "provider": "google"},
        }

        result = TierConfig._get_model_spec_with_fallback(tier_map, Tier.ADVANCE, "test")
        model_id, _ = TierConfig._resolve_model_spec(result)
        assert model_id == "some-model"
