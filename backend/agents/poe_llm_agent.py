"""
POE LLM Agent implementation.

Implements BaseLLMAgent for POE API (assistant, qwen3-max, gemini-3-pro, etc.).
"""

import os
import openai
from typing import Dict, Any, Optional, List
from agents.base_llm_agent import BaseLLMAgent, LLMResponse


class POELLMAgent(BaseLLMAgent):
    """
    POE LLM Agent for text-based language models via POE API.
    
    Supports models: assistant, qwen3-max, gemini-3-pro, claude-opus-4.5, etc.
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
        Initialize POE LLM agent.
        
        Args:
            model_id: POE model identifier
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
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=timeout
            )
            
            content = response.choices[0].message.content
            
            return LLMResponse(
                success=True,
                content=content,
                metadata={
                    'model': self.model_id,
                    'finish_reason': response.choices[0].finish_reason
                }
            )
            
        except openai.APITimeoutError as e:
            return LLMResponse(
                success=False,
                error=f"POE API timeout after {timeout} seconds: {str(e)}",
                error_type="timeout_error"
            )
        except openai.APIConnectionError as e:
            return LLMResponse(
                success=False,
                error=f"Failed to connect to POE API: {str(e)}",
                error_type="connection_error"
            )
        except openai.APIError as e:
            return LLMResponse(
                success=False,
                error=f"POE API error: {str(e)}",
                error_type="api_error"
            )
        except Exception as e:
            return LLMResponse(
                success=False,
                error=f"LLM generation failed: {str(e)}",
                error_type="processing_error"
            )
