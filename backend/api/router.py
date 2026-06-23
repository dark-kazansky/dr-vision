"""
API aggregator router for Doc Intelligence.

Collects all v1 sub-routers into a single router that is registered
on the FastAPI app in server.py.

All endpoint paths are mounted WITHOUT a /v1 prefix to maintain
backward compatibility with existing frontend integrations.

All routes in this router require authentication (Bearer token).
Public routes (/health, /auth/*, /docs) are registered separately.
"""

from fastapi import APIRouter, Depends

from auth.dependencies import get_current_user
from api.v1 import (
    parse,
    classify,
    extract,
    split,
    system,
    workflow,
    jobs,
    journey_jobs,
    saved_files,
    api_explorer,
    public_workflows,
    providers,
    banking,
    execution_states,
    uploads,
    data_store,
    observability,
    layout,
    documents,
    durable,
    table,
    postprocess,
    workflow_export,
    batch,
    templates,
    compare,
)

# ─── Authenticated Router ─────────────────────────────────────────────────────
# All routes under this router require a valid Bearer token.

auth_router = APIRouter(dependencies=[Depends(get_current_user)])

# Core OCR pipeline
auth_router.include_router(parse.router)
auth_router.include_router(classify.router)
auth_router.include_router(extract.router)
auth_router.include_router(split.router)

# Workflow & execution
auth_router.include_router(workflow.router)
auth_router.include_router(public_workflows.router)
auth_router.include_router(durable.router)
auth_router.include_router(workflow_export.router)
auth_router.include_router(execution_states.router)

# Jobs & batch processing
auth_router.include_router(jobs.router)
auth_router.include_router(documents.router)
auth_router.include_router(batch.router)

# Document intelligence
auth_router.include_router(layout.router)
auth_router.include_router(table.router)
auth_router.include_router(postprocess.router)
auth_router.include_router(templates.router)
auth_router.include_router(compare.router)

# Data & storage
auth_router.include_router(banking.router)
auth_router.include_router(uploads.router)
auth_router.include_router(data_store.router)
auth_router.include_router(saved_files.router)

# System & observability
auth_router.include_router(system.router)
auth_router.include_router(providers.router)
auth_router.include_router(api_explorer.router)
auth_router.include_router(observability.router)

# ─── Public Router ────────────────────────────────────────────────────────────
# Aggregates authenticated + non-authenticated routes.

router = APIRouter()
router.include_router(auth_router)

# Journey jobs use API Key auth (webhooks) — mounted separately
router.include_router(journey_jobs.router)
