"""
Pydantic schemas for the Journey Job Manager API.

Request/response models for:
- Job submission
- Job status/result polling
- Job listing with filters
- Job cancellation
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class JobStepDefinition(BaseModel):
    """A step to execute within a job."""

    id: Optional[str] = Field(default=None, description="Node ID from the frontend workflow.")
    type: Literal["parse", "classify", "extract", "split"] = Field(
        ..., description="Step type."
    )
    label: Optional[str] = Field(default=None, description="Human-readable label.")
    tier: str = Field(default="Normal", description="Processing tier.")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Step-specific config.")


class JobSubmitRequest(BaseModel):
    """Request body for submitting a new job."""

    workflow_id: Optional[str] = Field(
        default=None, description="ID of a saved workflow to execute."
    )
    workflow_name: Optional[str] = Field(
        default=None, description="Human-readable name for this execution."
    )
    steps: List[JobStepDefinition] = Field(
        ..., min_length=1, description="Ordered list of steps to execute."
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Max retries per failed node."
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class NodeProgressResponse(BaseModel):
    """Progress info for a single node."""

    node_id: str
    node_type: str
    node_label: str
    status: str
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class JobResponse(BaseModel):
    """Full job response."""

    job_id: str
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    status: str
    progress: float = Field(ge=0.0, le=1.0)
    nodes: List[NodeProgressResponse] = []
    filename: Optional[str] = None
    file_count: int = 0
    max_retries: int = 3
    minio_path: Optional[str] = None
    result_minio_path: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    error: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None


class JobSubmitResponse(BaseModel):
    """Response after submitting a job."""

    job_id: str
    status: str = "queued"
    poll_url: str
    message: str = "Job submitted successfully"


class JobListResponse(BaseModel):
    """Response for listing jobs."""

    success: bool = True
    jobs: List[JobResponse]
    total: int
    limit: int
    offset: int


class JobCancelResponse(BaseModel):
    """Response for cancelling a job."""

    success: bool
    job_id: str
    message: str
