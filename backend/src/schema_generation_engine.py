"""Schema generation engine module."""

import os
import json
import re
from typing import List, Optional
from dataclasses import dataclass
import openai
from .models import SchemaField, FieldType


@dataclass
class SchemaGenerationResult:
    """Result of schema generation operation."""
    success: bool
    schema: Optional[List[SchemaField]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class SchemaGenerationEngine:
    """Handles automatic schema generation using Poe API models."""
    
    def __init__(self, model_id: str = "qwen3-max"):
        """Initialize schema generation engine."""
        self.model_id = model_id
        api_key = os.getenv('POE_API_KEY')
        if not api_key:
            raise ValueError("POE_API_KEY not set")
        self.client = openai.OpenAI(api_key=api_key, base_url="https://api.poe.com/v1")

    def generate_schema(self, prompt: str, sample_text: Optional[str] = None) -> SchemaGenerationResult:
        """Generate extraction schema."""
        try:
            generation_prompt = self._build_generation_prompt(prompt, sample_text)
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "Generate extraction schemas. Return only valid JSON arrays."},
                    {"role": "user", "content": generation_prompt}
                ],
                temperature=0.3,
                max_tokens=4096
            )
            content = response.choices[0].message.content
            schema = self._parse_schema_response(content)
            if not schema:
                return SchemaGenerationResult(success=False, error="Failed to parse schema", error_type="parsing_error")
            return SchemaGenerationResult(success=True, schema=schema)
        except Exception as e:
            return SchemaGenerationResult(success=False, error=str(e), error_type="processing_error")

    def _build_generation_prompt(self, user_prompt: str, sample_text: Optional[str] = None) -> str:
        """Build LLM prompt."""
        prompt = f"Generate schema for: {user_prompt}\n\n"
        if sample_text:
            prompt += f"Sample: {sample_text[:2000]}\n\n"
        prompt += 'Return JSON array: [{"name": "field", "type": "string", "description": "desc", "required": true}]'
        return prompt
    
    def _parse_schema_response(self, response: str) -> Optional[List[SchemaField]]:
        """Parse LLM response."""
        try:
            try:
                schema_data = json.loads(response)
            except json.JSONDecodeError:
                match = re.search(r'\[.*?\]', response, re.DOTALL)
                if match:
                    schema_data = json.loads(match.group(0))
                else:
                    return None
            if not isinstance(schema_data, list):
                return None
            fields = []
            for data in schema_data:
                if 'name' in data and 'type' in data:
                    try:
                        field = SchemaField(
                            name=data['name'],
                            type=FieldType(data.get('type', 'string')),
                            description=data.get('description', ''),
                            required=data.get('required', False)
                        )
                        fields.append(field)
                    except:
                        continue
            return fields if fields else None
        except:
            return None
