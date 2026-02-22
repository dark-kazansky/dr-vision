"""
Tier configuration for Dr.Vision.

This module provides centralized tier-to-model mappings for different features.
Modify this file to change which models are used for each tier.

Available Models (from settings.yaml):
- assistant: POE Assistant (Fast, free tier)
- gemini-3-flash: Gemini 3 Flash (Balanced)
- gemini-3-pro: Gemini 3 Pro (High quality)
- qwen3-max: Qwen3 Max (Strong reasoning)
- claude-opus-4.5: Claude Opus 4.5 (Premium)

Google Studio Models (direct Gemini API):
- gemini-1.5-flash: Gemini 1.5 Flash (Fast, cost-effective)
- gemini-1.5-pro: Gemini 1.5 Pro (High quality)
- gemini-2.0-flash-exp: Gemini 2.0 Flash Experimental

Model Configuration Format:
- Simple string: "model_id" - Uses model from settings.yaml or auto-detects provider
- Dict with provider: {"model": "model_id", "provider": "google"} - Explicit provider
"""

from typing import Dict, List, Union
from enum import Enum


# Type alias for model configuration
ModelSpec = Union[str, Dict[str, str]]


class Tier(str, Enum):
    """Available processing tiers."""
    RAPID = "Rapid"
    NORMAL = "Normal"
    ADVANCE = "Advance"
    MULTIMODAL = "Multimodal"


