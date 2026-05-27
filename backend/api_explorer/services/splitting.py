"""
API Explorer service metadata for the 'Tách tài liệu' group.
Contains 1 endpoint: split_sections.
"""

from typing import List
from core.schemas import EndpointField, EndpointMeta

ENDPOINTS: List[EndpointMeta] = [
    EndpointMeta(
        id="split_sections",
        group="Tách tài liệu",
        method="POST",
        path="/split",
        summary="Tách tài liệu theo sections",
        description="Phân tích và tách tài liệu thành các phần theo danh mục do người dùng định nghĩa.",
        fields=[
            EndpointField(name="file", type="file", required=True, label="File (PNG/JPG/PDF)", accept=".png,.jpg,.jpeg,.pdf"),
            EndpointField(name="split_mode", type="select", required=False, label="Chế độ tách", default="sections",
                          options=["sections", "document_type"]),
            EndpointField(name="splitter_tier", type="select", required=False, label="Tier", default="Normal",
                          options=["Rapid", "Normal", "Advance"]),
            EndpointField(name="categories", type="textarea", required=True, label="Danh mục (JSON)",
                          placeholder='[{"name":"Thông tin khách hàng","description":"Phần chứa thông tin cá nhân","order":1},{"name":"Chi tiết đơn hàng","description":"Phần liệt kê sản phẩm","order":2}]'),
            EndpointField(name="allow_uncategorized", type="checkbox", required=False, label="Cho phép phần không phân loại", default=True),
        ],
    ),
]
