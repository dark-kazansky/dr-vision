"""
Agent Factory for creating agent instances from configuration.

Moved from core/agent_factory.py to agents/factory.py as part of the
Langflow-inspired architecture migration.
"""

import os
from typing import Optional, Dict, Any

from agents.base_llm_agent import BaseLLMAgent
from agents.base_vlm_agent import BaseVLMAgent
from agents.base_ocr_agent import BaseOCRAgent
from agents.poe_llm_agent import POELLMAgent
from agents.lmstudio_llm_agent import LMStudioLLMAgent
from agents.ollama_llm_agent import OllamaLLMAgent
from agents.google_llm_agent import GoogleLLMAgent
from agents.bedrock_llm_agent import BedrockLLMAgent
from agents.poe_vlm_agent import POEVLMAgent
from agents.lmstudio_vlm_agent import LMStudioVLMAgent
from agents.ollama_vlm_agent import OllamaVLMAgent
from agents.google_vlm_agent import GoogleVLMAgent
from agents.bedrock_vlm_agent import BedrockVLMAgent
from agents.lmstudio_ocr_agent import LMStudioOCRAgent
from agents.vllm_ocr_agent import VLLMOCRAgent
from agents.vlm_ocr_adapter import VLMOCRAdapter
from config import Config


class AgentFactory:
    """Factory for creating agent instances."""
    
    @staticmethod
    def create_ocr_agent(model_config) -> BaseOCRAgent:
        """
        Create OCR agent from model configuration.
        
        Args:
            model_config: ModelConfig dataclass or dictionary
            
        Returns:
            BaseOCRAgent instance (may be a VLM-to-OCR adapter for VLM providers)
            
        Raises:
            ValueError: If provider is not supported
        """
        # Handle both ModelConfig dataclass and dictionary
        if hasattr(model_config, 'provider'):
            # ModelConfig dataclass
            provider = model_config.provider.lower()
            model_id = model_config.model_id
            base_url = model_config.base_url
            max_tokens = model_config.max_tokens
            temperature = model_config.temperature
            top_p = model_config.top_p
        else:
            # Dictionary
            provider = model_config.get('provider', '').lower()
            model_id = model_config['model_id']
            base_url = model_config['base_url']
            max_tokens = model_config.get('max_tokens', 4096)
            temperature = model_config.get('temperature', 0.2)
            top_p = model_config.get('top_p', 0.9)
        
        # Native OCR agents
        if provider == 'lm_studio':
            return LMStudioOCRAgent(
                model_id=model_id,
                base_url=base_url,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
        
        elif provider == 'lightonocr_api' or provider == 'vllm':
            return VLLMOCRAgent(
                model_id=model_id,
                base_url=base_url,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
        
        # VLM providers - use VLM-to-OCR adapter
        elif provider == 'google' or provider == 'google_studio':
            # Create VLM agent
            vlm_agent = GoogleVLMAgent(
                model_id=model_id,
                api_key=os.getenv('GOOGLE_STUDIO_API_KEY'),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
            # Wrap in adapter
            return VLMOCRAdapter(vlm_agent=vlm_agent)
        
        elif provider == 'poe' or provider == 'poe_api':
            # Create VLM agent
            vlm_agent = POEVLMAgent(
                model_id=model_id,
                api_key=os.getenv('POE_API_KEY'),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
            # Wrap in adapter
            return VLMOCRAdapter(vlm_agent=vlm_agent)
        
        elif provider == 'ollama':
            # Create VLM agent
            vlm_agent = OllamaVLMAgent(
                model_id=model_id,
                base_url=base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
            # Wrap in adapter
            return VLMOCRAdapter(vlm_agent=vlm_agent)
        
        elif provider == 'bedrock' or provider == 'bedrock_runtime':
            # Resolve model ARN from environment variables
            bedrock_model_id = model_id
            if model_id == 'claude-haiku':
                bedrock_model_id = os.getenv('CLAUDE_HAIKU_ID', model_id)
            elif model_id == 'claude-sonnet':
                bedrock_model_id = os.getenv('CLAUDE_SONET_ID', model_id)
            
            # Create Bedrock VLM agent
            vlm_agent = BedrockVLMAgent(
                model_id=bedrock_model_id,
                region=os.getenv('BEDROCK_REGION', 'ap-southeast-2'),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
            # Wrap in adapter
            return VLMOCRAdapter(vlm_agent=vlm_agent)
        
        else:
            raise ValueError(f"Unsupported OCR provider: {provider}. Supported: lm_studio, vllm, google, poe, ollama, bedrock")
    
    @staticmethod
    def create_llm_agent(
        model_id: str,
        provider: Optional[str] = None,
        config: Optional[Config] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseLLMAgent:
        """
        Create LLM agent.
        
        Args:
            model_id: Model identifier
            provider: Provider name (poe, lmstudio, ollama, google)
            config: Optional Config instance for provider resolution
            base_url: Base URL for local providers
            api_key: API key for cloud providers
            **kwargs: Additional parameters
            
        Returns:
            BaseLLMAgent instance
            
        Raises:
            ValueError: If provider is not supported or model not found
        """
        if not provider:
            if config is not None:
                # Look up provider from configuration
                model_entry = config.models.get(model_id)
                if model_entry is not None:
                    provider = model_entry.get('provider')
                else:
                    available = config.get_available_models()
                    raise ValueError(
                        f"Model '{model_id}' not found in configuration. "
                        f"Available models: {available}"
                    )
            else:
                # Fallback: auto-detect provider from model_id (legacy behavior)
                if model_id in ['assistant', 'qwen3-max', 'gemini-3-pro', 'claude-opus-4.5']:
                    provider = 'poe'
                elif model_id.startswith('gemini-'):
                    provider = 'google'
                else:
                    provider = 'lmstudio'  # Default to LM Studio
        
        provider = provider.lower()
        
        if provider == 'poe' or provider == 'poe_api':
            return POELLMAgent(
                model_id=model_id,
                api_key=api_key or os.getenv('POE_API_KEY'),
                **kwargs
            )
        
        elif provider == 'google' or provider == 'google_studio':
            return GoogleLLMAgent(
                model_id=model_id,
                api_key=api_key or os.getenv('GOOGLE_STUDIO_API_KEY'),
                **kwargs
            )
        
        elif provider == 'lmstudio' or provider == 'lm_studio':
            return LMStudioLLMAgent(
                model_id=model_id,
                base_url=base_url or os.getenv('LM_STUDIO_BASE_URL', 'http://localhost:1234'),
                **kwargs
            )
        
        elif provider == 'ollama':
            return OllamaLLMAgent(
                model_id=model_id,
                base_url=base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                **kwargs
            )
        
        elif provider == 'bedrock' or provider == 'bedrock_runtime':
            # Resolve model ARN from environment variables
            bedrock_model_id = model_id
            if model_id == 'claude-haiku':
                bedrock_model_id = os.getenv('CLAUDE_HAIKU_ID', model_id)
            elif model_id == 'claude-sonnet':
                bedrock_model_id = os.getenv('CLAUDE_SONET_ID', model_id)
            
            return BedrockLLMAgent(
                model_id=bedrock_model_id,
                region=os.getenv('BEDROCK_REGION', 'ap-southeast-2'),
                **kwargs
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def create_vlm_agent(
        model_id: str,
        provider: Optional[str] = None,
        config: Optional[Config] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseVLMAgent:
        """
        Create VLM agent.
        
        Args:
            model_id: Model identifier
            provider: Provider name (poe, lmstudio, ollama, google, bedrock)
            config: Optional Config instance for provider resolution
            base_url: Base URL for local providers
            api_key: API key for cloud providers
            **kwargs: Additional parameters
            
        Returns:
            BaseVLMAgent instance
            
        Raises:
            ValueError: If provider is not supported
        """
        if not provider:
            if config is not None:
                model_entry = config.models.get(model_id)
                if model_entry is not None:
                    provider = model_entry.get('provider')
            
            if not provider:
                # Auto-detect provider from model_id
                if model_id in ['gemini-3-pro', 'claude-opus-4.5']:
                    provider = 'poe'
                elif model_id.startswith('gemini-'):
                    provider = 'google'
                elif model_id in ['llava', 'bakllava']:
                    provider = 'ollama'
                else:
                    provider = 'lmstudio'
        
        provider = provider.lower()
        
        if provider == 'poe' or provider == 'poe_api':
            return POEVLMAgent(
                model_id=model_id,
                api_key=api_key or os.getenv('POE_API_KEY'),
                **kwargs
            )
        
        elif provider == 'google' or provider == 'google_studio':
            return GoogleVLMAgent(
                model_id=model_id,
                api_key=api_key or os.getenv('GOOGLE_STUDIO_API_KEY'),
                **kwargs
            )
        
        elif provider == 'lmstudio' or provider == 'lm_studio':
            return LMStudioVLMAgent(
                model_id=model_id,
                base_url=base_url or os.getenv('LM_STUDIO_BASE_URL', 'http://localhost:1234'),
                **kwargs
            )
        
        elif provider == 'ollama':
            return OllamaVLMAgent(
                model_id=model_id,
                base_url=base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                **kwargs
            )
        
        elif provider == 'bedrock' or provider == 'bedrock_runtime':
            bedrock_model_id = model_id
            if model_id == 'claude-haiku':
                bedrock_model_id = os.getenv('CLAUDE_HAIKU_ID', model_id)
            elif model_id == 'claude-sonnet':
                bedrock_model_id = os.getenv('CLAUDE_SONET_ID', model_id)
            
            return BedrockVLMAgent(
                model_id=bedrock_model_id,
                region=os.getenv('BEDROCK_REGION', 'ap-southeast-2'),
                **kwargs
            )
        
        else:
            raise ValueError(f"Unsupported VLM provider: {provider}")
    
    @staticmethod
    def create_from_config(config: Config, model_id: str, provider_override: Optional[str] = None) -> BaseOCRAgent:
        """
        Create OCR agent from Config instance and model ID.

        Args:
            config: Config instance
            model_id: Model ID from configuration
            provider_override: Optional provider to use instead of the one in config

        Returns:
            BaseOCRAgent instance

        Raises:
            ValueError: If model not found or provider not supported
        """
        model_config = config.get_model_config(model_id)
        if not model_config:
            raise ValueError(f"Model not found: {model_id}")

        # Apply provider override if specified
        if provider_override:
            if hasattr(model_config, 'provider'):
                # ModelConfig dataclass — create a copy with overridden provider
                import dataclasses
                model_config = dataclasses.replace(model_config, provider=provider_override)
            elif isinstance(model_config, dict):
                model_config = {**model_config, 'provider': provider_override}

        return AgentFactory.create_ocr_agent(model_config)
