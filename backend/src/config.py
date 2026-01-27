"""
Configuration loader and validator for OCR Web UI.

This module provides configuration management with:
- YAML file loading
- Environment variable overrides
- Configuration validation
- Singleton pattern for global access

Environment Variables:
    LM_STUDIO_BASE_URL: Override base URL for LM Studio provider
    DEFAULT_MODEL_ID: Override default model selection
    UPLOAD_FOLDER: Override upload directory path
    MAX_FILE_SIZE_MB: Override maximum file size limit
"""

import os
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


@dataclass
class ModelConfig:
    """Configuration for a single OCR model."""
    model_id: str
    provider: str
    name: str
    base_url: str  # Resolved from provider
    max_tokens: int = 4096
    temperature: float = 0.2
    top_p: float = 0.9


class Config:
    """
    Singleton configuration object for OCR Web UI.
    
    Loads configuration from YAML file and applies environment variable overrides.
    Provides validated access to all configuration sections.
    """
    
    _instance: Optional['Config'] = None
    _config_data: Dict[str, Any] = {}
    
    def __init__(self, config_data: Dict[str, Any]):
        """
        Initialize Config with configuration data.
        
        Args:
            config_data: Dictionary containing configuration values
        """
        self._config_data = config_data
    
    @classmethod
    def load(cls, config_path: str = 'config/config.yaml') -> 'Config':
        """
        Load configuration from YAML file with environment variable overrides.
        
        This method implements the singleton pattern - subsequent calls return
        the same instance unless the configuration is explicitly reloaded.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Config instance with loaded configuration
            
        Raises:
            ConfigurationError: If file not found or YAML is invalid
        """
        # Load YAML file
        config_file = Path(config_path)
        if not config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax in {config_path}: {e}")
        
        if config_data is None:
            raise ConfigurationError(f"Configuration file is empty: {config_path}")
        
        # Apply environment variable overrides
        cls._apply_env_overrides(config_data)
        
        # Create new instance (allows reload)
        cls._instance = cls(config_data)
        return cls._instance
    
    @classmethod
    def _apply_env_overrides(cls, config_data: Dict[str, Any]) -> None:
        """
        Apply environment variable overrides to configuration data.
        
        Supported environment variables:
        - LM_STUDIO_BASE_URL: Override api_providers.lm_studio.base_url
        - DEFAULT_MODEL_ID: Override default_model
        - UPLOAD_FOLDER: Override upload.folder
        - MAX_FILE_SIZE_MB: Override upload.max_size_mb
        
        Args:
            config_data: Configuration dictionary to modify in-place
        """
        # Override LM Studio base URL
        lm_studio_url = os.environ.get('LM_STUDIO_BASE_URL')
        if lm_studio_url:
            if 'api_providers' not in config_data:
                config_data['api_providers'] = {}
            if 'lm_studio' not in config_data['api_providers']:
                config_data['api_providers']['lm_studio'] = {}
            config_data['api_providers']['lm_studio']['base_url'] = lm_studio_url
        
        # Override default model
        default_model = os.environ.get('DEFAULT_MODEL_ID')
        if default_model:
            config_data['default_model'] = default_model
        
        # Override upload folder
        upload_folder = os.environ.get('UPLOAD_FOLDER')
        if upload_folder:
            if 'upload' not in config_data:
                config_data['upload'] = {}
            config_data['upload']['folder'] = upload_folder
        
        # Override max file size
        max_file_size = os.environ.get('MAX_FILE_SIZE_MB')
        if max_file_size:
            try:
                max_size_value = int(max_file_size)
                if 'upload' not in config_data:
                    config_data['upload'] = {}
                config_data['upload']['max_size_mb'] = max_size_value
            except ValueError:
                # Log warning but continue with file value
                import logging
                logging.warning(
                    f"Invalid MAX_FILE_SIZE_MB environment variable: {max_file_size}. "
                    f"Using default value from configuration file."
                )
    
    @property
    def models(self) -> Dict[str, Any]:
        """
        Get model configurations.
        
        Returns:
            Dictionary mapping model IDs to model configuration dictionaries
        """
        return self._config_data.get('models', {})
    
    @property
    def fastapi_config(self) -> Dict[str, Any]:
        """
        Get FastAPI-specific configuration.
        
        Returns:
            Dictionary containing FastAPI settings (debug, host, port, cors_origins)
        """
        return self._config_data.get('fastapi', {})
    
    @property
    def upload_config(self) -> Dict[str, Any]:
        """
        Get file upload configuration.
        
        Returns:
            Dictionary containing upload settings (folder, max_size_mb, allowed_extensions)
        """
        return self._config_data.get('upload', {})
    
    @property
    def pdf_config(self) -> Dict[str, Any]:
        """
        Get PDF processing configuration.
        
        Returns:
            Dictionary containing PDF settings (render_dpi, default_process_all_pages)
        """
        return self._config_data.get('pdf', {})
    
    @property
    def api_providers(self) -> Dict[str, Any]:
        """
        Get API provider configurations.
        
        Returns:
            Dictionary mapping provider names to provider configuration dictionaries
        """
        return self._config_data.get('api_providers', {})
    
    @property
    def default_model(self) -> Optional[str]:
        """
        Get default model ID.
        
        Returns:
            Default model ID string, or None if not configured
        """
        return self._config_data.get('default_model')
    
    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """
        Get configuration for a specific model.
        
        Resolves the provider's base_url and returns a complete ModelConfig object.
        
        Args:
            model_id: ID of the model to retrieve
            
        Returns:
            ModelConfig object if model exists, None otherwise
        """
        models = self.models
        if model_id not in models:
            return None
        
        model_data = models[model_id]
        
        # Resolve provider base URL
        provider_name = model_data.get('provider')
        if not provider_name:
            return None
        
        providers = self.api_providers
        if provider_name not in providers:
            return None
        
        provider_config = providers[provider_name]
        base_url = provider_config.get('base_url')
        
        if not base_url:
            return None
        
        # Create ModelConfig object
        return ModelConfig(
            model_id=model_data.get('model_id', model_id),
            provider=provider_name,
            name=model_data.get('name', model_id),
            base_url=base_url,
            max_tokens=model_data.get('max_tokens', 4096),
            temperature=model_data.get('temperature', 0.2),
            top_p=model_data.get('top_p', 0.9)
        )
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available model IDs.
        
        Returns:
            List of model ID strings
        """
        return list(self.models.keys())
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Checks for:
        - Required top-level sections (api_providers, models, fastapi, upload)
        - Required fields within each section
        - Valid model configurations with proper provider references
        - Valid data types for numeric fields
        
        Returns:
            List of error messages. Empty list if configuration is valid.
        """
        errors = []
        
        # Check required top-level sections
        required_sections = ['api_providers', 'models', 'fastapi', 'upload']
        for section in required_sections:
            if section not in self._config_data:
                errors.append(f"Missing required configuration section: {section}")
        
        # Validate api_providers section
        if 'api_providers' in self._config_data:
            providers = self._config_data['api_providers']
            if not isinstance(providers, dict):
                errors.append("api_providers must be a dictionary")
            elif not providers:
                errors.append("api_providers section is empty")
            else:
                for provider_name, provider_config in providers.items():
                    if not isinstance(provider_config, dict):
                        errors.append(f"Provider '{provider_name}' configuration must be a dictionary")
                        continue
                    
                    if 'base_url' not in provider_config:
                        errors.append(f"Provider '{provider_name}' missing required field: base_url")
                    elif not isinstance(provider_config['base_url'], str):
                        errors.append(f"Provider '{provider_name}' base_url must be a string")
        
        # Validate models section
        if 'models' in self._config_data:
            models = self._config_data['models']
            if not isinstance(models, dict):
                errors.append("models must be a dictionary")
            elif not models:
                errors.append("models section is empty - at least one model must be configured")
            else:
                for model_id, model_config in models.items():
                    if not isinstance(model_config, dict):
                        errors.append(f"Model '{model_id}' configuration must be a dictionary")
                        continue
                    
                    # Check required model fields
                    required_model_fields = ['model_id', 'provider', 'name']
                    for field in required_model_fields:
                        if field not in model_config:
                            errors.append(f"Model '{model_id}' missing required field: {field}")
                    
                    # Validate provider reference
                    if 'provider' in model_config:
                        provider = model_config['provider']
                        if 'api_providers' in self._config_data:
                            if provider not in self._config_data['api_providers']:
                                errors.append(
                                    f"Model '{model_id}' references unknown provider: {provider}"
                                )
                    
                    # Validate numeric fields
                    if 'max_tokens' in model_config:
                        if not isinstance(model_config['max_tokens'], int):
                            errors.append(f"Model '{model_id}' max_tokens must be an integer")
                        elif model_config['max_tokens'] <= 0:
                            errors.append(f"Model '{model_id}' max_tokens must be positive")
                    
                    if 'temperature' in model_config:
                        temp = model_config['temperature']
                        if not isinstance(temp, (int, float)):
                            errors.append(f"Model '{model_id}' temperature must be a number")
                        elif temp < 0 or temp > 2:
                            errors.append(f"Model '{model_id}' temperature must be between 0 and 2")
                    
                    if 'top_p' in model_config:
                        top_p = model_config['top_p']
                        if not isinstance(top_p, (int, float)):
                            errors.append(f"Model '{model_id}' top_p must be a number")
                        elif top_p < 0 or top_p > 1:
                            errors.append(f"Model '{model_id}' top_p must be between 0 and 1")
        
        # Validate default_model
        if 'default_model' in self._config_data:
            default_model = self._config_data['default_model']
            if not isinstance(default_model, str):
                errors.append("default_model must be a string")
            elif 'models' in self._config_data:
                if default_model not in self._config_data['models']:
                    errors.append(
                        f"default_model '{default_model}' not found in models section"
                    )
        
        # Validate fastapi section
        if 'fastapi' in self._config_data:
            fastapi = self._config_data['fastapi']
            if not isinstance(fastapi, dict):
                errors.append("fastapi must be a dictionary")
            else:
                required_fastapi_fields = ['host', 'port']
                for field in required_fastapi_fields:
                    if field not in fastapi:
                        errors.append(f"fastapi section missing required field: {field}")
                
                if 'port' in fastapi:
                    port = fastapi['port']
                    if not isinstance(port, int):
                        errors.append("fastapi.port must be an integer")
                    elif port < 1 or port > 65535:
                        errors.append("fastapi.port must be between 1 and 65535")
                
                if 'cors_origins' in fastapi:
                    if not isinstance(fastapi['cors_origins'], list):
                        errors.append("fastapi.cors_origins must be a list")
        
        # Validate upload section
        if 'upload' in self._config_data:
            upload = self._config_data['upload']
            if not isinstance(upload, dict):
                errors.append("upload must be a dictionary")
            else:
                required_upload_fields = ['folder', 'max_size_mb', 'allowed_extensions']
                for field in required_upload_fields:
                    if field not in upload:
                        errors.append(f"upload section missing required field: {field}")
                
                if 'max_size_mb' in upload:
                    max_size = upload['max_size_mb']
                    if not isinstance(max_size, (int, float)):
                        errors.append("upload.max_size_mb must be a number")
                    elif max_size <= 0:
                        errors.append("upload.max_size_mb must be positive")
                
                if 'allowed_extensions' in upload:
                    extensions = upload['allowed_extensions']
                    if not isinstance(extensions, list):
                        errors.append("upload.allowed_extensions must be a list")
                    elif not extensions:
                        errors.append("upload.allowed_extensions cannot be empty")
        
        return errors
