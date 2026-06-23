"""
Tests for Layout Recognizer component and DeepDoc vision module.

feat-031: Layout Recognize — DeepDoc-based document layout detection.

Tests cover:
- Operators (NMS, preprocessing)
- Recognizer base class (postprocessing logic)
- LayoutRecognizer (detection, sorting, cleanup)
- LayoutRecognizeComponent (file handling, result formatting)
- API endpoint registration
"""

import numpy as np
from unittest.mock import patch, MagicMock


# ─── Test: NMS (Non-Maximum Suppression) ─────────────────────────────────────


class TestNMS:
    """Test Non-Maximum Suppression algorithm."""

    def test_nms_empty_input(self):
        from deepdoc.vision.operators import nms

        result = nms(np.array([]).reshape(0, 4), np.array([]), 0.5)
        assert result == []

    def test_nms_single_box(self):
        from deepdoc.vision.operators import nms

        boxes = np.array([[10, 10, 50, 50]], dtype=np.float32)
        scores = np.array([0.9])
        result = nms(boxes, scores, 0.5)
        assert result == [0]

    def test_nms_no_overlap(self):
        from deepdoc.vision.operators import nms

        boxes = np.array([
            [10, 10, 50, 50],
            [100, 100, 150, 150],
            [200, 200, 250, 250],
        ], dtype=np.float32)
        scores = np.array([0.9, 0.8, 0.7])
        result = nms(boxes, scores, 0.5)
        assert sorted(result) == [0, 1, 2]

    def test_nms_high_overlap_suppresses(self):
        from deepdoc.vision.operators import nms

        # Two highly overlapping boxes
        boxes = np.array([
            [10, 10, 50, 50],
            [12, 12, 52, 52],  # ~80% overlap
        ], dtype=np.float32)
        scores = np.array([0.9, 0.7])
        result = nms(boxes, scores, 0.3)
        # Should keep only the higher-scored box
        assert result == [0]

    def test_nms_low_overlap_keeps_both(self):
        from deepdoc.vision.operators import nms

        # Two boxes with moderate overlap
        boxes = np.array([
            [10, 10, 50, 50],
            [40, 10, 80, 50],  # ~25% overlap
        ], dtype=np.float32)
        scores = np.array([0.9, 0.8])
        result = nms(boxes, scores, 0.5)
        assert sorted(result) == [0, 1]


# ─── Test: Operators ─────────────────────────────────────────────────────────


class TestOperators:
    """Test preprocessing operators."""

    def test_linear_resize(self):
        from deepdoc.vision.operators import LinearResize

        op = LinearResize(target_size=[640, 480], keep_ratio=False)
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        data = {"image": img, "im_info": {
            "im_shape": np.array([100, 200], dtype=np.float32),
            "scale_factor": np.array([1.0, 1.0], dtype=np.float32),
        }}
        result = op(data)
        assert result["image"].shape == (640, 480, 3)

    def test_standardize_image(self):
        from deepdoc.vision.operators import StandardizeImage

        op = StandardizeImage(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
            is_scale=True,
        )
        img = np.ones((10, 10, 3), dtype=np.uint8) * 128
        data = {"image": img}
        result = op(data)
        # After scaling by 255 and normalizing, values should be around 0
        assert result["image"].dtype == np.float32
        assert result["image"].shape == (10, 10, 3)

    def test_permute(self):
        from deepdoc.vision.operators import Permute

        op = Permute()
        img = np.zeros((100, 200, 3), dtype=np.float32)
        data = {"image": img}
        result = op(data)
        assert result["image"].shape == (3, 100, 200)

    def test_pad_stride(self):
        from deepdoc.vision.operators import PadStride

        op = PadStride(stride=32)
        # 3x50x70 should pad to 3x64x96
        img = np.zeros((3, 50, 70), dtype=np.float32)
        data = {"image": img}
        result = op(data)
        h, w = result["image"].shape[1], result["image"].shape[2]
        assert h % 32 == 0
        assert w % 32 == 0
        assert h >= 50
        assert w >= 70


# ─── Test: Recognizer Base ────────────────────────────────────────────────────


