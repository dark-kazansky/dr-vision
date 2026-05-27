"""
API Explorer service metadata for the 'OCR / Parse' group.
Contains 1 endpoint: parse.
"""

from typing import List
from core.schemas import EndpointField, EndpointMeta

ENDPOINTS: List[EndpointMeta] = [
    EndpointMeta(
        id="parse",
        group="OCR / Parse",
        method="POST",
        path="/parse",
        summary="Trích xuất văn bản từ file",
        description="Upload file ảnh hoặc PDF, trích xuất văn bản bằng model OCR được chọn. Hỗ trợ xử lý nền cho PDF nhiều trang.",
        fields=[
            EndpointField(name="file", type="file", required=True, label="File (PNG/JPG/PDF)", accept=".png,.jpg,.jpeg,.pdf"),
            EndpointField(name="model_id", type="text", required=True, label="Model ID", placeholder="lightonocr-2-1b"),
            EndpointField(name="tier", type="select", required=False, label="Tier", default="Normal",
                          options=["Rapid", "Normal", "Advance"]),
            EndpointField(name="force_ocr", type="checkbox", required=False, label="Bắt buộc OCR (kể cả PDF text)", default=False),
            EndpointField(name="parse_formatting", type="checkbox", required=False, label="Parse định dạng Markdown", default=True),
            EndpointField(name="process_all_pages", type="checkbox", required=False, label="Xử lý tất cả trang PDF", default=True),
        ],
    ),
]
