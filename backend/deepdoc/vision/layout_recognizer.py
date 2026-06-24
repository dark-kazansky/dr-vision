"""
Layout Recognizer — Document layout detection using YOLOv10.

Ported from infiniflow/ragflow deepdoc/vision/layout_recognizer.py
License: Apache License 2.0 (original code by InfiniFlow Authors)

Detects 10 layout components:
- Text, Title, Figure, Figure caption, Table, Table caption,
  Header, Footer, Reference, Equation
"""

import logging
from typing import Dict, List

import numpy as np

from .recognizer import Recognizer

logger = logging.getLogger(__name__)

# Layout labels for YOLOv10 model
LAYOUT_LABELS = [
    "title",
    "Text",
    "Reference",
    "Figure",
    "Figure caption",
    "Table",
    "Table caption",
    "Table caption",
    "Equation",
    "Figure caption",
]


class LayoutRecognizer(Recognizer):
    """
    Document layout recognizer using YOLOv10 architecture.

    Detects document regions and classifies them into layout types.
    Can operate standalone (raw detection) or combined with OCR results
    to tag text boxes with their layout context.
    """

    labels = LAYOUT_LABELS
    garbage_layouts = ["footer", "header", "reference"]

    def __init__(self, model_dir: str):
        """
        Initialize layout recognizer.

        Args:
            model_dir: Directory containing 'layout.onnx' model file
        """
        super().__init__(self.labels, "layout", model_dir)

    def detect(
        self,
        image_list: List[np.ndarray],
        thr: float = 0.2,
        batch_size: int = 16,
        scale_factor: int = 3,
    ) -> List[List[Dict]]:
        """
        Detect layout regions in images.

        Args:
            image_list: List of document page images (BGR numpy arrays)
            thr: Confidence threshold for detections
            batch_size: Batch size for inference
            scale_factor: Scale factor applied during image rendering
                         (used to convert bbox coordinates back to page space)

        Returns:
            List of layout detections per page. Each detection is a dict with:
            - type: layout label (text, title, figure, table, etc.)
            - score: confidence score
            - x0, x1, top, bottom: bounding box in page coordinates
            - page_number: page index
        """
        raw_layouts = super().__call__(image_list, thr, batch_size)

        page_layouts = []
        for pn, detections in enumerate(raw_layouts):
            page_lts = []
            for det in detections:
                score = float(det["score"])
                label_type = det["type"]

                # Filter low-confidence garbage layouts
                if score < 0.4 and label_type in self.garbage_layouts:
                    continue

                x0, y0, x1, y1 = det["bbox"]
                page_lts.append({
                    "type": label_type,
                    "score": score,
                    "x0": float(x0) / scale_factor,
                    "x1": float(x1) / scale_factor,
                    "top": float(y0) / scale_factor,
                    "bottom": float(y1) / scale_factor,
                    "page_number": pn,
                })

            # Sort by Y coordinate
            if page_lts:
                avg_h = np.mean([lt["bottom"] - lt["top"] for lt in page_lts])
                page_lts = self.sort_Y_firstly(page_lts, avg_h / 2 if avg_h > 0 else 0)

            page_layouts.append(page_lts)

        return page_layouts

    def detect_and_tag(
        self,
        image_list: List[np.ndarray],
        ocr_boxes: List[List[Dict]],
        thr: float = 0.2,
        batch_size: int = 16,
        scale_factor: int = 3,
        drop_garbage: bool = True,
    ) -> tuple:
        """
        Detect layouts and tag OCR boxes with layout type.

        This combines layout detection with OCR results to determine
        which layout region each text box belongs to.

        Args:
            image_list: List of page images (BGR numpy)
            ocr_boxes: Per-page OCR results. Each box should have:
                       x0, x1, top, bottom, text
            thr: Detection confidence threshold
            batch_size: Inference batch size
            scale_factor: Image scale factor
            drop_garbage: Whether to drop header/footer/reference text

        Returns:
            Tuple of (tagged_boxes, page_layouts):
            - tagged_boxes: OCR boxes with added 'layout_type' and 'layoutno' fields
            - page_layouts: Raw layout detections per page
        """
        assert len(image_list) == len(ocr_boxes), (
            f"image_list ({len(image_list)}) and ocr_boxes ({len(ocr_boxes)}) "
            f"must have same length"
        )

        page_layouts = self.detect(image_list, thr, batch_size, scale_factor)
        all_boxes = []

        for pn, lts in enumerate(page_layouts):
            bxs = list(ocr_boxes[pn])  # Copy to avoid mutating input
            lts = self.layouts_cleanup(bxs, lts)
            page_layouts[pn] = lts  # Update with cleaned layouts

            # Tag each OCR box with its layout type
            for lt_type in [
                "footer", "header", "reference", "figure caption",
                "table caption", "title", "table", "text", "figure", "equation",
            ]:
                lts_of_type = [lt for lt in lts if lt["type"] == lt_type]
                i = 0
                while i < len(bxs):
                    if bxs[i].get("layout_type"):
                        i += 1
                        continue

                    ii = self.find_overlapped_with_threshold(
                        bxs[i], lts_of_type, thr=0.4
                    )
                    if ii is None:
                        bxs[i]["layout_type"] = ""
                        i += 1
                        continue

                    lts_of_type[ii]["visited"] = True

                    # Optionally drop garbage (header/footer/reference)
                    if drop_garbage and lt_type in self.garbage_layouts:
                        bxs.pop(i)
                        continue

                    bxs[i]["layoutno"] = f"{lt_type}-{ii}"
                    bxs[i]["layout_type"] = (
                        lt_type if lt_type != "equation" else "figure"
                    )
                    i += 1

            all_boxes.extend(bxs)

        return all_boxes, page_layouts
