"""
Agent Factory for creating agent instances from configuration.

This module provides factory functions to create agents based on configuration.
"""

import os
from typing import Optional, Dict, Any

from agents import (
    BaseLLMAgent, BaseVLMAgent, BaseOCRAgent,
    POELLMAgent, LMStudioLLMAgent, OllamaLLMAgent, GoogleLLMAgent,
    POEVLMAgent, LMStudioVLMAgent, OllamaVLMAgent, GoogleVLMAgent,
    LMStudioOCRAgent, VLLMOCRAgent, VLMOCRAdapter
)
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
        
        else:
            raise ValueError(f"Unsupported OCR provider: {provider}. Supported: lm_studio, vllm, google, poe, ollama")
    
    @staticmethod
    def create_llm_agent(
        model_id: str,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseLLMAgent:
        """
        Create LLM agent.
        
        Args:
            model_id: Model identifier
            provider: Provider name (poe, lmstudio, ollama)
            base_url: Base URL for local providers
            api_key: API key for cloud providers
            **kwargs: Additional parameters
            
        Returns:
            BaseLLMAgent instance
            
        Raises:
            ValueError: If provider is not supported
        """
        if not provider:
            # Auto-detect provider from model_id
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
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def create_vlm_agent(
        model_id: str,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseVLMAgent:
        """
        Create VLM agent.
        
        Args:
            model_id: Model identifier
            provider: Provider name (poe, lmstudio, ollama)
            base_url: Base URL for local providers
            api_key: API key for cloud providers
            **kwargs: Additional parameters
            
        Returns:
            BaseVLMAgent instance
            
        Raises:
            ValueError: If provider is not supported
        """
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
        
        else:
            raise ValueError(f"Unsupported VLM provider: {provider}")
    
    @staticmethod
    def create_from_config(config: Config, model_id: str) -> BaseOCRAgent:
        """
        Create OCR agent from Config instance and model ID.
        
        Args:
            config: Config instance
            model_id: Model ID from configuration
            
        Returns:
            BaseOCRAgent instance
            
        Raises:
            ValueError: If model not found or provider not supported
        """
        model_config = config.get_model_config(model_id)
        if not model_config:
            raise ValueError(f"Model not found: {model_id}")
        
        return AgentFactory.create_ocr_agent(model_config)
