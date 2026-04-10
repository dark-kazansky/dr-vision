"""
Test tier configuration with provider support.

Tests the enhanced tier config that supports both string and dict model specifications.
"""

import pytest
from config.tier_config import TierConfig, Tier


class TestTierProviderConfig:
    """Test tier configuration with provider support."""
    
    def test_string_model_spec(self):
        """Test simple string model specification."""
        # Dict format should work (now using dict specs)
        model_id = TierConfig.get_parser_model(Tier.RAPID)
        assert isinstance(model_id, str)
        assert model_id == "deepseek-ocr"
    
    def test_model_spec_with_provider(self):
        """Test model specification with provider."""
        # Get model spec (returns tuple)
        model_id, provider = TierConfig.get_parser_model_spec(Tier.RAPID)
        assert isinstance(model_id, str)
        assert model_id == "deepseek-ocr"
        # Provider should be specified for dict specs
        assert provider == "lmstudio"
    
    def test_all_tier_methods(self):
        """Test all tier getter methods."""
        tiers = [Tier.RAPID, Tier.NORMAL, Tier.ADVANCE]
        
        for tier in tiers:
            # Test legacy methods (return string)
            assert isinstance(TierConfig.get_parser_model(tier), str)
            assert isinstance(TierConfig.get_extractor_model(tier), str)
            assert isinstance(TierConfig.get_classifier_llm_model(tier), str)
            assert isinstance(TierConfig.get_splitter_model(tier), str)
            
            # Test new methods (return tuple)
            model_id, provider = TierConfig.get_parser_model_spec(tier)
            assert isinstance(model_id, str)
            assert provider is None or isinstance(provider, str)
    
    def test_export_to_json(self):
        """Test JSON export for frontend."""
        config = TierConfig.export_to_json()
        
        # Check structure
        assert "parser" in config
        assert "extractor" in config
        assert "classifier_llm" in config
        assert "splitter" in config
        assert "descriptions" in config
        assert "colors" in config
        assert "tiers" in config
        
        # Check that all values are strings (normalized for frontend)
        for key in ["parser", "extractor", "classifier_llm", "splitter"]:
            for tier, model in config[key].items():
                assert isinstance(model, str), f"{key}.{tier} should be string, got {type(model)}"
    
    def test_tier_descriptions(self):
        """Test tier descriptions."""
        for tier in [Tier.RAPID, Tier.NORMAL, Tier.ADVANCE, Tier.MULTIMODAL]:
            desc = TierConfig.get_tier_description(tier)
            assert isinstance(desc, str)
            assert len(desc) > 0
    
    def test_tier_colors(self):
        """Test tier colors."""
        for tier in [Tier.RAPID, Tier.NORMAL, Tier.ADVANCE, Tier.MULTIMODAL]:
            color = TierConfig.get_tier_color(tier)
            assert isinstance(color, str)
            assert color.startswith("#")
    
    def test_get_all_tiers(self):
        """Test getting all available tiers."""
        tiers = TierConfig.get_all_tiers()
        assert isinstance(tiers, list)
        assert len(tiers) == 4
        assert "Rapid" in tiers
        assert "Normal" in tiers
        assert "Advance" in tiers
        assert "Multimodal" in tiers
    
    def test_invalid_tier_fallback(self):
        """Test fallback for invalid tier."""
        # Should fall back to NORMAL tier
        model_id = TierConfig.get_parser_model("InvalidTier")
        normal_model = TierConfig.get_parser_model(Tier.NORMAL)
        assert model_id == normal_model


class TestModelSpecResolution:
    """Test model specification resolution."""
    
    def test_resolve_string_spec(self):
        """Test resolving string model spec."""
        model_id, provider = TierConfig._resolve_model_spec("gemini-3-pro")
        assert model_id == "gemini-3-pro"
        assert provider is None
    
    def test_resolve_dict_spec(self):
        """Test resolving dict model spec."""
        spec = {"model": "gemini-1.5-pro", "provider": "google"}
        model_id, provider = TierConfig._resolve_model_spec(spec)
        assert model_id == "gemini-1.5-pro"
        assert provider == "google"
    
    def test_resolve_dict_spec_without_provider(self):
        """Test resolving dict spec without provider."""
        spec = {"model": "gemini-1.5-pro"}
        model_id, provider = TierConfig._resolve_model_spec(spec)
        assert model_id == "gemini-1.5-pro"
        assert provider is None
    
    def test_resolve_invalid_spec(self):
        """Test resolving invalid spec."""
        model_id, provider = TierConfig._resolve_model_spec(123)  # Invalid type
        assert model_id == ""
        assert provider is None


class TestProviderExamples:
    """Test example configurations from documentation."""
    
    def test_google_studio_example(self):
        """Test Google Studio configuration example."""
        # Simulate config
        test_config = {
            Tier.RAPID: {"model": "gemini-1.5-flash", "provider": "google"},
            Tier.NORMAL: {"model": "gemini-1.5-pro", "provider": "google"},
        }
        
        for tier, spec in test_config.items():
            model_id, provider = TierConfig._resolve_model_spec(spec)
            assert provider == "google"
            assert "gemini" in model_id
    
    def test_mixed_provider_example(self):
        """Test mixed provider configuration."""
        test_config = {
            Tier.RAPID: "assistant",  # POE
            Tier.NORMAL: {"model": "gemini-1.5-flash", "provider": "google"},  # Google
            Tier.ADVANCE: "claude-opus-4.5",  # POE
        }
        
        # Rapid - POE (string)
        model_id, provider = TierConfig._resolve_model_spec(test_config[Tier.RAPID])
        assert model_id == "assistant"
        assert provider is None
        
        # Normal - Google (dict)
        model_id, provider = TierConfig._resolve_model_spec(test_config[Tier.NORMAL])
        assert model_id == "gemini-1.5-flash"
        assert provider == "google"
        
        # Advance - POE (string)
        model_id, provider = TierConfig._resolve_model_spec(test_config[Tier.ADVANCE])
        assert model_id == "claude-opus-4.5"
        assert provider is None
    
    def test_ollama_example(self):
        """Test Ollama configuration example."""
        spec = {"model": "llama3", "provider": "ollama"}
        model_id, provider = TierConfig._resolve_model_spec(spec)
        assert model_id == "llama3"
        assert provider == "ollama"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
