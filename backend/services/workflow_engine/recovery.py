"""
Recovery Orchestrator — Automatic failure recovery for the workflow engine.

Handles two types of recovery:

1. Startup Recovery:
   - Find workflow runs that were in-progress when the process crashed
   - Replay their event history to determine current state
   - Re-schedule any pending activities that lost their workers

2. Periodic Recovery:
   - Reclaim timed-out tasks (worker died mid-execution)
   - Detect stale workflows (no activity for too long)
   - Clean up resources (old completed runs, fired timers, dead locks)

This ensures the system is self-healing: no manual intervention needed
after crashes, restarts, or worker failures.
"""

import asyncio
import logging
from typing import Optional

from services.workflow_engine.event_store import EventStore
from services.workflow_engine.models import WorkflowRunStatus
from services.workflow_engine.scheduler import WorkflowScheduler
from services.workflow_engine.task_queue import TaskQueue
from services.workflow_engine.timer_service import TimerService

logger = logging.getLogger(__name__)


class RecoveryOrchestrator:
    """
    Self-healing recovery system for the durable workflow engine.

    Runs as a background process that periodically:
    - Reclaims timed-out tasks from dead workers
    - Resumes stale workflows
    - Cleans up old data

    Also provides on-demand startup recovery.
    """

    def __init__(
        self,
        event_store: EventStore,
        task_queue: TaskQueue,
        timer_service: TimerService,
        scheduler: WorkflowScheduler,
        reclaim_interval_seconds: float = 30.0,
        stale_threshold_seconds: int = 600,
        cleanup_interval_seconds: float = 3600.0,
        cleanup_retention_hours: int = 168,
    ) -> None:
        """
        Args:
            event_store: The event store for workflow state.
            task_queue: The distributed task queue.
            timer_service: The durable timer service.
            scheduler: The workflow scheduler (for resuming workflows).
            reclaim_interval_seconds: How often to check for timed-out tasks.
            stale_threshold_seconds: How long a workflow can be idle before recovery.
            cleanup_interval_seconds: How often to run cleanup (default 1 hour).
            cleanup_retention_hours: How long to keep completed data (default 7 days).
        """
        self._event_store = event_store
        self._task_queue = task_queue
        self._timer_service = timer_service
        self._scheduler = scheduler
        self._reclaim_interval = reclaim_interval_seconds
        self._stale_threshold = stale_threshold_seconds
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_retention_hours = cleanup_retention_hours
        self._running = False
        self._reclaim_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the recovery orchestrator background loops."""
        if self._running:
            return
        self._running = True

        # Run startup recovery first
        await self.recover_on_startup()

        # Start periodic loops
        self._reclaim_task = asyncio.create_task(
            self._reclaim_loop(), name="recovery-reclaim-loop"
        )
        self._cleanup_task = asyncio.create_task(
            self._cleanup_loop(), name="recovery-cleanup-loop"
        )

        logger.info(
            "RecoveryOrchestrator started (reclaim_interval=%.0fs, stale_threshold=%ds)",
            self._reclaim_interval, self._stale_threshold,
        )

    async def stop(self) -> None:
        """Stop all background loops."""
        self._running = False

        tasks = [t for t in (self._reclaim_task, self._cleanup_task) if t]
        for task in tasks:
            task.cancel()

        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._reclaim_task = None
        self._cleanup_task = None
        logger.info("RecoveryOrchestrator stopped")

    # ------------------------------------------------------------------
    # Startup Recovery
    # ------------------------------------------------------------------

    async def recover_on_startup(self) -> int:
        """
        Recover workflows that were interrupted by a process crash.

        Finds all runs in active states (running, waiting_activity, waiting_timer)
        and attempts to resume them by replaying events and re-scheduling.

        Returns:
            Number of workflows recovered.
        """
        logger.info("Starting startup recovery...")
        recovered = 0

        # 1. Reclaim any timed-out tasks first
        reclaimed = await self._task_queue.reclaim_timed_out()
        if reclaimed > 0:
            logger.info("Startup: reclaimed %d timed-out tasks", reclaimed)

        # 2. Find stale workflows (no recent events)
        stale_runs = await self._event_store.list_stale_runs(
            stale_seconds=self._stale_threshold,
        )

        for run_data in stale_runs:
            run_id = run_data["run_id"]
            try:
                success = await self._scheduler.resume_workflow(run_id)
                if success:
                    recovered += 1
                    logger.info(
                        "Recovered workflow run %s (was %s)",
                        run_id, run_data["status"],
                    )
            except Exception as e:
                logger.error(
                    "Failed to recover workflow run %s: %s", run_id, e
                )

        # 3. Also check runs in RUNNING/WAITING state that aren't stale
        #    but may have lost their scheduled tasks
        active_runs = await self._event_store.list_runs_by_status(
            WorkflowRunStatus.WAITING_ACTIVITY
        )

        for run_data in active_runs:
            run_id = run_data["run_id"]
            # Check if this run has any active tasks in the queue
            tasks = await self._task_queue.get_tasks_by_run(run_id, status="pending")
            processing = await self._task_queue.get_tasks_by_run(run_id, status="processing")

            if not tasks and not processing:
                # Run is waiting but has no tasks — needs re-scheduling
                try:
                    success = await self._scheduler.resume_workflow(run_id)
                    if success:
                        recovered += 1
                        logger.info(
                            "Recovered orphaned workflow run %s (no active tasks)",
                            run_id,
                        )
                except Exception as e:
                    logger.error(
                        "Failed to recover orphaned run %s: %s", run_id, e
                    )

        if recovered > 0:
            logger.info("Startup recovery complete: %d workflow(s) recovered", recovered)
        else:
            logger.info("Startup recovery complete: no workflows needed recovery")

        return recovered

    # ------------------------------------------------------------------
    # Periodic task reclaim
    # ------------------------------------------------------------------

    async def _reclaim_loop(self) -> None:
        """Periodically reclaim timed-out tasks and check for stale workflows."""
        logger.debug("Reclaim loop started")

        while self._running:
            try:
                await asyncio.sleep(self._reclaim_interval)

                # Reclaim timed-out tasks
                reclaimed = await self._task_queue.reclaim_timed_out()

                # If tasks were reclaimed, the affected workflows may need re-evaluation
                if reclaimed > 0:
                    logger.info("Periodic reclaim: %d tasks recovered", reclaimed)

                # Check for stale workflows periodically
                stale_runs = await self._event_store.list_stale_runs(
                    stale_seconds=self._stale_threshold,
                    limit=10,
                )

                for run_data in stale_runs:
                    try:
                        await self._scheduler.resume_workflow(run_data["run_id"])
                    except Exception as e:
                        logger.debug(
                            "Failed to resume stale run %s: %s",
                            run_data["run_id"], e,
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Reclaim loop error: %s", e)
                await asyncio.sleep(5)

        logger.debug("Reclaim loop stopped")

    # ------------------------------------------------------------------
    # Periodic cleanup
    # ------------------------------------------------------------------

    async def _cleanup_loop(self) -> None:
        """Periodically clean up old completed data."""
        logger.debug("Cleanup loop started (interval=%.0fs)", self._cleanup_interval)

        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self.run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Cleanup loop error: %s", e)
                await asyncio.sleep(60)

        logger.debug("Cleanup loop stopped")

    async def run_cleanup(self) -> dict:
        """
        Run a full cleanup cycle.

        Returns a summary dict with counts of deleted items.
        """
        results = {
            "old_runs": 0,
            "old_tasks": 0,
            "old_timers": 0,
        }

        try:
            results["old_runs"] = await self._event_store.delete_old_runs(
                older_than_hours=self._cleanup_retention_hours
            )
        except Exception as e:
            logger.warning("Cleanup old runs failed: %s", e)

        try:
            results["old_tasks"] = await self._task_queue.cleanup_old_tasks(
                older_than_hours=self._cleanup_retention_hours
            )
        except Exception as e:
            logger.warning("Cleanup old tasks failed: %s", e)

        try:
            results["old_timers"] = await self._timer_service.cleanup_old_timers(
                older_than_hours=self._cleanup_retention_hours
            )
        except Exception as e:
            logger.warning("Cleanup old timers failed: %s", e)

        # Clean up scheduler locks for completed runs
        self._scheduler.cleanup_locks()

        total = sum(results.values())
        if total > 0:
            logger.info(
                "Cleanup complete: %d runs, %d tasks, %d timers removed",
                results["old_runs"], results["old_tasks"], results["old_timers"],
            )

        return results

    # ------------------------------------------------------------------
    # Manual recovery tools
    # ------------------------------------------------------------------

    async def force_fail_workflow(self, run_id: str, reason: str = "") -> bool:
        """
        Force-fail a stuck workflow.

        Use when a workflow is stuck and automatic recovery can't fix it.
        """
        error = reason or "Force-failed by operator"

        try:
            run_data = await self._event_store.get_run(run_id)
            if run_data is None:
                return False

            if run_data["status"] in (
                WorkflowRunStatus.COMPLETED,
                WorkflowRunStatus.FAILED,
                WorkflowRunStatus.CANCELLED,
            ):
                return False

            # Cancel tasks and timers
            await self._task_queue.cancel_by_run(run_id)
            await self._timer_service.cancel_all_for_run(run_id)

            # Emit failure event
            from services.workflow_engine.models import WorkflowEventType
            await self._event_store.append(
                run_id=run_id,
                event_type=WorkflowEventType.WORKFLOW_FAILED,
                payload={"error": error, "forced": True},
            )

            await self._event_store.update_run_status(
                run_id, WorkflowRunStatus.FAILED, error=error
            )

            logger.warning("Force-failed workflow run %s: %s", run_id, error)
            return True

        except Exception as e:
            logger.error("Failed to force-fail run %s: %s", run_id, e)
            return False

    async def get_health_summary(self) -> dict:
        """
        Get a health summary of the workflow engine.

        Useful for monitoring dashboards and alerting.
        """
        summary = {
            "active_runs": 0,
            "stale_runs": 0,
            "pending_tasks": 0,
            "processing_tasks": 0,
            "timed_out_estimate": 0,
        }

        try:
            active = await self._event_store.list_runs_by_status(
                WorkflowRunStatus.RUNNING
            )
            waiting = await self._event_store.list_runs_by_status(
                WorkflowRunStatus.WAITING_ACTIVITY
            )
            summary["active_runs"] = len(active) + len(waiting)

            stale = await self._event_store.list_stale_runs(
                stale_seconds=self._stale_threshold
            )
            summary["stale_runs"] = len(stale)

            summary["pending_tasks"] = await self._task_queue.get_pending_count()
            summary["processing_tasks"] = await self._task_queue.get_processing_count()

        except Exception as e:
            logger.warning("Failed to get health summary: %s", e)

        return summary
