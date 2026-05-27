"""
Pydantic schemas for the Public Workflow Execution API (v1).

All request and response models for:
- Workflow CRUD
- Workflow execution (sync + async)
- Individual step execution
- Job polling
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Step definition
# ---------------------------------------------------------------------------

class StepDefinition(BaseModel):
    """A single step in a workflow definition."""

    type: str = Field(
        ...,
        description="Step type (e.g., parse, classify, extract, split, ocr, upload, condition).",
        examples=["parse"],
    )
    tier: str = Field(
        default="Normal",
        description="Processing tier: Rapid, Normal, or Advance.",
        examples=["Normal"],
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Step-specific configuration. "
            "classify: {rules: [{doc_type, description}]}. "
            "extract: {schema: {fields: [{name, type, description, required}]}, target: 'document'}. "
            "split: {categories: [{name, description, order}], allow_uncategorized: true}."
        ),
    )


# ---------------------------------------------------------------------------
# Workflow CRUD
# ---------------------------------------------------------------------------

class WorkflowCreate(BaseModel):
    """Request body for creating a new workflow."""

    name: str = Field(..., min_length=1, max_length=200, description="Human-readable workflow name.", examples=["Invoice Processing"])
    description: Optional[str] = Field(default=None, max_length=1000, description="Optional description of what this workflow does.")
    steps: List[StepDefinition] = Field(default_factory=list, description="Ordered list of steps to execute.")
    graph_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Full graph structure (nodes + edges + positions) for canvas rendering. Stored as JSONB.",
    )


class WorkflowUpdate(BaseModel):
    """Request body for updating an existing workflow."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    steps: Optional[List[StepDefinition]] = Field(default=None, min_length=1)
    graph_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated graph structure for canvas rendering.",
    )


class WorkflowResponse(BaseModel):
    """Full workflow definition returned by the API."""

    workflow_id: str = Field(..., description="Unique workflow identifier (UUID).")
    name: str
    description: Optional[str] = None
    steps: List[StepDefinition] = Field(default_factory=list)
    graph_data: Optional[Dict[str, Any]] = Field(default=None, description="Graph structure for canvas.")
    status: Optional[str] = Field(default="draft", description="Workflow status: draft, published.")
    created_at: datetime
    updated_at: datetime


class WorkflowListItem(BaseModel):
    """Summary item in the workflow list."""

    workflow_id: str
    name: str
    description: Optional[str] = None
    step_count: int
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    """Response for GET /api/v1/workflows."""

    success: bool = True
    total: int
    workflows: List[WorkflowListItem]


# ---------------------------------------------------------------------------
# Execution responses
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    """Result of a single step in a workflow execution."""

    step: str = Field(..., description="Step type that was executed.")
    tier: str
    result: Dict[str, Any] = Field(..., description="Step-specific output data.")


class WorkflowExecuteResponse(BaseModel):
    """Response for synchronous workflow execution."""

    success: bool
    workflow_id: str
    filename: str
    results: Optional[List[StepResult]] = None
    error: Optional[str] = None
    completed_steps: Optional[List[StepResult]] = None


class AsyncJobResponse(BaseModel):
    """Response when a workflow is dispatched to a background job."""

    job_id: str
    status: str = "pending"
    poll_url: str = Field(..., description="URL to poll for job status.")
    message: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response for GET /api/v1/jobs/{job_id}/status."""

    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_at: Optional[float] = None
    completed_at: Optional[float] = None


# ---------------------------------------------------------------------------
# Individual step responses
# ---------------------------------------------------------------------------

class ParseStepResponse(BaseModel):
    """Response for POST /api/v1/workflows/{id}/steps/parse."""

    success: bool
    text: Optional[str] = None
    file_type: Optional[str] = None
    pages: Optional[int] = None
    is_scanned: Optional[bool] = None
    error: Optional[str] = None


class ClassifyStepResponse(BaseModel):
    """Response for POST /api/v1/workflows/{id}/steps/classify."""

    success: bool
    document_type: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    error: Optional[str] = None


class ExtractStepResponse(BaseModel):
    """Response for POST /api/v1/workflows/{id}/steps/extract."""

    success: bool
    structured_data: Optional[Any] = None
    field_errors: Optional[Dict[str, str]] = None
    error: Optional[str] = None


class SplitStepResponse(BaseModel):
    """Response for POST /api/v1/workflows/{id}/steps/split."""

    success: bool
    chunks: Optional[List[Dict[str, Any]]] = None
    unknown_chunks: Optional[List[Dict[str, Any]]] = None
    document_types: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    error: str
    completed_steps: Optional[List[StepResult]] = None
