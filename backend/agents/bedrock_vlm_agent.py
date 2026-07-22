"""
AWS Bedrock VLM Agent implementation.

Implements BaseVLMAgent for AWS Bedrock models (Claude Haiku, Sonnet, etc.)
using the Bedrock Converse API with vision support.
"""

import os
import base64
import boto3
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from agents.base_vlm_agent import BaseVLMAgent, VLMResponse

logger = logging.getLogger(__name__)


class BedrockVLMAgent(BaseVLMAgent):
    """
    AWS Bedrock VLM Agent for vision-language models via Bedrock Converse API.

    Supports Claude models with vision capabilities (Haiku, Sonnet, etc.).
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
        # Extract region from ARN if present, otherwise use provided/env region
        self.region = self._resolve_region(model_id, region)
        self.client = boto3.client("bedrock-runtime", region_name=self.region)

    @staticmethod
    def _resolve_region(model_id: str, region: Optional[str] = None) -> str:
        """Extract region from ARN or fall back to provided/env region."""
        if model_id and model_id.startswith("arn:aws:bedrock:"):
            # ARN format: arn:aws:bedrock:<region>:<account>:...
            parts = model_id.split(":")
            if len(parts) >= 4 and parts[3]:
                return parts[3]
        return region or os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION", "ap-southeast-1")

    def generate_from_image(
        self,
        image_path: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 60,
    ) -> VLMResponse:
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            ext = Path(image_path).suffix.lower()
            media_map = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif", ".webp": "webp"}
            media_format = media_map.get(ext, "png")

            return self._converse(image_bytes, media_format, prompt, system_prompt, timeout)

        except IOError as e:
            return VLMResponse(success=False, error=f"Failed to read image: {e}", error_type="file_error")
        except Exception as e:
            return VLMResponse(success=False, error=f"Bedrock VLM failed: {e}", error_type="processing_error")

    def generate_from_images(
        self,
        image_paths: List[str],
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 60,
    ) -> VLMResponse:
        try:
            content = [{"text": prompt}]
            for image_path in image_paths:
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                ext = Path(image_path).suffix.lower()
                media_map = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif", ".webp": "webp"}
                media_format = media_map.get(ext, "png")
                content.append({
                    "image": {"format": media_format, "source": {"bytes": image_bytes}}
                })

            messages = [{"role": "user", "content": content}]
            kwargs = self._build_converse_kwargs(messages, system_prompt)
            response = self.client.converse(**kwargs)

            text = self._extract_text(response)
            return VLMResponse(
                success=True,
                content=text,
                metadata={"model": self.model_id, "image_count": len(image_paths)},
            )
        except Exception as e:
            return VLMResponse(success=False, error=f"Bedrock VLM failed: {e}", error_type="processing_error")

    def generate_from_base64(
        self,
        image_base64: str,
        prompt: str,
        media_type: str = "image/png",
        system_prompt: Optional[str] = None,
        timeout: int = 60,
    ) -> VLMResponse:
        try:
            image_bytes = base64.b64decode(image_base64)
            # Convert MIME type to Bedrock format
            format_map = {"image/png": "png", "image/jpeg": "jpeg", "image/gif": "gif", "image/webp": "webp"}
            media_format = format_map.get(media_type, "png")
            return self._converse(image_bytes, media_format, prompt, system_prompt, timeout)
        except Exception as e:
            return VLMResponse(success=False, error=f"Bedrock VLM failed: {e}", error_type="processing_error")

    def _converse(
        self,
        image_bytes: bytes,
        media_format: str,
        prompt: str,
        system_prompt: Optional[str],
        timeout: int,
    ) -> VLMResponse:
        """Call Bedrock Converse API with a single image."""
        try:
            content = [
                {"text": prompt},
                {"image": {"format": media_format, "source": {"bytes": image_bytes}}},
            ]
            messages = [{"role": "user", "content": content}]
            kwargs = self._build_converse_kwargs(messages, system_prompt)

            logger.info("Bedrock converse: model=%s region=%s", self.model_id, self.region)
            response = self.client.converse(**kwargs)

            text = self._extract_text(response)
            return VLMResponse(
                success=True,
                content=text,
                metadata={
                    "model": self.model_id,
                    "stop_reason": response.get("stopReason"),
                    "usage": response.get("usage"),
                },
            )
        except self.client.exceptions.ValidationException as e:
            return VLMResponse(success=False, error=f"Bedrock validation error: {e}", error_type="validation_error")
        except self.client.exceptions.ThrottlingException as e:
            return VLMResponse(success=False, error=f"Bedrock throttled: {e}", error_type="rate_limit_error")
        except self.client.exceptions.ModelTimeoutException as e:
            return VLMResponse(success=False, error=f"Bedrock timeout: {e}", error_type="timeout_error")
        except Exception as e:
            return VLMResponse(success=False, error=f"Bedrock API error: {e}", error_type="api_error")

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
