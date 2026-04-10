"""
Ollama LLM Agent implementation.

Implements BaseLLMAgent for Ollama local language models.
"""

import requests
from typing import Dict, Any, Optional, List
from agents.base_llm_agent import BaseLLMAgent, LLMResponse


class OllamaLLMAgent(BaseLLMAgent):
    """
    Ollama LLM Agent for local language models.
    
    Supports any model available in Ollama (llama3, mistral, qwen, etc.).
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
        Initialize Ollama LLM agent.
        
        Args:
            model_id: Ollama model identifier (e.g., 'llama3', 'mistral')
            base_url: Ollama base URL (default: http://localhost:11434)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            **kwargs: Additional parameters
        """
        super().__init__(model_id, temperature, max_tokens, top_p, **kwargs)
        self.base_url = base_url
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 60
    ) -> LLMResponse:
        """
        Generate text from prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds
            
        Returns:
            LLMResponse with generated text or error
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return self.chat(messages, timeout)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        timeout: int = 60
    ) -> LLMResponse:
        """
        Chat completion with message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            timeout: Request timeout in seconds
            
        Returns:
            LLMResponse with generated text or error
        """
        try:
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
                
                return LLMResponse(
                    success=False,
                    error=f"Ollama error: {error_detail}",
                    error_type="api_error"
                )
            
            result = response.json()
            
            # Ollama response format
            if "message" not in result or "content" not in result["message"]:
                return LLMResponse(
                    success=False,
                    error="Invalid Ollama response: Missing 'message.content' field",
                    error_type="api_error"
                )
            
            content = result["message"]["content"]
            
            return LLMResponse(
                success=True,
                content=content,
                metadata={
                    'model': self.model_id,
                    'done': result.get('done', False),
                    'total_duration': result.get('total_duration'),
                    'load_duration': result.get('load_duration'),
                    'prompt_eval_count': result.get('prompt_eval_count'),
                    'eval_count': result.get('eval_count'),
                }
            )
            
        except requests.exceptions.ConnectionError as e:
            return LLMResponse(
                success=False,
                error=f"Ollama server is not running at {self.base_url}. Please start Ollama.",
                error_type="connection_error"
            )
        except requests.exceptions.Timeout as e:
            return LLMResponse(
                success=False,
                error=f"Request timed out after {timeout} seconds",
                error_type="timeout_error"
            )
        except Exception as e:
            return LLMResponse(
                success=False,
                error=f"LLM generation failed: {str(e)}",
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
