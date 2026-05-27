"""
API Explorer service metadata for the 'Phân loại' group.
Contains 2 endpoints: classify, classify_text.
"""

from typing import List
from core.schemas import EndpointField, EndpointMeta

ENDPOINTS: List[EndpointMeta] = [
    EndpointMeta(
        id="classify",
        group="Phân loại",
        method="POST",
        path="/classify",
        summary="Phân loại tài liệu (có file)",
        description="Upload file, OCR rồi phân loại theo các quy tắc do người dùng định nghĩa.",
        fields=[
            EndpointField(name="file", type="file", required=True, label="File (PNG/JPG/PDF)", accept=".png,.jpg,.jpeg,.pdf"),
            EndpointField(name="parser_model_id", type="text", required=True, label="Parser Model ID", placeholder="lightonocr-2-1b"),
            EndpointField(name="tier", type="select", required=False, label="Tier", default="Normal",
                          options=["Rapid", "Normal", "Advance"]),
            EndpointField(name="classification_rules", type="textarea", required=True, label="Quy tắc phân loại (JSON)",
                          placeholder='[{"doc_type":"Hóa đơn","description":"Tài liệu thanh toán"},{"doc_type":"Hợp đồng","description":"Văn bản pháp lý"}]'),
            EndpointField(name="max_pages", type="number", required=False, label="Số trang tối đa", default=5),
        ],
    ),
    EndpointMeta(
        id="classify_text",
        group="Phân loại",
        method="POST",
        path="/classify-text",
        summary="Phân loại từ văn bản có sẵn",
        description="Phân loại trực tiếp từ văn bản, không cần OCR lại.",
        fields=[
            EndpointField(name="text", type="textarea", required=True, label="Văn bản cần phân loại", placeholder="Nhập nội dung văn bản..."),
            EndpointField(name="classification_rules", type="textarea", required=True, label="Quy tắc phân loại (JSON)",
                          placeholder='[{"doc_type":"Hóa đơn","description":"Tài liệu thanh toán"}]'),
            EndpointField(name="tier", type="select", required=False, label="Tier", default="Normal",
                          options=["Rapid", "Normal", "Advance"]),
        ],
    ),
]
