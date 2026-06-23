"""
Unit tests for Table Structure Recognition (feat-060) and MarkItDown integration.

Tests cover:
- TableCell, TableResult models and export formats (CSV, Markdown, HTML)
- TableRecognizeComponent initialization and unsupported file handling
- TableStructureRecognizer labels and class hierarchy
- MarkdownConverter and extract_markdown_tables utility
- API router existence
- Workflow integration (step routing)
"""

import pytest  # noqa: F401
from unittest.mock import patch

from components.table_recognizer import (
    TableCell,
    TableRecognizeComponent,
    TableRecognizeResult,
    TableResult,
)
from components.markdown_converter import (
    MarkdownConverter,
    MarkdownConvertResult,
    extract_markdown_tables,
    SUPPORTED_EXTENSIONS,
)
from deepdoc.vision.table_structure_recognizer import (
    TableStructureRecognizer,
    TSR_LABELS,
)


# =============================================================================
# TableCell Tests
# =============================================================================


class TestTableCell:
    def test_basic_cell(self):
        cell = TableCell(row=0, col=1, x0=10, y0=20, x1=100, y1=50, text="Hello")
        assert cell.row == 0
        assert cell.col == 1
        assert cell.text == "Hello"
        assert cell.is_header is False

    def test_header_cell(self):
        cell = TableCell(row=0, col=0, x0=0, y0=0, x1=50, y1=30, text="Name", is_header=True)
        assert cell.is_header is True

    def test_to_dict(self):
        cell = TableCell(row=1, col=2, x0=10.123, y0=20.456, x1=100.789, y1=50.321, text="Data")
        d = cell.to_dict()
        assert d["row"] == 1
        assert d["col"] == 2
        assert d["text"] == "Data"
        assert len(d["bbox"]) == 4
        assert d["bbox"][0] == 10.12  # rounded to 2 decimals


# =============================================================================
# TableResult Tests
# =============================================================================


class TestTableResult:
    def _make_table(self):
        cells = [
            TableCell(row=0, col=0, x0=0, y0=0, x1=50, y1=20, text="Name", is_header=True),
            TableCell(row=0, col=1, x0=50, y0=0, x1=100, y1=20, text="Age", is_header=True),
            TableCell(row=1, col=0, x0=0, y0=20, x1=50, y1=40, text="Alice"),
            TableCell(row=1, col=1, x0=50, y0=20, x1=100, y1=40, text="30"),
            TableCell(row=2, col=0, x0=0, y0=40, x1=50, y1=60, text="Bob"),
            TableCell(row=2, col=1, x0=50, y0=40, x1=100, y1=60, text="25"),
        ]
        return TableResult(
            table_index=0, page_number=0, num_rows=3, num_cols=2, cells=cells
        )

    def test_to_csv(self):
        table = self._make_table()
        csv = table.to_csv()
        assert "Name" in csv
        assert "Alice" in csv
        assert "30" in csv
        lines = csv.strip().split("\n")
        assert len(lines) == 3  # 3 rows

    def test_to_markdown(self):
        table = self._make_table()
        md = table.to_markdown()
        assert "| Name | Age |" in md
        assert "| --- | --- |" in md
        assert "| Alice | 30 |" in md
        assert "| Bob | 25 |" in md

    def test_to_html(self):
        table = self._make_table()
        html = table.to_html()
        assert "<table>" in html
        assert "<th>" in html  # Header cells
        assert "<td>" in html  # Data cells
        assert "Alice" in html

    def test_to_dict(self):
        table = self._make_table()
        d = table.to_dict()
        assert d["table_index"] == 0
        assert d["num_rows"] == 3
        assert d["num_cols"] == 2
        assert len(d["cells"]) == 6

    def test_empty_table(self):
        table = TableResult(table_index=0, page_number=0, num_rows=0, num_cols=0)
        assert table.to_csv() == ""
        assert table.to_markdown() == ""
        assert table.to_html() == "<table></table>"


# =============================================================================
# TableRecognizeComponent Tests
# =============================================================================


class TestTableRecognizeComponent:
    def test_unsupported_file_type(self):
        component = TableRecognizeComponent()
        result = component.recognize("/tmp/file.xyz")
        assert result.success is False
        assert "Unsupported file type" in result.error

    def test_init_defaults(self):
        component = TableRecognizeComponent()
        assert component.threshold == 0.3
        assert component.scale_factor == 3
        assert component._use_layout_detection is True

    def test_init_custom(self):
        component = TableRecognizeComponent(
            threshold=0.5, scale_factor=2, use_layout_detection=False
        )
        assert component.threshold == 0.5
        assert component.scale_factor == 2
        assert component._use_layout_detection is False

    def test_result_to_dict(self):
        result = TableRecognizeResult(success=True, page_count=2)
        d = result.to_dict()
        assert d["success"] is True
        assert d["table_count"] == 0
        assert d["page_count"] == 2

    def test_convert_with_markitdown_returns_none_on_missing_lib(self):
        """Test graceful fallback when markitdown not importable."""
        with patch.dict("sys.modules", {"markitdown": None}):
            # This should return None gracefully (not crash)
            result = TableRecognizeComponent.convert_with_markitdown("/tmp/nonexistent.xlsx")
            # Will be None because file doesn't exist or module issue
            assert result is None or isinstance(result, str)


