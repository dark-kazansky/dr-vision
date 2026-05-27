"""
API Explorer service metadata for the 'File đã lưu' group.
Contains 2 endpoints: raw_ocr, parsed_docx.
"""

from typing import List
from core.schemas import EndpointField, EndpointMeta

ENDPOINTS: List[EndpointMeta] = [
    EndpointMeta(
        id="raw_ocr",
        group="File đã lưu",
        method="GET",
        path="/raw-ocr/{filename}",
        summary="Lấy văn bản OCR thô",
        description="Đọc nội dung file văn bản OCR đã lưu.",
        fields=[
            EndpointField(name="filename", type="text", required=True, label="Tên file (không có .txt)", placeholder="ten_file", path_param=True),
        ],
    ),
    EndpointMeta(
        id="parsed_docx",
        group="File đã lưu",
        method="GET",
        path="/parsed/{filename}",
        summary="Tải file DOCX đã parse",
        description="Tải xuống file DOCX được tạo từ kết quả OCR.",
        fields=[
            EndpointField(name="filename", type="text", required=True, label="Tên file (không có .docx)", placeholder="ten_file", path_param=True),
        ],
    ),
]
