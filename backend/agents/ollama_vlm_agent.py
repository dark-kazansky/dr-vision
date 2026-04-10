"""
Ollama VLM Agent implementation.

Implements BaseVLMAgent for Ollama vision-language models.
"""

import base64
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from agents.base_vlm_agent import BaseVLMAgent, VLMResponse


class OllamaVLMAgent(BaseVLMAgent):
    """
    Ollama VLM Agent for local vision-language models.
    
    Supports vision models in Ollama (llava, bakllava, etc.).
    """
    
    def __init__(
        self,
        model_id: str,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        **kwargs
    ):
        """
        Initialize Ollama VLM agent.
        
        Args:
            model_id: Ollama model identifier (e.g., 'llava', 'bakllava')
            base_url: Ollama base URL (default: http://localhost:11434)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            **kwargs: Additional parameters
        """
        super().__init__(model_id, temperature, max_tokens, top_p, **kwargs)
        self.base_url = base_url
    
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
            
            return self.generate_from_base64(
                image_data,
                prompt,
                system_prompt=system_prompt,
                timeout=timeout
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
            # Encode all images
            images = []
            for image_path in image_paths:
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                    images.append(image_data)
            
            # Build messages
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Ollama supports multiple images in a single message
            messages.append({
                "role": "user",
                "content": prompt,
                "images": images
            })
            
            # Call API
            endpoint = f"{self.base_url}/api/chat"
            
            payload = {
                "model": self.model_id,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "top_p": self.top_p,
                }
            }
            
            response = requests.post(endpoint, json=payload, timeout=timeout)
            
            if response.status_code != 200:
                error_detail = f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    if 'error' in error_json:
                        error_detail = f"{error_detail}: {error_json['error']}"
                except:
                    error_detail = f"{error_detail}: {response.text[:200]}"
                
                return VLMResponse(
                    success=False,
                    error=f"Ollama error: {error_detail}",
                    error_type="api_error"
                )
            
            result = response.json()
            
            if "message" not in result or "content" not in result["message"]:
                return VLMResponse(
                    success=False,
                    error="Invalid Ollama response: Missing 'message.content' field",
                    error_type="api_error"
                )
            
            content = result["message"]["content"]
            
            return VLMResponse(
                success=True,
                content=content,
                metadata={
                    'model': self.model_id,
                    'image_count': len(image_paths),
                    'done': result.get('done', False),
                    'total_duration': result.get('total_duration'),
                    'eval_count': result.get('eval_count'),
                }
            )
            
        except requests.exceptions.ConnectionError as e:
            return VLMResponse(
                success=False,
                error=f"Ollama server is not running at {self.base_url}. Please start Ollama.",
                error_type="connection_error"
            )
        except requests.exceptions.Timeout as e:
            return VLMResponse(
                success=False,
                error=f"Request timed out after {timeout} seconds",
                error_type="timeout_error"
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
            media_type: Image media type (not used by Ollama, kept for compatibility)
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds
            
        Returns:
            VLMResponse with generated text or error
        """
        try:
            # Build messages
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Ollama expects images as base64 strings in the images array
            messages.append({
                "role": "user",
                "content": prompt,
                "images": [image_base64]
            })
            
            # Call API
            endpoint = f"{self.base_url}/api/chat"
            
            payload = {
                "model": self.model_id,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "top_p": self.top_p,
                }
            }
            
            response = requests.post(endpoint, json=payload, timeout=timeout)
            
            if response.status_code != 200:
                error_detail = f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    if 'error' in error_json:
                        error_detail = f"{error_detail}: {error_json['error']}"
                except:
                    error_detail = f"{error_detail}: {response.text[:200]}"
                
                return VLMResponse(
                    success=False,
                    error=f"Ollama error: {error_detail}",
                    error_type="api_error"
                )
            
            result = response.json()
            
            if "message" not in result or "content" not in result["message"]:
                return VLMResponse(
                    success=False,
                    error="Invalid Ollama response: Missing 'message.content' field",
                    error_type="api_error"
                )
            
            content = result["message"]["content"]
            
            return VLMResponse(
                success=True,
                content=content,
                metadata={
                    'model': self.model_id,
                    'done': result.get('done', False),
                    'total_duration': result.get('total_duration'),
                    'eval_count': result.get('eval_count'),
                }
            )
            
        except requests.exceptions.ConnectionError as e:
            return VLMResponse(
                success=False,
                error=f"Ollama server is not running at {self.base_url}. Please start Ollama.",
                error_type="connection_error"
            )
        except requests.exceptions.Timeout as e:
            return VLMResponse(
                success=False,
                error=f"Request timed out after {timeout} seconds",
                error_type="timeout_error"
            )
        except Exception as e:
            return VLMResponse(
                success=False,
                error=f"VLM generation failed: {str(e)}",
                error_type="processing_error"
            )
    
    def check_model_available(self) -> bool:
        """
        Check if the model is available in Ollama.
        
        Returns:
            True if model is available
        """
        try:
            endpoint = f"{self.base_url}/api/tags"
            response = requests.get(endpoint, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                models = result.get('models', [])
                
                # Check if model exists
                for model in models:
                    if model.get('name') == self.model_id or model.get('name', '').startswith(f"{self.model_id}:"):
                        return True
            
            return False
            
        except:
            return False
    
    def pull_model(self, timeout: int = 300) -> bool:
        """
        Pull/download the model from Ollama registry.
        
        Args:
            timeout: Request timeout in seconds (default: 300 for large models)
            
        Returns:
            True if model was pulled successfully
        """
        try:
            endpoint = f"{self.base_url}/api/pull"
            
            payload = {
                "name": self.model_id,
                "stream": False
            }
            
            response = requests.post(endpoint, json=payload, timeout=timeout)
            
            return response.status_code == 200
            
        except:
            return False