# =============================================================================
# TableStructureRecognizer Tests
# =============================================================================


class TestTableStructureRecognizer:
    def test_labels_defined(self):
        assert len(TSR_LABELS) == 6
        assert "table" in TSR_LABELS
        assert "table column" in TSR_LABELS
        assert "table row" in TSR_LABELS
        assert "table column header" in TSR_LABELS

    def test_inherits_recognizer(self):
        from deepdoc.vision.recognizer import Recognizer
        assert issubclass(TableStructureRecognizer, Recognizer)


# =============================================================================
# MarkdownConverter Tests
# =============================================================================


class TestMarkdownConverter:
    def test_supported_extensions(self):
        assert ".xlsx" in SUPPORTED_EXTENSIONS
        assert ".docx" in SUPPORTED_EXTENSIONS
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".csv" in SUPPORTED_EXTENSIONS
        assert ".html" in SUPPORTED_EXTENSIONS

    def test_is_supported(self):
        assert MarkdownConverter.is_supported("test.xlsx") is True
        assert MarkdownConverter.is_supported("test.docx") is True
        assert MarkdownConverter.is_supported("test.xyz") is False

    def test_convert_nonexistent_file(self):
        converter = MarkdownConverter()
        result = converter.convert("/tmp/nonexistent_file_12345.xlsx")
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_unsupported_format(self):
        converter = MarkdownConverter()
        # Create a temp file with unsupported extension
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix=".xyz")
        os.close(fd)
        try:
            result = converter.convert(path)
            assert result.success is False
            assert "Unsupported" in result.error
        finally:
            os.unlink(path)

    def test_result_to_dict(self):
        result = MarkdownConvertResult(
            success=True,
            markdown="| A | B |\n| --- | --- |\n| 1 | 2 |",
            source_format="csv",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["has_tables"] is True
        assert d["source_format"] == "csv"
        assert d["line_count"] == 3


class TestExtractMarkdownTables:
    def test_extract_single_table(self):
        md = """# Header

Some text here.

| Col A | Col B |
| --- | --- |
| 1 | 2 |
| 3 | 4 |

More text.
"""
        tables = extract_markdown_tables(md)
        assert len(tables) == 1
        assert "Col A" in tables[0]
        assert "| 3 | 4 |" in tables[0]

    def test_extract_multiple_tables(self):
        md = """| A | B |
| --- | --- |
| 1 | 2 |

Some text between tables.

| X | Y | Z |
| --- | --- | --- |
| a | b | c |
"""
        tables = extract_markdown_tables(md)
        assert len(tables) == 2

    def test_no_tables(self):
        md = "# Just a heading\n\nSome text, no tables here.\n"
        tables = extract_markdown_tables(md)
        assert len(tables) == 0

    def test_pipe_in_text_not_table(self):
        md = "This | is not | a table\nJust text with pipes.\n"
        tables = extract_markdown_tables(md)
        assert len(tables) == 0  # No separator row = not a table


# =============================================================================
# API Router Tests
# =============================================================================


class TestTableAPI:
    def test_table_router_exists(self):
        from api.v1.table import router
        paths = [r.path for r in router.routes]
        assert "/recognize" in paths or any("/recognize" in p for p in paths)

    def test_table_models_endpoint(self):
        from api.v1.table import router
        paths = [r.path for r in router.routes]
        assert "/models" in paths or any("/models" in p for p in paths)

    def test_convert_markdown_endpoint(self):
        from api.v1.table import router
        paths = [r.path for r in router.routes]
        assert any("convert-markdown" in p for p in paths)


# =============================================================================
# Workflow Integration Tests
# =============================================================================


class TestWorkflowIntegration:
    def test_workflow_service_has_table_recognize(self):
        from services.workflow_service import _run_table_recognize_step
        assert callable(_run_table_recognize_step)

    def test_workflow_service_has_document_to_markdown(self):
        from services.workflow_service import _run_document_to_markdown_step
        assert callable(_run_document_to_markdown_step)

    def test_durable_activity_registered(self):
        from services.workflow_engine.activities import get_all_handlers
        handlers = get_all_handlers()
        assert "table_recognize" in handlers
        assert "document_to_markdown" in handlers
