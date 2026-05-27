"""
API Explorer service metadata for the 'Workflow' group.
Contains 2 endpoints: workflow_execute, condition_evaluate.
"""

from typing import List
from core.schemas import EndpointField, EndpointMeta

ENDPOINTS: List[EndpointMeta] = [
    EndpointMeta(
        id="workflow_execute",
        group="Workflow",
        method="POST",
        path="/workflow/execute",
        summary="Chạy pipeline nhiều bước",
        description="Thực thi một chuỗi các bước xử lý (parse → classify → extract → split) trên một file.",
        fields=[
            EndpointField(name="file", type="file", required=True, label="File (PNG/JPG/PDF)", accept=".png,.jpg,.jpeg,.pdf"),
            EndpointField(name="workflow", type="textarea", required=True, label="Định nghĩa Workflow (JSON)",
                          placeholder='{"steps":[{"type":"parse","tier":"Normal"},{"type":"classify","tier":"Normal","config":{"rules":[{"doc_type":"Hóa đơn","description":"Tài liệu thanh toán"}]}}]}'),
        ],
    ),
    EndpointMeta(
        id="condition_evaluate",
        group="Workflow",
        method="POST",
        path="/condition/evaluate",
        summary="Đánh giá điều kiện workflow",
        description="Kiểm tra kết quả bước trước có thỏa mãn điều kiện nào không, dùng để rẽ nhánh workflow.",
        fields=[
            EndpointField(name="conditions", type="textarea", required=True, label="Điều kiện (JSON)",
                          placeholder='[{"operator":"equals","value":"Hóa đơn"},{"operator":"equals","value":"Hợp đồng"}]'),
            EndpointField(name="previous_result", type="textarea", required=True, label="Kết quả bước trước (JSON)",
                          placeholder='{"document_type":"Hóa đơn","confidence":0.95}'),
            EndpointField(name="field_name", type="text", required=False, label="Tên trường đánh giá", default="document_type"),
        ],
    ),
]
