"""Bug condition exploration test for api_explorer.py.

This test is EXPECTED TO FAIL on unfixed code. Failure confirms the bug exists:
- `EndpointMeta` is not importable from `core.schemas` (ImportError)
- `ENDPOINTS` entries are plain dicts, not typed Pydantic instances (AssertionError)
- The `/api-explorer/endpoints` route has no `response_model` declared (AssertionError)

Validates: Requirements 1.1, 1.2, 1.3
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from api_explorer import ENDPOINTS


class TestEndpointMetaImportable:
    """Requirement 1.1 / 1.2: EndpointMeta must be importable from core.schemas.

    On unfixed code this raises ImportError — confirming the bug.
    """

    def test_endpoint_meta_importable_from_core_schemas(self):
        """EndpointMeta should be importable from core.schemas.

        EXPECTED TO FAIL on unfixed code with ImportError.
        Validates: Requirements 1.2
        """
        # This import will raise ImportError on unfixed code because
        # EndpointMeta does not yet exist in core.schemas.
        from core.schemas import EndpointMeta  # noqa: F401


class TestEndpointsAreTypedInstances:
    """Requirement 1.3: ENDPOINTS entries must be typed Pydantic instances, not plain dicts.

    On unfixed code every entry is a plain dict — asserting isinstance fails.
    """

    @given(endpoint=st.sampled_from(ENDPOINTS))
    @settings(max_examples=17)
    def test_each_endpoint_is_endpoint_meta_instance(self, endpoint):
        """Every entry in ENDPOINTS must be an EndpointMeta instance.

        EXPECTED TO FAIL on unfixed code with ImportError (EndpointMeta missing)
        or AssertionError (entries are plain dicts).
        Validates: Requirements 1.3
        """
        from core.schemas import EndpointMeta

        assert isinstance(endpoint, EndpointMeta), (
            f"Expected EndpointMeta instance, got {type(endpoint).__name__}: {endpoint!r}\n"
            "This confirms the bug: ENDPOINTS entries are plain dicts, not typed Pydantic models."
        )


class TestRouteHasResponseModel:
    """Requirement 1.1: The /api-explorer/endpoints route must declare a response_model.

    On unfixed code the route has no response_model — asserting it fails.
    """

    def test_get_endpoints_route_has_response_model(self):
        """The GET /api-explorer/endpoints route must have a response_model declared.

        EXPECTED TO FAIL on unfixed code with AssertionError because the route
        decorator uses @router.get("/endpoints") with no response_model kwarg.
        Validates: Requirements 1.1
        """
        from api_explorer import router

        # Find the route registered at /endpoints (stored with prefix as /api-explorer/endpoints)
        endpoints_route = None
        for route in router.routes:
            if hasattr(route, "path") and route.path.endswith("/endpoints"):
                endpoints_route = route
                break

        assert endpoints_route is not None, (
            "Route /endpoints not found on the api_explorer router."
        )

        # On unfixed code, response_model is None — this assertion will fail.
        assert endpoints_route.response_model is not None, (
            f"Route GET /endpoints has no response_model (got {endpoints_route.response_model!r}).\n"
            "This confirms the bug: the route returns an untyped dict with no Pydantic validation."
        )
