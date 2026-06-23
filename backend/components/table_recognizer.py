"""
Table Recognizer Component — Structured table extraction for Doc Intelligence pipeline.

Wraps the DeepDoc TableStructureRecognizer for use in Doc Journey workflows.
Handles: file loading, table region detection, cell grid extraction, and
multi-format output (JSON cells, CSV, markdown, HTML).

Can work standalone or in combination with LayoutRecognizer:
1. Standalone: detect tables in full page images
2. Combined: receive pre-cropped table regions from layout detection
"""

import csv
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TableCell:
    """A single cell in a detected table."""

    row: int
    col: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str = ""
    is_header: bool = False
    rowspan: int = 1
    colspan: int = 1

    def to_dict(self) -> dict:
        return {
            "row": self.row,
            "col": self.col,
            "bbox": [round(self.x0, 2), round(self.y0, 2), round(self.x1, 2), round(self.y1, 2)],
            "text": self.text,
            "is_header": self.is_header,
            "rowspan": self.rowspan,
            "colspan": self.colspan,
        }


@dataclass
class TableResult:
    """A single detected table with its structure."""

    table_index: int
    page_number: int
    num_rows: int
    num_cols: int
    cells: List[TableCell] = field(default_factory=list)
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1] of the whole table
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "table_index": self.table_index,
            "page_number": self.page_number,
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "cells": [c.to_dict() for c in self.cells],
            "bbox": self.bbox,
            "confidence": round(self.confidence, 4),
        }

    def to_csv(self) -> str:
        """Export table as CSV string."""
        if not self.cells:
            return ""

        # Build grid
        grid = [["" for _ in range(self.num_cols)] for _ in range(self.num_rows)]
        for cell in self.cells:
            if 0 <= cell.row < self.num_rows and 0 <= cell.col < self.num_cols:
                grid[cell.row][cell.col] = cell.text

        output = io.StringIO()
        writer = csv.writer(output)
        for row in grid:
            writer.writerow(row)
        return output.getvalue()

    def to_markdown(self) -> str:
        """Export table as markdown table."""
        if not self.cells:
            return ""

        # Build grid
        grid = [["" for _ in range(self.num_cols)] for _ in range(self.num_rows)]
        for cell in self.cells:
            if 0 <= cell.row < self.num_rows and 0 <= cell.col < self.num_cols:
                grid[cell.row][cell.col] = cell.text

        lines = []
        for i, row in enumerate(grid):
            line = "| " + " | ".join(cell or " " for cell in row) + " |"
            lines.append(line)
            # Add separator after header row
            if i == 0:
                sep = "| " + " | ".join("---" for _ in row) + " |"
                lines.append(sep)

        return "\n".join(lines)

    def to_html(self) -> str:
        """Export table as HTML."""
        if not self.cells:
            return "<table></table>"

        # Build grid
        grid = [["" for _ in range(self.num_cols)] for _ in range(self.num_rows)]
        header_rows = set()
        for cell in self.cells:
            if 0 <= cell.row < self.num_rows and 0 <= cell.col < self.num_cols:
                grid[cell.row][cell.col] = cell.text
                if cell.is_header:
                    header_rows.add(cell.row)

        html = "<table>\n"
        for i, row in enumerate(grid):
            html += "  <tr>\n"
            tag = "th" if i in header_rows else "td"
            for cell_text in row:
                html += f"    <{tag}>{cell_text}</{tag}>\n"
            html += "  </tr>\n"
        html += "</table>"
        return html


@dataclass
class TableRecognizeResult:
    """Result of table recognition operation."""

    success: bool
    tables: List[TableResult] = field(default_factory=list)
    page_count: int = 0
    error: Optional[str] = None
    error_type: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "tables": [t.to_dict() for t in self.tables],
            "table_count": len(self.tables),
            "page_count": self.page_count,
            "error": self.error,
        }


