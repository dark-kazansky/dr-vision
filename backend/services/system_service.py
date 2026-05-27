"""
System service — health check and model/tier inspection logic.
"""

import logging
import os
import sys

from core.schemas import HealthResponse
from core.utils import check_server_status
from config import Config, TierConfig

logger = logging.getLogger(__name__)


def get_health(config: Config) -> HealthResponse:
    """Return server health status and available models."""
    available_models = config.get_available_models()

    server_running = False
    providers = config.api_providers

    if providers:
        first_provider = list(providers.values())[0]
        base_url = first_provider.get("base_url")
        if base_url:
            status = check_server_status(base_url)
            server_running = status.get("running", False)

    if server_running and available_models:
        status = "healthy"
    elif available_models:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(status=status, server_running=server_running, available_models=available_models)


def get_models_info(config: Config) -> dict:
    """Return detailed model availability information grouped by provider."""
    logger.info("=== MODEL CHECK REQUEST ===")

    models_info = []

    for model_id, model_config in config.models.items():
        provider = model_config.get("provider")
        provider_config = config.api_providers.get(provider, {})

        api_key_set = False
        api_key_name = None
        if provider == "google_studio":
            api_key_name = "GOOGLE_STUDIO_API_KEY"
            api_key_set = bool(os.getenv("GOOGLE_STUDIO_API_KEY"))
        elif provider == "poe_api":
            api_key_name = "POE_API_KEY"
            api_key_set = bool(os.getenv("POE_API_KEY"))
        elif provider == "lm_studio":
            api_key_name = "N/A (local)"
            api_key_set = True

        models_info.append(
            {
                "model_id": model_id,
                "name": model_config.get("name", model_id),
                "provider": provider,
                "base_url": provider_config.get("base_url"),
                "api_key_name": api_key_name,
                "api_key_set": api_key_set,
                "available": api_key_set,
            }
        )
        logger.info("  %s: provider=%s, api_key=%s, available=%s", model_id, provider, api_key_name, api_key_set)

    by_provider: dict = {}
    for model in models_info:
        by_provider.setdefault(model["provider"], []).append(model)

    available_count = len([m for m in models_info if m["available"]])
    logger.info("Total models: %d, Available: %d", len(models_info), available_count)
    logger.info("===========================")

    return {
        "success": True,
        "models": models_info,
        "by_provider": by_provider,
        "total_models": len(models_info),
        "available_models": available_count,
    }


def get_tier_config() -> dict:
    """Return tier-to-model mapping for all features."""
    # Also include provider info per cell for the frontend editor
    def spec_to_dict(spec) -> dict:
        if isinstance(spec, str):
            return {"model": spec, "provider": None}
        return {"model": spec.get("model", ""), "provider": spec.get("provider")}

    from config.tier_config import TierConfig as TC
    return {
        "success": True,
        "config": TierConfig.export_to_json(),
        "full": {
            "parser":         {k: spec_to_dict(v) for k, v in TC.PARSER_TIER_TO_MODEL.items()},
            "extractor":      {k: spec_to_dict(v) for k, v in TC.EXTRACTOR_TIER_TO_MODEL.items()},
            "classifier_llm": {k: spec_to_dict(v) for k, v in TC.CLASSIFIER_LLM_TIER_TO_MODEL.items()},
            "splitter":       {k: spec_to_dict(v) for k, v in TC.SPLITTER_TIER_TO_MODEL.items()},
        },
    }


def update_tier_config(updates: list) -> dict:
    """Apply tier-model updates at runtime AND persist to disk."""
    from config.tier_config import TierConfig as TC

    feature_map = {
        "parser":         TC.PARSER_TIER_TO_MODEL,
        "extractor":      TC.EXTRACTOR_TIER_TO_MODEL,
        "classifier_llm": TC.CLASSIFIER_LLM_TIER_TO_MODEL,
        "splitter":       TC.SPLITTER_TIER_TO_MODEL,
    }

    applied = []
    errors = []
    for u in updates:
        feature = u.feature
        tier = u.tier
        provider = u.provider
        model = u.model

        if feature not in feature_map:
            errors.append(f"Unknown feature: {feature}")
            continue

        # Update in-memory mapping
        feature_map[feature][tier] = {"model": model, "provider": provider}
        applied.append(f"{feature}.{tier} → {provider}/{model}")
        logger.info("Tier config updated: %s.%s = %s/%s", feature, tier, provider, model)

    # Persist to disk so changes survive restart
    _persist_tier_config(TC)

    return {
        "success": len(errors) == 0,
        "applied": applied,
        "errors": errors,
        "config": TierConfig.export_to_json(),
    }


def _persist_tier_config(tc_class) -> None:
    """Save current tier config to a JSON file for persistence across restarts."""
    import json
    persist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "tier_overrides.json")
    try:
        data = {
            "parser": {k: v for k, v in tc_class.PARSER_TIER_TO_MODEL.items()},
            "extractor": {k: v for k, v in tc_class.EXTRACTOR_TIER_TO_MODEL.items()},
            "classifier_llm": {k: v for k, v in tc_class.CLASSIFIER_LLM_TIER_TO_MODEL.items()},
            "splitter": {k: v for k, v in tc_class.SPLITTER_TIER_TO_MODEL.items()},
        }
        with open(persist_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Tier config persisted to %s", persist_path)
    except Exception as e:
        logger.warning("Failed to persist tier config: %s", e)


def get_logging_info() -> dict:
    """Return runtime info for the logging smoke-test endpoint."""
    logger.info("=" * 50)
    logger.info("TEST LOGGING ENDPOINT CALLED")
    logger.info("If you can see this in your terminal, logging is working!")
    logger.info("=" * 50)

    return {
        "success": True,
        "message": "Check your backend terminal for log output",
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "stdout_isatty": sys.stdout.isatty(),
    }
