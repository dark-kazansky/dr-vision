"""
Configuration module for Doc Intelligence.

This module provides configuration management including:
- Config class for loading and accessing settings
- ConfigurationError for configuration errors
- ModelConfig dataclass for model configurations
- TierConfig for tier-to-model mappings
"""

from config.manager import Config, ConfigurationError, ModelConfig
from config.tier_config import TierConfig, Tier
from config.banking_schemas import (
    BANKING_CLASSIFICATION_RULES,
    SCHEMA_REGISTRY,
    get_schema_for_doc_type,
    get_workflow_template,
    list_workflow_templates,
)

__all__ = [
    'Config', 'ConfigurationError', 'ModelConfig', 'TierConfig', 'Tier',
    'BANKING_CLASSIFICATION_RULES', 'SCHEMA_REGISTRY',
    'get_schema_for_doc_type', 'get_workflow_template', 'list_workflow_templates',
]
