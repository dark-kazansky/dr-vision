"""
Pull-based Worker — Executes activities by polling the task queue.

Workers are the execution units of the workflow engine. They:
1. Poll the task queue for available tasks
2. Execute the activity (calling the registered activity handler)
3. Report results back to the scheduler (via ack/nack)
4. Send periodic heartbeats to prove they're alive

Key design decisions:
- Pull-based: Workers decide when to take work (natural backpressure)
- Stateless: No local state — all context comes from the task payload
- Horizontally scalable: Add more workers without coordination
- Graceful shutdown: Finish current task before stopping

Workers don't know about workflow state — they just execute individual activities
and report results. The scheduler handles all orchestration decisions.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Coroutine, Dict, Optional

from services.workflow_engine.models import ActivityTask
from services.workflow_engine.scheduler import WorkflowScheduler
from services.workflow_engine.task_queue import TaskQueue

logger = logging.getLogger(__name__)

# Type alias for activity handler functions
ActivityHandler = Callable[[ActivityTask], Coroutine[Any, Any, Dict[str, Any]]]


class Worker:
    """
    Pull-based activity worker.

    Polls the task queue, executes activities via registered handlers,
    and reports results to the scheduler.

    Usage:
        worker = Worker(
            task_queue=task_queue,
            scheduler=scheduler,
            queue_name="default",
        )
        worker.register_handler("ocr_parse", handle_ocr_parse)
        worker.register_handler("ocr_classify", handle_ocr_classify)
        await worker.start()
        ...
        await worker.stop()
    """

    def __init__(
        self,
        task_queue: TaskQueue,
        scheduler: WorkflowScheduler,
        queue_name: str = "default",
        worker_id: Optional[str] = None,
        poll_interval_seconds: float = 1.0,
        heartbeat_interval_seconds: float = 30.0,
        max_concurrent: int = 2,
    ) -> None:
        """
        Args:
            task_queue: The distributed task queue to poll.
            scheduler: The workflow scheduler to report results to.
            queue_name: Which queue to poll from.
            worker_id: Unique identifier for this worker (auto-generated if None).
            poll_interval_seconds: How often to poll when queue is empty.
            heartbeat_interval_seconds: How often to send heartbeats for running tasks.
            max_concurrent: Maximum concurrent activity executions.
        """
        self._task_queue = task_queue
        self._scheduler = scheduler
        self._queue_name = queue_name
        self._worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._poll_interval = poll_interval_seconds
        self._heartbeat_interval = heartbeat_interval_seconds
        self._max_concurrent = max_concurrent

        # Activity handlers registry: activity_type → handler function
        self._handlers: Dict[str, ActivityHandler] = {}

        # Runtime state
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._active_tasks: Dict[str, asyncio.Task] = {}  # task_id → asyncio.Task
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}  # task_id → heartbeat task
        self._semaphore: Optional[asyncio.Semaphore] = None

    @property
    def worker_id(self) -> str:
        return self._worker_id

    @property
    def active_count(self) -> int:
        return len(self._active_tasks)

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(
        self,
        activity_type: str,
        handler: ActivityHandler,
    ) -> None:
        """
        Register a handler function for an activity type.

        The handler receives an ActivityTask and must return a dict (the output).
        If the handler raises an exception, the activity is marked as failed.

        Args:
            activity_type: The activity type this handler processes.
            handler: Async function (ActivityTask) → Dict[str, Any].
        """
        self._handlers[activity_type] = handler
        logger.debug(
            "Worker %s: registered handler for '%s'",
            self._worker_id, activity_type,
        )

    def register_handlers(self, handlers: Dict[str, ActivityHandler]) -> None:
        """Register multiple handlers at once."""
        for activity_type, handler in handlers.items():
            self.register_handler(activity_type, handler)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the worker polling loop."""
        if self._running:
            return
        self._running = True
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._poll_task = asyncio.create_task(
            self._poll_loop(), name=f"{self._worker_id}-poll"
        )
        logger.info(
            "Worker %s started (queue='%s', max_concurrent=%d, handlers=%s)",
            self._worker_id, self._queue_name, self._max_concurrent,
            list(self._handlers.keys()),
        )

    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the worker.

        Args:
            graceful: If True, wait for current tasks to finish before stopping.
                      If False, cancel immediately.
        """
        self._running = False

        # Stop polling
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        if graceful and self._active_tasks:
            # Wait for active tasks to complete (with timeout)
            logger.info(
                "Worker %s: graceful shutdown, waiting for %d active task(s)...",
                self._worker_id, len(self._active_tasks),
            )
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks.values(), return_exceptions=True),
                    timeout=60.0,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Worker %s: shutdown timeout, cancelling remaining tasks",
                    self._worker_id,
                )
        elif not graceful:
            # Cancel all active tasks
            for task in self._active_tasks.values():
                task.cancel()

        # Cancel all heartbeat tasks
        for hb_task in self._heartbeat_tasks.values():
            hb_task.cancel()

        self._active_tasks.clear()
        self._heartbeat_tasks.clear()

        logger.info("Worker %s stopped", self._worker_id)

    # ------------------------------------------------------------------
    # Poll loop
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Main polling loop — pulls tasks from the queue and executes them."""
        logger.debug("Worker %s: poll loop started", self._worker_id)

        while self._running:
            try:
                # Wait for capacity
                if self._semaphore is None:
                    break
                await self._semaphore.acquire()

                if not self._running:
                    self._semaphore.release()
                    break

                # Poll for a task
                tasks = await self._task_queue.poll(
                    worker_id=self._worker_id,
                    queue_name=self._queue_name,
                    batch_size=1,
                )

                if not tasks:
                    # No tasks available — release semaphore and wait
                    self._semaphore.release()
                    await asyncio.sleep(self._poll_interval)
                    continue

                task = tasks[0]

                # Check if we have a handler for this activity type
                if task.activity_type not in self._handlers:
                    logger.warning(
                        "Worker %s: no handler for activity type '%s', nacking task %s",
                        self._worker_id, task.activity_type, task.task_id,
                    )
                    await self._task_queue.nack(
                        task.task_id,
                        error=f"No handler registered for activity type: {task.activity_type}",
                    )
                    self._semaphore.release()
                    continue

                # Execute the task asynchronously
                execution_task = asyncio.create_task(
                    self._execute_task(task),
                    name=f"{self._worker_id}-exec-{task.task_id[:8]}",
                )
                self._active_tasks[task.task_id] = execution_task

                # Start heartbeat for this task
                hb_task = asyncio.create_task(
                    self._heartbeat_loop(task.task_id),
                    name=f"{self._worker_id}-hb-{task.task_id[:8]}",
                )
                self._heartbeat_tasks[task.task_id] = hb_task

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Worker %s: poll loop error: %s", self._worker_id, e)
                if self._semaphore:
                    self._semaphore.release()
                await asyncio.sleep(self._poll_interval)

        logger.debug("Worker %s: poll loop stopped", self._worker_id)

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    async def _execute_task(self, task: ActivityTask) -> None:
        """Execute a single activity task and report results."""
        start_time = time.time()
        task_id = task.task_id
        run_id = task.workflow_run_id
        activity_id = task.activity_id

        try:
            # Notify scheduler that activity started
            await self._scheduler.on_activity_started(
                run_id=run_id,
                activity_id=activity_id,
                worker_id=self._worker_id,
            )

            # Get handler
            handler = self._handlers[task.activity_type]

            # Execute the activity
            logger.debug(
                "Worker %s: executing activity '%s' (task=%s, run=%s)",
                self._worker_id, task.activity_type, task_id[:8], run_id[:8],
            )

            output = await handler(task)

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Ack the task
            await self._task_queue.ack(task_id, result=output)

            # Notify scheduler of success
            await self._scheduler.on_activity_completed(
                run_id=run_id,
                activity_id=activity_id,
                output=output,
                duration_ms=duration_ms,
            )

            logger.debug(
                "Worker %s: activity '%s' completed in %dms (task=%s)",
                self._worker_id, task.activity_type, duration_ms, task_id[:8],
            )

        except asyncio.CancelledError:
            # Task was cancelled (worker shutdown)
            logger.info(
                "Worker %s: task %s cancelled during execution",
                self._worker_id, task_id[:8],
            )
            # Don't ack or nack — let visibility timeout handle it
            raise

        except Exception as e:
            # Activity failed
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            logger.warning(
                "Worker %s: activity '%s' failed (task=%s): %s",
                self._worker_id, task.activity_type, task_id[:8], error_msg,
            )

            # Nack the task (task_queue handles retry count)
            await self._task_queue.nack(task_id, error=error_msg)

            # Notify scheduler of failure
            await self._scheduler.on_activity_failed(
                run_id=run_id,
                activity_id=activity_id,
                error=error_msg,
                duration_ms=duration_ms,
            )

        finally:
            # Cleanup
            self._active_tasks.pop(task_id, None)

            # Stop heartbeat
            hb_task = self._heartbeat_tasks.pop(task_id, None)
            if hb_task:
                hb_task.cancel()

            # Release semaphore
            if self._semaphore:
                self._semaphore.release()

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self, task_id: str) -> None:
        """Send periodic heartbeats for a running task."""
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                success = await self._task_queue.heartbeat(task_id)
                if not success:
                    # Task no longer in processing state (completed, cancelled, etc.)
                    break
        except asyncio.CancelledError:
            pass


