"""
Batch Processor — Parallel multi-file document processing with progress tracking.

Orchestrates processing of multiple files (or zip archives) through a configured
workflow pipeline. Each file is processed independently with configurable concurrency.

Features:
- Upload multiple files or a zip archive
- Parallel processing (configurable max concurrency)
- Per-file progress tracking via event bus
- Batch-level summary (total/completed/failed/skipped)
- Cancel support (stops remaining unstarted files)
- Resume capability (skip already-processed files)
- Results aggregation

Architecture:
    BatchProcessor manages a collection of file tasks.
    Each file task runs through the workflow_service (same OCR pipeline).
    Progress emitted via asyncio.Queue for SSE streaming.
"""

import asyncio
import logging
import os
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums & Models
# =============================================================================


class BatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # Some files completed, some failed


class FileStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class FileTask:
    """A single file within a batch."""

    file_id: str
    filename: str
    file_path: str
    status: FileStatus = FileStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
        }


@dataclass
class BatchJob:
    """A batch processing job containing multiple files."""

    batch_id: str
    status: BatchStatus = BatchStatus.PENDING
    files: List[FileTask] = field(default_factory=list)
    workflow_steps: List[Dict[str, Any]] = field(default_factory=list)
    max_concurrency: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.files)

    @property
    def completed_count(self) -> int:
        return sum(1 for f in self.files if f.status == FileStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for f in self.files if f.status == FileStatus.FAILED)

    @property
    def pending_count(self) -> int:
        return sum(1 for f in self.files if f.status == FileStatus.PENDING)

    @property
    def progress(self) -> float:
        if not self.files:
            return 0.0
        done = sum(
            1 for f in self.files
            if f.status in (FileStatus.COMPLETED, FileStatus.FAILED, FileStatus.SKIPPED, FileStatus.CANCELLED)
        )
        return done / len(self.files)

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "total": self.total,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "pending": self.pending_count,
            "progress": round(self.progress, 3),
            "max_concurrency": self.max_concurrency,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "files": [f.to_dict() for f in self.files],
        }

    def summary_dict(self) -> dict:
        """Lightweight summary without per-file details."""
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "total": self.total,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "pending": self.pending_count,
            "progress": round(self.progress, 3),
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# Batch Event (for SSE streaming)
# =============================================================================


@dataclass
class BatchEvent:
    """Event emitted during batch processing."""

    batch_id: str
    event_type: str  # batch_started, file_started, file_completed, file_failed, batch_completed, etc.
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_sse_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "event": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }


# =============================================================================
# Batch Processor
# =============================================================================


# File processing function type
FileProcessor = Callable[[str, List[Dict[str, Any]]], Coroutine[Any, Any, Dict[str, Any]]]


