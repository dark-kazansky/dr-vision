"""
Extractor function for structured data extraction.

This function extracts structured data from text based on provided schemas.
"""

import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

from agents import BaseLLMAgent
from core import ExtractionConfig


@dataclass
class ExtractResult:
    """Result of extraction operation."""
    success: bool
    structured_data: Optional[Dict[str, Any]] = None
    field_errors: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class Extractor:
    """
    Extractor for structured data extraction using LLM agents.
    """
    
    def __init__(self, agent: BaseLLMAgent):
        """
        Initialize extractor.
        
        Args:
            agent: LLM agent for extraction
        """
        self.agent = agent
    
    def extract(
        self,
        text: str,
        config: ExtractionConfig,
        timeout: int = 60
    ) -> ExtractResult:
        """
        Extract structured data from text.
        
        Args:
            text: Text to extract from
            config: Extraction configuration with schema
            timeout: Request timeout in seconds
            
        Returns:
            ExtractResult with structured data
        """
        try:
            # Build prompt
            prompt = self._build_prompt(text, config)
            
            # Call LLM
            response = self.agent.generate(prompt, timeout=timeout)
            
            if not response.success:
                return ExtractResult(
                    success=False,
                    error=response.error,
                    error_type=response.error_type
                )
            
            # Parse response
            return self._parse_response(response.content, config)
            
        except Exception as e:
            return ExtractResult(
                success=False,
                error=f"Extraction failed: {str(e)}",
                error_type="processing_error"
            )
    
    def _build_prompt(self, text: str, config: ExtractionConfig) -> str:
        """Build extraction prompt."""
        # Build schema description
        schema_desc = []
        for field in config.fields:
            field_type = field.type.value if hasattr(field.type, 'value') else str(field.type)
            field_info = f"- {field.name} ({field_type})"
            if field.description:
                field_info += f": {field.description}"
            if field.required:
                field_info += " [REQUIRED]"
            schema_desc.append(field_info)
        
        schema_text = "\n".join(schema_desc)
        
        # Build target description
        target_str = config.target.value if hasattr(config.target, 'value') else str(config.target)
        target_desc = {
            "document": "Extract data from the entire document",
            "page": "Extract data from each page separately",
            "table_row": "Extract data from each table row"
        }.get(target_str, "Extract data")
        
        prompt = f"""{target_desc} according to this schema:

{schema_text}

Text to extract from:
---
{text}
---

Return the extracted data as JSON. For required fields, ensure they are present. Use null for missing optional fields.

Respond ONLY with valid JSON."""
        
        return prompt
    
    def _parse_response(self, content: str, config: ExtractionConfig) -> ExtractResult:
        """Parse LLM response."""
        try:
            # Remove markdown code blocks
            if content.startswith('```'):
                lines = content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines).strip()
            
            # Parse JSON
            structured_data = json.loads(content)
            
            # Validate and convert fields
            field_errors = self._validate_fields(structured_data, config)
            
            return ExtractResult(
                success=True,
                structured_data=structured_data,
                field_errors=field_errors if field_errors else None
            )
            
        except json.JSONDecodeError as e:
            return ExtractResult(
                success=False,
                error=f"Failed to parse response: {str(e)}",
                error_type="parsing_error"
            )
    
    def _validate_fields(
        self,
        data: Dict[str, Any],
        config: ExtractionConfig
    ) -> Dict[str, str]:
        """Validate extracted data against schema."""
        field_errors = {}
        
        for field in config.fields:
            field_name = field.name
            field_type = field.type.value if hasattr(field.type, 'value') else str(field.type)
            
            # Check required fields
            if field.required and (field_name not in data or data[field_name] is None):
                field_errors[field_name] = f"Required field '{field_name}' is missing"
                continue
            
            # Skip if field not present
            if field_name not in data or data[field_name] is None:
                continue
            
            value = data[field_name]
            
            # Type validation
            try:
                if field_type == 'number':
                    if isinstance(value, str):
                        try:
                            data[field_name] = int(value)
                        except ValueError:
                            data[field_name] = float(value)
                    elif not isinstance(value, (int, float)):
                        raise ValueError(f"Cannot convert to number")
                
                elif field_type == 'boolean':
                    if isinstance(value, str):
                        value_lower = value.lower().strip()
                        if value_lower in ('true', 'yes', '1', 'y'):
                            data[field_name] = True
                        elif value_lower in ('false', 'no', '0', 'n'):
                            data[field_name] = False
                        else:
                            raise ValueError(f"Cannot convert to boolean")
                    elif not isinstance(value, bool):
                        raise ValueError(f"Cannot convert to boolean")
                
                elif field_type == 'date':
                    if isinstance(value, str):
                        from datetime import datetime
                        date_formats = [
                            '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y',
                            '%Y/%m/%d', '%B %d, %Y', '%d %B %Y',
                            '%m-%d-%Y', '%d-%m-%Y'
                        ]
                        parsed = False
                        for fmt in date_formats:
                            try:
                                datetime.strptime(value, fmt)
                                parsed = True
                                break
                            except ValueError:
                                continue
                        if not parsed:
                            raise ValueError(f"Cannot parse date")
                
                elif field_type == 'string':
                    if not isinstance(value, str):
                        data[field_name] = str(value)
            
            except (ValueError, TypeError) as e:
                field_errors[field_name] = f"Type conversion error: {str(e)}"
        
        return field_errors
