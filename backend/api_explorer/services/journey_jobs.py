"""
API Explorer service metadata for the 'Journey Jobs' group.
Contains 4 endpoints: submit_job, list_jobs, get_job, cancel_job.
"""

from typing import List
from core.schemas import EndpointField, EndpointMeta

ENDPOINTS: List[EndpointMeta] = [
    EndpointMeta(
        id="submit_job",
        group="Journey Jobs",
        method="POST",
        path="/api/v1/jobs",
        summary="Submit workflow execution job",
        description="Submit a new workflow execution job to the queue. Returns immediately with a job_id for polling.",
        fields=[
            EndpointField(name="file", type="file", required=True, label="File", placeholder="Upload file to process"),
            EndpointField(name="workflow", type="json", required=True, label="Workflow JSON", placeholder='{"steps": [{"type": "parse", "tier": "Normal"}]}'),
            EndpointField(name="workflow_id", type="text", required=False, label="Workflow ID", placeholder="Optional saved workflow ID"),
            EndpointField(name="workflow_name", type="text", required=False, label="Workflow Name", placeholder="Optional name"),
            EndpointField(name="max_retries", type="number", required=False, label="Max Retries", placeholder="3"),
        ],
    ),
    EndpointMeta(
        id="list_jobs",
        group="Journey Jobs",
        method="GET",
        path="/api/v1/jobs",
        summary="List all jobs",
        description="List jobs with optional filtering by status and workflow_id. Supports pagination.",
        fields=[
            EndpointField(name="status", type="text", required=False, label="Status Filter", placeholder="queued|running|completed|failed|cancelled"),
            EndpointField(name="workflow_id", type="text", required=False, label="Workflow ID", placeholder="Filter by workflow"),
            EndpointField(name="limit", type="number", required=False, label="Limit", placeholder="50"),
            EndpointField(name="offset", type="number", required=False, label="Offset", placeholder="0"),
        ],
    ),
    EndpointMeta(
        id="get_job",
        group="Journey Jobs",
        method="GET",
        path="/api/v1/jobs/{job_id}",
        summary="Get job details",
        description="Get full job details including per-node progress, retry counts, and results.",
        fields=[
            EndpointField(name="job_id", type="text", required=True, label="Job ID", placeholder="abc123...", path_param=True),
        ],
    ),
    EndpointMeta(
        id="cancel_job",
        group="Journey Jobs",
        method="POST",
        path="/api/v1/jobs/{job_id}/cancel",
        summary="Cancel a job",
        description="Cancel a queued or running job. Running jobs will stop after the current node completes.",
        fields=[
            EndpointField(name="job_id", type="text", required=True, label="Job ID", placeholder="abc123...", path_param=True),
        ],
    ),
]
