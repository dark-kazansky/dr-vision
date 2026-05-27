"""
API aggregator router for Dr.Vision.

Collects all v1 sub-routers into a single router that is registered
on the FastAPI app in server.py.

All endpoint paths are mounted WITHOUT a /v1 prefix to maintain
backward compatibility with existing frontend integrations.
"""

from fastapi import APIRouter

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
)

router = APIRouter()

# Register all v1 routers — no prefix added to preserve existing paths
router.include_router(jobs.router)
router.include_router(system.router)
router.include_router(saved_files.router)
router.include_router(parse.router)
router.include_router(classify.router)
router.include_router(extract.router)
router.include_router(split.router)
router.include_router(workflow.router)
router.include_router(api_explorer.router)
router.include_router(providers.router)

# Public Workflow Execution API (v1) — additive, does not affect existing routes
router.include_router(public_workflows.router)

# Banking Data Mining API
router.include_router(banking.router)

# Journey Job Manager API (v1)
router.include_router(journey_jobs.router)

# Execution State API (v1) — feat-007
router.include_router(execution_states.router)

# Uploads API (v1) — feat-012
router.include_router(uploads.router)

# Data Store API (v1) — feat-013
router.include_router(data_store.router)

