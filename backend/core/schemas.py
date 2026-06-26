"""
Pydantic schemas for request/response validation.

This module defines all data schemas used for API request validation,
response serialization, and data transfer objects in the Doc Intelligence application.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
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
    workflow_engine: Optional[Dict[str, str]] = Field(
        default=None,
        description="Workflow engine status (added by /health endpoint)"
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


class ClassificationRule(BaseModel):
    """Classification rule model."""
    type: str = Field(..., description="Document type name")
    description: str = Field(..., description="Description of the document type")


class ClassificationResult(BaseModel):
    """Classification result for a single document."""
    fileName: Optional[str] = Field(None, description="Name of the classified file")
    documentType: str = Field(..., description="Classified document type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence (0.0 to 1.0)")
    reasoning: Optional[str] = Field(None, description="Explanation of the classification")


class ClassifyResponse(BaseModel):
    """Response model for classification endpoint."""
    success: bool = Field(..., description="Whether classification succeeded")
    results: Optional[List[ClassificationResult]] = Field(None, description="Classification results")
    error: Optional[str] = Field(None, description="Error message if classification failed")
    error_type: Optional[str] = Field(None, description="Type of error that occurred")


class ChunkCategoryModel(BaseModel):
    """Category definition for splitting."""
    name: str = Field(..., min_length=1, max_length=200, description="Category name")
    description: str = Field(default="", max_length=2000, description="Category description")
    order: int = Field(default=0, ge=0, description="Display order (lower values appear first)")


class ChunkModel(BaseModel):
    """Individual chunk in split results."""
    content: str = Field(..., description="Text content of the chunk")
    category: str = Field(..., description="Assigned category name")
    page_number: int = Field(..., ge=1, description="Page number where chunk appears")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")


class DocumentTypeResult(BaseModel):
    """Result for a single document type identified during document-type splitting."""
    type_name: str = Field(..., min_length=1, description="Document type name")
    page_numbers: List[int] = Field(..., min_length=1, description="Page numbers for this type")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")

    @validator('page_numbers', each_item=True)
    def validate_page_numbers(cls, v):
        """Validate each page number is >= 1."""
        if v < 1:
            raise ValueError("Page numbers must be >= 1")
        return v


class SplitResponse(BaseModel):
    """Response model for split operation."""
    success: bool = Field(..., description="Whether the split operation succeeded")
    chunks: List[ChunkModel] = Field(default=[], description="List of categorized chunks")
    unknown_chunks: List[ChunkModel] = Field(default=[], description="List of chunks that don't match any category")
    document_types: Optional[List[DocumentTypeResult]] = Field(None, description="List of document type results (populated in document_type split mode)")
    filename: Optional[str] = Field(None, description="Name of the file that was processed")
    error: Optional[str] = Field(None, description="Error message if split failed")
    error_type: Optional[str] = Field(None, description="Type of error that occurred")


# --- API Explorer schemas ---

class EndpointField(BaseModel):
    """Metadata for a single input field in an API Explorer endpoint."""
    name: str = Field(..., description="Field name used as the form/query parameter key")
    type: str = Field(..., description="UI input type: file, text, textarea, select, checkbox, number")
    required: bool = Field(False, description="Whether this field is required")
    label: str = Field("", description="Human-readable label for the field")
    placeholder: Optional[str] = Field(None, description="Placeholder text for text/textarea inputs")
    accept: Optional[str] = Field(None, description="Accepted MIME types or extensions for file inputs")
    default: Optional[Any] = Field(None, description="Default value for the field")
    options: Optional[List[str]] = Field(None, description="Selectable options for select inputs")
    path_param: Optional[bool] = Field(None, description="True when this field maps to a URL path parameter")


class EndpointMeta(BaseModel):
    """Metadata for a single API endpoint shown in the API Explorer."""
    id: str = Field(..., description="Unique endpoint identifier")
    group: str = Field(..., description="Display group name")
    method: str = Field(..., description="HTTP method: GET or POST")
    path: str = Field(..., description="URL path for the endpoint")
    summary: str = Field(..., description="Short description of what the endpoint does")
    description: str = Field("", description="Detailed description")
    fields: List[EndpointField] = Field(default_factory=list, description="Input fields for this endpoint")


class EndpointGroup(BaseModel):
    """A named group of endpoints in the API Explorer."""
    name: str = Field(..., description="Group display name")
    endpoints: List[EndpointMeta] = Field(..., description="Endpoints in this group")


class ApiExplorerResponse(BaseModel):
    """Response model for GET /api-explorer/endpoints."""
    success: bool = Field(..., description="Whether the request succeeded")
    total: int = Field(..., description="Total number of endpoints")
    groups: List[EndpointGroup] = Field(..., description="Endpoints grouped by category")
    endpoints: List[EndpointMeta] = Field(..., description="Flat list of all endpoints")