# =============================================================================
# Worker Pool (convenience for running multiple workers)
# =============================================================================


class WorkerPool:
    """
    Manages a pool of workers for horizontal scaling within a single process.

    Usage:
        pool = WorkerPool(task_queue, scheduler, num_workers=4)
        pool.register_handler("ocr_parse", handle_parse)
        await pool.start()
        ...
        await pool.stop()
    """

    def __init__(
        self,
        task_queue: TaskQueue,
        scheduler: WorkflowScheduler,
        num_workers: int = 2,
        queue_name: str = "default",
        max_concurrent_per_worker: int = 1,
        poll_interval_seconds: float = 1.0,
        heartbeat_interval_seconds: float = 30.0,
    ) -> None:
        self._task_queue = task_queue
        self._scheduler = scheduler
        self._num_workers = num_workers
        self._queue_name = queue_name
        self._max_concurrent = max_concurrent_per_worker
        self._poll_interval = poll_interval_seconds
        self._heartbeat_interval = heartbeat_interval_seconds
        self._handlers: Dict[str, ActivityHandler] = {}
        self._workers: list[Worker] = []

    def register_handler(self, activity_type: str, handler: ActivityHandler) -> None:
        """Register a handler for all workers in the pool."""
        self._handlers[activity_type] = handler

    def register_handlers(self, handlers: Dict[str, ActivityHandler]) -> None:
        """Register multiple handlers for all workers."""
        self._handlers.update(handlers)

    async def start(self) -> None:
        """Create and start all workers."""
        for i in range(self._num_workers):
            worker = Worker(
                task_queue=self._task_queue,
                scheduler=self._scheduler,
                queue_name=self._queue_name,
                worker_id=f"pool-worker-{i}",
                poll_interval_seconds=self._poll_interval,
                heartbeat_interval_seconds=self._heartbeat_interval,
                max_concurrent=self._max_concurrent,
            )
            worker.register_handlers(self._handlers)
            await worker.start()
            self._workers.append(worker)

        logger.info(
            "WorkerPool started: %d workers on queue '%s'",
            self._num_workers, self._queue_name,
        )

    async def stop(self, graceful: bool = True) -> None:
        """Stop all workers in the pool."""
        for worker in self._workers:
            await worker.stop(graceful=graceful)
        self._workers.clear()
        logger.info("WorkerPool stopped")

    @property
    def total_active(self) -> int:
        """Total number of active tasks across all workers."""
        return sum(w.active_count for w in self._workers)

    @property
    def workers(self) -> list:
        return list(self._workers)
