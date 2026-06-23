"""
Unit tests for Batch Processing (feat-062).

Tests: BatchProcessor service, models, zip extraction, API router.
"""

import asyncio
import os
import tempfile
import zipfile

import pytest

from services.batch_processor import (
    BatchEvent,
    BatchJob,
    BatchProcessor,
    BatchStatus,
    FileStatus,
    FileTask,
)


class TestFileTask:
    def test_defaults(self):
        task = FileTask(file_id="f1", filename="test.pdf", file_path="/tmp/test.pdf")
        assert task.status == FileStatus.PENDING
        assert task.result is None
        assert task.error is None

    def test_to_dict(self):
        task = FileTask(file_id="f1", filename="doc.pdf", file_path="/x", status=FileStatus.COMPLETED)
        d = task.to_dict()
        assert d["file_id"] == "f1"
        assert d["status"] == "completed"
        assert d["filename"] == "doc.pdf"


class TestBatchJob:
    def test_counts(self):
        batch = BatchJob(
            batch_id="b1",
            files=[
                FileTask(file_id="1", filename="a.pdf", file_path="/a", status=FileStatus.COMPLETED),
                FileTask(file_id="2", filename="b.pdf", file_path="/b", status=FileStatus.FAILED),
                FileTask(file_id="3", filename="c.pdf", file_path="/c", status=FileStatus.PENDING),
            ],
        )
        assert batch.total == 3
        assert batch.completed_count == 1
        assert batch.failed_count == 1
        assert batch.pending_count == 1

    def test_progress(self):
        batch = BatchJob(
            batch_id="b1",
            files=[
                FileTask(file_id="1", filename="a.pdf", file_path="/a", status=FileStatus.COMPLETED),
                FileTask(file_id="2", filename="b.pdf", file_path="/b", status=FileStatus.COMPLETED),
                FileTask(file_id="3", filename="c.pdf", file_path="/c", status=FileStatus.PENDING),
                FileTask(file_id="4", filename="d.pdf", file_path="/d", status=FileStatus.PENDING),
            ],
        )
        assert batch.progress == 0.5

    def test_empty_batch_progress(self):
        batch = BatchJob(batch_id="b1")
        assert batch.progress == 0.0

    def test_to_dict(self):
        batch = BatchJob(batch_id="test123")
        d = batch.to_dict()
        assert d["batch_id"] == "test123"
        assert d["status"] == "pending"
        assert "files" in d

    def test_summary_dict(self):
        batch = BatchJob(batch_id="test123")
        d = batch.summary_dict()
        assert "files" not in d
        assert d["batch_id"] == "test123"


