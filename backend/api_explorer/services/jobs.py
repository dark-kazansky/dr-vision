"""
API Explorer service metadata for the 'Background Jobs' group.
Contains 2 endpoints: job_status, job_result.
"""

from typing import List
from core.schemas import EndpointField, EndpointMeta

ENDPOINTS: List[EndpointMeta] = [
    EndpointMeta(
        id="job_status",
        group="Background Jobs",
        method="GET",
        path="/job/{job_id}/status",
        summary="Kiểm tra trạng thái job nền",
        description="Dùng để poll trạng thái của job xử lý nền (PDF nhiều trang).",
        fields=[
            EndpointField(name="job_id", type="text", required=True, label="Job ID", placeholder="abc123...", path_param=True),
        ],
    ),
    EndpointMeta(
        id="job_result",
        group="Background Jobs",
        method="GET",
        path="/job/{job_id}/result",
        summary="Lấy kết quả job nền",
        description="Lấy kết quả đầy đủ của job đã hoàn thành.",
        fields=[
            EndpointField(name="job_id", type="text", required=True, label="Job ID", placeholder="abc123...", path_param=True),
        ],
    ),
]