class TierConfig:
    """
    Centralized tier-to-model mapping configuration.
    
    Modify the mappings below to change which models are used for each tier.
    
    Model Specification Formats:
    1. Simple string: "model_id" - Uses model from settings.yaml or auto-detects provider
    2. Dict with provider: {"model": "model_id", "provider": "google"} - Explicit provider
    
    Examples:
        "gemini-3-pro"  # Uses POE (from settings.yaml)
        {"model": "gemini-1.5-pro", "provider": "google"}  # Uses Google Studio API
        {"model": "llama3", "provider": "ollama"}  # Uses Ollama
    """
    
    # =============================================================================
    # PARSER (OCR) TIER MAPPINGS
    # =============================================================================
    # Used for: Document parsing and OCR
    # Priority: Speed and accuracy balance
    
    PARSER_TIER_TO_MODEL: Dict[str, ModelSpec] = {
        Tier.RAPID: {"model": "deepseek-ocr", "provider": "lmstudio"},                   
        Tier.NORMAL: {"model": "gemini-2.5-flash-image", "provider": "google"},            
        Tier.ADVANCE: {"model": "gemini-3-pro-image-preview", "provider": "google"},       
        # Note: Google models use VLM agents for OCR (vision-based text extraction)
        # LM Studio uses dedicated OCR models
    }
    
    # =============================================================================
    # EXTRACTOR TIER MAPPINGS
    # =============================================================================
    # Used for: Structured data extraction
    # Priority: Accuracy and reasoning
    
    EXTRACTOR_TIER_TO_MODEL: Dict[str, ModelSpec] = {
        Tier.RAPID: {"model": "gemini-2.5-flash-lite", "provider": "google"}, 
        Tier.NORMAL: {"model": "gemini-2.5-flash", "provider": "google"},     
        Tier.ADVANCE: {"model": "gemini-3-pro-preview", "provider": "google"},
        # Example with Google Studio:
        # Tier.ADVANCE: {"model": "gemini-1.5-pro", "provider": "google"},
    }
    
    # =============================================================================
    # CLASSIFIER LLM TIER MAPPINGS
    # =============================================================================
    # Used for: Classification step (determining document type)
    # Priority: Classification accuracy
    
    CLASSIFIER_LLM_TIER_TO_MODEL: Dict[str, ModelSpec] = {
        Tier.RAPID: {"model": "gemini-2.5-flash-lite", "provider": "google"},    
        Tier.NORMAL: {"model": "gemini-2.5-flash", "provider": "google"},        
        Tier.ADVANCE: {"model": "gemini-3-pro-preview", "provider": "google"},   
        Tier.MULTIMODAL: {"model": "gemini-3.1-pro-preview", "provider": "google"}, 
    }
    
    # =============================================================================
    # SPLITTER TIER MAPPINGS
    # =============================================================================
    # Used for: Document splitting and categorization
    # Priority: Vision and understanding
    
    SPLITTER_TIER_TO_MODEL: Dict[str, ModelSpec] = {
        Tier.RAPID: {"model": "gemini-2.5-flash-lite", "provider": "google"},    
        Tier.NORMAL: {"model": "gemini-2.5-flash", "provider": "google"},        
        Tier.ADVANCE: {"model": "gemini-3-pro-preview", "provider": "google"},   
    }
    
    # =============================================================================
    # TIER METADATA
    # =============================================================================
    # Descriptions and characteristics of each tier
    
    TIER_DESCRIPTIONS: Dict[str, str] = {
        Tier.RAPID: "Fast processing with good accuracy. Uses free/cheaper models.",
        Tier.NORMAL: "Balanced speed and quality. Recommended for most use cases.",
        Tier.ADVANCE: "Highest quality processing. Uses premium models for best results.",
        Tier.MULTIMODAL: "Direct vision processing without OCR. Best for complex layouts.",
    }
    
    TIER_COLORS: Dict[str, str] = {
        Tier.RAPID: "#FFB399",      # Light orange
        Tier.NORMAL: "#FF8C5A",     # Medium orange
        Tier.ADVANCE: "#FF6F3C",    # Dark orange
        Tier.MULTIMODAL: "#E55A2B", # Darker orange
    }
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    @classmethod
    def _resolve_model_spec(cls, model_spec: ModelSpec) -> tuple[str, str | None]:
        """
        Resolve model specification to (model_id, provider).
        
        Args:
            model_spec: Either a string model_id or dict with model and provider
            
        Returns:
            Tuple of (model_id, provider) where provider may be None for auto-detection
        """
        if isinstance(model_spec, str):
            return (model_spec, None)
        elif isinstance(model_spec, dict):
            return (model_spec.get("model", ""), model_spec.get("provider"))
        else:
            return ("", None)
    
    @classmethod
    def get_parser_model(cls, tier: str) -> str:
        """
        Get parser model for a tier.
        
        Returns:
            Model ID string (for backward compatibility)
        """
        model_spec = cls.PARSER_TIER_TO_MODEL.get(tier, cls.PARSER_TIER_TO_MODEL[Tier.NORMAL])
        model_id, _ = cls._resolve_model_spec(model_spec)
        return model_id
    
    @classmethod
    def get_parser_model_spec(cls, tier: str) -> tuple[str, str | None]:
        """
        Get parser model specification for a tier.
        
        Returns:
            Tuple of (model_id, provider) where provider may be None
        """
        model_spec = cls.PARSER_TIER_TO_MODEL.get(tier, cls.PARSER_TIER_TO_MODEL[Tier.NORMAL])
        return cls._resolve_model_spec(model_spec)
    
    @classmethod
    def get_extractor_model(cls, tier: str) -> str:
        """
        Get extractor model for a tier.
        
        Returns:
            Model ID string (for backward compatibility)
        """
        model_spec = cls.EXTRACTOR_TIER_TO_MODEL.get(tier, cls.EXTRACTOR_TIER_TO_MODEL[Tier.NORMAL])
        model_id, _ = cls._resolve_model_spec(model_spec)
        return model_id
    
    @classmethod
    def get_extractor_model_spec(cls, tier: str) -> tuple[str, str | None]:
        """
        Get extractor model specification for a tier.
        
        Returns:
            Tuple of (model_id, provider) where provider may be None
        """
        model_spec = cls.EXTRACTOR_TIER_TO_MODEL.get(tier, cls.EXTRACTOR_TIER_TO_MODEL[Tier.NORMAL])
        return cls._resolve_model_spec(model_spec)
    
    @classmethod
    def get_classifier_llm_model(cls, tier: str) -> str:
        """
        Get classifier LLM model for a tier.
        
        Returns:
            Model ID string (for backward compatibility)
        """
        model_spec = cls.CLASSIFIER_LLM_TIER_TO_MODEL.get(tier, cls.CLASSIFIER_LLM_TIER_TO_MODEL[Tier.NORMAL])
        model_id, _ = cls._resolve_model_spec(model_spec)
        return model_id
    
    @classmethod
    def get_classifier_llm_model_spec(cls, tier: str) -> tuple[str, str | None]:
        """
        Get classifier LLM model specification for a tier.
        
        Returns:
            Tuple of (model_id, provider) where provider may be None
        """
        model_spec = cls.CLASSIFIER_LLM_TIER_TO_MODEL.get(tier, cls.CLASSIFIER_LLM_TIER_TO_MODEL[Tier.NORMAL])
        return cls._resolve_model_spec(model_spec)
    
    @classmethod
    def get_splitter_model(cls, tier: str) -> str:
        """
        Get splitter model for a tier.
        
        Returns:
            Model ID string (for backward compatibility)
        """
        model_spec = cls.SPLITTER_TIER_TO_MODEL.get(tier, cls.SPLITTER_TIER_TO_MODEL[Tier.NORMAL])
        model_id, _ = cls._resolve_model_spec(model_spec)
        return model_id
    
    @classmethod
    def get_splitter_model_spec(cls, tier: str) -> tuple[str, str | None]:
        """
        Get splitter model specification for a tier.
        
        Returns:
            Tuple of (model_id, provider) where provider may be None
        """
        model_spec = cls.SPLITTER_TIER_TO_MODEL.get(tier, cls.SPLITTER_TIER_TO_MODEL[Tier.NORMAL])
        return cls._resolve_model_spec(model_spec)
    
    @classmethod
    def get_all_tiers(cls) -> List[str]:
        """Get list of all available tiers."""
        return [tier.value for tier in Tier]
    
    @classmethod
    def get_tier_description(cls, tier: str) -> str:
        """Get description for a tier."""
        return cls.TIER_DESCRIPTIONS.get(tier, "")
    
    @classmethod
    def get_tier_color(cls, tier: str) -> str:
        """Get color for a tier."""
        return cls.TIER_COLORS.get(tier, "#FF8C5A")
    
    @classmethod
    def export_to_json(cls) -> dict:
        """
        Export tier configuration as JSON for frontend.
        
        Converts ModelSpec (string or dict) to simple string format for frontend compatibility.
        
        Returns:
            Dictionary with all tier mappings
        """
        def normalize_model_spec(spec: ModelSpec) -> str:
            """Convert ModelSpec to string for frontend."""
            if isinstance(spec, str):
                return spec
            elif isinstance(spec, dict):
                return spec.get("model", "")
            return ""
        
        return {
            "parser": {k: normalize_model_spec(v) for k, v in cls.PARSER_TIER_TO_MODEL.items()},
            "extractor": {k: normalize_model_spec(v) for k, v in cls.EXTRACTOR_TIER_TO_MODEL.items()},
            "classifier_llm": {k: normalize_model_spec(v) for k, v in cls.CLASSIFIER_LLM_TIER_TO_MODEL.items()},
            "splitter": {k: normalize_model_spec(v) for k, v in cls.SPLITTER_TIER_TO_MODEL.items()},
            "descriptions": cls.TIER_DESCRIPTIONS,
            "colors": cls.TIER_COLORS,
            "tiers": cls.get_all_tiers(),
        }


