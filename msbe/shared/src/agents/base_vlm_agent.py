"""
Base VLM Agent for vision-language models.

All VLM agents (POE, Ollama, LM Studio, vLLM) inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VLMResponse:
    """Response from VLM agent."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseVLMAgent(ABC):
    """
    Base class for all VLM (Vision-Language Model) agents.
    
    This abstract class defines the interface that all VLM implementations
    must follow (POE, Ollama, LM Studio, vLLM, etc.).
    """
    
    def __init__(
        self,
        model_id: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        **kwargs
    ):
        """
        Initialize VLM agent.
        
        Args:
            model_id: Model identifier
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            **kwargs: Additional model-specific parameters
        """
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.extra_params = kwargs
    
    @abstractmethod
    def generate_from_image(
        self,
        image_path: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 60
    ) -> VLMResponse:
        """
        Generate text from image and prompt.
        
        Args:
            image_path: Path to image file
            prompt: User prompt
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds
            
        Returns:
            VLMResponse with generated text or error
        """
        pass
    
    @abstractmethod
    def generate_from_images(
        self,
        image_paths: List[str],
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 60
    ) -> VLMResponse:
        """
        Generate text from multiple images and prompt.
        
        Args:
            image_paths: List of paths to image files
            prompt: User prompt
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds
            
        Returns:
            VLMResponse with generated text or error
        """
        pass
    
    @abstractmethod
    def generate_from_base64(
        self,
        image_base64: str,
        prompt: str,
        media_type: str = "image/png",
        system_prompt: Optional[str] = None,
        timeout: int = 60
    ) -> VLMResponse:
        """
        Generate text from base64-encoded image and prompt.
        
        Args:
            image_base64: Base64-encoded image
            prompt: User prompt
            media_type: Image media type (e.g., 'image/png', 'image/jpeg')
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds
            
        Returns:
            VLMResponse with generated text or error
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate agent configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.model_id:
            return False
        if self.temperature < 0 or self.temperature > 1:
            return False
        if self.max_tokens <= 0:
            return False
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get agent configuration.
        
        Returns:
            Dictionary with agent configuration
        """
        return {
            'model_id': self.model_id,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'top_p': self.top_p,
            **self.extra_params
        }
