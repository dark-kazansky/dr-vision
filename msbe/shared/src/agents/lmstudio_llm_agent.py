"""
LM Studio LLM Agent implementation.

Implements BaseLLMAgent for LM Studio local models.
"""

import requests
from typing import Dict, Any, Optional, List
from agents.base_llm_agent import BaseLLMAgent, LLMResponse


class LMStudioLLMAgent(BaseLLMAgent):
    """
    LM Studio LLM Agent for local language models.
    
    Supports any model loaded in LM Studio with OpenAI-compatible API.
    """
    
    def __init__(
        self,
        model_id: str,
        base_url: str = "http://localhost:1234",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        **kwargs
    ):
        """
        Initialize LM Studio LLM agent.
        
        Args:
            model_id: Model identifier
            base_url: LM Studio base URL
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
            endpoint = f"{self.base_url}/v1/chat/completions"
            
            payload = {
                "model": self.model_id,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            
            response = requests.post(endpoint, json=payload, timeout=timeout)
            
            if response.status_code != 200:
                return LLMResponse(
                    success=False,
                    error=f"LM Studio error: HTTP {response.status_code}",
                    error_type="api_error"
                )
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            return LLMResponse(
                success=True,
                content=content,
                metadata={
                    'model': self.model_id,
                    'finish_reason': result["choices"][0].get("finish_reason")
                }
            )
            
        except requests.exceptions.ConnectionError as e:
            return LLMResponse(
                success=False,
                error=f"LM Studio server is not running at {self.base_url}",
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
