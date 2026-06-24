"""
Markdown Converter Component — Convert any document to LLM-ready Markdown.

Uses Microsoft's MarkItDown library (https://github.com/microsoft/markitdown)
to convert documents while preserving structure: headings, tables, lists, links.

Supported formats: PDF, DOCX, PPTX, XLSX, HTML, CSV, images, and more.
Particularly strong at preserving table structure in native document formats.

Usage:
    from components.markdown_converter import MarkdownConverter

    converter = MarkdownConverter()
    result = converter.convert("document.xlsx")
    print(result.markdown)  # Tables preserved as markdown tables
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# File extensions supported by markitdown
SUPPORTED_EXTENSIONS = {
    # Office documents
    ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
    # PDF
    ".pdf",
    # Web
    ".html", ".htm",
    # Data
    ".csv", ".tsv", ".json", ".xml",
    # Text
    ".txt", ".md", ".rst",
    # Images (OCR via markitdown plugins)
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff",
    # Archives
    ".zip",
}


@dataclass
class MarkdownConvertResult:
    """Result of markdown conversion."""

    success: bool
    markdown: str = ""
    source_format: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "markdown": self.markdown,
            "source_format": self.source_format,
            "char_count": len(self.markdown),
            "line_count": self.markdown.count("\n") + 1 if self.markdown else 0,
            "has_tables": "|" in self.markdown and "---" in self.markdown,
            "error": self.error,
        }


class MarkdownConverter:
    """
    Document-to-Markdown converter using Microsoft MarkItDown.

    Key strengths:
    - Preserves table structure as markdown tables (|col1|col2|)
    - Maintains heading hierarchy
    - Preserves lists, links, code blocks
    - Single function call API
    - Supports 20+ file formats

    Best for:
    - XLSX/CSV → markdown tables (native, no OCR needed)
    - DOCX/PPTX → structured markdown
    - HTML → clean markdown
    - PDF (text-based) → markdown with tables

    For scanned documents/images: use OCR pipeline instead (or combine both).
    """

    def __init__(self, enable_llm_descriptions: bool = False):
        """
        Initialize markdown converter.

        Args:
            enable_llm_descriptions: Whether to use LLM for image descriptions
                                    (requires additional config, default False)
        """
        self._md = None
        self._enable_llm = enable_llm_descriptions

    def _get_converter(self):
        """Lazy-load the MarkItDown instance."""
        if self._md is None:
            try:
                from markitdown import MarkItDown
                self._md = MarkItDown()
                logger.debug("MarkItDown initialized")
            except ImportError:
                raise RuntimeError(
                    "markitdown is required. Install with: pip install markitdown"
                )
        return self._md

    def convert(self, file_path: str) -> MarkdownConvertResult:
        """
        Convert a document file to Markdown.

        Args:
            file_path: Path to the document to convert

        Returns:
            MarkdownConvertResult with the markdown content
        """
        path = Path(file_path)

        if not path.exists():
            return MarkdownConvertResult(
                success=False,
                error=f"File not found: {file_path}",
            )

        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return MarkdownConvertResult(
                success=False,
                error=f"Unsupported format: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )

        try:
            md = self._get_converter()
            result = md.convert(file_path)

            markdown_text = result.text_content or ""

            return MarkdownConvertResult(
                success=True,
                markdown=markdown_text,
                source_format=ext.lstrip("."),
            )

        except Exception as e:
            logger.warning("MarkItDown conversion failed for %s: %s", file_path, e)
            return MarkdownConvertResult(
                success=False,
                error=f"Conversion failed: {str(e)}",
            )

    def convert_to_tables_only(self, file_path: str) -> list:
        """
        Convert a document and extract only the table portions.

        Useful for spreadsheets and documents where you only need table data.

        Args:
            file_path: Path to the document

        Returns:
            List of markdown table strings found in the converted output
        """
        result = self.convert(file_path)
        if not result.success or not result.markdown:
            return []

        return extract_markdown_tables(result.markdown)

    @staticmethod
    def is_supported(file_path: str) -> bool:
        """Check if a file format is supported for conversion."""
        ext = Path(file_path).suffix.lower()
        return ext in SUPPORTED_EXTENSIONS


def extract_markdown_tables(markdown_text: str) -> list:
    """
    Extract individual markdown tables from a markdown document.

    A markdown table is identified by lines containing | characters
    with a separator row (containing ---).

    Args:
        markdown_text: Full markdown text

    Returns:
        List of table strings (each is a complete markdown table)
    """
    lines = markdown_text.split("\n")
    tables = []
    current_table: list = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        # Detect table row (contains | and is not empty)
        is_table_row = "|" in stripped and stripped.startswith("|")

        if is_table_row:
            current_table.append(line)
            in_table = True
        else:
            if in_table and current_table:
                # Verify it's a real table (has separator row)
                table_text = "\n".join(current_table)
                if "---" in table_text:
                    tables.append(table_text)
                current_table = []
            in_table = False

    # Don't forget last table
    if current_table:
        table_text = "\n".join(current_table)
        if "---" in table_text:
            tables.append(table_text)

    return tables