class BatchProcessor:
    """
    Manages batch processing jobs.

    Usage:
        processor = BatchProcessor(file_processor=my_process_func)
        batch_id = await processor.create_batch(file_paths, steps)
        await processor.start_batch(batch_id)

        # Subscribe to events
        async for event in processor.subscribe(batch_id):
            print(event)
    """

    def __init__(
        self,
        file_processor: Optional[FileProcessor] = None,
        default_concurrency: int = 3,
        upload_folder: str = "uploads",
    ):
        """
        Args:
            file_processor: Async function(file_path, steps) → result dict
            default_concurrency: Default max parallel files
            upload_folder: Where uploaded files are stored
        """
        self._file_processor = file_processor
        self._default_concurrency = default_concurrency
        self._upload_folder = upload_folder
        self._batches: Dict[str, BatchJob] = {}
        self._event_queues: Dict[str, List[asyncio.Queue]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # Batch lifecycle
    # ------------------------------------------------------------------

    def create_batch(
        self,
        file_paths: List[str],
        workflow_steps: List[Dict[str, Any]],
        max_concurrency: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new batch job from a list of file paths.

        Returns the batch_id.
        """
        batch_id = uuid.uuid4().hex[:16]
        concurrency = max_concurrency or self._default_concurrency

        files = []
        for fp in file_paths:
            files.append(FileTask(
                file_id=uuid.uuid4().hex[:12],
                filename=os.path.basename(fp),
                file_path=fp,
            ))

        batch = BatchJob(
            batch_id=batch_id,
            files=files,
            workflow_steps=workflow_steps,
            max_concurrency=concurrency,
            metadata=metadata or {},
        )
        self._batches[batch_id] = batch

        logger.info(
            "Batch %s created (%d files, concurrency=%d)",
            batch_id, len(files), concurrency,
        )
        return batch_id

    async def start_batch(self, batch_id: str) -> bool:
        """Start processing a batch. Returns False if batch not found."""
        batch = self._batches.get(batch_id)
        if batch is None:
            return False

        if batch.status != BatchStatus.PENDING:
            return False

        batch.status = BatchStatus.PROCESSING
        batch.started_at = datetime.now(timezone.utc)

        # Emit batch_started event
        await self._emit(batch_id, "batch_started", {
            "total": batch.total,
            "max_concurrency": batch.max_concurrency,
        })

        # Start processing in background
        task = asyncio.create_task(
            self._process_batch(batch),
            name=f"batch-{batch_id}",
        )
        self._tasks[batch_id] = task

        return True

    async def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a running batch. Stops remaining unstarted files."""
        batch = self._batches.get(batch_id)
        if batch is None:
            return False

        if batch.status not in (BatchStatus.PENDING, BatchStatus.PROCESSING):
            return False

        batch.cancelled = True

        # Mark pending files as cancelled
        for f in batch.files:
            if f.status == FileStatus.PENDING:
                f.status = FileStatus.CANCELLED

        # Cancel the background task
        task = self._tasks.get(batch_id)
        if task and not task.done():
            task.cancel()

        batch.status = BatchStatus.CANCELLED
        batch.completed_at = datetime.now(timezone.utc)

        await self._emit(batch_id, "batch_cancelled", {
            "completed": batch.completed_count,
            "cancelled": sum(1 for f in batch.files if f.status == FileStatus.CANCELLED),
        })

        logger.info("Batch %s cancelled", batch_id)
        return True

    def get_batch(self, batch_id: str) -> Optional[BatchJob]:
        """Get a batch job by ID."""
        return self._batches.get(batch_id)

    def list_batches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent batches (summary only)."""
        batches = sorted(
            self._batches.values(),
            key=lambda b: b.created_at,
            reverse=True,
        )[:limit]
        return [b.summary_dict() for b in batches]

    # ------------------------------------------------------------------
    # Event subscription
    # ------------------------------------------------------------------

    def subscribe(self, batch_id: str) -> asyncio.Queue:
        """Subscribe to events for a batch. Returns a queue to read events from."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        if batch_id not in self._event_queues:
            self._event_queues[batch_id] = []
        self._event_queues[batch_id].append(queue)
        return queue

    def unsubscribe(self, batch_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        if batch_id in self._event_queues:
            self._event_queues[batch_id] = [
                q for q in self._event_queues[batch_id] if q is not queue
            ]

    async def _emit(self, batch_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to all subscribers."""
        event = BatchEvent(batch_id=batch_id, event_type=event_type, data=data)
        queues = self._event_queues.get(batch_id, [])
        dead: List[asyncio.Queue] = []

        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(queue)

        for q in dead:
            self._event_queues.get(batch_id, []).remove(q) if q in self._event_queues.get(batch_id, []) else None

    # ------------------------------------------------------------------
    # Core processing logic
    # ------------------------------------------------------------------

    async def _process_batch(self, batch: BatchJob) -> None:
        """Process all files in a batch with concurrency control."""
        semaphore = asyncio.Semaphore(batch.max_concurrency)
        tasks = []

        for file_task in batch.files:
            if batch.cancelled:
                break
            if file_task.status != FileStatus.PENDING:
                continue

            tasks.append(
                asyncio.create_task(
                    self._process_file(batch, file_task, semaphore)
                )
            )

        # Wait for all tasks
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.CancelledError:
                pass

        # Determine final batch status
        if batch.cancelled:
            batch.status = BatchStatus.CANCELLED
        elif batch.failed_count > 0 and batch.completed_count > 0:
            batch.status = BatchStatus.PARTIAL
        elif batch.failed_count > 0 and batch.completed_count == 0:
            batch.status = BatchStatus.FAILED
        else:
            batch.status = BatchStatus.COMPLETED

        batch.completed_at = datetime.now(timezone.utc)

        await self._emit(batch.batch_id, "batch_completed", {
            "status": batch.status.value,
            "total": batch.total,
            "completed": batch.completed_count,
            "failed": batch.failed_count,
        })

        logger.info(
            "Batch %s finished: %s (completed=%d, failed=%d)",
            batch.batch_id, batch.status.value,
            batch.completed_count, batch.failed_count,
        )

    async def _process_file(
        self,
        batch: BatchJob,
        file_task: FileTask,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Process a single file within the batch."""
        async with semaphore:
            if batch.cancelled:
                file_task.status = FileStatus.CANCELLED
                return

            file_task.status = FileStatus.PROCESSING
            file_task.started_at = datetime.now(timezone.utc)

            await self._emit(batch.batch_id, "file_started", {
                "file_id": file_task.file_id,
                "filename": file_task.filename,
            })

            start_time = time.time()

            try:
                if self._file_processor is None:
                    raise RuntimeError("No file processor configured")

                result = await self._file_processor(
                    file_task.file_path,
                    batch.workflow_steps,
                )

                file_task.status = FileStatus.COMPLETED
                file_task.result = result
                file_task.duration_ms = int((time.time() - start_time) * 1000)
                file_task.completed_at = datetime.now(timezone.utc)

                await self._emit(batch.batch_id, "file_completed", {
                    "file_id": file_task.file_id,
                    "filename": file_task.filename,
                    "duration_ms": file_task.duration_ms,
                })

            except asyncio.CancelledError:
                file_task.status = FileStatus.CANCELLED
                raise

            except Exception as e:
                file_task.status = FileStatus.FAILED
                file_task.error = str(e)
                file_task.duration_ms = int((time.time() - start_time) * 1000)
                file_task.completed_at = datetime.now(timezone.utc)

                await self._emit(batch.batch_id, "file_failed", {
                    "file_id": file_task.file_id,
                    "filename": file_task.filename,
                    "error": str(e),
                    "duration_ms": file_task.duration_ms,
                })

                logger.warning(
                    "Batch %s: file '%s' failed: %s",
                    batch.batch_id, file_task.filename, e,
                )

    # ------------------------------------------------------------------
    # Utility: extract zip
    # ------------------------------------------------------------------

    def extract_zip(self, zip_path: str) -> List[str]:
        """
        Extract a zip file and return paths to extracted files.

        Only extracts supported document types.
        """
        supported_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".csv", ".html"}
        extracted = []

        extract_dir = os.path.join(
            self._upload_folder, f"batch_{uuid.uuid4().hex[:8]}"
        )
        os.makedirs(extract_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    # Skip hidden files and __MACOSX
                    if info.filename.startswith((".", "__")):
                        continue

                    ext = Path(info.filename).suffix.lower()
                    if ext not in supported_extensions:
                        continue

                    # Extract to flat directory (avoid nested paths)
                    safe_name = Path(info.filename).name
                    target_path = os.path.join(extract_dir, safe_name)

                    # Handle duplicate names
                    if os.path.exists(target_path):
                        base, ext_part = os.path.splitext(safe_name)
                        target_path = os.path.join(
                            extract_dir, f"{base}_{uuid.uuid4().hex[:4]}{ext_part}"
                        )

                    with zf.open(info) as src, open(target_path, "wb") as dst:
                        dst.write(src.read())

                    extracted.append(target_path)

        except zipfile.BadZipFile:
            raise ValueError("Invalid zip file")

        logger.info("Extracted %d files from zip to %s", len(extracted), extract_dir)
        return extracted

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_batch(self, batch_id: str) -> None:
        """Remove batch from memory and clean up subscriber queues."""
        self._batches.pop(batch_id, None)
        self._event_queues.pop(batch_id, None)
        self._tasks.pop(batch_id, None)

    def cleanup_old_batches(self, max_age_hours: int = 24) -> int:
        """Remove completed batches older than max_age_hours."""
        now = datetime.now(timezone.utc)
        to_remove = []

        for batch_id, batch in self._batches.items():
            if batch.status in (BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED, BatchStatus.PARTIAL):
                if batch.completed_at:
                    age = (now - batch.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(batch_id)

        for bid in to_remove:
            self.cleanup_batch(bid)

        return len(to_remove)


# =============================================================================
# Module-level singleton
# =============================================================================

batch_processor = BatchProcessor()
