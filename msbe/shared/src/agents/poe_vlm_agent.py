"""
POE VLM Agent implementation.

Implements BaseVLMAgent for POE API vision models (gemini-3-pro, etc.).
"""

import os
import base64
import openai
from typing import Dict, Any, Optional, List
from pathlib import Path
from agents.base_vlm_agent import BaseVLMAgent, VLMResponse


class POEVLMAgent(BaseVLMAgent):
    """
    POE VLM Agent for vision-language models via POE API.
    
    Supports models with vision capabilities: gemini-3-pro, etc.
    """
    
    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        **kwargs
    ):
        """
        Initialize POE VLM agent.
        
        Args:
            model_id: POE model identifier (must support vision)
            api_key: POE API key (defaults to POE_API_KEY env var)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            **kwargs: Additional parameters
        """
        super().__init__(model_id, temperature, max_tokens, top_p, **kwargs)
        
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv('POE_API_KEY')
        if not self.api_key:
            raise ValueError("POE_API_KEY is required")
        
        # Initialize OpenAI client with POE configuration
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.poe.com/v1"
        )
    
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
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Determine media type
            ext = Path(image_path).suffix.lower()
            media_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
            }
            media_type = media_types.get(ext, 'image/png')
            
            return self.generate_from_base64(
                image_data,
                prompt,
                media_type,
                system_prompt,
                timeout
            )
            
        except IOError as e:
            return VLMResponse(
                success=False,
                error=f"Failed to read image file: {str(e)}",
                error_type="file_error"
            )
        except Exception as e:
            return VLMResponse(
                success=False,
                error=f"Image processing failed: {str(e)}",
                error_type="processing_error"
            )
    
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
        try:
            # Build message content with text and images
            content = [{"type": "text", "text": prompt}]
            
            # Add all images
            for image_path in image_paths:
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                
                ext = Path(image_path).suffix.lower()
                media_types = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                }
                media_type = media_types.get(ext, 'image/png')
                
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_data}"
                    }
                })
            
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": content})
            
            # Call API
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=timeout
            )
            
            content_text = response.choices[0].message.content
            
            return VLMResponse(
                success=True,
                content=content_text,
                metadata={
                    'model': self.model_id,
                    'image_count': len(image_paths),
                    'finish_reason': response.choices[0].finish_reason
                }
            )
            
        except openai.APITimeoutError as e:
            return VLMResponse(
                success=False,
                error=f"POE API timeout after {timeout} seconds: {str(e)}",
                error_type="timeout_error"
            )
        except openai.APIConnectionError as e:
            return VLMResponse(
                success=False,
                error=f"Failed to connect to POE API: {str(e)}",
                error_type="connection_error"
            )
        except openai.APIError as e:
            return VLMResponse(
                success=False,
                error=f"POE API error: {str(e)}",
                error_type="api_error"
            )
        except Exception as e:
            return VLMResponse(
                success=False,
                error=f"VLM generation failed: {str(e)}",
                error_type="processing_error"
            )
    
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
            media_type: Image media type
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds
            
        Returns:
            VLMResponse with generated text or error
        """
        try:
            # Build message content
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_base64}"
                    }
                }
            ]
            
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": content})
            
            # Call API
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=timeout
            )
            
            content_text = response.choices[0].message.content
            
            return VLMResponse(
                success=True,
                content=content_text,
                metadata={
                    'model': self.model_id,
                    'finish_reason': response.choices[0].finish_reason
                }
            )
            
        except openai.APITimeoutError as e:
            return VLMResponse(
                success=False,
                error=f"POE API timeout after {timeout} seconds: {str(e)}",
                error_type="timeout_error"
            )
        except openai.APIConnectionError as e:
            return VLMResponse(
                success=False,
                error=f"Failed to connect to POE API: {str(e)}",
                error_type="connection_error"
            )
        except openai.APIError as e:
            return VLMResponse(
                success=False,
                error=f"POE API error: {str(e)}",
                error_type="api_error"
            )
        except Exception as e:
            return VLMResponse(
                success=False,
                error=f"VLM generation failed: {str(e)}",
                error_type="processing_error"
            )
