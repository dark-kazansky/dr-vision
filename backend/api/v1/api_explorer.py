"""
API Explorer router — returns metadata for all endpoints.

Used to render the interactive API explorer UI on the frontend.

GET /api-explorer/endpoints
"""

from fastapi import APIRouter
from core.schemas import EndpointGroup, ApiExplorerResponse

# Import endpoint metadata from the service modules
from api_explorer.services.system import ENDPOINTS as SYSTEM_ENDPOINTS
from api_explorer.services.ocr import ENDPOINTS as OCR_ENDPOINTS
from api_explorer.services.classification import ENDPOINTS as CLASSIFICATION_ENDPOINTS
from api_explorer.services.extraction import ENDPOINTS as EXTRACTION_ENDPOINTS
from api_explorer.services.splitting import ENDPOINTS as SPLITTING_ENDPOINTS
from api_explorer.services.workflow import ENDPOINTS as WORKFLOW_ENDPOINTS
from api_explorer.services.jobs import ENDPOINTS as JOBS_ENDPOINTS
from api_explorer.services.saved_files import ENDPOINTS as SAVED_FILES_ENDPOINTS

router = APIRouter(prefix="/api-explorer", tags=["API Explorer"])

# Ordered list of all endpoints
ENDPOINTS = (
    SYSTEM_ENDPOINTS
    + OCR_ENDPOINTS
    + CLASSIFICATION_ENDPOINTS
    + EXTRACTION_ENDPOINTS
    + SPLITTING_ENDPOINTS
    + WORKFLOW_ENDPOINTS
    + JOBS_ENDPOINTS
    + SAVED_FILES_ENDPOINTS
)


@router.get("/endpoints", response_model=ApiExplorerResponse)
async def get_endpoints() -> ApiExplorerResponse:
    """Return metadata for all API endpoints to power the API Explorer UI."""
    groups: dict = {}
    for ep in ENDPOINTS:
        groups.setdefault(ep.group, []).append(ep)

    return ApiExplorerResponse(
        success=True,
        total=len(ENDPOINTS),
        groups=[EndpointGroup(name=name, endpoints=eps) for name, eps in groups.items()],
        endpoints=ENDPOINTS,
    )
