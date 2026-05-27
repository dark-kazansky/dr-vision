"""
API Explorer package — aggregates endpoint metadata from all service modules
and exposes the /api-explorer/endpoints route.
"""

from typing import List
from fastapi import APIRouter
from core.schemas import EndpointMeta, EndpointGroup, ApiExplorerResponse

from api_explorer.services.system import ENDPOINTS as _SYSTEM_ENDPOINTS
from api_explorer.services.ocr import ENDPOINTS as _OCR_ENDPOINTS
from api_explorer.services.classification import ENDPOINTS as _CLASSIFICATION_ENDPOINTS
from api_explorer.services.extraction import ENDPOINTS as _EXTRACTION_ENDPOINTS
from api_explorer.services.splitting import ENDPOINTS as _SPLITTING_ENDPOINTS
from api_explorer.services.workflow import ENDPOINTS as _WORKFLOW_ENDPOINTS
from api_explorer.services.jobs import ENDPOINTS as _JOBS_ENDPOINTS
from api_explorer.services.saved_files import ENDPOINTS as _SAVED_FILES_ENDPOINTS
from api_explorer.services.journey_jobs import ENDPOINTS as _JOURNEY_JOBS_ENDPOINTS

ENDPOINTS: List[EndpointMeta] = (
    _SYSTEM_ENDPOINTS
    + _OCR_ENDPOINTS
    + _CLASSIFICATION_ENDPOINTS
    + _EXTRACTION_ENDPOINTS
    + _SPLITTING_ENDPOINTS
    + _WORKFLOW_ENDPOINTS
    + _JOBS_ENDPOINTS
    + _SAVED_FILES_ENDPOINTS
    + _JOURNEY_JOBS_ENDPOINTS
)

router = APIRouter(prefix="/api-explorer", tags=["API Explorer"])

@router.get("/endpoints", response_model=ApiExplorerResponse)
async def get_endpoints() -> ApiExplorerResponse:
    """Return metadata for all API endpoints to power the frontend API Explorer UI."""
    groups: dict = {}
    for ep in ENDPOINTS:
        if ep.group not in groups:
            groups[ep.group] = []
        groups[ep.group].append(ep)

    return ApiExplorerResponse(
        success=True,
        total=len(ENDPOINTS),
        groups=[EndpointGroup(name=name, endpoints=eps) for name, eps in groups.items()],
        endpoints=ENDPOINTS,
    )
