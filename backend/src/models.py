"""
Pydantic models for request/response validation.

This module defines all data models used for API request validation,
response serialization, and data transfer objects in the OCR Web UI application.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class TierEnum(str, Enum):
    """OCR processing tier options."""
    RAPID = "Rapid"
    NORMAL = "Normal"
    ADVANCE = "Advance"


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


class OCRResponse(BaseModel):
    """Response model for OCR processing.
    
    This model represents the result of an OCR operation, including
    success status, extracted text, or error information.
    """
    success: bool = Field(
        ..., 
        description="Whether the OCR operation completed successfully"
    )
    text: Optional[str] = Field(
        None, 
        description="Extracted text from the OCR operation. Present only if success is True"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message describing what went wrong. Present only if success is False"
    )
    error_type: Optional[str] = Field(
        None, 
        description="Type of error that occurred (e.g., 'invalid_model', 'connection_error', 'processing_error')"
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
