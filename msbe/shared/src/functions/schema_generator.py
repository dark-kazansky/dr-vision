"""
Schema Generator function for dynamic schema generation.

This function generates extraction schemas based on document text and user prompts.
"""

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from agents import BaseLLMAgent
from core import SchemaField, FieldType
from core.utils import strip_code_blocks


@dataclass
class GenerateSchemaResult:
    """Result of schema generation operation."""
    success: bool
    fields: Optional[List[SchemaField]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class SchemaGenerator:
    """
    Schema generator for creating extraction schemas using LLM agents.
    """
    
    def __init__(self, agent: BaseLLMAgent):
        """
        Initialize schema generator.
        
        Args:
            agent: LLM agent for schema generation
        """
        self.agent = agent
    
    def generate(
        self,
        text: str,
        prompt: str,
        timeout: int = 60
    ) -> GenerateSchemaResult:
        """
        Generate extraction schema based on text and prompt.
        
        Args:
            text: Document text to analyze
            prompt: User prompt describing what to extract
            timeout: Request timeout in seconds
            
        Returns:
            GenerateSchemaResult with generated schema fields
        """
        try:
            # Build prompt
            full_prompt = self._build_prompt(text, prompt)
            
            # Call LLM
            response = self.agent.generate(full_prompt, timeout=timeout)
            
            if not response.success:
                return GenerateSchemaResult(
                    success=False,
                    error=response.error,
                    error_type=response.error_type
                )
            
            # Parse response
            return self._parse_response(response.content)
            
        except Exception as e:
            return GenerateSchemaResult(
                success=False,
                error=f"Schema generation failed: {str(e)}",
                error_type="processing_error"
            )
    
    def _build_prompt(self, text: str, user_prompt: str) -> str:
        """Build schema generation prompt."""
        prompt = f"""Analyze this document and generate an extraction schema based on the user's request.

User request: {user_prompt}

Document text:
{text[:2000]}

Generate a JSON schema with fields to extract. Each field should have:
- name: field name (snake_case)
- type: one of "string", "number", "date", "boolean"
- description: what this field represents
- required: true or false

Example response:
{{
    "fields": [
        {{"name": "vendor_name", "type": "string", "description": "Name of the vendor", "required": true}},
        {{"name": "total_amount", "type": "number", "description": "Total amount", "required": true}},
        {{"name": "invoice_date", "type": "date", "description": "Invoice date", "required": false}}
    ]
}}

Respond ONLY with valid JSON."""
        
        return prompt
    
    def _parse_response(self, content: str) -> GenerateSchemaResult:
        """Parse LLM response."""
        try:
            # Remove markdown code blocks
            content = strip_code_blocks(content)
            
            # Parse JSON
            data = json.loads(content)
            
            # Convert to SchemaField objects
            fields = []
            for field_data in data.get('fields', []):
                field_type_str = field_data.get('type', 'string')
                field_type = FieldType(field_type_str)
                
                field = SchemaField(
                    name=field_data.get('name'),
                    type=field_type,
                    description=field_data.get('description', ''),
                    required=field_data.get('required', False)
                )
                fields.append(field)
            
            return GenerateSchemaResult(
                success=True,
                fields=fields
            )
            
        except json.JSONDecodeError as e:
            return GenerateSchemaResult(
                success=False,
                error=f"Failed to parse response: {str(e)}",
                error_type="parsing_error"
            )
        except Exception as e:
            return GenerateSchemaResult(
                success=False,
                error=f"Failed to process schema: {str(e)}",
                error_type="processing_error"
            )
