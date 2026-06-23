"""
State Machine — Deterministic state reconstruction from event history.

The core principle: given the same sequence of events, the state machine
always produces the same WorkflowRun state. This enables:
- Recovery after crashes (replay events → exact state)
- Debugging (replay to any point in time)
- Audit (full history of what happened and why)

Usage:
    events = await event_store.load_history(run_id)
    workflow_run = StateMachine.replay(events, workflow_definition)
    next_action = StateMachine.determine_next_action(workflow_run, workflow_definition)
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from services.workflow_engine.models import (
    ActivityDefinition,
    ActivityState,
    ActivityStatus,
    WorkflowDefinition,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowRun,
    WorkflowRunStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Next Action (what should the scheduler do after replay)
# =============================================================================


class NextActionType(str, Enum):
    """What the scheduler should do next."""

    SCHEDULE_ACTIVITY = "schedule_activity"
    RETRY_ACTIVITY = "retry_activity"
    COMPLETE_WORKFLOW = "complete_workflow"
    FAIL_WORKFLOW = "fail_workflow"
    WAIT_TIMER = "wait_timer"
    WAIT_ACTIVITY = "wait_activity"
    NO_OP = "no_op"  # Workflow already in terminal state


class NextAction:
    """Describes the next action the scheduler should take."""

    __slots__ = ("action_type", "activity_id", "delay_seconds", "error", "data")

    def __init__(
        self,
        action_type: NextActionType,
        activity_id: Optional[str] = None,
        delay_seconds: float = 0,
        error: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.action_type = action_type
        self.activity_id = activity_id
        self.delay_seconds = delay_seconds
        self.error = error
        self.data = data or {}

    def __repr__(self) -> str:
        return (
            f"NextAction(type={self.action_type.value}, "
            f"activity={self.activity_id}, delay={self.delay_seconds}s)"
        )


# =============================================================================
# State Machine
# =============================================================================


class StateMachine:
    """
    Deterministic state machine for workflow execution.

    All methods are pure functions (no side effects, no I/O).
    State is derived entirely from events.
    """

    @staticmethod
    def replay(
        events: List[WorkflowEvent],
        definition: WorkflowDefinition,
    ) -> WorkflowRun:
        """
        Reconstruct a WorkflowRun from its event history.

        This is the core replay function. Given the same events and definition,
        it always produces the same result (deterministic).

        Args:
            events: Ordered list of events for this run.
            definition: The workflow blueprint (activities, config).

        Returns:
            The current state of the workflow run.
        """
        run = WorkflowRun(
            workflow_id=definition.workflow_id,
            workflow_name=definition.name,
        )

        # Initialize activity states from definition
        for activity_def in definition.activities:
            run.activity_states[activity_def.activity_id] = ActivityState(
                activity_id=activity_def.activity_id,
                activity_type=activity_def.activity_type,
                label=activity_def.label,
            )

        # Apply each event in order
        for event in events:
            _apply_event(run, event)

        return run

    @staticmethod
    def determine_next_action(
        run: WorkflowRun,
        definition: WorkflowDefinition,
    ) -> NextAction:
        """
        Determine what the scheduler should do next based on current state.

        This examines the workflow run state and decides:
        - Which activity to schedule next (if any)
        - Whether to retry a failed activity
        - Whether the workflow is complete
        - Whether the workflow has failed

        Args:
            run: Current state (from replay).
            definition: Workflow blueprint.

        Returns:
            A NextAction describing what to do.
        """
        # Terminal states — nothing to do
        if run.status in (
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLED,
            WorkflowRunStatus.TIMED_OUT,
        ):
            return NextAction(action_type=NextActionType.NO_OP)

        # Waiting for timer — nothing to do until timer fires
        if run.status == WorkflowRunStatus.WAITING_TIMER:
            return NextAction(action_type=NextActionType.WAIT_TIMER)

        # Build activity lookup
        activity_defs = {a.activity_id: a for a in definition.activities}

        # Check if any activity is currently running/scheduled
        for act_state in run.activity_states.values():
            if act_state.status in (ActivityStatus.RUNNING, ActivityStatus.SCHEDULED):
                return NextAction(
                    action_type=NextActionType.WAIT_ACTIVITY,
                    activity_id=act_state.activity_id,
                )

        # Find the next activity to schedule
        next_activity = _find_next_activity(run, definition)

        if next_activity is not None:
            return NextAction(
                action_type=NextActionType.SCHEDULE_ACTIVITY,
                activity_id=next_activity.activity_id,
            )

        # Check if all activities are done
        all_done = all(
            state.status in (ActivityStatus.COMPLETED, ActivityStatus.SKIPPED)
            for state in run.activity_states.values()
        )

        if all_done:
            return NextAction(action_type=NextActionType.COMPLETE_WORKFLOW)

        # Check if any activity failed without remaining retries
        for act_id, act_state in run.activity_states.items():
            if act_state.status == ActivityStatus.FAILED:
                act_def = activity_defs.get(act_id)
                if act_def is None:
                    continue
                retry_policy = act_def.retry_policy
                if retry_policy.should_retry(act_state.attempt, act_state.error or ""):
                    delay = retry_policy.get_delay(act_state.attempt)
                    return NextAction(
                        action_type=NextActionType.RETRY_ACTIVITY,
                        activity_id=act_id,
                        delay_seconds=delay,
                    )
                else:
                    return NextAction(
                        action_type=NextActionType.FAIL_WORKFLOW,
                        error=(
                            f"Activity '{act_state.label or act_id}' failed after "
                            f"{act_state.attempt + 1} attempts: {act_state.error}"
                        ),
                    )

        # Shouldn't reach here — fallback
        return NextAction(action_type=NextActionType.NO_OP)

    @staticmethod
    def get_activity_input(
        run: WorkflowRun,
        activity_def: ActivityDefinition,
    ) -> Dict[str, Any]:
        """
        Build the input payload for an activity based on upstream results.

        Activities can reference outputs from their dependencies.
        """
        input_data: Dict[str, Any] = {
            "workflow_run_id": run.run_id,
            "activity_id": activity_def.activity_id,
            "activity_type": activity_def.activity_type,
            "config": activity_def.config,
            "workflow_input": run.input_data,
        }

        # Include outputs from dependencies
        upstream_outputs: Dict[str, Any] = {}
        for dep_id in activity_def.depends_on:
            if dep_id in run.activity_results:
                upstream_outputs[dep_id] = run.activity_results[dep_id]

        if upstream_outputs:
            input_data["upstream_outputs"] = upstream_outputs

        # Include the last completed activity's output as "previous_output"
        # (for simple sequential workflows)
        if run.activity_results:
            last_completed = _get_last_completed_activity(run, activity_def)
            if last_completed and last_completed in run.activity_results:
                input_data["previous_output"] = run.activity_results[last_completed]

        return input_data


# =============================================================================
# Event Application (private, deterministic)
# =============================================================================


def _apply_event(run: WorkflowRun, event: WorkflowEvent) -> None:
    """
    Apply a single event to mutate the workflow run state.

    This function must be deterministic: same event → same state change.
    """
    run.last_event_sequence = event.sequence_num
    payload = event.payload
    event_type = event.event_type

    # Handle string event types (from DB storage)
    if isinstance(event_type, str):
        try:
            event_type = WorkflowEventType(event_type)
        except ValueError:
            logger.warning("Unknown event type: %s", event_type)
            return

    match event_type:
        # --- Workflow lifecycle ---
        case WorkflowEventType.WORKFLOW_STARTED:
            run.status = WorkflowRunStatus.RUNNING
            run.run_id = event.workflow_run_id
            run.started_at = event.timestamp
            if "input_data" in payload:
                run.input_data = payload["input_data"]

        case WorkflowEventType.WORKFLOW_COMPLETED:
            run.status = WorkflowRunStatus.COMPLETED
            run.completed_at = event.timestamp
            if "output_data" in payload:
                run.output_data = payload["output_data"]

        case WorkflowEventType.WORKFLOW_FAILED:
            run.status = WorkflowRunStatus.FAILED
            run.completed_at = event.timestamp
            run.error = payload.get("error")

        case WorkflowEventType.WORKFLOW_CANCELLED:
            run.status = WorkflowRunStatus.CANCELLED
            run.completed_at = event.timestamp

        case WorkflowEventType.WORKFLOW_TIMED_OUT:
            run.status = WorkflowRunStatus.TIMED_OUT
            run.completed_at = event.timestamp
            run.error = payload.get("error", "Workflow timed out")

        # --- Activity lifecycle ---
        case WorkflowEventType.ACTIVITY_SCHEDULED:
            activity_id = payload.get("activity_id", "")
            state = _get_or_create_activity_state(run, activity_id, payload)
            state.status = ActivityStatus.SCHEDULED
            state.scheduled_at = event.timestamp
            run.status = WorkflowRunStatus.WAITING_ACTIVITY

        case WorkflowEventType.ACTIVITY_STARTED:
            activity_id = payload.get("activity_id", "")
            state = _get_or_create_activity_state(run, activity_id, payload)
            state.status = ActivityStatus.RUNNING
            state.started_at = event.timestamp
            run.status = WorkflowRunStatus.RUNNING

        case WorkflowEventType.ACTIVITY_COMPLETED:
            activity_id = payload.get("activity_id", "")
            state = _get_or_create_activity_state(run, activity_id, payload)
            state.status = ActivityStatus.COMPLETED
            state.completed_at = event.timestamp
            state.output = payload.get("output")
            state.duration_ms = payload.get("duration_ms")
            state.error = None
            # Store result for downstream access
            run.activity_results[activity_id] = payload.get("output")
            run.status = WorkflowRunStatus.RUNNING

        case WorkflowEventType.ACTIVITY_FAILED:
            activity_id = payload.get("activity_id", "")
            state = _get_or_create_activity_state(run, activity_id, payload)
            state.status = ActivityStatus.FAILED
            state.error = payload.get("error")
            state.completed_at = event.timestamp
            state.duration_ms = payload.get("duration_ms")
            run.status = WorkflowRunStatus.RUNNING

        case WorkflowEventType.ACTIVITY_RETRYING:
            activity_id = payload.get("activity_id", "")
            state = _get_or_create_activity_state(run, activity_id, payload)
            state.status = ActivityStatus.SCHEDULED
            state.attempt = payload.get("attempt", state.attempt + 1)
            state.next_retry_at = event.timestamp
            state.error = None
            run.status = WorkflowRunStatus.WAITING_ACTIVITY

        case WorkflowEventType.ACTIVITY_TIMED_OUT:
            activity_id = payload.get("activity_id", "")
            state = _get_or_create_activity_state(run, activity_id, payload)
            state.status = ActivityStatus.TIMED_OUT
            state.error = payload.get("error", "Activity timed out")
            state.completed_at = event.timestamp
            run.status = WorkflowRunStatus.RUNNING

        case WorkflowEventType.ACTIVITY_SKIPPED:
            activity_id = payload.get("activity_id", "")
            state = _get_or_create_activity_state(run, activity_id, payload)
            state.status = ActivityStatus.SKIPPED
            state.completed_at = event.timestamp

        # --- Timer lifecycle ---
        case WorkflowEventType.TIMER_SCHEDULED:
            timer_id = payload.get("timer_id", "")
            if timer_id not in run.pending_timers:
                run.pending_timers.append(timer_id)
            run.status = WorkflowRunStatus.WAITING_TIMER

        case WorkflowEventType.TIMER_FIRED:
            timer_id = payload.get("timer_id", "")
            if timer_id in run.pending_timers:
                run.pending_timers.remove(timer_id)
            if not run.pending_timers:
                run.status = WorkflowRunStatus.RUNNING

        case WorkflowEventType.TIMER_CANCELLED:
            timer_id = payload.get("timer_id", "")
            if timer_id in run.pending_timers:
                run.pending_timers.remove(timer_id)
            if not run.pending_timers:
                run.status = WorkflowRunStatus.RUNNING

        # --- Checkpoint ---
        case WorkflowEventType.CHECKPOINT_SAVED:
            # Checkpoint is informational — no state change needed
            pass

        case _:
            logger.debug("Unhandled event type in replay: %s", event_type)


# =============================================================================
# Helpers (private)
# =============================================================================


def _get_or_create_activity_state(
    run: WorkflowRun,
    activity_id: str,
    payload: Dict[str, Any],
) -> ActivityState:
    """Get existing activity state or create a new one from event payload."""
    if activity_id in run.activity_states:
        return run.activity_states[activity_id]

    state = ActivityState(
        activity_id=activity_id,
        activity_type=payload.get("activity_type", "unknown"),
        label=payload.get("label", ""),
    )
    run.activity_states[activity_id] = state
    return state


def _find_next_activity(
    run: WorkflowRun,
    definition: WorkflowDefinition,
) -> Optional[ActivityDefinition]:
    """
    Find the next activity that should be scheduled.

    Rules:
    - Must be in PENDING status
    - All dependencies must be COMPLETED
    - Follows definition order (first eligible activity wins)
    """
    for activity_def in definition.activities:
        act_id = activity_def.activity_id
        state = run.activity_states.get(act_id)

        if state is None:
            continue

        # Only schedule pending activities
        if state.status != ActivityStatus.PENDING:
            continue

        # Check dependencies
        deps_met = all(
            run.activity_states.get(dep_id, ActivityState(activity_id=dep_id, activity_type="")).status
            == ActivityStatus.COMPLETED
            for dep_id in activity_def.depends_on
        )

        if deps_met:
            return activity_def

    return None


def _get_last_completed_activity(
    run: WorkflowRun,
    current_def: ActivityDefinition,
) -> Optional[str]:
    """
    Get the activity_id of the most recently completed activity
    that is a direct dependency or the previous activity in sequence.
    """
    # If explicit dependencies, use the last one
    if current_def.depends_on:
        for dep_id in reversed(current_def.depends_on):
            if dep_id in run.activity_results:
                return dep_id
        return None

    # Otherwise, find the last completed activity by order
    last_completed: Optional[str] = None
    for act_id, act_state in run.activity_states.items():
        if act_id == current_def.activity_id:
            break
        if act_state.status == ActivityStatus.COMPLETED:
            last_completed = act_id

    return last_completed
