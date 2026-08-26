"""
Pydantic models shared between the orchestrator service, the gateway,
and any caller. Field names match the frontend ``useJobs`` /
``useWorkflowStore`` types so the two halves of the system serialise
identically.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Workflow nodes
# ---------------------------------------------------------------------------

NodeType = Literal[
    "upload",
    "ocr",
    "parse",
    "classify",
    "extract",
    "split",
    "condition",
    "validate",
    "script",
]


class Connection(BaseModel):
    """Outgoing edge from a node."""

    targetId: str
    outputIndex: Optional[int] = None

    model_config = ConfigDict(extra="ignore")


class WorkflowNode(BaseModel):
    """A node in a workflow graph."""

    id: str
    type: NodeType
    label: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    tier: Optional[str] = "Normal"
    config: Optional[Dict[str, Any]] = None
    connections: Optional[List[Connection]] = None
    inactive: Optional[bool] = False

    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# Workflow records (saved graphs)
# ---------------------------------------------------------------------------

class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    nodes: List[WorkflowNode] = Field(default_factory=list)


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    nodes: Optional[List[WorkflowNode]] = None


class WorkflowSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    createdAt: int
    updatedAt: int
    nodeCount: int


class WorkflowRecord(WorkflowSummary):
    nodes: List[WorkflowNode]


# ---------------------------------------------------------------------------
# Run records
# ---------------------------------------------------------------------------

RunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
NodeStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class JobLogEntry(BaseModel):
    ts: int
    level: Literal["info", "warn", "error"]
    message: str
    nodeId: Optional[str] = None


class NodeRunRecord(BaseModel):
    nodeId: str
    nodeLabel: str
    nodeType: str
    status: NodeStatus = "pending"
    startedAt: Optional[int] = None
    finishedAt: Optional[int] = None
    error: Optional[str] = None
    outputSummary: Optional[str] = None


class RunRecord(BaseModel):
    id: str
    workflowId: Optional[str] = None
    workflowName: str
    status: RunStatus = "queued"
    createdAt: int
    startedAt: Optional[int] = None
    finishedAt: Optional[int] = None
    inputFiles: List[str]
    nodes: List[NodeRunRecord]
    logs: List[JobLogEntry] = Field(default_factory=list)
    error: Optional[str] = None
    cancelRequested: bool = False


class RunSummary(BaseModel):
    """Compact projection used by ``GET /workflow-runs``."""

    id: str
    workflowId: Optional[str]
    workflowName: str
    status: RunStatus
    createdAt: int
    startedAt: Optional[int]
    finishedAt: Optional[int]
    inputFiles: List[str]
    totalNodes: int
    completedNodes: int
    failedNodes: int
    error: Optional[str]


class RunListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    runs: List[RunSummary]


# ---------------------------------------------------------------------------
# Run requests
# ---------------------------------------------------------------------------

class AdhocRunRequest(BaseModel):
    """Body of ``POST /workflows/run-json`` (no file uploads)."""

    nodes: List[WorkflowNode]
    workflow_name: Optional[str] = "Ad-hoc workflow"
    file_names: List[str] = Field(default_factory=list)
