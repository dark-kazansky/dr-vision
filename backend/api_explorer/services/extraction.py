"""
API Explorer service metadata for the 'Trích xuất dữ liệu' group.
Contains 3 endpoints: extract, extract_text, generate_schema.
"""

from typing import List
from core.schemas import EndpointField, EndpointMeta

ENDPOINTS: List[EndpointMeta] = [
    EndpointMeta(
        id="extract",
        group="Trích xuất dữ liệu",
        method="POST",
        path="/extract",
        summary="Trích xuất dữ liệu có cấu trúc từ file",
        description="Upload file, OCR rồi trích xuất các trường dữ liệu theo schema định nghĩa sẵn.",
        fields=[
            EndpointField(name="file", type="file", required=True, label="File (PNG/JPG/PDF)", accept=".png,.jpg,.jpeg,.pdf"),
            EndpointField(name="parser_model_id", type="text", required=True, label="Parser Model ID", placeholder="lightonocr-2-1b"),
            EndpointField(name="extractor_model_id", type="text", required=False, label="Extractor Model ID", placeholder="qwen3-max"),
            EndpointField(name="extraction_target", type="select", required=False, label="Phạm vi trích xuất", default="document",
                          options=["document", "page", "table_row"]),
            EndpointField(name="extraction_schema", type="textarea", required=True, label="Schema trích xuất (JSON)",
                          placeholder='[{"name":"invoice_number","type":"string","description":"Số hóa đơn","required":true}]'),
        ],
    ),
    EndpointMeta(
        id="extract_text",
        group="Trích xuất dữ liệu",
        method="POST",
        path="/extract-text",
        summary="Trích xuất từ văn bản có sẵn",
        description="Trích xuất dữ liệu có cấu trúc từ văn bản, không cần OCR lại.",
        fields=[
            EndpointField(name="text", type="textarea", required=True, label="Văn bản nguồn", placeholder="Nhập nội dung văn bản..."),
            EndpointField(name="extraction_schema", type="textarea", required=True, label="Schema trích xuất (JSON)",
                          placeholder='[{"name":"ten_khach_hang","type":"string","description":"Tên khách hàng","required":true}]'),
            EndpointField(name="extraction_target", type="select", required=False, label="Phạm vi trích xuất", default="document",
                          options=["document", "page", "table_row"]),
            EndpointField(name="extractor_model_id", type="text", required=False, label="Model ID", placeholder="gemini-2.5-flash"),
            EndpointField(name="tier", type="select", required=False, label="Tier", default="Normal",
                          options=["Rapid", "Normal", "Advance"]),
        ],
    ),
    EndpointMeta(
        id="generate_schema",
        group="Trích xuất dữ liệu",
        method="POST",
        path="/generate-schema",
        summary="Tự động tạo schema bằng AI",
        description="Mô tả bằng ngôn ngữ tự nhiên, AI sẽ tạo schema trích xuất phù hợp.",
        fields=[
            EndpointField(name="prompt", type="textarea", required=True, label="Mô tả schema cần tạo",
                          placeholder="Tạo schema để trích xuất thông tin từ hóa đơn: tên khách hàng, số hóa đơn, ngày lập, tổng tiền"),
            EndpointField(name="file", type="file", required=False, label="File mẫu (tùy chọn)", accept=".png,.jpg,.jpeg,.pdf"),
            EndpointField(name="tier", type="select", required=False, label="Tier", default="Normal",
                          options=["Rapid", "Normal", "Advance"]),
        ],
    ),
]
