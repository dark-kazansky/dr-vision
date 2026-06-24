"""
Workflow Engine — High-level facade that wires all components together.

This is the main entry point for using the durable workflow engine.
It initializes all subsystems, manages their lifecycle, and provides
a clean API for starting/querying/cancelling workflows.

Usage:
    from services.workflow_engine import WorkflowEngine

    engine = WorkflowEngine(pool)
    await engine.start()

    run_id = await engine.start_workflow(definition, input_data={"file_path": "/path/to/file"})
    status = await engine.get_run_status(run_id)

    await engine.stop()
"""

import logging
from typing import Any, Dict, List, Optional

import asyncpg

from services.workflow_engine.activities import get_all_handlers
from services.workflow_engine.event_store import EventStore
from services.workflow_engine.models import (
    DurableTimer,
    WorkflowDefinition,
)
from services.workflow_engine.recovery import RecoveryOrchestrator
from services.workflow_engine.scheduler import WorkflowScheduler
from services.workflow_engine.task_queue import TaskQueue
from services.workflow_engine.timer_service import TimerService
from services.workflow_engine.worker import ActivityHandler, WorkerPool

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    High-level facade for the durable workflow orchestration engine.

    Wires together: EventStore, TaskQueue, TimerService, Scheduler,
    Recovery, and Workers into a single lifecycle-managed unit.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        num_workers: int = 2,
        queue_name: str = "default",
        timer_poll_interval: float = 1.0,
        reclaim_interval: float = 30.0,
        stale_threshold: int = 600,
    ) -> None:
        """
        Args:
            pool: asyncpg connection pool.
            num_workers: Number of activity workers to run.
            queue_name: Default task queue name.
            timer_poll_interval: How often to check for due timers (seconds).
            reclaim_interval: How often to reclaim timed-out tasks (seconds).
            stale_threshold: Seconds of inactivity before a run is considered stale.
        """
        self._pool = pool
        self._num_workers = num_workers
        self._queue_name = queue_name
        self._started = False

        # Initialize components
        self._event_store = EventStore(pool)
        self._task_queue = TaskQueue(pool)
        self._timer_service = TimerService(
            pool,
            poll_interval_seconds=timer_poll_interval,
            on_timer_fired=self._handle_timer_fired,
        )
        self._scheduler = WorkflowScheduler(
            event_store=self._event_store,
            task_queue=self._task_queue,
            timer_service=self._timer_service,
        )
        self._recovery = RecoveryOrchestrator(
            event_store=self._event_store,
            task_queue=self._task_queue,
            timer_service=self._timer_service,
            scheduler=self._scheduler,
            reclaim_interval_seconds=reclaim_interval,
            stale_threshold_seconds=stale_threshold,
        )
        self._worker_pool = WorkerPool(
            task_queue=self._task_queue,
            scheduler=self._scheduler,
            num_workers=num_workers,
            queue_name=queue_name,
        )

        # Register default OCR activity handlers
        self._worker_pool.register_handlers(get_all_handlers())

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def event_store(self) -> EventStore:
        return self._event_store

    @property
    def task_queue(self) -> TaskQueue:
        return self._task_queue

    @property
    def timer_service(self) -> TimerService:
        return self._timer_service

    @property
    def scheduler(self) -> WorkflowScheduler:
        return self._scheduler

    @property
    def recovery(self) -> RecoveryOrchestrator:
        return self._recovery

    @property
    def is_running(self) -> bool:
        return self._started

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """
        Start the workflow engine.

        Initializes schemas, starts workers, timer service, and recovery.
        """
        if self._started:
            return

        # Initialize database schemas
        await self._event_store.init_schema()
        await self._task_queue.init_schema()
        await self._timer_service.init_schema()

        # Start background services
        await self._timer_service.start()
        await self._worker_pool.start()
        await self._recovery.start()

        self._started = True
        logger.info(
            "WorkflowEngine started (workers=%d, queue='%s')",
            self._num_workers, self._queue_name,
        )

    async def stop(self) -> None:
        """Stop the workflow engine gracefully."""
        if not self._started:
            return

        self._started = False

        # Stop in reverse order
        await self._recovery.stop()
        await self._worker_pool.stop(graceful=True)
        await self._timer_service.stop()

        logger.info("WorkflowEngine stopped")

    # ------------------------------------------------------------------
    # Workflow operations
    # ------------------------------------------------------------------

    async def start_workflow(
        self,
        definition: WorkflowDefinition,
        input_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a new workflow execution.

        Args:
            definition: The workflow blueprint (activities, config).
            input_data: Input data accessible to all activities.
            metadata: Optional metadata (user_id, source, etc.).

        Returns:
            The run_id of the started workflow.
        """
        if not self._started:
            raise RuntimeError("WorkflowEngine is not started")

        return await self._scheduler.start_workflow(
            definition=definition,
            input_data=input_data,
            metadata=metadata,
        )

    async def cancel_workflow(self, run_id: str, reason: str = "") -> bool:
        """Cancel a running workflow."""
        return await self._scheduler.cancel_workflow(run_id, reason)

    async def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status and metadata of a workflow run."""
        return await self._event_store.get_run(run_id)

    async def get_run_events(self, run_id: str) -> list:
        """Get the full event history for a workflow run."""
        return await self._event_store.load_history(run_id)

    async def get_run_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the fully reconstructed workflow state (replay events).

        Returns the WorkflowRun as a dict, including all activity states.
        """
        from services.workflow_engine.state_machine import StateMachine

        run_data = await self._event_store.get_run(run_id)
        if run_data is None:
            return None

        definition = self._scheduler.get_definition(run_data["workflow_id"])
        if definition is None:
            # Return basic info without full replay
            return run_data

        events = await self._event_store.load_history(run_id)
        workflow_run = StateMachine.replay(events, definition)
        return workflow_run.model_dump()

    async def list_runs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List workflow runs, optionally filtered by status."""
        if status:
            return await self._event_store.list_runs_by_status(status, limit=limit)
        # List all recent runs
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM workflow_runs ORDER BY created_at DESC LIMIT $1",
                limit,
            )
        from services.workflow_engine.event_store import _row_to_run
        return [_row_to_run(r) for r in rows]

    async def get_health(self) -> Dict[str, Any]:
        """Get engine health summary."""
        return await self._recovery.get_health_summary()

    # ------------------------------------------------------------------
    # Activity handler registration
    # ------------------------------------------------------------------

    def register_activity(
        self,
        activity_type: str,
        handler: ActivityHandler,
    ) -> None:
        """
        Register a custom activity handler.

        Args:
            activity_type: The activity type string.
            handler: Async function that takes ActivityTask and returns Dict.
        """
        self._worker_pool.register_handler(activity_type, handler)

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------

    async def _handle_timer_fired(self, timer: DurableTimer) -> None:
        """Callback when a durable timer fires — routes to scheduler."""
        await self._scheduler.on_timer_fired(
            run_id=timer.workflow_run_id,
            timer_name=timer.name,
            payload=timer.payload,
        )
