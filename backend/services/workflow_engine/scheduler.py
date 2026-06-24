"""
Workflow Scheduler — The orchestrator brain.

The scheduler is the central coordinator that:
1. Reacts to events (activity completed, activity failed, timer fired)
2. Replays event history to determine current state
3. Decides the next action (schedule activity, retry, complete, fail)
4. Enqueues tasks or emits events based on decisions

The scheduler does NOT execute activities — it only decides what to do next.
Workers execute activities and report results back to the scheduler.

Flow:
    Event occurs → Scheduler replays state → Determines next action → Executes decision

This separation ensures:
- Scheduler is lightweight (no heavy computation)
- Workers can scale independently
- State is always consistent (derived from events)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.workflow_engine.event_store import EventStore
from services.workflow_engine.models import (
    ActivityDefinition,
    WorkflowDefinition,
    WorkflowEventType,
    WorkflowRunStatus,
)
from services.workflow_engine.retry_policy import evaluate_retry
from services.workflow_engine.state_machine import (
    NextActionType,
    StateMachine,
)
from services.workflow_engine.task_queue import TaskQueue
from services.workflow_engine.timer_service import TimerService

logger = logging.getLogger(__name__)


class WorkflowScheduler:
    """
    The orchestrator brain — reacts to events and schedules next steps.

    Usage:
        scheduler = WorkflowScheduler(event_store, task_queue, timer_service)

        # Start a new workflow
        run_id = await scheduler.start_workflow(definition, input_data)

        # Called by workers when activity completes
        await scheduler.on_activity_completed(run_id, activity_id, output)

        # Called by workers when activity fails
        await scheduler.on_activity_failed(run_id, activity_id, error)

        # Called by timer service when timer fires
        await scheduler.on_timer_fired(run_id, timer_name)
    """

    def __init__(
        self,
        event_store: EventStore,
        task_queue: TaskQueue,
        timer_service: TimerService,
    ) -> None:
        self._event_store = event_store
        self._task_queue = task_queue
        self._timer_service = timer_service
        # Workflow definitions cache (workflow_id → definition)
        self._definitions: Dict[str, WorkflowDefinition] = {}
        # Lock per run to prevent concurrent scheduling decisions
        self._run_locks: Dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------
    # Definition management
    # ------------------------------------------------------------------

    def register_definition(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition for scheduling."""
        self._definitions[definition.workflow_id] = definition
        logger.debug("Registered workflow definition: %s", definition.workflow_id)

    def get_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a registered workflow definition."""
        return self._definitions.get(workflow_id)

    # ------------------------------------------------------------------
    # Start workflow
    # ------------------------------------------------------------------

    async def start_workflow(
        self,
        definition: WorkflowDefinition,
        input_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a new workflow execution.

        Creates the run record, emits WORKFLOW_STARTED, and schedules
        the first activity.

        Args:
            definition: The workflow blueprint.
            input_data: Input data for the workflow (available to all activities).
            metadata: Optional metadata (e.g., user_id, source).

        Returns:
            The run_id of the started workflow.
        """
        # Register definition if not already registered
        self._definitions[definition.workflow_id] = definition

        # Create run in event store
        run_id = await self._event_store.create_run(
            workflow_id=definition.workflow_id,
            workflow_name=definition.name,
            input_data=input_data,
            timeout_seconds=definition.timeout_seconds,
            metadata=metadata,
        )

        # Emit WORKFLOW_STARTED event
        await self._event_store.append(
            run_id=run_id,
            event_type=WorkflowEventType.WORKFLOW_STARTED,
            payload={"input_data": input_data or {}},
        )

        # Update run status
        await self._event_store.update_run_status(
            run_id, WorkflowRunStatus.RUNNING
        )

        # Schedule workflow timeout timer
        if definition.timeout_seconds > 0:
            timeout_at = datetime.now(timezone.utc)
            from datetime import timedelta
            timeout_at += timedelta(seconds=definition.timeout_seconds)
            await self._timer_service.schedule(
                workflow_run_id=run_id,
                name="__workflow_timeout__",
                fire_at=timeout_at,
                payload={"reason": "Workflow execution timeout"},
            )

        # Advance the workflow (schedule first activity)
        await self._advance(run_id, definition)

        logger.info(
            "Started workflow '%s' (run_id=%s, activities=%d)",
            definition.name, run_id, len(definition.activities),
        )
        return run_id

    # ------------------------------------------------------------------
    # Event handlers (called by workers/timer service)
    # ------------------------------------------------------------------

    async def on_activity_completed(
        self,
        run_id: str,
        activity_id: str,
        output: Any = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """
        Called when a worker successfully completes an activity.

        Appends ACTIVITY_COMPLETED event and advances the workflow.
        """
        lock = self._get_run_lock(run_id)
        async with lock:
            # Append event
            await self._event_store.append(
                run_id=run_id,
                event_type=WorkflowEventType.ACTIVITY_COMPLETED,
                payload={
                    "activity_id": activity_id,
                    "output": output,
                    "duration_ms": duration_ms,
                },
            )

            # Advance
            definition = await self._get_definition_for_run(run_id)
            if definition:
                await self._advance(run_id, definition)

    async def on_activity_failed(
        self,
        run_id: str,
        activity_id: str,
        error: str,
        duration_ms: Optional[int] = None,
    ) -> None:
        """
        Called when a worker reports an activity failure.

        Evaluates retry policy and either retries or fails the workflow.
        """
        lock = self._get_run_lock(run_id)
        async with lock:
            # Append failure event
            await self._event_store.append(
                run_id=run_id,
                event_type=WorkflowEventType.ACTIVITY_FAILED,
                payload={
                    "activity_id": activity_id,
                    "error": error,
                    "duration_ms": duration_ms,
                },
            )

            # Advance (state machine will determine retry or fail)
            definition = await self._get_definition_for_run(run_id)
            if definition:
                await self._advance(run_id, definition)

    async def on_activity_started(
        self,
        run_id: str,
        activity_id: str,
        worker_id: Optional[str] = None,
    ) -> None:
        """Called when a worker begins executing an activity."""
        await self._event_store.append(
            run_id=run_id,
            event_type=WorkflowEventType.ACTIVITY_STARTED,
            payload={
                "activity_id": activity_id,
                "worker_id": worker_id,
            },
        )

    async def on_timer_fired(
        self,
        run_id: str,
        timer_name: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Called when a durable timer fires.

        If it's the workflow timeout timer, fails the workflow.
        Otherwise, appends TIMER_FIRED and advances.
        """
        lock = self._get_run_lock(run_id)
        async with lock:
            # Check if this is the workflow timeout
            if timer_name == "__workflow_timeout__":
                await self._timeout_workflow(run_id)
                return

            # Append timer fired event
            await self._event_store.append(
                run_id=run_id,
                event_type=WorkflowEventType.TIMER_FIRED,
                payload={
                    "timer_id": timer_name,
                    "timer_payload": payload or {},
                },
            )

            # Advance
            definition = await self._get_definition_for_run(run_id)
            if definition:
                await self._advance(run_id, definition)

    async def cancel_workflow(self, run_id: str, reason: str = "") -> bool:
        """
        Cancel a running workflow.

        Cancels all pending tasks and timers, emits WORKFLOW_CANCELLED.
        """
        lock = self._get_run_lock(run_id)
        async with lock:
            # Check current status
            run_data = await self._event_store.get_run(run_id)
            if run_data is None:
                return False

            if run_data["status"] in (
                WorkflowRunStatus.COMPLETED,
                WorkflowRunStatus.FAILED,
                WorkflowRunStatus.CANCELLED,
            ):
                return False

            # Cancel pending tasks
            await self._task_queue.cancel_by_run(run_id)

            # Cancel timers
            await self._timer_service.cancel_all_for_run(run_id)

            # Emit cancellation event
            await self._event_store.append(
                run_id=run_id,
                event_type=WorkflowEventType.WORKFLOW_CANCELLED,
                payload={"reason": reason},
            )

            # Update status
            await self._event_store.update_run_status(
                run_id, WorkflowRunStatus.CANCELLED
            )

            logger.info("Cancelled workflow run %s: %s", run_id, reason)
            return True

    # ------------------------------------------------------------------
    # Core scheduling logic
    # ------------------------------------------------------------------

    async def _advance(
        self,
        run_id: str,
        definition: WorkflowDefinition,
    ) -> None:
        """
        The core scheduling loop: replay state → decide → act.

        This is called after every event to determine what happens next.
        """
        # 1. Load event history
        events = await self._event_store.load_history(run_id)

        # 2. Replay to get current state
        workflow_run = StateMachine.replay(events, definition)

        # 3. Determine next action
        action = StateMachine.determine_next_action(workflow_run, definition)

        # 4. Execute the decision
        match action.action_type:
            case NextActionType.SCHEDULE_ACTIVITY:
                await self._schedule_activity(run_id, action.activity_id, definition, workflow_run)

            case NextActionType.RETRY_ACTIVITY:
                await self._retry_activity(
                    run_id, action.activity_id, definition, workflow_run, action.delay_seconds
                )

            case NextActionType.COMPLETE_WORKFLOW:
                await self._complete_workflow(run_id, workflow_run)

            case NextActionType.FAIL_WORKFLOW:
                await self._fail_workflow(run_id, action.error or "Unknown error")

            case NextActionType.WAIT_ACTIVITY | NextActionType.WAIT_TIMER | NextActionType.NO_OP:
                pass  # Nothing to do, waiting for external event

    async def _schedule_activity(
        self,
        run_id: str,
        activity_id: Optional[str],
        definition: WorkflowDefinition,
        workflow_run: Any,
    ) -> None:
        """Schedule an activity for execution by enqueueing it."""
        if activity_id is None:
            return

        # Find activity definition
        activity_def = self._find_activity_def(definition, activity_id)
        if activity_def is None:
            logger.error("Activity definition not found: %s", activity_id)
            return

        # Build activity input
        activity_input = StateMachine.get_activity_input(workflow_run, activity_def)

        # Emit ACTIVITY_SCHEDULED event
        await self._event_store.append(
            run_id=run_id,
            event_type=WorkflowEventType.ACTIVITY_SCHEDULED,
            payload={
                "activity_id": activity_id,
                "activity_type": activity_def.activity_type,
                "label": activity_def.label,
                "attempt": 0,
            },
        )

        # Enqueue task for workers
        await self._task_queue.enqueue(
            workflow_run_id=run_id,
            activity_id=activity_id,
            activity_type=activity_def.activity_type,
            payload=activity_input,
            queue_name=activity_def.queue_name,
            timeout_seconds=activity_def.timeout_seconds,
            max_attempts=activity_def.retry_policy.max_attempts,
            attempt=0,
        )

        logger.debug(
            "Scheduled activity '%s' (%s) for run %s",
            activity_def.label or activity_id, activity_def.activity_type, run_id,
        )

    async def _retry_activity(
        self,
        run_id: str,
        activity_id: Optional[str],
        definition: WorkflowDefinition,
        workflow_run: Any,
        delay_seconds: float,
    ) -> None:
        """Retry a failed activity with delay."""
        if activity_id is None:
            return

        activity_def = self._find_activity_def(definition, activity_id)
        if activity_def is None:
            return

        # Get current attempt from state
        act_state = workflow_run.activity_states.get(activity_id)
        new_attempt = (act_state.attempt + 1) if act_state else 1

        # Evaluate retry with jitter
        retry_decision = evaluate_retry(
            policy=activity_def.retry_policy,
            attempt=act_state.attempt if act_state else 0,
            error=act_state.error or "" if act_state else "",
        )

        if not retry_decision.should_retry:
            # Shouldn't happen (state machine already checked), but safety net
            await self._fail_workflow(
                run_id,
                f"Activity '{activity_def.label or activity_id}' exhausted retries",
            )
            return

        actual_delay = retry_decision.delay_seconds

        # Emit ACTIVITY_RETRYING event
        await self._event_store.append(
            run_id=run_id,
            event_type=WorkflowEventType.ACTIVITY_RETRYING,
            payload={
                "activity_id": activity_id,
                "activity_type": activity_def.activity_type,
                "label": activity_def.label,
                "attempt": new_attempt,
                "delay_seconds": actual_delay,
            },
        )

        # Build activity input
        activity_input = StateMachine.get_activity_input(workflow_run, activity_def)

        # Enqueue with delay
        await self._task_queue.enqueue(
            workflow_run_id=run_id,
            activity_id=activity_id,
            activity_type=activity_def.activity_type,
            payload=activity_input,
            queue_name=activity_def.queue_name,
            timeout_seconds=activity_def.timeout_seconds,
            max_attempts=activity_def.retry_policy.max_attempts,
            attempt=new_attempt,
            delay_seconds=actual_delay,
        )

        logger.info(
            "Retrying activity '%s' (attempt %d, delay=%.1fs) for run %s",
            activity_def.label or activity_id, new_attempt, actual_delay, run_id,
        )

    async def _complete_workflow(self, run_id: str, workflow_run: Any) -> None:
        """Mark workflow as completed."""
        # Collect all activity outputs as workflow output
        output_data = {
            "activity_results": workflow_run.activity_results,
        }

        # Emit completion event
        await self._event_store.append(
            run_id=run_id,
            event_type=WorkflowEventType.WORKFLOW_COMPLETED,
            payload={"output_data": output_data},
        )

        # Update run status
        await self._event_store.update_run_status(
            run_id, WorkflowRunStatus.COMPLETED, output_data=output_data
        )

        # Cancel workflow timeout timer
        await self._timer_service.cancel(run_id, "__workflow_timeout__")

        logger.info("Workflow run %s completed successfully", run_id)

    async def _fail_workflow(self, run_id: str, error: str) -> None:
        """Mark workflow as failed."""
        # Emit failure event
        await self._event_store.append(
            run_id=run_id,
            event_type=WorkflowEventType.WORKFLOW_FAILED,
            payload={"error": error},
        )

        # Update run status
        await self._event_store.update_run_status(
            run_id, WorkflowRunStatus.FAILED, error=error
        )

        # Cancel pending tasks and timers
        await self._task_queue.cancel_by_run(run_id)
        await self._timer_service.cancel_all_for_run(run_id)

        logger.warning("Workflow run %s failed: %s", run_id, error)

    async def _timeout_workflow(self, run_id: str) -> None:
        """Handle workflow timeout."""
        await self._event_store.append(
            run_id=run_id,
            event_type=WorkflowEventType.WORKFLOW_TIMED_OUT,
            payload={"error": "Workflow execution exceeded timeout"},
        )

        await self._event_store.update_run_status(
            run_id, WorkflowRunStatus.TIMED_OUT, error="Workflow execution exceeded timeout"
        )

        # Cancel pending tasks and timers
        await self._task_queue.cancel_by_run(run_id)
        await self._timer_service.cancel_all_for_run(run_id)

        logger.warning("Workflow run %s timed out", run_id)

    # ------------------------------------------------------------------
    # Recovery support
    # ------------------------------------------------------------------

    async def resume_workflow(self, run_id: str) -> bool:
        """
        Resume a workflow that was interrupted (e.g., after process restart).

        Replays events and determines the next action to take.
        Called by the recovery orchestrator.
        """
        definition = await self._get_definition_for_run(run_id)
        if definition is None:
            logger.warning("Cannot resume run %s: no definition found", run_id)
            return False

        lock = self._get_run_lock(run_id)
        async with lock:
            await self._advance(run_id, definition)

        logger.info("Resumed workflow run %s", run_id)
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_run_lock(self, run_id: str) -> asyncio.Lock:
        """Get or create a per-run lock to prevent concurrent scheduling."""
        if run_id not in self._run_locks:
            self._run_locks[run_id] = asyncio.Lock()
        return self._run_locks[run_id]

    def _find_activity_def(
        self,
        definition: WorkflowDefinition,
        activity_id: str,
    ) -> Optional[ActivityDefinition]:
        """Find an activity definition by ID."""
        for activity in definition.activities:
            if activity.activity_id == activity_id:
                return activity
        return None

    async def _get_definition_for_run(
        self, run_id: str
    ) -> Optional[WorkflowDefinition]:
        """Get the workflow definition for a run."""
        run_data = await self._event_store.get_run(run_id)
        if run_data is None:
            return None
        return self._definitions.get(run_data["workflow_id"])

    def cleanup_locks(self, run_ids: Optional[List[str]] = None) -> None:
        """Remove locks for completed runs (memory cleanup)."""
        if run_ids:
            for run_id in run_ids:
                self._run_locks.pop(run_id, None)
        else:
            self._run_locks.clear()
