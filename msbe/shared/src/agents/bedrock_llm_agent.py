"""
AWS Bedrock LLM Agent implementation.

Implements BaseLLMAgent for AWS Bedrock models (Claude Haiku, Sonnet, etc.)
using the Bedrock Converse API for text-only generation.
"""

import os
import boto3
import logging
from typing import Dict, Any, Optional, List
from agents.base_llm_agent import BaseLLMAgent, LLMResponse

logger = logging.getLogger(__name__)


class BedrockLLMAgent(BaseLLMAgent):
    """
    AWS Bedrock LLM Agent using the Converse API.

    Supports Claude models for text generation.
    Uses inference profile ARNs or standard model IDs.
    """

    def __init__(
        self,
        model_id: str,
        region: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        **kwargs
    ):
        super().__init__(model_id, temperature, max_tokens, top_p, **kwargs)
        self.region = self._resolve_region(model_id, region)
        self.client = boto3.client("bedrock-runtime", region_name=self.region)

    @staticmethod
    def _resolve_region(model_id: str, region: Optional[str] = None) -> str:
        """Extract region from ARN or fall back to provided/env region."""
        if model_id and model_id.startswith("arn:aws:bedrock:"):
            parts = model_id.split(":")
            if len(parts) >= 4 and parts[3]:
                return parts[3]
        return region or os.getenv("BEDROCK_REGION", "ap-southeast-2")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 60,
    ) -> LLMResponse:
        try:
            messages = [{"role": "user", "content": [{"text": prompt}]}]
            kwargs = self._build_converse_kwargs(messages, system_prompt)

            logger.info("Bedrock LLM converse: model=%s region=%s", self.model_id, self.region)
            response = self.client.converse(**kwargs)

            text = self._extract_text(response)
            return LLMResponse(
                success=True,
                content=text,
                metadata={
                    "model": self.model_id,
                    "stop_reason": response.get("stopReason"),
                    "usage": response.get("usage"),
                },
            )
        except Exception as e:
            return LLMResponse(success=False, error=f"Bedrock API error: {e}", error_type="api_error")

    def chat(
        self,
        messages: List[Dict[str, str]],
        timeout: int = 60,
    ) -> LLMResponse:
        try:
            bedrock_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                if role == "system":
                    continue  # system handled separately
                bedrock_messages.append({
                    "role": role,
                    "content": [{"text": msg.get("content", "")}],
                })

            system_prompt = None
            for msg in messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content")
                    break

            kwargs = self._build_converse_kwargs(bedrock_messages, system_prompt)
            response = self.client.converse(**kwargs)
            text = self._extract_text(response)

            return LLMResponse(
                success=True,
                content=text,
                metadata={"model": self.model_id},
            )
        except Exception as e:
            return LLMResponse(success=False, error=f"Bedrock API error: {e}", error_type="api_error")

    def _build_converse_kwargs(self, messages: list, system_prompt: Optional[str]) -> dict:
        kwargs = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
            },
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]
        return kwargs

    @staticmethod
    def _extract_text(response: dict) -> str:
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])
        parts = [block["text"] for block in content if "text" in block]
        return "\n".join(parts)
