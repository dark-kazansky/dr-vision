"""
Workflow Engine Models — Core data structures for durable workflow orchestration.

All state is reconstructed from events (event-sourcing).
Models are pure data containers — no business logic here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class WorkflowRunStatus(str, Enum):
    """Lifecycle states of a workflow run."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_ACTIVITY = "waiting_activity"
    WAITING_TIMER = "waiting_timer"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ActivityStatus(str, Enum):
    """Lifecycle states of a single activity within a workflow."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


class TaskStatus(str, Enum):
    """Status of a task in the distributed task queue."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class TimerStatus(str, Enum):
    """Status of a durable timer."""

    SCHEDULED = "scheduled"
    FIRED = "fired"
    CANCELLED = "cancelled"


class WorkflowEventType(str, Enum):
    """Types of events in the workflow event log."""

    # Workflow lifecycle
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_TIMED_OUT = "workflow_timed_out"

    # Activity lifecycle
    ACTIVITY_SCHEDULED = "activity_scheduled"
    ACTIVITY_STARTED = "activity_started"
    ACTIVITY_COMPLETED = "activity_completed"
    ACTIVITY_FAILED = "activity_failed"
    ACTIVITY_RETRYING = "activity_retrying"
    ACTIVITY_TIMED_OUT = "activity_timed_out"
    ACTIVITY_SKIPPED = "activity_skipped"

    # Timer lifecycle
    TIMER_SCHEDULED = "timer_scheduled"
    TIMER_FIRED = "timer_fired"
    TIMER_CANCELLED = "timer_cancelled"

    # Checkpoint
    CHECKPOINT_SAVED = "checkpoint_saved"


# =============================================================================
# Retry Policy
# =============================================================================


class RetryPolicy(BaseModel):
    """
    Configurable retry strategy for activities.

    Supports exponential backoff with jitter, max attempts,
    and non-retryable error classification.
    """

    max_attempts: int = Field(default=3, ge=1, le=100)
    initial_delay_seconds: float = Field(default=1.0, ge=0.1, le=3600)
    max_delay_seconds: float = Field(default=300.0, ge=1.0, le=86400)
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    non_retryable_errors: List[str] = Field(default_factory=list)

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number (0-indexed)."""
        delay = self.initial_delay_seconds * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay_seconds)

    def is_retryable(self, error: str) -> bool:
        """Check if an error is retryable based on configured non-retryable patterns."""
        if not self.non_retryable_errors:
            return True
        error_lower = error.lower()
        return not any(
            pattern.lower() in error_lower
            for pattern in self.non_retryable_errors
        )

    def should_retry(self, attempt: int, error: str) -> bool:
        """Determine if we should retry given current attempt and error."""
        if attempt >= self.max_attempts - 1:
            return False
        return self.is_retryable(error)


# =============================================================================
# Activity Definition
# =============================================================================


class ActivityDefinition(BaseModel):
    """
    Definition of a single activity (step) in a workflow.

    Activities are the units of work that workers execute.
    Each activity has a type, configuration, and retry policy.
    """

    activity_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    activity_type: str  # e.g., "ocr_parse", "ocr_classify", "ocr_extract"
    label: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, ge=10, le=86400)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    queue_name: str = "default"

    # Dependencies — activity IDs that must complete before this one
    depends_on: List[str] = Field(default_factory=list)


# =============================================================================
# Workflow Definition
# =============================================================================


class WorkflowDefinition(BaseModel):
    """
    Blueprint for a workflow — defines activities and their execution order.

    The scheduler uses this to determine what to do next after each activity
    completes or fails.
    """

    workflow_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    activities: List[ActivityDefinition] = Field(default_factory=list)
    timeout_seconds: int = Field(default=3600, ge=60, le=604800)  # 1 hour default, max 7 days
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Workflow Event
# =============================================================================


class WorkflowEvent(BaseModel):
    """
    A single immutable event in the workflow event log.

    Events are the source of truth. All state is derived by replaying events.
    """

    event_id: Optional[int] = None  # Set by EventStore (BIGSERIAL)
    workflow_run_id: str
    sequence_num: int = 0  # Monotonically increasing per run
    event_type: WorkflowEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


# =============================================================================
# Activity State (derived from events)
# =============================================================================


class ActivityState(BaseModel):
    """
    Current state of an activity within a workflow run.

    Reconstructed from events during replay.
    """

    activity_id: str
    activity_type: str
    label: str = ""
    status: ActivityStatus = ActivityStatus.PENDING
    attempt: int = 0
    output: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None


# =============================================================================
# Workflow Run (derived from events)
# =============================================================================


class WorkflowRun(BaseModel):
    """
    Current state of a workflow execution.

    Reconstructed by replaying all events for this run.
    This is a derived view — never stored directly, always computed.
    """

    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    workflow_id: str = ""
    workflow_name: str = ""
    status: WorkflowRunStatus = WorkflowRunStatus.PENDING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)

    # Per-activity state
    activity_states: Dict[str, ActivityState] = Field(default_factory=dict)

    # Results from completed activities (activity_id → output)
    activity_results: Dict[str, Any] = Field(default_factory=dict)

    # Metadata
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    last_event_sequence: int = 0

    # Timer tracking
    pending_timers: List[str] = Field(default_factory=list)

    model_config = {"use_enum_values": True}


# =============================================================================
# Activity Task (task queue item)
# =============================================================================


class ActivityTask(BaseModel):
    """
    A task dispatched to the distributed task queue for worker execution.

    Workers poll for these, execute them, and report results back.
    """

    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    queue_name: str = "default"
    workflow_run_id: str
    activity_id: str
    activity_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    attempt: int = 0
    max_attempts: int = 3
    timeout_seconds: int = 300
    visible_after: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Worker tracking
    worker_id: Optional[str] = None
    heartbeat_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING

    model_config = {"use_enum_values": True}


# =============================================================================
# Durable Timer
# =============================================================================


class DurableTimer(BaseModel):
    """
    A persistent timer that survives process restarts.

    Used for: business timeouts, delayed execution, scheduled actions.
    """

    timer_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    workflow_run_id: str
    name: str = ""
    fire_at: datetime
    status: TimerStatus = TimerStatus.SCHEDULED
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fired_at: Optional[datetime] = None

    model_config = {"use_enum_values": True}

    @property
    def is_due(self) -> bool:
        """Check if timer should fire now."""
        return (
            self.status == TimerStatus.SCHEDULED
            and datetime.now(timezone.utc) >= self.fire_at
        )
