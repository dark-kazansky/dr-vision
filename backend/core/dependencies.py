"""
FastAPI dependency injection functions for Dr.Vision.

Provides injectable dependencies for configuration and agent creation,
decoupling route handlers from direct agent construction.
"""

import logging
from fastapi import Depends, HTTPException

from config import Config, ConfigurationError, TierConfig
from core.agent_factory import AgentFactory
from functions.parser import Parser
from functions.classifier import Classifier
from functions.extractor import Extractor

logger = logging.getLogger(__name__)


def get_config() -> Config:
    """Get configuration instance.

    Returns:
        Loaded Config singleton.

    Raises:
        HTTPException(500): When configuration cannot be loaded.
    """
    try:
        return Config.load()
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")


def get_parser(
    config: Config = Depends(get_config),
    tier: str = "Normal",
) -> Parser:
    """Create a Parser with an OCR agent resolved from tier configuration.

    Args:
        config: Application configuration (injected).
        tier: Processing tier (Rapid, Normal, Advance).

    Returns:
        Parser instance ready for use.
    """
    model_id, provider = TierConfig.get_parser_model_spec(tier)
    logger.debug("Creating parser for tier=%s model=%s provider=%s", tier, model_id, provider)

    if provider:
        # Provider explicitly specified in tier config — build OCR agent via
        # the config-based factory path so the correct provider is used.
        ocr_agent = AgentFactory.create_from_config(config, model_id)
    else:
        ocr_agent = AgentFactory.create_from_config(config, model_id)

    return Parser(ocr_agent=ocr_agent)


def get_classifier(
    config: Config = Depends(get_config),
    tier: str = "Normal",
) -> Classifier:
    """Create a Classifier with an LLM agent resolved from tier configuration.

    Args:
        config: Application configuration (injected).
        tier: Processing tier (Rapid, Normal, Advance, Multimodal).

    Returns:
        Classifier instance ready for use.
    """
    model_id, provider = TierConfig.get_classifier_llm_model_spec(tier)
    logger.debug("Creating classifier for tier=%s model=%s provider=%s", tier, model_id, provider)

    llm_agent = AgentFactory.create_llm_agent(model_id, provider=provider, config=config)
    return Classifier(agent=llm_agent)


def get_extractor(
    config: Config = Depends(get_config),
    tier: str = "Normal",
) -> Extractor:
    """Create an Extractor with an LLM agent resolved from tier configuration.

    Args:
        config: Application configuration (injected).
        tier: Processing tier (Rapid, Normal, Advance).

    Returns:
        Extractor instance ready for use.
    """
    model_id, provider = TierConfig.get_extractor_model_spec(tier)
    logger.debug("Creating extractor for tier=%s model=%s provider=%s", tier, model_id, provider)

    llm_agent = AgentFactory.create_llm_agent(model_id, provider=provider, config=config)
    return Extractor(agent=llm_agent)
