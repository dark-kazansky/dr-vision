"""Preservation property tests for api_explorer.py.

These tests encode the baseline facts about the current ENDPOINTS list and the
GET /api-explorer/endpoints route.  They are expected to PASS on unfixed code
(establishing a regression baseline) and must continue to pass after the fix.

The helper `_get` / `_getattr` utilities make field access work with BOTH plain
dicts (current unfixed code) and Pydantic model instances (after the fix).

Validates: Requirements 3.1, 3.2, 3.3
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from fastapi import FastAPI
import httpx

from api_explorer import ENDPOINTS, router as explorer_router


# ---------------------------------------------------------------------------
# Baseline constants
# ---------------------------------------------------------------------------

EXPECTED_IDS = {
    "health",
    "models_check",
    "tier_config",
    "list_saved_files",
    "parse",
    "classify",
    "classify_text",
    "extract",
    "extract_text",
    "generate_schema",
    "split_sections",
    "workflow_execute",
    "condition_evaluate",
    "job_status",
    "job_result",
    "raw_ocr",
    "parsed_docx",
    "submit_job",
    "list_jobs",
    "get_job",
    "cancel_job",
}

EXPECTED_GROUPS = {
    "Hệ thống",
    "OCR / Parse",
    "Phân loại",
    "Trích xuất dữ liệu",
    "Tách tài liệu",
    "Workflow",
    "Background Jobs",
    "File đã lưu",
    "Journey Jobs",
}

REQUIRED_ENDPOINT_KEYS = {"id", "group", "method", "path", "summary", "description", "fields"}
REQUIRED_FIELD_KEYS = {"name", "type", "required"}
VALID_METHODS = {"GET", "POST"}


# ---------------------------------------------------------------------------
# Compatibility helper — works with both dict and Pydantic model instances
# ---------------------------------------------------------------------------

def _get(obj, key):
    """Return obj[key] for dicts or getattr(obj, key) for Pydantic models."""
    if isinstance(obj, dict):
        return obj[key]
    return getattr(obj, key)


def _has_key(obj, key):
    """Return True if obj has the given key (dict) or attribute (Pydantic model)."""
    if isinstance(obj, dict):
        return key in obj
    return hasattr(obj, key)


# ---------------------------------------------------------------------------
# Property-based tests — structural invariants over ENDPOINTS
# ---------------------------------------------------------------------------

class TestEndpointsStructuralInvariants:
    """Property tests asserting structural invariants over every ENDPOINTS entry.

    Validates: Requirements 3.1, 3.2
    """

    @given(ep=st.sampled_from(ENDPOINTS))
    @settings(max_examples=21)
    def test_endpoint_has_all_required_keys(self, ep):
        """Every endpoint entry must have all required keys/attributes.

        Validates: Requirements 3.2
        """
        for key in REQUIRED_ENDPOINT_KEYS:
            assert _has_key(ep, key), (
                f"Endpoint entry is missing required key '{key}': {ep!r}"
            )

    @given(ep=st.sampled_from(ENDPOINTS))
    @settings(max_examples=21)
    def test_endpoint_id_is_non_empty_string(self, ep):
        """Every endpoint id must be a non-empty string.

        Validates: Requirements 3.2
        """
        ep_id = _get(ep, "id")
        assert isinstance(ep_id, str), f"id must be str, got {type(ep_id)}: {ep!r}"
        assert ep_id, f"id must be non-empty: {ep!r}"

    @given(ep=st.sampled_from(ENDPOINTS))
    @settings(max_examples=21)
    def test_endpoint_method_is_get_or_post(self, ep):
        """Every endpoint method must be 'GET' or 'POST'.

        Validates: Requirements 3.2
        """
        method = _get(ep, "method")
        assert method in VALID_METHODS, (
            f"method must be GET or POST, got {method!r}: {ep!r}"
        )

    @given(ep=st.sampled_from(ENDPOINTS))
    @settings(max_examples=21)
    def test_endpoint_fields_is_a_list(self, ep):
        """Every endpoint fields value must be a list.

        Validates: Requirements 3.2
        """
        fields = _get(ep, "fields")
        assert isinstance(fields, list), (
            f"fields must be a list, got {type(fields)}: {ep!r}"
        )

    @given(ep=st.sampled_from(ENDPOINTS))
    @settings(max_examples=21)
    def test_each_field_has_required_keys(self, ep):
        """Every field dict/object inside an endpoint must have name, type, required.

        Validates: Requirements 3.2
        """
        fields = _get(ep, "fields")
        for field in fields:
            for key in REQUIRED_FIELD_KEYS:
                assert _has_key(field, key), (
                    f"Field in endpoint '{_get(ep, 'id')}' is missing key '{key}': {field!r}"
                )

    @given(ep=st.sampled_from(ENDPOINTS))
    @settings(max_examples=21)
    def test_endpoint_group_is_known(self, ep):
        """Every endpoint group must be one of the 8 expected group names.

        Validates: Requirements 3.1, 3.2
        """
        group = _get(ep, "group")
        assert group in EXPECTED_GROUPS, (
            f"Unexpected group '{group}' in endpoint '{_get(ep, 'id')}'. "
            f"Expected one of: {EXPECTED_GROUPS}"
        )

    @given(ep=st.sampled_from(ENDPOINTS))
    @settings(max_examples=21)
    def test_endpoint_id_is_in_expected_set(self, ep):
        """Every endpoint id must be in the expected set of 17 IDs.

        Validates: Requirements 3.1, 3.2
        """
        ep_id = _get(ep, "id")
        assert ep_id in EXPECTED_IDS, (
            f"Unexpected endpoint id '{ep_id}'. Expected one of: {EXPECTED_IDS}"
        )


class TestEndpointsCount:
    """Tests asserting the exact count of ENDPOINTS entries.

    Validates: Requirements 3.1
    """

    def test_endpoints_has_exactly_17_entries(self):
        """ENDPOINTS must contain exactly 21 entries.

        Validates: Requirements 3.1
        """
        assert len(ENDPOINTS) == 21, (
            f"Expected 21 endpoints, got {len(ENDPOINTS)}"
        )

    def test_all_expected_ids_are_present(self):
        """All 17 expected endpoint IDs must be present in ENDPOINTS.

        Validates: Requirements 3.1
        """
        actual_ids = {_get(ep, "id") for ep in ENDPOINTS}
        assert actual_ids == EXPECTED_IDS, (
            f"Missing IDs: {EXPECTED_IDS - actual_ids}\n"
            f"Extra IDs: {actual_ids - EXPECTED_IDS}"
        )

    def test_all_expected_groups_are_present(self):
        """All 8 expected group names must be present in ENDPOINTS.

        Validates: Requirements 3.1
        """
        actual_groups = {_get(ep, "group") for ep in ENDPOINTS}
        assert actual_groups == EXPECTED_GROUPS, (
            f"Missing groups: {EXPECTED_GROUPS - actual_groups}\n"
            f"Extra groups: {actual_groups - EXPECTED_GROUPS}"
        )


# ---------------------------------------------------------------------------
# Integration tests — GET /api-explorer/endpoints via httpx.AsyncClient
# ---------------------------------------------------------------------------

@pytest.fixture
def explorer_app():
    """Minimal FastAPI app with only the api_explorer router mounted."""
    app = FastAPI()
    app.include_router(explorer_router)
    return app


@pytest.fixture
def explorer_client(explorer_app):
    """httpx.AsyncClient wired to the explorer_app via ASGITransport."""
    transport = httpx.ASGITransport(app=explorer_app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


class TestGetEndpointsIntegration:
    """Integration tests for GET /api-explorer/endpoints.

    Validates: Requirements 3.1, 3.2, 3.3
    """

    @pytest.mark.asyncio
    async def test_returns_success_true(self, explorer_client):
        """GET /api-explorer/endpoints must return success == True.

        Validates: Requirements 3.3
        """
        async with explorer_client as client:
            resp = await client.get("/api-explorer/endpoints")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

    @pytest.mark.asyncio
    async def test_total_is_17(self, explorer_client):
        """GET /api-explorer/endpoints must return total == 21.

        Validates: Requirements 3.1
        """
        async with explorer_client as client:
            resp = await client.get("/api-explorer/endpoints")

        body = resp.json()
        assert body["total"] == 21, (
            f"Expected total=21, got {body['total']}"
        )

    @pytest.mark.asyncio
    async def test_groups_count_is_8(self, explorer_client):
        """GET /api-explorer/endpoints must return exactly 9 groups.

        Validates: Requirements 3.1
        """
        async with explorer_client as client:
            resp = await client.get("/api-explorer/endpoints")

        body = resp.json()
        assert len(body["groups"]) == 9, (
            f"Expected 9 groups, got {len(body['groups'])}: "
            f"{[g['name'] for g in body['groups']]}"
        )

    @pytest.mark.asyncio
    async def test_group_names_match_expected_set(self, explorer_client):
        """GET /api-explorer/endpoints must return exactly the 8 expected group names.

        Validates: Requirements 3.1, 3.2
        """
        async with explorer_client as client:
            resp = await client.get("/api-explorer/endpoints")

        body = resp.json()
        actual_group_names = {g["name"] for g in body["groups"]}
        assert actual_group_names == EXPECTED_GROUPS, (
            f"Missing groups: {EXPECTED_GROUPS - actual_group_names}\n"
            f"Extra groups: {actual_group_names - EXPECTED_GROUPS}"
        )

    @pytest.mark.asyncio
    async def test_all_17_ids_present_in_endpoints(self, explorer_client):
        """GET /api-explorer/endpoints must include all 21 expected endpoint IDs.

        Validates: Requirements 3.1, 3.2
        """
        async with explorer_client as client:
            resp = await client.get("/api-explorer/endpoints")

        body = resp.json()
        actual_ids = {ep["id"] for ep in body["endpoints"]}
        assert actual_ids == EXPECTED_IDS, (
            f"Missing IDs: {EXPECTED_IDS - actual_ids}\n"
            f"Extra IDs: {actual_ids - EXPECTED_IDS}"
        )

    @pytest.mark.asyncio
    async def test_endpoints_list_length_is_17(self, explorer_client):
        """GET /api-explorer/endpoints must return a flat endpoints list of length 21.

        Validates: Requirements 3.1
        """
        async with explorer_client as client:
            resp = await client.get("/api-explorer/endpoints")

        body = resp.json()
        assert len(body["endpoints"]) == 21, (
            f"Expected 21 endpoints in flat list, got {len(body['endpoints'])}"
        )

    @pytest.mark.asyncio
    async def test_each_endpoint_in_response_has_required_fields(self, explorer_client):
        """Every endpoint object in the response must have all required fields.

        Validates: Requirements 3.2
        """
        async with explorer_client as client:
            resp = await client.get("/api-explorer/endpoints")

        body = resp.json()
        for ep in body["endpoints"]:
            for key in REQUIRED_ENDPOINT_KEYS:
                assert key in ep, (
                    f"Endpoint '{ep.get('id', '?')}' missing key '{key}' in response"
                )

    @pytest.mark.asyncio
    async def test_response_has_all_top_level_keys(self, explorer_client):
        """GET /api-explorer/endpoints response must have success, total, groups, endpoints.

        Validates: Requirements 3.1, 3.3
        """
        async with explorer_client as client:
            resp = await client.get("/api-explorer/endpoints")

        body = resp.json()
        for key in ("success", "total", "groups", "endpoints"):
            assert key in body, f"Response missing top-level key '{key}'"
