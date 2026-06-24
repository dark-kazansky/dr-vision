"""
Durable Workflow Orchestration Engine.

A lightweight, PostgreSQL-backed durable execution runtime inspired by Temporal.
Provides event-sourced state management, distributed task queues, retry policies,
durable timers, and automatic failure recovery.

Architecture:
- Event Store: Append-only event log per workflow run (replay for state recovery)
- State Machine: Deterministic state reconstruction from event history
- Task Queue: PostgreSQL-backed with visibility timeout (SELECT FOR UPDATE SKIP LOCKED)
- Workers: Pull-based, horizontally scalable activity executors
- Scheduler: Orchestrator brain — reacts to events and schedules next activities
- Recovery: Auto-recovers interrupted workflows on startup

Usage:
    from services.workflow_engine import WorkflowEngine

    engine = WorkflowEngine(pool)
    await engine.start()

    run_id = await engine.start_workflow(
        workflow_id="my-workflow",
        activities=[...],
        input_data={...},
    )

    await engine.stop()
"""

from services.workflow_engine.engine import WorkflowEngine
from services.workflow_engine.models import (
    ActivityDefinition,
    ActivityTask,
    DurableTimer,
    RetryPolicy,
    WorkflowDefinition,
    WorkflowEventType,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowEvent,
)

__all__ = [
    "WorkflowEngine",
    "ActivityDefinition",
    "ActivityTask",
    "DurableTimer",
    "RetryPolicy",
    "WorkflowDefinition",
    "WorkflowEventType",
    "WorkflowRun",
    "WorkflowRunStatus",
    "WorkflowEvent",
]