class TableRecognizeComponent:
    """
    High-level table recognition component for Doc Intelligence.

    Usage:
        component = TableRecognizeComponent()
        result = component.recognize("document.pdf")
        for table in result.tables:
            print(table.to_csv())
            print(table.to_markdown())

    Supports: PDF (multi-page), images (PNG, JPG, JPEG)

    Two modes:
    1. Full page: detects table regions first (via layout), then extracts structure
    2. Pre-cropped: directly processes cropped table images
    """

    def __init__(
        self,
        threshold: float = 0.3,
        scale_factor: int = 3,
        model_dir: Optional[str] = None,
        use_layout_detection: bool = True,
    ):
        """
        Initialize table recognizer component.

        Args:
            threshold: Confidence threshold for structure detections (0.0 - 1.0)
            scale_factor: PDF rendering zoom factor
            model_dir: Path to directory with ONNX models. If None, auto-download.
            use_layout_detection: Whether to use layout detection to find table regions first
        """
        self.threshold = threshold
        self.scale_factor = scale_factor
        self._tsr = None
        self._layout = None
        self._model_dir = model_dir
        self._use_layout_detection = use_layout_detection

    def _get_tsr(self):
        """Lazy-load the table structure recognizer."""
        if self._tsr is None:
            from deepdoc.model_manager import ensure_table_model, get_model_dir

            model_dir = self._model_dir or get_model_dir()
            if self._model_dir is None:
                ensure_table_model()

            from deepdoc.vision.table_structure_recognizer import TableStructureRecognizer
            self._tsr = TableStructureRecognizer(model_dir)
            logger.info("TableStructureRecognizer initialized from %s", model_dir)

        return self._tsr

    def _get_layout(self):
        """Lazy-load the layout recognizer (for table region detection)."""
        if self._layout is None:
            from deepdoc.model_manager import ensure_layout_model, get_model_dir

            model_dir = self._model_dir or get_model_dir()
            if self._model_dir is None:
                ensure_layout_model()

            from deepdoc.vision.layout_recognizer import LayoutRecognizer
            self._layout = LayoutRecognizer(model_dir)

        return self._layout

    def recognize(self, file_path: str) -> TableRecognizeResult:
        """
        Detect and extract table structure from a document file.

        Args:
            file_path: Path to image or PDF file

        Returns:
            TableRecognizeResult with detected tables and their cells
        """
        try:
            ext = Path(file_path).suffix.lower()

            if ext in [".png", ".jpg", ".jpeg"]:
                images = self._load_image(file_path)
            elif ext == ".pdf":
                images = self._load_pdf_pages(file_path)
            else:
                return TableRecognizeResult(
                    success=False,
                    error=f"Unsupported file type: {ext}",
                    error_type="validation_error",
                )

            if not images:
                return TableRecognizeResult(
                    success=False,
                    error="No images could be extracted from file",
                    error_type="processing_error",
                )

            tables = []
            table_idx = 0

            for page_num, page_img in enumerate(images):
                # Step 1: Find table regions (optional)
                table_regions = self._find_table_regions(page_img, page_num)

                if not table_regions:
                    # Try processing the full page as a table
                    table_regions = [{"image": page_img, "bbox": None, "score": 1.0}]

                # Step 2: Extract structure from each table region
                for region in table_regions:
                    region_img = region["image"]
                    tsr = self._get_tsr()

                    # Run TSR on the cropped region
                    structures = tsr.detect([region_img], thr=self.threshold)

                    if not structures or not structures[0]:
                        continue

                    structure = structures[0]
                    h, w = region_img.shape[:2]

                    # Extract cell grid from structure
                    cells_data = tsr.extract_cells(structure, w, h)

                    if not cells_data:
                        continue

                    # Build TableResult
                    max_row = max(c["row"] for c in cells_data) + 1
                    max_col = max(c["col"] for c in cells_data) + 1

                    cells = [
                        TableCell(
                            row=c["row"],
                            col=c["col"],
                            x0=c["x0"],
                            y0=c["y0"],
                            x1=c["x1"],
                            y1=c["y1"],
                            is_header=c.get("is_header", False),
                        )
                        for c in cells_data
                    ]

                    tables.append(TableResult(
                        table_index=table_idx,
                        page_number=page_num,
                        num_rows=max_row,
                        num_cols=max_col,
                        cells=cells,
                        bbox=region.get("bbox"),
                        confidence=region.get("score", 0.0),
                    ))
                    table_idx += 1

            return TableRecognizeResult(
                success=True,
                tables=tables,
                page_count=len(images),
            )

        except FileNotFoundError as e:
            return TableRecognizeResult(
                success=False,
                error=str(e),
                error_type="model_not_found",
            )
        except Exception as e:
            logger.exception("Table recognition failed: %s", e)
            return TableRecognizeResult(
                success=False,
                error=f"Table recognition failed: {str(e)}",
                error_type="processing_error",
            )

    def recognize_cropped(self, images: List[np.ndarray]) -> TableRecognizeResult:
        """
        Recognize table structure from pre-cropped table images.

        Use when you already have table regions (e.g., from layout detection).

        Args:
            images: List of cropped table images (BGR numpy arrays)

        Returns:
            TableRecognizeResult
        """
        try:
            tsr = self._get_tsr()
            tables = []

            for idx, img in enumerate(images):
                structures = tsr.detect([img], thr=self.threshold)
                if not structures or not structures[0]:
                    continue

                structure = structures[0]
                h, w = img.shape[:2]
                cells_data = tsr.extract_cells(structure, w, h)

                if not cells_data:
                    continue

                max_row = max(c["row"] for c in cells_data) + 1
                max_col = max(c["col"] for c in cells_data) + 1

                cells = [
                    TableCell(
                        row=c["row"],
                        col=c["col"],
                        x0=c["x0"],
                        y0=c["y0"],
                        x1=c["x1"],
                        y1=c["y1"],
                        is_header=c.get("is_header", False),
                    )
                    for c in cells_data
                ]

                tables.append(TableResult(
                    table_index=idx,
                    page_number=0,
                    num_rows=max_row,
                    num_cols=max_col,
                    cells=cells,
                    confidence=1.0,
                ))

            return TableRecognizeResult(
                success=True,
                tables=tables,
                page_count=len(images),
            )
        except Exception as e:
            return TableRecognizeResult(
                success=False,
                error=f"Table recognition failed: {str(e)}",
                error_type="processing_error",
            )

    def _find_table_regions(
        self, page_img: np.ndarray, page_num: int
    ) -> List[Dict[str, Any]]:
        """
        Find table regions in a page using layout detection.

        Returns list of cropped table images with their bounding boxes.
        """
        if not self._use_layout_detection:
            return []

        try:
            layout = self._get_layout()
            page_layouts = layout.detect(
                [page_img], thr=0.3, scale_factor=self.scale_factor
            )

            if not page_layouts or not page_layouts[0]:
                return []

            regions = []
            for det in page_layouts[0]:
                if det["type"] != "table":
                    continue

                # Crop the table region from the page image
                x0 = max(0, int(det["x0"]))
                y0 = max(0, int(det["top"]))
                x1 = min(page_img.shape[1], int(det["x1"]))
                y1 = min(page_img.shape[0], int(det["bottom"]))

                if x1 <= x0 or y1 <= y0:
                    continue

                cropped = page_img[y0:y1, x0:x1].copy()
                regions.append({
                    "image": cropped,
                    "bbox": [float(x0), float(y0), float(x1), float(y1)],
                    "score": det["score"],
                    "page_number": page_num,
                })

            return regions

        except Exception as e:
            logger.debug("Layout detection for table regions failed: %s", e)
            return []

    def _load_image(self, file_path: str) -> List[np.ndarray]:
        """Load a single image file."""
        img = cv2.imread(file_path)
        if img is None:
            raise ValueError(f"Cannot read image: {file_path}")
        return [img]

    def _load_pdf_pages(self, file_path: str) -> List[np.ndarray]:
        """Render PDF pages to images using pypdfium2."""
        try:
            import pypdfium2 as pdfium
        except ImportError:
            raise RuntimeError(
                "pypdfium2 is required for PDF processing. "
                "Install with: pip install pypdfium2"
            )

        pdf = pdfium.PdfDocument(file_path)
        images = []

        try:
            for page_idx in range(len(pdf)):
                page = pdf[page_idx]
                bitmap = page.render(scale=self.scale_factor)
                pil_image = bitmap.to_pil()
                img_array = np.array(pil_image)
                if img_array.ndim == 2:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
                else:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                images.append(img_bgr)
        finally:
            pdf.close()

        return images

    @staticmethod
    def convert_with_markitdown(file_path: str) -> Optional[str]:
        """
        Convert a document to Markdown using Microsoft's MarkItDown library.

        Best for: XLSX, DOCX, PPTX, HTML, CSV — preserves table structure natively.
        For scanned PDFs/images, use recognize() instead (ONNX-based detection).

        Args:
            file_path: Path to document file

        Returns:
            Markdown string with preserved table structure, or None if conversion fails.
        """
        try:
            from markitdown import MarkItDown

            md = MarkItDown()
            result = md.convert(file_path)
            return result.text_content
        except ImportError:
            logger.warning(
                "markitdown not installed. Install with: pip install markitdown"
            )
            return None
        except Exception as e:
            logger.debug("MarkItDown conversion failed for %s: %s", file_path, e)
            return None