class TestBatchProcessor:
    def test_create_batch(self):
        processor = BatchProcessor()
        batch_id = processor.create_batch(
            file_paths=["/tmp/a.pdf", "/tmp/b.pdf"],
            workflow_steps=[{"type": "parse"}],
            max_concurrency=2,
        )
        assert batch_id is not None
        batch = processor.get_batch(batch_id)
        assert batch is not None
        assert batch.total == 2
        assert batch.max_concurrency == 2
        assert batch.status == BatchStatus.PENDING

    def test_list_batches(self):
        processor = BatchProcessor()
        processor.create_batch(["/a"], [{"type": "parse"}])
        processor.create_batch(["/b", "/c"], [{"type": "parse"}])
        batches = processor.list_batches()
        assert len(batches) == 2

    def test_get_nonexistent(self):
        processor = BatchProcessor()
        assert processor.get_batch("nonexistent") is None

    def test_cleanup_batch(self):
        processor = BatchProcessor()
        bid = processor.create_batch(["/a"], [{"type": "parse"}])
        processor.cleanup_batch(bid)
        assert processor.get_batch(bid) is None

    @pytest.mark.asyncio
    async def test_start_batch(self):
        results = []

        async def mock_processor(file_path, steps):
            await asyncio.sleep(0.01)
            results.append(file_path)
            return {"text": f"processed {file_path}"}

        processor = BatchProcessor(file_processor=mock_processor)
        bid = processor.create_batch(["/a.pdf", "/b.pdf"], [{"type": "parse"}])
        success = await processor.start_batch(bid)
        assert success is True

        # Wait for processing
        await asyncio.sleep(0.2)

        batch = processor.get_batch(bid)
        assert batch is not None
        assert batch.completed_count == 2
        assert batch.status == BatchStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_cancel_batch(self):
        async def slow_processor(file_path, steps):
            await asyncio.sleep(10)  # Simulate slow processing
            return {}

        processor = BatchProcessor(file_processor=slow_processor)
        bid = processor.create_batch(
            [f"/file{i}.pdf" for i in range(10)],
            [{"type": "parse"}],
            max_concurrency=1,
        )
        await processor.start_batch(bid)
        await asyncio.sleep(0.05)

        success = await processor.cancel_batch(bid)
        assert success is True

        batch = processor.get_batch(bid)
        assert batch is not None
        assert batch.status == BatchStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_file_failure(self):
        async def failing_processor(file_path, steps):
            if "bad" in file_path:
                raise RuntimeError("Processing failed")
            return {"ok": True}

        processor = BatchProcessor(file_processor=failing_processor)
        bid = processor.create_batch(
            ["/good.pdf", "/bad.pdf", "/good2.pdf"],
            [{"type": "parse"}],
        )
        await processor.start_batch(bid)
        await asyncio.sleep(0.2)

        batch = processor.get_batch(bid)
        assert batch is not None
        assert batch.completed_count == 2
        assert batch.failed_count == 1
        assert batch.status == BatchStatus.PARTIAL

    @pytest.mark.asyncio
    async def test_subscribe_events(self):
        events = []

        async def mock_processor(file_path, steps):
            await asyncio.sleep(0.01)
            return {"done": True}

        processor = BatchProcessor(file_processor=mock_processor)
        bid = processor.create_batch(["/a.pdf"], [{"type": "parse"}])

        queue = processor.subscribe(bid)
        await processor.start_batch(bid)
        await asyncio.sleep(0.2)

        while not queue.empty():
            event = queue.get_nowait()
            events.append(event.event_type)

        assert "batch_started" in events
        assert "file_started" in events
        assert "file_completed" in events
        assert "batch_completed" in events


class TestBatchZipExtract:
    def test_extract_zip(self):
        processor = BatchProcessor(upload_folder=tempfile.gettempdir())

        # Create a test zip
        zip_path = os.path.join(tempfile.gettempdir(), "test_batch.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("doc1.pdf", b"fake pdf content")
            zf.writestr("doc2.png", b"fake image content")
            zf.writestr("readme.txt", b"not a supported file")
            zf.writestr("__MACOSX/._hidden", b"mac garbage")

        try:
            extracted = processor.extract_zip(zip_path)
            # Should only extract pdf and png (not txt, not __MACOSX)
            assert len(extracted) == 2
            filenames = [os.path.basename(f) for f in extracted]
            assert "doc1.pdf" in filenames
            assert "doc2.png" in filenames
        finally:
            os.unlink(zip_path)
            for f in extracted:
                if os.path.exists(f):
                    os.unlink(f)

    def test_invalid_zip(self):
        processor = BatchProcessor(upload_folder=tempfile.gettempdir())

        # Create a non-zip file
        bad_path = os.path.join(tempfile.gettempdir(), "not_a_zip.zip")
        with open(bad_path, "w") as f:
            f.write("this is not a zip")

        try:
            with pytest.raises(ValueError, match="Invalid zip"):
                processor.extract_zip(bad_path)
        finally:
            os.unlink(bad_path)


class TestBatchEvent:
    def test_to_sse_dict(self):
        event = BatchEvent(
            batch_id="b1",
            event_type="file_completed",
            data={"file_id": "f1", "filename": "test.pdf"},
        )
        d = event.to_sse_dict()
        assert d["batch_id"] == "b1"
        assert d["event"] == "file_completed"
        assert d["file_id"] == "f1"


class TestBatchAPIRouter:
    def test_router_exists(self):
        from api.v1.batch import router
        assert router is not None
        assert len(router.routes) >= 5  # process, list, get, stream, cancel, results
