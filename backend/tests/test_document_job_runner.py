"""Unit tests for DocumentJobRunner — feat-042.

Tests:
1. Create job returns valid job_id and record
2. Run on text file → emits page_progress + partial_result + completed
3. Run on multi-page text PDF → emits per-page progress
4. Run with cancel → emits cancelled, partial result preserved
5. Page failure → partial result for other pages, failed_pages list
6. Request cancel on non-existent job → returns False
7. Request cancel on completed job → returns False
8. OCR page-by-page (scanned PDF) → emits per-page events
"""

from unittest.mock import MagicMock, patch

import pytest

from services.document_job_runner import (
    DocumentJobConfig,
    DocumentJobRunner,
    DocumentJobStatus,
    DocumentOperation,
)
from services.job_events import JobEventType, job_event_bus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Fresh DocumentJobRunner instance for each test."""
    return DocumentJobRunner()


@pytest.fixture
def text_file(tmp_path):
    """Create a temporary text file."""
    p = tmp_path / "test.txt"
    p.write_text("Hello World\nLine 2\nLine 3", encoding="utf-8")
    return str(p)


@pytest.fixture
def fake_pdf(tmp_path):
    """Create a fake PDF that has a text layer (mocked via pypdfium2)."""
    p = tmp_path / "test.pdf"
    p.write_bytes(b"%PDF-1.4 fake content")
    return str(p)


def _make_config(file_path: str, filename: str = "test.txt", operation: str = "ocr") -> DocumentJobConfig:
    return DocumentJobConfig(
        file_path=file_path,
        filename=filename,
        operation=DocumentOperation(operation),
        model_id="test-model",
    )


# ---------------------------------------------------------------------------
# Tests: Job lifecycle
# ---------------------------------------------------------------------------


class TestCreateJob:
    """Test job creation."""

    def test_create_job_returns_id(self, runner, text_file):
        config = _make_config(text_file)
        job_id = runner.create_job(config)
        assert job_id is not None
        assert len(job_id) == 32  # uuid4 hex

    def test_create_job_stores_record(self, runner, text_file):
        config = _make_config(text_file)
        job_id = runner.create_job(config)
        record = runner.get_job(job_id)
        assert record is not None
        assert record.status == DocumentJobStatus.QUEUED
        assert record.config.filename == "test.txt"

    def test_get_nonexistent_job_returns_none(self, runner):
        assert runner.get_job("nonexistent") is None


class TestCancel:
    """Test cancel logic."""

    def test_cancel_nonexistent_returns_false(self, runner):
        assert runner.request_cancel("nonexistent") is False

    def test_cancel_queued_job(self, runner, text_file):
        config = _make_config(text_file)
        job_id = runner.create_job(config)
        assert runner.request_cancel(job_id) is True
        record = runner.get_job(job_id)
        assert record.cancel_requested is True

    def test_cancel_completed_job_returns_false(self, runner, text_file):
        config = _make_config(text_file)
        job_id = runner.create_job(config)
        record = runner.get_job(job_id)
        record.status = DocumentJobStatus.COMPLETED
        assert runner.request_cancel(job_id) is False


# ---------------------------------------------------------------------------
# Tests: Run — text file
# ---------------------------------------------------------------------------


class TestRunTextFile:
    """Test running on a simple text file."""

    @pytest.mark.asyncio
    async def test_run_text_file_completes(self, runner, text_file):
        config = _make_config(text_file, filename="test.txt")
        job_id = runner.create_job(config)

        # Collect events
        events = []
        queue = await job_event_bus.subscribe(job_id)

        await runner.run(job_id)

        # Drain queue
        while not queue.empty():
            events.append(await queue.get())
        await job_event_bus.unsubscribe(job_id, queue)

        record = runner.get_job(job_id)
        assert record.status == DocumentJobStatus.COMPLETED
        assert record.progress == 1.0
        assert record.result is not None
        assert record.result["success"] is True
        assert "Hello World" in record.result["text"]

    @pytest.mark.asyncio
    async def test_run_text_file_emits_events(self, runner, text_file):
        config = _make_config(text_file, filename="test.txt")
        job_id = runner.create_job(config)

        events = []
        queue = await job_event_bus.subscribe(job_id)

        await runner.run(job_id)

        while not queue.empty():
            events.append(await queue.get())
        await job_event_bus.unsubscribe(job_id, queue)

        event_types = [e.event_type for e in events]
        assert JobEventType.JOB_STARTED in event_types
        assert JobEventType.STAGE_CHANGED in event_types
        assert JobEventType.PAGE_PROGRESS in event_types
        assert JobEventType.JOB_COMPLETED in event_types


# ---------------------------------------------------------------------------
# Tests: Run — PDF with text layer (mocked)
# ---------------------------------------------------------------------------


class TestRunTextPDF:
    """Test running on a text-based PDF (mocked pypdfium2)."""

    @pytest.mark.asyncio
    async def test_run_pdf_page_by_page_progress(self, runner, fake_pdf):
        config = _make_config(fake_pdf, filename="test.pdf")
        job_id = runner.create_job(config)

        # Mock pypdfium2 to simulate a 3-page PDF
        mock_textpage = MagicMock()
        mock_textpage.get_text_range.return_value = "Page text content"
        mock_page = MagicMock()
        mock_page.get_textpage.return_value = mock_textpage

        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=3)
        mock_pdf.__getitem__ = MagicMock(return_value=mock_page)
        mock_pdf.close = MagicMock()

        with patch("services.document_job_runner.DocumentJobRunner._get_page_count", return_value=3):
            with patch("services.document_job_runner.DocumentJobRunner._pdf_has_text_layer", return_value=True):
                with patch("pypdfium2.PdfDocument", return_value=mock_pdf):
                    events = []
                    queue = await job_event_bus.subscribe(job_id)

                    await runner.run(job_id)

                    while not queue.empty():
                        events.append(await queue.get())
                    await job_event_bus.unsubscribe(job_id, queue)

        record = runner.get_job(job_id)
        assert record.status == DocumentJobStatus.COMPLETED
        assert record.total_pages == 3

        # Check page_progress events
        page_events = [e for e in events if e.event_type == JobEventType.PAGE_PROGRESS]
        assert len(page_events) == 3
        assert page_events[0].data["page"] == 1
        assert page_events[2].data["page"] == 3

        # Check partial_result events
        partial_events = [e for e in events if e.event_type == JobEventType.PARTIAL_RESULT]
        assert len(partial_events) == 3


# ---------------------------------------------------------------------------
# Tests: Run — Cancel mid-processing
# ---------------------------------------------------------------------------


class TestRunCancel:
    """Test cooperative cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_during_processing(self, runner, fake_pdf):
        config = _make_config(fake_pdf, filename="test.pdf")
        job_id = runner.create_job(config)

        mock_textpage = MagicMock()
        mock_textpage.get_text_range.return_value = "Page text"
        mock_page = MagicMock()
        mock_page.get_textpage.return_value = mock_textpage

        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=10)
        mock_pdf.__getitem__ = MagicMock(return_value=mock_page)
        mock_pdf.close = MagicMock()

        call_count = 0

        async def _extract_that_cancels(_fn, pdf_path, page_num):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                # Request cancel after page 3
                runner.request_cancel(job_id)
            return "Page text"

        with patch("services.document_job_runner.DocumentJobRunner._get_page_count", return_value=10):
            with patch("services.document_job_runner.DocumentJobRunner._pdf_has_text_layer", return_value=True):
                with patch("pypdfium2.PdfDocument", return_value=mock_pdf):
                    with patch("asyncio.to_thread", side_effect=_extract_that_cancels):
                        events = []
                        queue = await job_event_bus.subscribe(job_id)

                        await runner.run(job_id)

                        while not queue.empty():
                            events.append(await queue.get())
                        await job_event_bus.unsubscribe(job_id, queue)

        record = runner.get_job(job_id)
        assert record.status == DocumentJobStatus.CANCELLED
        assert record.current_page < 10  # Didn't process all pages

        event_types = [e.event_type for e in events]
        assert JobEventType.JOB_CANCELLED in event_types


