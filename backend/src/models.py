"""
Pydantic models for request/response validation.

This module defines all data models used for API request validation,
response serialization, and data transfer objects in the OCR Web UI application.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class TierEnum(str, Enum):
    """OCR processing tier options."""
    RAPID = "Rapid"
    NORMAL = "Normal"
    ADVANCE = "Advance"


class FieldType(str, Enum):
    """Field type enumeration for extraction schema fields."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"


class ExtractionTarget(str, Enum):
    """Extraction target enumeration for specifying extraction scope."""
    DOCUMENT = "document"
    PAGE = "page"
    TABLE_ROW = "table_row"


class OCRRequest(BaseModel):
    """Request model for OCR processing.
    
    This model validates incoming OCR requests and ensures all required
    parameters are present and valid.
    """
    model_id: str = Field(
        ..., 
        description="Model ID to use for OCR processing. Must match a model configured in config.yaml"
    )
    process_all_pages: bool = Field(
        False, 
        description="Whether to process all pages of a PDF document. If False, only the first page is processed"
    )
    tier: TierEnum = Field(
        TierEnum.NORMAL, 
        description="Processing tier that determines OCR quality and speed (Rapid, Normal, or Advance)"
    )


class SchemaField(BaseModel):
    """Schema field definition for extraction configuration.
    
    This model defines a single field in an extraction schema, including
    its name, data type, description, and whether it's required.
    """
    name: str = Field(
        ..., 
        min_length=1, 
        description="Field name - must be non-empty and unique within the schema"
    )
    type: FieldType = Field(
        ..., 
        description="Field data type (string, number, boolean, or date)"
    )
    description: str = Field(
        default="", 
        description="Human-readable description of what this field represents"
    )
    required: bool = Field(
        default=False, 
        description="Whether this field must be present in extraction results"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate field name is not empty and contains valid characters."""
        if not v or not v.strip():
            raise ValueError("Field name cannot be empty")
        # Allow alphanumeric, underscore, hyphen, and spaces
        if not all(c.isalnum() or c in ('_', '-', ' ') for c in v):
            raise ValueError("Field name contains invalid characters")
        return v.strip()


class ExtractionConfig(BaseModel):
    """Extraction configuration model.
    
    This model defines the complete extraction configuration including
    the target scope (document, page, or table row) and the schema
    defining what fields to extract.
    """
    enabled: bool = Field(
        default=False, 
        description="Whether extraction is enabled for this OCR request"
    )
    target: ExtractionTarget = Field(
        ..., 
        description="Extraction target scope - determines result structure"
    )
    fields: List[SchemaField] = Field(
        ..., 
        min_items=1, 
        description="List of fields to extract - must contain at least one field",
        alias="schema"
    )
    
    model_config = {"populate_by_name": True}
    
    @validator('fields')
    def validate_unique_names(cls, v):
        """Validate all field names are unique within the schema."""
        names = [field.name for field in v]
        if len(names) != len(set(names)):
            raise ValueError("Schema field names must be unique")
        return v


class ExtractionResult(BaseModel):
    """Extraction result model.
    
    This model represents the result of a structured extraction operation,
    including the extracted data and any errors that occurred.
    """
    success: bool = Field(
        ..., 
        description="Whether the extraction operation completed successfully"
    )
    structured_data: Optional[Any] = Field(
        None, 
        description="Extracted structured data - single object for document target, list for page/table_row targets"
    )
    extraction_config: Optional[ExtractionConfig] = Field(
        None, 
        description="The extraction configuration that was used"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message if extraction failed"
    )
    error_type: Optional[str] = Field(
        None, 
        description="Type of error that occurred (e.g., 'validation_error', 'processing_error', 'extraction_error')"
    )


class OCRResponse(BaseModel):
    """Response model for OCR processing.
    
    This model represents the result of an OCR operation, including
    success status, extracted text, structured data (if extraction enabled),
    or error information.
    """
    success: bool = Field(
        ..., 
        description="Whether the OCR operation completed successfully"
    )
    text: Optional[str] = Field(
        None, 
        description="Extracted text from the OCR operation. Present only if success is True"
    )
    structured_data: Optional[Any] = Field(
        None, 
        description="Extracted structured data when extraction is enabled. Single object for document target, list for page/table_row targets"
    )
    extraction_config: Optional[Dict[str, Any]] = Field(
        None, 
        description="The extraction configuration that was used, if extraction was enabled"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message describing what went wrong. Present only if success is False"
    )
    error_type: Optional[str] = Field(
        None, 
        description="Type of error that occurred (e.g., 'invalid_model', 'connection_error', 'processing_error', 'timeout_error')"
    )
    field_errors: Optional[Dict[str, str]] = Field(
        None,
        description="Field-level extraction errors mapping field names to error messages"
    )
    partial_results: Optional[Dict[str, Any]] = Field(
        None,
        description="Partial results when extraction partially succeeds or fails with recoverable data"
    )
    pages: Optional[int] = Field(
        None, 
        description="Number of pages processed in a PDF document"
    )
    filename: Optional[str] = Field(
        None, 
        description="Name of the file that was processed"
    )
    model: Optional[str] = Field(
        None, 
        description="Model ID that was used for processing"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint.
    
    This model provides information about the API server status
    and available OCR models.
    """
    status: str = Field(
        ..., 
        description="Overall health status of the API (e.g., 'healthy', 'degraded')"
    )
    server_running: bool = Field(
        ..., 
        description="Whether the OCR API server (e.g., LM Studio) is running and accessible"
    )
    available_models: List[str] = Field(
        ..., 
        description="List of model IDs that are currently available for OCR processing"
    )


class ModelInfo(BaseModel):
    """Model information for listing available models.
    
    This model provides details about a specific OCR model configuration.
    """
    model_id: str = Field(
        ..., 
        description="Unique identifier for the model"
    )
    name: str = Field(
        ..., 
        description="Human-readable display name for the model"
    )
    provider: str = Field(
        ..., 
        description="API provider that hosts this model (e.g., 'lm_studio')"
    )


class ErrorResponse(BaseModel):
    """Response model for error responses.
    
    This model provides structured error information for failed requests.
    """
    detail: str = Field(
        ..., 
        description="Detailed error message describing what went wrong"
    )
    error_type: Optional[str] = Field(
        None, 
        description="Type of error that occurred (e.g., 'invalid_model', 'invalid_file', 'connection_error')"
    )
