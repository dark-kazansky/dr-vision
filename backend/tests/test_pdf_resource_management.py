"""Tests for PDF resource management in parser (Task 7.5).

Validates: Requirement 17.1
- PdfDocument is closed after successful processing
- PdfDocument is closed even when an exception occurs during processing
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from functions.parser import Parser, ParseResult


def _make_mock_pdf(page_count=1, page_text="Sample text"):
    """Create a mock PdfDocument with configurable pages and text."""
    mock_pdf = MagicMock()
    mock_pdf.__len__ = MagicMock(return_value=page_count)

    mock_textpage = MagicMock()
    mock_textpage.get_text_range.return_value = page_text

    mock_page = MagicMock()
    mock_page.get_textpage.return_value = mock_textpage

    mock_pdf.__getitem__ = MagicMock(return_value=mock_page)
    return mock_pdf


@pytest.fixture(autouse=True)
def mock_pypdfium2():
    """Inject a mock pypdfium2 module so the local import inside _parse_pdf resolves."""
    mock_module = MagicMock()
    with patch.dict(sys.modules, {"pypdfium2": mock_module}):
        yield mock_module


class TestPdfResourceManagement:
    """Requirement 17.1: PdfDocument is always closed after processing."""

    def test_close_called_on_successful_text_extraction(self, mock_pypdfium2):
        mock_pdf = _make_mock_pdf(page_count=2, page_text="Hello world")
        mock_pypdfium2.PdfDocument.return_value = mock_pdf

        parser = Parser()
        result = parser._parse_pdf("fake.pdf", force_ocr=False)

        assert result.success is True
        mock_pdf.close.assert_called_once()

    def test_close_called_on_zero_pages(self, mock_pypdfium2):
        mock_pdf = _make_mock_pdf(page_count=0)
        mock_pypdfium2.PdfDocument.return_value = mock_pdf

        parser = Parser()
        result = parser._parse_pdf("fake.pdf", force_ocr=False)

        assert result.success is False
        assert "no pages" in result.error.lower()
        mock_pdf.close.assert_called_once()

    def test_close_called_when_page_access_raises(self, mock_pypdfium2):
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=3)
        mock_pdf.__getitem__ = MagicMock(side_effect=RuntimeError("corrupt page"))
        mock_pypdfium2.PdfDocument.return_value = mock_pdf

        parser = Parser()
        result = parser._parse_pdf("fake.pdf", force_ocr=False)

        assert result.success is False
        assert result.error_type == "processing_error"
        mock_pdf.close.assert_called_once()

    def test_close_called_when_ocr_agent_fails(self, mock_pypdfium2):
        """Close is called even when OCR path raises an exception."""
        mock_pdf = _make_mock_pdf(page_count=1, page_text="")
        mock_pypdfium2.PdfDocument.return_value = mock_pdf

        mock_ocr = MagicMock()
        mock_ocr.process_pdf_all_pages.side_effect = RuntimeError("OCR crashed")

        parser = Parser(ocr_agent=mock_ocr)
        result = parser._parse_pdf("fake.pdf", force_ocr=True)

        assert result.success is False
        mock_pdf.close.assert_called_once()
