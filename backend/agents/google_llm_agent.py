"""
Google Studio LLM Agent implementation.

Implements BaseLLMAgent for Google Gemini API (gemini-1.5-flash, gemini-1.5-pro, etc.).
"""

import os
import google.generativeai as genai
from typing import Dict, Any, Optional, List
from agents.base_llm_agent import BaseLLMAgent, LLMResponse


class GoogleLLMAgent(BaseLLMAgent):
    """
    Google Studio LLM Agent for text-based language models via Google Gemini API.
    
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
        Initialize Google Studio LLM agent.
        
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
        try:
            # Combine system prompt and user prompt if system prompt exists
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Generate content
            response = self.model.generate_content(
                full_prompt,
                request_options={'timeout': timeout}
            )
            
            # Extract text from response
            content = response.text
            
            return LLMResponse(
                success=True,
                content=content,
                metadata={
                    'model': self.model_id,
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
            
        except Exception as e:
            error_msg = str(e)
            error_type = "processing_error"
            
            # Categorize error types
            if "timeout" in error_msg.lower():
                error_type = "timeout_error"
            elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                error_type = "auth_error"
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                error_type = "quota_error"
            elif "connection" in error_msg.lower():
                error_type = "connection_error"
            
            return LLMResponse(
                success=False,
                error=f"Google LLM generation failed: {error_msg}",
                error_type=error_type
            )
    
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
            # Convert messages to Google format
            chat_history = []
            system_instruction = None
            
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                
                if role == 'system':
                    # Google uses system_instruction separately
                    system_instruction = content
                elif role == 'user':
                    chat_history.append({
                        'role': 'user',
                        'parts': [content]
                    })
                elif role == 'assistant':
                    chat_history.append({
                        'role': 'model',
                        'parts': [content]
                    })
            
            # Create chat session
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=self.model_id,
                    generation_config={
                        'temperature': self.temperature,
                        'max_output_tokens': self.max_tokens,
                        'top_p': self.top_p,
                    },
                    system_instruction=system_instruction
                )
            else:
                model = self.model
            
            chat = model.start_chat(history=chat_history[:-1] if len(chat_history) > 1 else [])
            
            # Send last message
            last_message = chat_history[-1]['parts'][0] if chat_history else ""
            response = chat.send_message(
                last_message,
                request_options={'timeout': timeout}
            )
            
            content = response.text
            
            return LLMResponse(
                success=True,
                content=content,
                metadata={
                    'model': self.model_id,
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
            
            return LLMResponse(
                success=False,
                error=f"Google chat completion failed: {error_msg}",
                error_type=error_type
            )
