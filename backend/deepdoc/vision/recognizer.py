"""
Base Recognizer class for ONNX model inference.

Ported from infiniflow/ragflow deepdoc/vision/recognizer.py
License: Apache License 2.0 (original code by InfiniFlow Authors)

Handles:
- ONNX model loading
- Image preprocessing (resize, normalize, pad)
- Inference with batching
- Postprocessing (NMS, bbox decoding)
- Layout cleanup utilities (overlap, sorting)
"""

import gc
import logging
import math
from functools import cmp_to_key
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from .operators import nms

logger = logging.getLogger(__name__)


class Recognizer:
    """Base ONNX model recognizer with preprocessing and postprocessing."""

    def __init__(self, label_list: List[str], task_name: str, model_dir: str):
        """
        Initialize recognizer with ONNX model.

        Args:
            label_list: List of class label names
            task_name: Model filename (without .onnx extension)
            model_dir: Directory containing ONNX model files
        """
        import os
        import onnxruntime as ort

        model_file_path = os.path.join(model_dir, task_name + ".onnx")
        if not os.path.exists(model_file_path):
            raise FileNotFoundError(
                f"Model file not found: {model_file_path}. "
                f"Please download models first."
            )

        options = ort.SessionOptions()
        options.enable_cpu_mem_arena = False
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.intra_op_num_threads = int(
            os.environ.get("DEEPDOC_INTRA_OP_THREADS", "2")
        )
        options.inter_op_num_threads = int(
            os.environ.get("DEEPDOC_INTER_OP_THREADS", "2")
        )

        providers = ["CPUExecutionProvider"]
        # Check for CUDA availability
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        self.ort_sess = ort.InferenceSession(
            model_file_path, sess_options=options, providers=providers
        )
        self.run_options = ort.RunOptions()
        self.input_names = [node.name for node in self.ort_sess.get_inputs()]
        self.output_names = [node.name for node in self.ort_sess.get_outputs()]
        self.input_shape = self.ort_sess.get_inputs()[0].shape[2:4]
        self.label_list = label_list

        logger.info(
            "Loaded model %s from %s (input_shape=%s, labels=%d)",
            task_name, model_dir, self.input_shape, len(label_list),
        )

    @staticmethod
    def sort_Y_firstly(arr: List[Dict], threshold: float) -> List[Dict]:
        """Sort boxes by Y coordinate first, then X within threshold."""

        def cmp(c1, c2):
            diff = c1["top"] - c2["top"]
            if abs(diff) < threshold:
                diff = c1["x0"] - c2["x0"]
            return diff

        return sorted(arr, key=cmp_to_key(cmp))

    @staticmethod
    def sort_X_firstly(arr: List[Dict], threshold: float) -> List[Dict]:
        """Sort boxes by X coordinate first, then Y within threshold."""

        def cmp(c1, c2):
            diff = c1["x0"] - c2["x0"]
            if abs(diff) < threshold:
                diff = c1["top"] - c2["top"]
            return diff

        return sorted(arr, key=cmp_to_key(cmp))

    @staticmethod
    def overlapped_area(
        a: Dict[str, float], b: Dict[str, float], ratio: bool = True
    ) -> float:
        """Calculate overlapping area between two bounding boxes."""
        tp, btm, x0, x1 = a["top"], a["bottom"], a["x0"], a["x1"]
        if b["x0"] > x1 or b["x1"] < x0:
            return 0
        if b["bottom"] < tp or b["top"] > btm:
            return 0

        x0_ = max(b["x0"], x0)
        x1_ = min(b["x1"], x1)
        tp_ = max(b["top"], tp)
        btm_ = min(b["bottom"], btm)

        ov = (btm_ - tp_) * (x1_ - x0_)
        if ov > 0 and ratio:
            area = (x1 - x0) * (btm - tp)
            ov = ov / area if area > 0 else 0
        return ov

    @staticmethod
    def layouts_cleanup(
        boxes: List[Dict], layouts: List[Dict], far: int = 2, thr: float = 0.7
    ) -> List[Dict]:
        """Remove overlapping layout detections, keeping the one with more text overlap."""

        def not_overlapped(a, b):
            return any([
                a["x1"] < b["x0"],
                a["x0"] > b["x1"],
                a["bottom"] < b["top"],
                a["top"] > b["bottom"],
            ])

        i = 0
        while i + 1 < len(layouts):
            j = i + 1
            while j < min(i + far, len(layouts)) and (
                layouts[i].get("type", "") != layouts[j].get("type", "")
                or not_overlapped(layouts[i], layouts[j])
            ):
                j += 1
            if j >= min(i + far, len(layouts)):
                i += 1
                continue
            if (
                Recognizer.overlapped_area(layouts[i], layouts[j]) < thr
                and Recognizer.overlapped_area(layouts[j], layouts[i]) < thr
            ):
                i += 1
                continue

            if layouts[i].get("score") and layouts[j].get("score"):
                if layouts[i]["score"] > layouts[j]["score"]:
                    layouts.pop(j)
                else:
                    layouts.pop(i)
                continue

            area_i, area_j = 0, 0
            for b in boxes:
                if not not_overlapped(b, layouts[i]):
                    area_i += Recognizer.overlapped_area(b, layouts[i], False)
                if not not_overlapped(b, layouts[j]):
                    area_j += Recognizer.overlapped_area(b, layouts[j], False)

            if area_i > area_j:
                layouts.pop(j)
            else:
                layouts.pop(i)

        return layouts

    @staticmethod
    def find_overlapped_with_threshold(
        box: Dict, boxes: List[Dict], thr: float = 0.3
    ) -> Optional[int]:
        """Find the most overlapped box above a threshold."""
        if not boxes:
            return None
        max_overlapped_i, max_overlapped, _max_overlapped = None, thr, 0
        for i in range(len(boxes)):
            ov = Recognizer.overlapped_area(box, boxes[i])
            _ov = Recognizer.overlapped_area(boxes[i], box)
            if (ov, _ov) < (max_overlapped, _max_overlapped):
                continue
            max_overlapped_i = i
            max_overlapped = ov
            _max_overlapped = _ov
        return max_overlapped_i

    def preprocess(self, image_list: List[np.ndarray]) -> List[Dict[str, Any]]:
        """
        Preprocess images for YOLOv10 inference.

        Args:
            image_list: List of BGR images (numpy arrays)

        Returns:
            List of input dictionaries for the model
        """
        inputs = []
        hh, ww = self.input_shape

        for img in image_list:
            h, w = img.shape[:2]
            # Scale ratio (new / old)
            r = min(hh / h, ww / w)
            new_unpad = int(round(w * r)), int(round(h * r))
            dw = (ww - new_unpad[0]) / 2
            dh = (hh - new_unpad[1]) / 2

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)
            img_resized = cv2.resize(
                img_rgb, new_unpad, interpolation=cv2.INTER_LINEAR
            )

            # Add border padding
            top = int(round(dh - 0.1))
            bottom = int(round(dh + 0.1))
            left = int(round(dw - 0.1))
            right = int(round(dw + 0.1))
            img_padded = cv2.copyMakeBorder(
                img_resized, top, bottom, left, right,
                cv2.BORDER_CONSTANT, value=(114, 114, 114),
            )

            img_padded /= 255.0
            img_chw = img_padded.transpose(2, 0, 1)
            img_batch = img_chw[np.newaxis, :, :, :].astype(np.float32)

            inputs.append({
                self.input_names[0]: img_batch,
                "scale_factor": [w / new_unpad[0], h / new_unpad[1], dw, dh],
            })

        return inputs

    def postprocess(
        self, boxes: np.ndarray, inputs: Dict[str, Any], thr: float
    ) -> List[Dict[str, Any]]:
        """
        Postprocess model output: decode boxes, apply NMS, filter by threshold.

        Args:
            boxes: Raw model output
            inputs: Preprocessing metadata (scale_factor)
            thr: Confidence threshold

        Returns:
            List of detection dicts with type, bbox, score
        """
        thr = max(thr, 0.08)
        boxes = np.squeeze(boxes)

        if boxes.ndim == 1:
            boxes = boxes.reshape(1, -1)

        # YOLOv10 output: [x1, y1, x2, y2, score, class_id]
        if boxes.shape[1] == 6:
            scores = boxes[:, 4]
            mask = scores > thr
            boxes_filtered = boxes[mask]
            if len(boxes_filtered) == 0:
                return []

            class_ids = boxes_filtered[:, 5].astype(int)
            coords = boxes_filtered[:, :4].astype(np.float32)
            scores_filtered = boxes_filtered[:, 4]

            # Undo padding and scaling
            dw, dh = inputs["scale_factor"][2], inputs["scale_factor"][3]
            sx, sy = inputs["scale_factor"][0], inputs["scale_factor"][1]
            coords[:, [0, 2]] -= dw
            coords[:, [1, 3]] -= dh
            coords *= np.array([sx, sy, sx, sy], dtype=np.float32)

            # Per-class NMS
            keep_indices = []
            for c in np.unique(class_ids):
                idx = np.where(class_ids == c)[0]
                k = nms(coords[idx], scores_filtered[idx], 0.45)
                keep_indices.extend(idx[k])

            results = []
            for i in keep_indices:
                cid = int(class_ids[i])
                if 0 <= cid < len(self.label_list):
                    results.append({
                        "type": self.label_list[cid].lower(),
                        "bbox": [float(t) for t in coords[i].tolist()],
                        "score": float(scores_filtered[i]),
                    })
            return results

        # Fallback: older format [N, 5+num_classes] (transposed)
        if boxes.ndim == 2 and boxes.shape[0] > boxes.shape[1]:
            boxes = boxes.T

        scores = np.max(boxes[:, 4:], axis=1)
        mask = scores > thr
        boxes_filtered = boxes[mask]
        scores_filtered = scores[mask]

        if len(boxes_filtered) == 0:
            return []

        class_ids = np.argmax(boxes_filtered[:, 4:], axis=1)
        coords = boxes_filtered[:, :4]

        # xywh to xyxy
        xyxy = np.copy(coords)
        xyxy[:, 0] = coords[:, 0] - coords[:, 2] / 2
        xyxy[:, 1] = coords[:, 1] - coords[:, 3] / 2
        xyxy[:, 2] = coords[:, 0] + coords[:, 2] / 2
        xyxy[:, 3] = coords[:, 1] + coords[:, 3] / 2

        # Scale to original image size
        sx, sy = inputs["scale_factor"][0], inputs["scale_factor"][1]
        scale_arr = np.array([sx, sy, sx, sy], dtype=np.float32)
        xyxy = np.multiply(xyxy, scale_arr)

        # Per-class NMS
        keep_indices = []
        for c in np.unique(class_ids):
            idx = np.where(class_ids == c)[0]
            k = nms(xyxy[idx], scores_filtered[idx], 0.45)
            keep_indices.extend(idx[k])

        return [{
            "type": self.label_list[class_ids[i]].lower(),
            "bbox": [float(t) for t in xyxy[i].tolist()],
            "score": float(scores_filtered[i]),
        } for i in keep_indices]

    def __call__(
        self, image_list: List[np.ndarray], thr: float = 0.7, batch_size: int = 16
    ) -> List[List[Dict[str, Any]]]:
        """
        Run inference on a list of images.

        Args:
            image_list: List of images (numpy arrays, BGR)
            thr: Confidence threshold
            batch_size: Number of images per batch

        Returns:
            List of detection results per image
        """
        res = []
        images = []
        for img in image_list:
            if not isinstance(img, np.ndarray):
                images.append(np.array(img))
            else:
                images.append(img)

        batch_count = math.ceil(len(images) / batch_size)
        for i in range(batch_count):
            start = i * batch_size
            end = min((i + 1) * batch_size, len(images))
            batch = images[start:end]
            inputs = self.preprocess(batch)

            for ins in inputs:
                feed = {
                    k: v for k, v in ins.items() if k in self.input_names
                }
                output = self.ort_sess.run(None, feed, self.run_options)[0]
                bb = self.postprocess(output, ins, thr)
                res.append(bb)

        return res

    def close(self):
        """Release ONNX session resources."""
        if hasattr(self, "ort_sess"):
            del self.ort_sess
        gc.collect()

    def __del__(self):
        self.close()