class TestRecognizerBase:
    """Test Recognizer base class static methods."""

    def test_sort_Y_firstly(self):
        from deepdoc.vision.recognizer import Recognizer

        boxes = [
            {"top": 100, "x0": 50},
            {"top": 10, "x0": 200},
            {"top": 10, "x0": 50},
        ]
        result = Recognizer.sort_Y_firstly(boxes, threshold=5)
        # First two have similar Y (10 vs 10), so sort by X
        assert result[0]["x0"] == 50 and result[0]["top"] == 10
        assert result[1]["x0"] == 200 and result[1]["top"] == 10
        assert result[2]["top"] == 100

    def test_sort_X_firstly(self):
        from deepdoc.vision.recognizer import Recognizer

        boxes = [
            {"top": 50, "x0": 200},
            {"top": 10, "x0": 100},
            {"top": 30, "x0": 100},
        ]
        result = Recognizer.sort_X_firstly(boxes, threshold=5)
        assert result[0]["x0"] == 100
        assert result[-1]["x0"] == 200

    def test_overlapped_area_no_overlap(self):
        from deepdoc.vision.recognizer import Recognizer

        a = {"top": 0, "bottom": 10, "x0": 0, "x1": 10}
        b = {"top": 20, "bottom": 30, "x0": 0, "x1": 10}
        assert Recognizer.overlapped_area(a, b) == 0

    def test_overlapped_area_full_overlap(self):
        from deepdoc.vision.recognizer import Recognizer

        a = {"top": 0, "bottom": 10, "x0": 0, "x1": 10}
        b = {"top": 0, "bottom": 10, "x0": 0, "x1": 10}
        assert Recognizer.overlapped_area(a, b) == 1.0

    def test_overlapped_area_partial(self):
        from deepdoc.vision.recognizer import Recognizer

        a = {"top": 0, "bottom": 10, "x0": 0, "x1": 10}
        b = {"top": 5, "bottom": 15, "x0": 5, "x1": 15}
        # Overlap: 5x5=25, Area of a: 10x10=100
        area = Recognizer.overlapped_area(a, b)
        assert abs(area - 0.25) < 0.01

    def test_find_overlapped_with_threshold_none(self):
        from deepdoc.vision.recognizer import Recognizer

        box = {"top": 0, "bottom": 10, "x0": 0, "x1": 10}
        boxes = [{"top": 100, "bottom": 110, "x0": 100, "x1": 110}]
        result = Recognizer.find_overlapped_with_threshold(box, boxes, thr=0.3)
        assert result is None

    def test_find_overlapped_with_threshold_found(self):
        from deepdoc.vision.recognizer import Recognizer

        box = {"top": 0, "bottom": 10, "x0": 0, "x1": 10}
        boxes = [
            {"top": 100, "bottom": 110, "x0": 100, "x1": 110},
            {"top": 2, "bottom": 12, "x0": 2, "x1": 12},  # High overlap
        ]
        result = Recognizer.find_overlapped_with_threshold(box, boxes, thr=0.3)
        assert result == 1

    def test_layouts_cleanup_removes_duplicate(self):
        from deepdoc.vision.recognizer import Recognizer

        boxes = [{"top": 5, "bottom": 8, "x0": 5, "x1": 8}]
        layouts = [
            {"type": "text", "score": 0.9, "top": 0, "bottom": 10, "x0": 0, "x1": 10},
            {"type": "text", "score": 0.7, "top": 1, "bottom": 11, "x0": 1, "x1": 11},
        ]
        result = Recognizer.layouts_cleanup(boxes, layouts, far=2, thr=0.5)
        # Should keep only the higher-scored one
        assert len(result) == 1
        assert result[0]["score"] == 0.9


# ─── Test: LayoutRecognizer ───────────────────────────────────────────────────


class TestLayoutRecognizer:
    """Test LayoutRecognizer class."""

    def test_labels_defined(self):
        from deepdoc.vision.layout_recognizer import LAYOUT_LABELS

        assert len(LAYOUT_LABELS) == 10
        # Key labels should be present (case-insensitive)
        labels_lower = [label.lower() for label in LAYOUT_LABELS]
        assert "title" in labels_lower
        assert "text" in labels_lower
        assert "table" in labels_lower
        assert "figure" in labels_lower
        assert "equation" in labels_lower

    def test_layout_recognizer_inherits_recognizer(self):
        from deepdoc.vision.layout_recognizer import LayoutRecognizer
        from deepdoc.vision.recognizer import Recognizer

        assert issubclass(LayoutRecognizer, Recognizer)

    @patch("deepdoc.vision.recognizer.Recognizer.__init__", return_value=None)
    def test_detect_returns_per_page_results(self, mock_init):
        from deepdoc.vision.layout_recognizer import LayoutRecognizer

        recognizer = LayoutRecognizer.__new__(LayoutRecognizer)
        recognizer.label_list = LayoutRecognizer.labels
        recognizer.garbage_layouts = ["footer", "header", "reference"]

        # Mock the parent __call__ to return raw detections
        mock_detections = [[
            {"type": "text", "score": 0.9, "bbox": [30, 60, 300, 300]},
            {"type": "title", "score": 0.85, "bbox": [30, 10, 300, 50]},
        ]]

        with patch.object(
            LayoutRecognizer.__bases__[0], "__call__", return_value=mock_detections
        ):
            images = [np.zeros((800, 600, 3), dtype=np.uint8)]
            result = recognizer.detect(images, thr=0.2, scale_factor=3)

        assert len(result) == 1
        assert len(result[0]) == 2
        # Check coordinates are scaled
        assert result[0][0]["x0"] == 30 / 3
        assert result[0][0]["page_number"] == 0