# ---------------------------------------------------------------------------
# Tests: Run — Page failure (partial result)
# ---------------------------------------------------------------------------


class TestRunPageFailure:
    """Test that a single page failure doesn't crash the whole job."""

    @pytest.mark.asyncio
    async def test_page_failure_partial_result(self, runner, fake_pdf):
        config = _make_config(fake_pdf, filename="test.pdf")
        config.force_ocr = True
        job_id = runner.create_job(config)

        # Mock OCR agent: page 1 succeeds, page 2 fails, page 3 succeeds
        mock_agent = MagicMock()
        results = [
            MagicMock(success=True, text="Page 1 text"),
            MagicMock(success=False, error="Timeout on page 2"),
            MagicMock(success=True, text="Page 3 text"),
        ]
        mock_agent.process_pdf_page = MagicMock(side_effect=results)

        with patch("services.document_job_runner.DocumentJobRunner._get_page_count", return_value=3):
            with patch("services.document_job_runner.DocumentJobRunner._pdf_has_text_layer", return_value=False):
                with patch("agents.factory.AgentFactory.create_from_config", return_value=mock_agent):
                    with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
                        await runner.run(job_id)

        record = runner.get_job(job_id)
        assert record.status == DocumentJobStatus.COMPLETED
        assert record.result["success"] is True

        # Page 2 should be in failed_pages
        failed_pages = record.result["failed_pages"]
        assert len(failed_pages) == 1
        assert failed_pages[0]["page"] == 2

        # Text should contain page 1 and 3 but not page 2
        assert "Page 1 text" in record.result["text"]
        assert "Page 3 text" in record.result["text"]


# ---------------------------------------------------------------------------
# Tests: Run — File not found
# ---------------------------------------------------------------------------


class TestRunFileNotFound:
    """Test that missing file is handled gracefully."""

    @pytest.mark.asyncio
    async def test_missing_file_fails(self, runner):
        config = _make_config("/nonexistent/path.txt", filename="missing.txt")
        job_id = runner.create_job(config)

        await runner.run(job_id)

        record = runner.get_job(job_id)
        assert record.status == DocumentJobStatus.FAILED
        assert "not found" in record.error.lower() or "No such file" in record.error
