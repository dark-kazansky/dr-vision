"""
Configuration module for Dr.Vision.

This module provides configuration management including:
- Config class for loading and accessing settings
- ConfigurationError for configuration errors
- ModelConfig dataclass for model configurations
- TierConfig for tier-to-model mappings
"""

from config.manager import Config, ConfigurationError, ModelConfig
from config.tier_config import TierConfig, Tier

__all__ = ['Config', 'ConfigurationError', 'ModelConfig', 'TierConfig', 'Tier']
