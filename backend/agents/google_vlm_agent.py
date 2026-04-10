"""
Google Studio VLM Agent implementation.

Implements BaseVLMAgent for Google Gemini Vision API (gemini-1.5-flash, gemini-1.5-pro, etc.).
"""

import os
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from PIL import Image
from agents.base_vlm_agent import BaseVLMAgent, VLMResponse


class GoogleVLMAgent(BaseVLMAgent):
    """
    Google Studio VLM Agent for vision-language models via Google Gemini API.
    
    Supports models: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp, etc.
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
        Initialize Google Studio VLM agent.
        
        Args:
            model_id: Google model identifier (e.g., 'gemini-1.5-flash')
            api_key: Google API key (defaults to GOOGLE_STUDIO_API_KEY env var)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            **kwargs: Additional parameters
        """
        super().__init__(model_id, temperature, max_tokens, top_p, **kwargs)
        
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv('GOOGLE_STUDIO_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_STUDIO_API_KEY is required")
        
        # Configure Google Generative AI
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=self.model_id,
            generation_config={
                'temperature': self.temperature,
                'max_output_tokens': self.max_tokens,
                'top_p': self.top_p,
            }
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
            # Load image
            image = Image.open(image_path)
            
            # Combine system prompt and user prompt if system prompt exists
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Generate content with image
            response = self.model.generate_content(
                [full_prompt, image],
                request_options={'timeout': timeout}
            )
            
            content = response.text
            
            return VLMResponse(
                success=True,
                content=content,
                metadata={
                    'model': self.model_id,
                    'image_path': image_path,
                    'finish_reason': response.candidates[0].finish_reason.name if response.candidates else None,
                    'safety_ratings': [
                        {
                            'category': rating.category.name,
                            'probability': rating.probability.name
                        }
                        for rating in response.candidates[0].safety_ratings
                    ] if response.candidates else []
                }
            )
            
        except FileNotFoundError:
            return VLMResponse(
                success=False,
                error=f"Image file not found: {image_path}",
                error_type="file_not_found"
            )
        except Exception as e:
            error_msg = str(e)
            error_type = "processing_error"
            
            if "timeout" in error_msg.lower():
                error_type = "timeout_error"
            elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                error_type = "auth_error"
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                error_type = "quota_error"
            elif "connection" in error_msg.lower():
                error_type = "connection_error"
            
            return VLMResponse(
                success=False,
                error=f"Google VLM generation failed: {error_msg}",
                error_type=error_type
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
            # Load all images
            images = []
            for image_path in image_paths:
                image = Image.open(image_path)
                images.append(image)
            
            # Combine system prompt and user prompt if system prompt exists
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Create content list with prompt and images
            content = [full_prompt] + images
            
            # Generate content with multiple images
            response = self.model.generate_content(
                content,
                request_options={'timeout': timeout}
            )
            
            text_content = response.text
            
            return VLMResponse(
                success=True,
                content=text_content,
                metadata={
                    'model': self.model_id,
                    'image_paths': image_paths,
                    'image_count': len(image_paths),
                    'finish_reason': response.candidates[0].finish_reason.name if response.candidates else None
                }
            )
            
        except FileNotFoundError as e:
            return VLMResponse(
                success=False,
                error=f"Image file not found: {str(e)}",
                error_type="file_not_found"
            )
        except Exception as e:
            error_msg = str(e)
            error_type = "processing_error"
            
            if "timeout" in error_msg.lower():
                error_type = "timeout_error"
            elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                error_type = "auth_error"
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                error_type = "quota_error"
            elif "connection" in error_msg.lower():
                error_type = "connection_error"
            
            return VLMResponse(
                success=False,
                error=f"Google VLM generation failed: {error_msg}",
                error_type=error_type
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
            media_type: Image media type (e.g., 'image/png', 'image/jpeg')
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds
            
        Returns:
            VLMResponse with generated text or error
        """
        try:
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            
            # Create image part for Google API
            image_part = {
                'mime_type': media_type,
                'data': image_data
            }
            
            # Combine system prompt and user prompt if system prompt exists
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Generate content with base64 image
            response = self.model.generate_content(
                [full_prompt, image_part],
                request_options={'timeout': timeout}
            )
            
            content = response.text
            
            return VLMResponse(
                success=True,
                content=content,
                metadata={
                    'model': self.model_id,
                    'media_type': media_type,
                    'finish_reason': response.candidates[0].finish_reason.name if response.candidates else None
                }
            )
            
        except Exception as e:
            error_msg = str(e)
            error_type = "processing_error"
            
            if "timeout" in error_msg.lower():
                error_type = "timeout_error"
            elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                error_type = "auth_error"
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                error_type = "quota_error"
            elif "connection" in error_msg.lower():
                error_type = "connection_error"
            elif "base64" in error_msg.lower() or "decode" in error_msg.lower():
                error_type = "decode_error"
            
            return VLMResponse(
                success=False,
                error=f"Google VLM generation from base64 failed: {error_msg}",
                error_type=error_type
            )
