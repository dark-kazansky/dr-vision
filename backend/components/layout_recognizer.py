"""
Layout Recognizer Component — Document layout detection for Doc Intelligence pipeline.

Wraps the DeepDoc LayoutRecognizer for use in Doc Journey workflows.
Handles: file loading, page rendering, inference, and result formatting.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LayoutRegion:
    """A detected layout region on a document page."""

    type: str  # text, title, figure, table, equation, etc.
    score: float
    x0: float
    y0: float
    x1: float
    y1: float
    page_number: int

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "score": round(self.score, 4),
            "bbox": [
                round(self.x0, 2),
                round(self.y0, 2),
                round(self.x1, 2),
                round(self.y1, 2),
            ],
            "page_number": self.page_number,
        }


@dataclass
class LayoutRecognizeResult:
    """Result of layout recognition operation."""

    success: bool
    regions: List[LayoutRegion] = field(default_factory=list)
    page_count: int = 0
    error: Optional[str] = None
    error_type: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "regions": [r.to_dict() for r in self.regions],
            "page_count": self.page_count,
            "error": self.error,
            "summary": self._summary() if self.success else None,
        }

    def _summary(self) -> dict:
        """Summarize detected regions by type."""
        counts: dict = {}
        for r in self.regions:
            counts[r.type] = counts.get(r.type, 0) + 1
        return counts


class LayoutRecognizeComponent:
    """
    High-level layout recognition component for Doc Intelligence.

    Usage:
        component = LayoutRecognizeComponent()
        result = component.recognize("document.pdf")

    Supports: PDF (multi-page), images (PNG, JPG, JPEG)
    """

    def __init__(
        self,
        threshold: float = 0.2,
        scale_factor: int = 3,
        model_dir: Optional[str] = None,
    ):
        """
        Initialize layout recognizer component.

        Args:
            threshold: Confidence threshold for detections (0.0 - 1.0)
            scale_factor: PDF rendering zoom factor (higher = better quality but slower)
            model_dir: Path to directory with ONNX models. If None, auto-download.
        """
        self.threshold = threshold
        self.scale_factor = scale_factor
        self._recognizer = None
        self._model_dir = model_dir

    def _get_recognizer(self):
        """Lazy-load the recognizer (downloads model if needed)."""
        if self._recognizer is None:
            from deepdoc.model_manager import ensure_layout_model, get_model_dir

            model_dir = self._model_dir or get_model_dir()

            # Ensure model is available
            if self._model_dir is None:
                ensure_layout_model()

            from deepdoc.vision.layout_recognizer import LayoutRecognizer

            self._recognizer = LayoutRecognizer(model_dir)
            logger.info("LayoutRecognizer initialized from %s", model_dir)

        return self._recognizer

    def recognize(self, file_path: str) -> LayoutRecognizeResult:
        """
        Detect layout regions in a document file.

        Args:
            file_path: Path to image or PDF file

        Returns:
            LayoutRecognizeResult with detected regions
        """
        try:
            ext = Path(file_path).suffix.lower()

            if ext in [".png", ".jpg", ".jpeg"]:
                images = self._load_image(file_path)
            elif ext == ".pdf":
                images = self._load_pdf_pages(file_path)
            else:
                return LayoutRecognizeResult(
                    success=False,
                    error=f"Unsupported file type: {ext}",
                    error_type="validation_error",
                )

            if not images:
                return LayoutRecognizeResult(
                    success=False,
                    error="No images could be extracted from file",
                    error_type="processing_error",
                )

            recognizer = self._get_recognizer()
            page_layouts = recognizer.detect(
                images,
                thr=self.threshold,
                scale_factor=self.scale_factor,
            )

            # Convert to LayoutRegion objects
            regions = []
            for page_detections in page_layouts:
                for det in page_detections:
                    regions.append(LayoutRegion(
                        type=det["type"],
                        score=det["score"],
                        x0=det["x0"],
                        y0=det["top"],
                        x1=det["x1"],
                        y1=det["bottom"],
                        page_number=det["page_number"],
                    ))

            return LayoutRecognizeResult(
                success=True,
                regions=regions,
                page_count=len(images),
            )

        except FileNotFoundError as e:
            return LayoutRecognizeResult(
                success=False,
                error=str(e),
                error_type="model_not_found",
            )
        except Exception as e:
            logger.exception("Layout recognition failed: %s", e)
            return LayoutRecognizeResult(
                success=False,
                error=f"Layout recognition failed: {str(e)}",
                error_type="processing_error",
            )

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
                # Render at scale_factor zoom for better detection quality
                bitmap = page.render(scale=self.scale_factor)
                pil_image = bitmap.to_pil()
                # Convert PIL to numpy BGR (OpenCV format)
                img_array = np.array(pil_image)
                if img_array.ndim == 2:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
                else:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                images.append(img_bgr)
        finally:
            pdf.close()

        return images
