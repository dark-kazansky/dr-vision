"""
Agent system for Dr.Vision.

This module provides base agent classes and implementations for:
- LLM agents (text-based language models)
- VLM agents (vision-language models)
- OCR agents (specialized OCR models)
"""

from agents.base_llm_agent import BaseLLMAgent
from agents.base_vlm_agent import BaseVLMAgent
from agents.base_ocr_agent import BaseOCRAgent

# LLM implementations
from agents.poe_llm_agent import POELLMAgent
from agents.lmstudio_llm_agent import LMStudioLLMAgent
from agents.ollama_llm_agent import OllamaLLMAgent
from agents.google_llm_agent import GoogleLLMAgent
from agents.bedrock_llm_agent import BedrockLLMAgent

# VLM implementations
from agents.poe_vlm_agent import POEVLMAgent
from agents.lmstudio_vlm_agent import LMStudioVLMAgent
from agents.ollama_vlm_agent import OllamaVLMAgent
from agents.google_vlm_agent import GoogleVLMAgent
from agents.bedrock_vlm_agent import BedrockVLMAgent

# OCR implementations
from agents.lmstudio_ocr_agent import LMStudioOCRAgent
from agents.vllm_ocr_agent import VLLMOCRAgent

# Adapters
from agents.vlm_ocr_adapter import VLMOCRAdapter

# Factory
from agents.factory import AgentFactory

__all__ = [
    # Base classes
    'BaseLLMAgent',
    'BaseVLMAgent',
    'BaseOCRAgent',
    
    # LLM implementations
    'POELLMAgent',
    'LMStudioLLMAgent',
    'OllamaLLMAgent',
    'GoogleLLMAgent',
    'BedrockLLMAgent',
    
    # VLM implementations
    'POEVLMAgent',
    'LMStudioVLMAgent',
    'OllamaVLMAgent',
    'GoogleVLMAgent',
    'BedrockVLMAgent',
    
    # OCR implementations
    'LMStudioOCRAgent',
    'VLLMOCRAgent',
    
    # Adapters
    'VLMOCRAdapter',

    # Factory
    'AgentFactory',
]