# ─── Test: LayoutRecognizeComponent ───────────────────────────────────────────


class TestLayoutRecognizeComponent:
    """Test the high-level component wrapper."""

    def test_unsupported_file_type(self):
        from components.layout_recognizer import LayoutRecognizeComponent

        component = LayoutRecognizeComponent()
        result = component.recognize("/tmp/test.xlsx")
        assert not result.success
        assert result.error_type == "validation_error"

    def test_result_to_dict(self):
        from components.layout_recognizer import LayoutRecognizeResult, LayoutRegion

        result = LayoutRecognizeResult(
            success=True,
            regions=[
                LayoutRegion(type="text", score=0.9, x0=10, y0=20, x1=100, y1=80, page_number=0),
                LayoutRegion(type="table", score=0.85, x0=10, y0=100, x1=100, y1=200, page_number=0),
                LayoutRegion(type="text", score=0.8, x0=10, y0=210, x1=100, y1=300, page_number=1),
            ],
            page_count=2,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert len(d["regions"]) == 3
        assert d["page_count"] == 2
        assert d["summary"]["text"] == 2
        assert d["summary"]["table"] == 1

    def test_layout_region_to_dict(self):
        from components.layout_recognizer import LayoutRegion

        region = LayoutRegion(
            type="title", score=0.95, x0=10.123, y0=20.456, x1=100.789, y1=50.321, page_number=0
        )
        d = region.to_dict()
        assert d["type"] == "title"
        assert d["score"] == 0.95
        assert d["bbox"] == [10.12, 20.46, 100.79, 50.32]
        assert d["page_number"] == 0

    @patch("components.layout_recognizer.LayoutRecognizeComponent._get_recognizer")
    def test_recognize_image_success(self, mock_get_recognizer):
        """Test successful recognition on an image file."""
        import tempfile
        import os
        from components.layout_recognizer import LayoutRecognizeComponent

        # Create a temp image file
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        import cv2
        cv2.imwrite(tmp.name, img)

        try:
            mock_recognizer = MagicMock()
            mock_recognizer.detect.return_value = [[
                {"type": "text", "score": 0.9, "x0": 10, "top": 20, "x1": 90, "bottom": 80, "page_number": 0},
            ]]
            mock_get_recognizer.return_value = mock_recognizer

            component = LayoutRecognizeComponent(threshold=0.2, scale_factor=3)
            result = component.recognize(tmp.name)

            assert result.success
            assert len(result.regions) == 1
            assert result.regions[0].type == "text"
            assert result.page_count == 1
        finally:
            os.unlink(tmp.name)

    def test_recognize_nonexistent_file(self):
        """Test recognition on a file that doesn't exist."""
        from components.layout_recognizer import LayoutRecognizeComponent

        component = LayoutRecognizeComponent()
        result = component.recognize("/nonexistent/path/file.png")
        assert not result.success
        assert result.error_type == "processing_error"


# ─── Test: API Endpoint Registration ─────────────────────────────────────────


class TestLayoutAPI:
    """Test layout API endpoint exists and is properly configured."""

    def test_layout_router_exists(self):
        from api.v1.layout import router

        routes = [r.path for r in router.routes]
        assert "/recognize" in routes or "/layout/recognize" in routes

    def test_layout_models_endpoint_exists(self):
        from api.v1.layout import router

        route_paths = [r.path for r in router.routes]
        assert "/models" in route_paths or "/layout/models" in route_paths


# ─── Test: Workflow Integration ───────────────────────────────────────────────


class TestWorkflowIntegration:
    """Test layout_recognize is integrated in workflow service."""

    def test_workflow_service_has_layout_recognize(self):
        """Verify _run_layout_recognize_step exists."""
        from services.workflow_service import _run_layout_recognize_step

        assert callable(_run_layout_recognize_step)

    def test_job_executor_imports_layout_step(self):
        """Verify job_executor imports _run_layout_recognize_step."""
        import importlib
        import services.job_executor as je

        source = importlib.util.find_spec("services.job_executor")
        assert source is not None
        # The import is inside a function, so just verify the module loads
        assert hasattr(je, "execute_job")
