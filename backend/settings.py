"""
Application settings using pydantic-settings.

Replaces config/manager.py and config/tier_config.py with a unified
pydantic-settings based configuration that reads from environment variables
and .env files.

Environment Variables:
    LM_STUDIO_BASE_URL: Override base URL for LM Studio provider
    DEFAULT_MODEL_ID: Override default model selection
    UPLOAD_FOLDER: Override upload directory path
    MAX_FILE_SIZE_MB: Override maximum file size limit
    FASTAPI_DEBUG: Override FastAPI debug mode (true/false)
    POE_API_KEY: API key for POE models
    GOOGLE_STUDIO_API_KEY: API key for Google Studio models
    BEDROCK_REGION: AWS Bedrock region
    CLAUDE_HAIKU_ID: Claude Haiku model ARN
    CLAUDE_SONET_ID: Claude Sonnet model ARN
    OLLAMA_BASE_URL: Ollama server base URL
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    model_id: str
    provider: str
    name: str
    base_url: str
    max_tokens: int = 4096
    temperature: float = 0.2
    top_p: float = 0.9


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env files.
    
    Load order: environment variables > .env file > defaults
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # --- Server settings ---
    fastapi_host: str = Field(default="0.0.0.0", alias="HOST")
    fastapi_port: int = Field(default=8000, alias="PORT")
    fastapi_debug: bool = Field(default=False, alias="FASTAPI_DEBUG")
    cors_origins_str: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
    )
    
    # --- Upload settings ---
    upload_folder: str = Field(default="uploads", alias="UPLOAD_FOLDER")
    max_file_size_mb: float = Field(default=10.0, alias="MAX_FILE_SIZE_MB")
    allowed_extensions: List[str] = Field(default=["pdf", "png", "jpg", "jpeg"])
    
    # --- PDF settings ---
    pdf_render_dpi: int = Field(default=200)
    pdf_process_all_pages: bool = Field(default=True)
    
    # --- Rate limiting ---
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests_per_minute: int = Field(default=30)
    rate_limit_burst_size: int = Field(default=10)
    
    # --- Background tasks ---
    background_tasks_enabled: bool = Field(default=False)
    background_tasks_threshold_pages: int = Field(default=5)
    
    # --- API provider base URLs ---
    lm_studio_base_url: str = Field(default="http://localhost:1234", alias="LM_STUDIO_BASE_URL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    
    # --- API keys ---
    poe_api_key: Optional[str] = Field(default=None, alias="POE_API_KEY")
    google_studio_api_key: Optional[str] = Field(default=None, alias="GOOGLE_STUDIO_API_KEY")
    bedrock_region: str = Field(default="ap-southeast-2", alias="BEDROCK_REGION")
    claude_haiku_id: Optional[str] = Field(default=None, alias="CLAUDE_HAIKU_ID")
    claude_sonet_id: Optional[str] = Field(default=None, alias="CLAUDE_SONET_ID")
    
    # --- Database ---
    database_url: Optional[str] = Field(
        default=None,
        alias="DATABASE_URL",
    )

    # --- JWT Authentication ---
    jwt_secret_key: str = Field(
        default="CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    # First admin user auto-created on startup if no users exist
    admin_email: Optional[str] = Field(default=None, alias="ADMIN_EMAIL")
    admin_password: Optional[str] = Field(default=None, alias="ADMIN_PASSWORD")
    admin_name: str = Field(default="Admin", alias="ADMIN_NAME")
    
    # --- MinIO Storage ---
    minio_endpoint: str = Field(default="http://localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: Optional[str] = Field(default=None, alias="MINIO_ACCESS_KEY")
    minio_secret_key: Optional[str] = Field(default=None, alias="MINIO_SECRET_KEY")
    minio_bucket_name: str = Field(default="drvision-docs", alias="MINIO_BUCKET_NAME")

    # --- Durable Workflow Engine ---
    durable_mode: bool = Field(default=False, alias="DURABLE_MODE")
    
    # --- Model configuration ---
    default_model: Optional[str] = Field(default=None, alias="DEFAULT_MODEL_ID")
    
    # Internal: loaded from settings.yaml
    _models: Dict[str, Any] = {}
    _api_providers: Dict[str, Any] = {}
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_yaml_config()
    
    def _load_yaml_config(self) -> None:
        """Load model definitions from config/settings.yaml."""
        config_path = Path("config/settings.yaml")
        if not config_path.exists():
            return
        
        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
            
            if config_data:
                self._models = config_data.get("models", {})
                self._api_providers = config_data.get("api_providers", {})
                
                # Apply env overrides to providers
                if "lm_studio" in self._api_providers:
                    self._api_providers["lm_studio"]["base_url"] = self.lm_studio_base_url
                if "ollama" in self._api_providers:
                    self._api_providers["ollama"]["base_url"] = self.ollama_base_url
                
        except Exception as e:
            import logging
            logging.warning(f"Failed to load config/settings.yaml: {e}")
    
    @field_validator("max_file_size_mb")
    @classmethod
    def validate_max_file_size(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("max_file_size_mb must be positive")
        return v
    
    @field_validator("fastapi_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if v < 1 or v > 65535:
            raise ValueError("fastapi_port must be between 1 and 65535")
        return v
    
    def check_required_secrets(self) -> List[str]:
        """
        Check that required secrets are configured.
        Returns list of missing secret names. Empty list = all good.
        """
        missing = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.minio_access_key:
            missing.append("MINIO_ACCESS_KEY")
        if not self.minio_secret_key:
            missing.append("MINIO_SECRET_KEY")
        return missing
    
    # --- Public API (compatible with old Config class) ---
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS_ORIGINS from comma-separated string."""
        return [
            origin.strip()
            for origin in self.cors_origins_str.split(",")
            if origin.strip()
        ]

    @property
    def models(self) -> Dict[str, Any]:
        """Get model configurations."""
        return self._models
    
    @property
    def api_providers(self) -> Dict[str, Any]:
        """Get API provider configurations."""
        return self._api_providers
    
    @property
    def fastapi_config(self) -> Dict[str, Any]:
        """Get FastAPI-specific configuration."""
        return {
            "host": self.fastapi_host,
            "port": self.fastapi_port,
            "debug": self.fastapi_debug,
            "cors_origins": self.cors_origins,
        }
    
    @property
    def upload_config(self) -> Dict[str, Any]:
        """Get file upload configuration."""
        return {
            "folder": self.upload_folder,
            "max_size_mb": self.max_file_size_mb,
            "allowed_extensions": self.allowed_extensions,
        }
    
    @property
    def pdf_config(self) -> Dict[str, Any]:
        """Get PDF processing configuration."""
        return {
            "render_dpi": self.pdf_render_dpi,
            "default_process_all_pages": self.pdf_process_all_pages,
        }
    
    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model."""
        if model_id not in self._models:
            return None
        
        model_data = self._models[model_id]
        provider_name = model_data.get("provider")
        if not provider_name or provider_name not in self._api_providers:
            return None
        
        provider_config = self._api_providers[provider_name]
        base_url = provider_config.get("base_url")
        if not base_url:
            return None
        
        return ModelConfig(
            model_id=model_data.get("model_id", model_id),
            provider=provider_name,
            name=model_data.get("name", model_id),
            base_url=base_url,
            max_tokens=model_data.get("max_tokens", 4096),
            temperature=model_data.get("temperature", 0.2),
            top_p=model_data.get("top_p", 0.9),
        )
    
    def get_available_models(self) -> List[str]:
        """Get list of available model IDs."""
        return list(self._models.keys())
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of error messages. Empty list if valid.
        """
        errors = []
        
        if not self._api_providers:
            errors.append("No API providers configured")
        
        if not self._models:
            errors.append("No models configured")
        
        for model_id, model_data in self._models.items():
            provider = model_data.get("provider")
            if not provider:
                errors.append(f"Model '{model_id}' missing provider")
            elif provider not in self._api_providers:
                errors.append(f"Model '{model_id}' references unknown provider: {provider}")
        
        return errors


# Re-export TierConfig from config/tier_config.py — it has the full implementation
# with provider-aware model specs, fallback logic, and export_to_json.
from config.tier_config import TierConfig, Tier  # noqa: F401, E402


# Module-level singleton
settings = Settings()
