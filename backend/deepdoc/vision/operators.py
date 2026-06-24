"""
Image preprocessing operators for ONNX model inference.

Ported from infiniflow/ragflow deepdoc/vision/operators.py
License: Apache License 2.0 (original code by InfiniFlow Authors)
"""

import numpy as np
import cv2


def preprocess(im_path, ops):
    """Apply a sequence of preprocessing operators to an image."""
    if isinstance(im_path, str):
        im = cv2.imread(im_path)
    else:
        im = np.array(im_path)
        if im.ndim == 2:
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)

    im_info = {
        "im_shape": np.array(im.shape[:2], dtype=np.float32),
        "scale_factor": np.array([1.0, 1.0], dtype=np.float32),
    }

    data = {"image": im, "im_info": im_info}
    for op in ops:
        data = op(data)
        if data is None:
            return None, None

    return data["image"], data["im_info"]


class LinearResize:
    """Resize image to target size with optional aspect ratio preservation."""

    def __init__(self, target_size, keep_ratio=False, interp=2):
        self.target_size = target_size  # [height, width]
        self.keep_ratio = keep_ratio
        self.interp = interp

    def __call__(self, data):
        im = data["image"]
        im_info = data["im_info"]

        target_h, target_w = self.target_size
        h, w = im.shape[:2]

        if self.keep_ratio:
            scale = min(target_h / h, target_w / w)
            new_h, new_w = int(h * scale), int(w * scale)
        else:
            new_h, new_w = target_h, target_w

        im = cv2.resize(im, (new_w, new_h), interpolation=self.interp)
        im_info["im_shape"] = np.array([new_h, new_w], dtype=np.float32)
        im_info["scale_factor"] = np.array(
            [new_h / h, new_w / w], dtype=np.float32
        )

        data["image"] = im
        data["im_info"] = im_info
        return data


class StandardizeImage:
    """Normalize image with mean and std."""

    def __init__(self, mean, std, is_scale=True):
        self.mean = np.array(mean, dtype=np.float32)
        self.std = np.array(std, dtype=np.float32)
        self.is_scale = is_scale

    def __call__(self, data):
        im = data["image"].astype(np.float32)
        if self.is_scale:
            im /= 255.0
        im = (im - self.mean) / self.std
        data["image"] = im
        return data


class Permute:
    """Transpose image from HWC to CHW format."""

    def __call__(self, data):
        im = data["image"]
        im = im.transpose(2, 0, 1)
        data["image"] = im
        return data


class PadStride:
    """Pad image to be divisible by stride."""

    def __init__(self, stride=32):
        self.stride = stride

    def __call__(self, data):
        im = data["image"]
        c, h, w = im.shape
        pad_h = int(np.ceil(h / self.stride) * self.stride) - h
        pad_w = int(np.ceil(w / self.stride) * self.stride) - w

        if pad_h > 0 or pad_w > 0:
            padding = np.zeros((c, h + pad_h, w + pad_w), dtype=im.dtype)
            padding[:, :h, :w] = im
            im = padding

        data["image"] = im
        return data


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.45):
    """
    Non-Maximum Suppression (NMS).

    Args:
        boxes: (N, 4) array of [x1, y1, x2, y2]
        scores: (N,) array of confidence scores
        iou_threshold: IoU threshold for suppression

    Returns:
        List of indices to keep
    """
    if len(boxes) == 0:
        return []

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h

        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]

    return keep