# =============================================================================
# QUICK MODIFICATION EXAMPLES
# =============================================================================

"""
Example 1: Use Google Studio models with explicit provider
-----------------------------------------------------------
PARSER_TIER_TO_MODEL = {
    Tier.RAPID: {"model": "gemini-1.5-flash", "provider": "google"},
    Tier.NORMAL: {"model": "gemini-1.5-pro", "provider": "google"},
    Tier.ADVANCE: "claude-opus-4.5",  # Still use POE for advance
}

Example 2: Mix POE and Google Studio models
--------------------------------------------
EXTRACTOR_TIER_TO_MODEL = {
    Tier.RAPID: "assistant",  # POE (from settings.yaml)
    Tier.NORMAL: {"model": "gemini-1.5-flash", "provider": "google"},  # Google Studio
    Tier.ADVANCE: "gemini-3-pro",  # POE (from settings.yaml)
}

Example 3: Use Ollama for local processing
-------------------------------------------
PARSER_TIER_TO_MODEL = {
    Tier.RAPID: {"model": "llama3", "provider": "ollama"},
    Tier.NORMAL: {"model": "llama3:70b", "provider": "ollama"},
    Tier.ADVANCE: "gemini-3-pro",  # Fall back to POE for best quality
}

Example 4: Use LM Studio for local models
------------------------------------------
EXTRACTOR_TIER_TO_MODEL = {
    Tier.RAPID: {"model": "local-model", "provider": "lmstudio"},
    Tier.NORMAL: {"model": "local-model", "provider": "lmstudio"},
    Tier.ADVANCE: {"model": "gemini-1.5-pro", "provider": "google"},
}

Example 5: Use same model for all tiers (testing)
--------------------------------------------------
PARSER_TIER_TO_MODEL = {
    Tier.RAPID: {"model": "gemini-1.5-pro", "provider": "google"},
    Tier.NORMAL: {"model": "gemini-1.5-pro", "provider": "google"},
    Tier.ADVANCE: {"model": "gemini-1.5-pro", "provider": "google"},
}

Example 6: Optimize for cost with Google Studio
------------------------------------------------
EXTRACTOR_TIER_TO_MODEL = {
    Tier.RAPID: "assistant",  # Free POE
    Tier.NORMAL: {"model": "gemini-1.5-flash", "provider": "google"},  # Cheaper Google
    Tier.ADVANCE: {"model": "gemini-1.5-pro", "provider": "google"},  # Better Google
}

Example 7: Add new tier with provider specification
----------------------------------------------------
class Tier(str, Enum):
    RAPID = "Rapid"
    NORMAL = "Normal"
    ADVANCE = "Advance"
    ULTRA = "Ultra"  # New tier

PARSER_TIER_TO_MODEL = {
    Tier.RAPID: "assistant",
    Tier.NORMAL: {"model": "gemini-1.5-flash", "provider": "google"},
    Tier.ADVANCE: {"model": "gemini-1.5-pro", "provider": "google"},
    Tier.ULTRA: "claude-opus-4.5",  # New tier mapping
}

Provider Options:
-----------------
- "poe" or "poe_api": POE API (cloud)
- "google" or "google_studio": Google Studio / Gemini API (cloud)
- "lmstudio" or "lm_studio": LM Studio (local)
- "ollama": Ollama (local)
- None (omit provider): Auto-detect from model_id or use settings.yaml
"""
