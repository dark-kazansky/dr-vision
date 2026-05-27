"""
API Explorer service metadata for the 'Hệ thống' group.
Contains 4 endpoints: health, models_check, tier_config, list_saved_files.
"""

from typing import List
from core.schemas import EndpointField, EndpointMeta

ENDPOINTS: List[EndpointMeta] = [
    EndpointMeta(
        id="health",
        group="Hệ thống",
        method="GET",
        path="/health",
        summary="Kiểm tra trạng thái server",
        description="Trả về trạng thái hoạt động của server và danh sách model khả dụng.",
        fields=[],
    ),
    EndpointMeta(
        id="models_check",
        group="Hệ thống",
        method="GET",
        path="/models/check",
        summary="Kiểm tra model khả dụng",
        description="Trả về thông tin chi tiết về từng model: provider, API key, trạng thái.",
        fields=[],
    ),
    EndpointMeta(
        id="tier_config",
        group="Hệ thống",
        method="GET",
        path="/tier-config",
        summary="Xem cấu hình Tier",
        description="Trả về mapping tier → model cho tất cả chức năng (parse, classify, extract, split).",
        fields=[],
    ),
    EndpointMeta(
        id="list_saved_files",
        group="Hệ thống",
        method="GET",
        path="/list-saved-files",
        summary="Liệt kê file đã xử lý",
        description="Trả về danh sách tất cả file đã được OCR và lưu trữ.",
        fields=[],
    ),
]
