"""
Extraction processor module for structured data extraction using Poe API.

This module handles structured data extraction from OCR text using
LLM models via the Poe API (assistant, qwen3-max, gemini-3-pro).
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import openai
from .models import ExtractionConfig


@dataclass
class ExtractionResult:
    """Result of extraction processing operation."""
    success: bool
    structured_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    field_errors: Optional[Dict[str, str]] = None  # Field-level error messages
    partial_results: Optional[Dict[str, Any]] = None  # Partial results when extraction partially succeeds


class ExtractionProcessor:
    """
    Handles structured data extraction using Poe API models.
    
    This class uses OpenAI-compatible API to communicate with Poe models
    for extracting structured data from OCR text based on user-defined schemas.
    """
    
    def __init__(self, model_id: str):
        """
        Initialize extraction processor with Poe API configuration.
        
        Args:
            model_id: Poe model identifier (assistant, qwen3-max, or gemini-3-pro)
        """
        self.model_id = model_id
        
        # Get POE API key from environment
        api_key = os.getenv('POE_API_KEY')
        if not api_key:
            raise ValueError("POE_API_KEY environment variable is not set")
        
        # Initialize OpenAI client with Poe API configuration
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.poe.com/v1"
        )
    
    def extract_from_text(
        self, 
        text: str, 
        extraction_config: ExtractionConfig,
        timeout: int = 60
    ) -> ExtractionResult:
        """
        Extract structured data from OCR text using the configured Poe model.
        
        Args:
            text: OCR text to extract data from
            extraction_config: Extraction configuration with schema and target
            timeout: Timeout in seconds for LLM API call (default: 60)
            
        Returns:
            ExtractionResult with success status and extracted structured data or error
        """
        try:
            # Handle table row extraction separately
            # Convert target to string for comparison (handles both enum and string)
            target_str = extraction_config.target.value if hasattr(extraction_config.target, 'value') else str(extraction_config.target)
            if target_str == "table_row":
                return self._extract_table_rows(text, extraction_config, timeout)
            
            # Build extraction prompt for document or page level
            prompt = self._build_extraction_prompt(text, extraction_config)
            
            # Call Poe API with timeout
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extraction assistant. Extract structured data from the provided text according to the given schema. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=4096,
                timeout=timeout
            )
            
            # Parse response
            content = response.choices[0].message.content
            structured_data = self._parse_json_response(content)
            
            # Check if parsing failed (returned raw response)
            if isinstance(structured_data, dict) and "raw_response" in structured_data and len(structured_data) == 1:
                return ExtractionResult(
                    success=False,
                    error="Failed to parse LLM response as valid JSON",
                    error_type="parsing_error",
                    partial_results={"raw_response": content}
                )
            
            # Validate and convert fields, track errors
            field_errors = {}
            if isinstance(structured_data, dict):
                field_errors = self._validate_and_convert_fields(structured_data, extraction_config)
            elif isinstance(structured_data, list):
                # For arrays (page/table extraction), validate each item
                for item in structured_data:
                    if isinstance(item, dict):
                        item_errors = self._validate_and_convert_fields(item, extraction_config)
                        # Merge errors (we'll track all errors across items)
                        field_errors.update(item_errors)
            
            return ExtractionResult(
                success=True,
                structured_data=structured_data,
                field_errors=field_errors if field_errors else None
            )
            
        except openai.APITimeoutError as e:
            return ExtractionResult(
                success=False,
                error=f"LLM request timed out after {timeout} seconds. Try reducing document size or increasing timeout.",
                error_type="timeout_error"
            )
        except openai.APIConnectionError as e:
            return ExtractionResult(
                success=False,
                error=f"Failed to connect to Poe API: {str(e)}",
                error_type="connection_error"
            )
        except openai.APIError as e:
            return ExtractionResult(
                success=False,
                error=f"Poe API error: {str(e)}",
                error_type="api_error"
            )
        except json.JSONDecodeError as e:
            return ExtractionResult(
                success=False,
                error=f"Failed to parse extraction response as JSON: {str(e)}",
                error_type="parsing_error"
            )
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"Extraction failed: {str(e)}",
                error_type="processing_error"
            )
    
    def _extract_table_rows(
        self,
        text: str,
        extraction_config: ExtractionConfig,
        timeout: int = 60
    ) -> ExtractionResult:
        """
        Extract structured data from table rows in the text.
        
        This method first detects tables in the text, then extracts data
        from each row according to the schema.
        
        Args:
            text: OCR text containing table data
            extraction_config: Extraction configuration with schema
            timeout: Timeout in seconds for LLM API call (default: 60)
            
        Returns:
            ExtractionResult with array of structured data (one per row)
        """
        try:
            # Build schema description
            schema_desc = []
            for field in extraction_config.fields:
                field_type = field.type.value if hasattr(field.type, 'value') else str(field.type)
                field_info = f"- {field.name} ({field_type})"
                if field.description:
                    field_info += f": {field.description}"
                if field.required:
                    field_info += " [REQUIRED]"
                schema_desc.append(field_info)
            
            schema_text = "\n".join(schema_desc)
            
            # Build table row extraction prompt
            prompt = f"""
