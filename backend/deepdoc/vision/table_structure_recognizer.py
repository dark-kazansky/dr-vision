"""
Table Structure Recognizer — Detect table rows, columns, headers, and spanning cells.

Ported from infiniflow/ragflow deepdoc/vision/table_structure_recognizer.py
License: Apache License 2.0 (original code by InfiniFlow Authors)

Detects 6 table structure components:
- table, table column, table row, table column header,
  table projected row header, table spanning cell

Content was rephrased for compliance with licensing restrictions.
Original source: https://github.com/infiniflow/ragflow/blob/main/deepdoc/vision/table_structure_recognizer.py
"""

import logging
from typing import Dict, List

import numpy as np

from .recognizer import Recognizer

logger = logging.getLogger(__name__)

# Table structure labels for the TSR ONNX model
TSR_LABELS = [
    "table",
    "table column",
    "table row",
    "table column header",
    "table projected row header",
    "table spanning cell",
]


class TableStructureRecognizer(Recognizer):
    """
    Table structure recognizer using ONNX model inference.

    Detects structural elements of tables: rows, columns, headers,
    and spanning cells. Aligns row/column boundaries for consistency.
    """

    labels = TSR_LABELS

    def __init__(self, model_dir: str):
        """
        Initialize table structure recognizer.

        Args:
            model_dir: Directory containing 'tsr.onnx' model file
        """
        super().__init__(self.labels, "tsr", model_dir)

    def detect(
        self,
        image_list: List[np.ndarray],
        thr: float = 0.2,
        batch_size: int = 16,
    ) -> List[List[Dict]]:
        """
        Detect table structure in images.

        Runs inference then aligns row/column boundaries for consistency.

        Args:
            image_list: List of table region images (BGR numpy arrays)
            thr: Confidence threshold for detections
            batch_size: Batch size for inference

        Returns:
            List of structure detections per image. Each detection has:
            - label: structure type (table row, table column, etc.)
            - score: confidence score
            - x0, x1, top, bottom: bounding box
        """
        raw_results = super().__call__(image_list, thr, batch_size)

        aligned_results = []
        for detections in raw_results:
            # Convert raw detections to standard format
            lts = [
                {
                    "label": d["type"],
                    "score": d["score"],
                    "x0": d["bbox"][0],
                    "x1": d["bbox"][2],
                    "top": d["bbox"][1],
                    "bottom": d["bbox"][3],
                }
                for d in detections
            ]

            if not lts:
                aligned_results.append([])
                continue

            # Align left/right for rows and headers
            lts = self._align_rows(lts)
            # Align top/bottom for columns
            lts = self._align_columns(lts)

            aligned_results.append(lts)

        return aligned_results

    def _align_rows(self, lts: List[Dict]) -> List[Dict]:
        """Align left/right edges of row-like elements."""
        row_labels = [b for b in lts if "row" in b["label"] or "header" in b["label"]]
        if not row_labels:
            return lts

        lefts = [b["x0"] for b in row_labels]
        rights = [b["x1"] for b in row_labels]

        left_edge = float(np.mean(lefts) if len(lefts) > 4 else np.min(lefts))
        right_edge = float(np.mean(rights) if len(rights) > 4 else np.max(rights))

        for b in lts:
            if "row" in b["label"] or "header" in b["label"]:
                if b["x0"] > left_edge:
                    b["x0"] = left_edge
                if b["x1"] < right_edge:
                    b["x1"] = right_edge

        return lts

    def _align_columns(self, lts: List[Dict]) -> List[Dict]:
        """Align top/bottom edges of column elements."""
        col_labels = [b for b in lts if b["label"] == "table column"]
        if not col_labels:
            return lts

        tops = [b["top"] for b in col_labels]
        bottoms = [b["bottom"] for b in col_labels]

        top_edge = float(np.median(tops) if len(tops) > 4 else np.min(tops))
        bottom_edge = float(np.median(bottoms) if len(bottoms) > 4 else np.max(bottoms))

        for b in lts:
            if b["label"] == "table column":
                if b["top"] > top_edge:
                    b["top"] = top_edge
                if b["bottom"] < bottom_edge:
                    b["bottom"] = bottom_edge

        return lts

    def extract_cells(
        self,
        structure: List[Dict],
        image_width: int,
        image_height: int,
    ) -> List[Dict]:
        """
        Extract cell grid from detected structure.

        Uses row/column intersections to determine cell boundaries.

        Args:
            structure: Detected structure elements from detect()
            image_width: Original image width
            image_height: Original image height

        Returns:
            List of cells with: row, col, x0, y0, x1, y1, is_header
        """
        rows = sorted(
            [s for s in structure if "row" in s["label"] or "header" in s["label"]],
            key=lambda x: x["top"],
        )
        cols = sorted(
            [s for s in structure if s["label"] == "table column"],
            key=lambda x: x["x0"],
        )

        if not rows or not cols:
            return []

        # Detect header rows
        header_rows = {
            i for i, r in enumerate(rows)
            if "header" in r["label"]
        }

        cells = []
        for ri, row in enumerate(rows):
            for ci, col in enumerate(cols):
                # Cell = intersection of row and column
                x0 = max(row["x0"], col["x0"])
                y0 = max(row["top"], col["top"])
                x1 = min(row["x1"], col["x1"])
                y1 = min(row["bottom"], col["bottom"])

                # Only valid if intersection has positive area
                if x1 > x0 and y1 > y0:
                    cells.append({
                        "row": ri,
                        "col": ci,
                        "x0": round(x0, 2),
                        "y0": round(y0, 2),
                        "x1": round(x1, 2),
                        "y1": round(y1, 2),
                        "is_header": ri in header_rows,
                    })

        return cells