You are a data extraction assistant. Analyze the following text and extract data from each table row.

Schema (extract these fields for each row):
{schema_text}

Text to analyze:
---
{text}
---

Instructions:
1. Identify any tables in the text
2. For each row in the table, extract the fields according to the schema
3. Return a JSON array where each element represents one table row
4. If no tables are found, return an empty array []
5. For required fields, ensure they are present. Use null for missing optional fields.

Return ONLY a JSON array of objects, one object per table row. Example format:
[
  {{"field1": "value1", "field2": "value2"}},
  {{"field1": "value3", "field2": "value4"}}
]
"""
            
            # Call Poe API with timeout
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extraction assistant. Extract structured data from tables and return valid JSON arrays."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4096,
                timeout=timeout
            )
            
            # Parse response
            content = response.choices[0].message.content
            structured_data = self._parse_json_response(content)
            
            # Check if parsing failed (returned raw response)
            if isinstance(structured_data, dict) and "raw_response" in structured_data and len(structured_data) == 1:
                return ExtractionResult(
                    success=False,
                    error="Failed to parse LLM response as valid JSON",
                    error_type="parsing_error",
                    partial_results={"raw_response": content}
                )
            
            # Ensure we have an array
            if not isinstance(structured_data, list):
                # If single object returned, wrap in array
                if isinstance(structured_data, dict):
                    structured_data = [structured_data]
                else:
                    # No valid data, return empty array
                    structured_data = []
            
            # Validate and convert fields for each row, track errors
            field_errors = {}
            for item in structured_data:
                if isinstance(item, dict):
                    item_errors = self._validate_and_convert_fields(item, extraction_config)
                    # Merge errors (track all errors across rows)
                    field_errors.update(item_errors)
            
            return ExtractionResult(
                success=True,
                structured_data=structured_data,
                field_errors=field_errors if field_errors else None
            )
            
        except openai.APITimeoutError as e:
            return ExtractionResult(
                success=False,
                error=f"LLM request timed out after {timeout} seconds. Try reducing document size or increasing timeout.",
                error_type="timeout_error"
            )
        except openai.APIConnectionError as e:
            return ExtractionResult(
                success=False,
                error=f"Failed to connect to Poe API: {str(e)}",
                error_type="connection_error"
            )
        except openai.APIError as e:
            return ExtractionResult(
                success=False,
                error=f"Poe API error: {str(e)}",
                error_type="api_error"
            )
        except json.JSONDecodeError as e:
            return ExtractionResult(
                success=False,
                error=f"Failed to parse extraction response as JSON: {str(e)}",
                error_type="parsing_error"
            )
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"Table row extraction failed: {str(e)}",
                error_type="processing_error"
            )
    
    def _parse_json_response(self, content: str) -> Any:
        """
        Parse JSON from LLM response, handling markdown code blocks.
        
        Args:
            content: Raw response content from LLM
            
        Returns:
            Parsed JSON data (dict or list)
        """
        # Try to parse as JSON directly
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        import re
        
        # Try to find JSON object in code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON array in code blocks
        array_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object without code blocks
        obj_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON array without code blocks
        arr_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if arr_match:
            try:
                return json.loads(arr_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If all parsing fails, return raw response wrapped
        return {"raw_response": content}
    
    def _validate_and_convert_fields(
        self,
        data: Dict[str, Any],
        extraction_config: ExtractionConfig
    ) -> Dict[str, str]:
        """
        Validate extracted data against schema and track field-level errors.
        
        Args:
            data: Extracted data dictionary
            extraction_config: Extraction configuration with schema
            
        Returns:
            Dictionary mapping field names to error messages
        """
        field_errors = {}
        
        for field in extraction_config.fields:
            field_name = field.name
            field_type = field.type.value if hasattr(field.type, 'value') else str(field.type)
            
            # Check if required field is missing
            if field.required and (field_name not in data or data[field_name] is None):
                field_errors[field_name] = f"Required field '{field_name}' is missing or null"
                continue
            
            # Skip validation if field is not present (optional field)
            if field_name not in data:
                continue
            
            value = data[field_name]
            
            # Skip null values for optional fields
            if value is None:
                continue
            
            # Validate and convert field types
            try:
                if field_type == 'number':
                    # Try to convert to number
                    if isinstance(value, str):
                        # Try int first, then float
                        try:
                            data[field_name] = int(value)
                        except ValueError:
                            data[field_name] = float(value)
                    elif not isinstance(value, (int, float)):
                        raise ValueError(f"Cannot convert {type(value).__name__} to number")
                
                elif field_type == 'boolean':
                    # Try to convert to boolean
                    if isinstance(value, str):
                        value_lower = value.lower().strip()
                        if value_lower in ('true', 'yes', '1', 'y'):
                            data[field_name] = True
                        elif value_lower in ('false', 'no', '0', 'n'):
                            data[field_name] = False
                        else:
                            raise ValueError(f"Cannot convert '{value}' to boolean")
                    elif not isinstance(value, bool):
                        raise ValueError(f"Cannot convert {type(value).__name__} to boolean")
                
                elif field_type == 'date':
                    # Try to parse date
                    if isinstance(value, str):
                        from datetime import datetime
                        # Try common date formats
                        date_formats = [
                            '%Y-%m-%d',
                            '%m/%d/%Y',
                            '%d/%m/%Y',
                            '%Y/%m/%d',
                            '%B %d, %Y',
                            '%d %B %Y',
                            '%m-%d-%Y',
                            '%d-%m-%Y'
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
                            raise ValueError(f"Cannot parse '{value}' as date")
                    elif not isinstance(value, str):
                        raise ValueError(f"Cannot convert {type(value).__name__} to date")
                
                elif field_type == 'string':
                    # Convert to string if not already
                    if not isinstance(value, str):
                        data[field_name] = str(value)
            
            except (ValueError, TypeError) as e:
                field_errors[field_name] = f"Type conversion error: {str(e)}"
        
        return field_errors
    
    def _build_extraction_prompt(
        self, 
        text: str, 
        extraction_config: ExtractionConfig
    ) -> str:
        """
        Build extraction prompt from text and configuration.
        
        Args:
            text: OCR text to extract from
            extraction_config: Extraction configuration
            
        Returns:
            Formatted prompt string
        """
        # Build schema description
        schema_desc = []
        for field in extraction_config.fields:
            # Convert enum to string value
            field_type = field.type.value if hasattr(field.type, 'value') else str(field.type)
            field_info = f"- {field.name} ({field_type})"
            if field.description:
                field_info += f": {field.description}"
            if field.required:
                field_info += " [REQUIRED]"
            schema_desc.append(field_info)
        
        schema_text = "\n".join(schema_desc)
        
        # Build prompt based on target
        # Convert target to string for dictionary lookup (handles both enum and string)
        target_str = extraction_config.target.value if hasattr(extraction_config.target, 'value') else str(extraction_config.target)
        target_desc = {
            "document": "Extract data from the entire document",
            "page": "Extract data from each page separately",
            "table_row": "Extract data from each table row"
        }.get(target_str, "Extract data")
        
        prompt = f"""
{target_desc} according to the following schema:

{schema_text}

Text to extract from:
---
{text}
---

Return the extracted data as a JSON object. For required fields, ensure they are present. If a field cannot be found, use null for optional fields or your best estimate for required fields.
"""
        
        return prompt.strip()
