"""
HTTP client used by every service to talk to its peers.

The client owns its httpx.AsyncClient so the caller does not have to
manage connection pooling. Errors are wrapped so logs always identify
which downstream service misbehaved.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx


class ServiceUnavailableError(Exception):
    """Raised when a downstream service is unreachable (connection error)."""

    def __init__(self, service_name: str, base_url: str) -> None:
        self.service_name = service_name
        self.base_url = base_url
        super().__init__(f"{service_name} is unreachable at {base_url}")


class DownstreamServiceError(Exception):
    """Raised when a downstream service returns an HTTP 4xx/5xx."""

    def __init__(self, service_name: str, status_code: int, response_text: str) -> None:
        self.service_name = service_name
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(
            f"{service_name} returned HTTP {status_code}: {response_text}"
        )


class ServiceClient:
    """Async HTTP client wrapping a single downstream service."""

    def __init__(self, *, service_name: str, base_url: str, timeout: float = 60.0) -> None:
        self.service_name = service_name
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        client = self._ensure_client()
        try:
            response = await client.request(method, path, **kwargs)
        except (httpx.ConnectError, httpx.ReadError):
            raise ServiceUnavailableError(self.service_name, self.base_url)
        except httpx.RequestError as e:
            raise ServiceUnavailableError(self.service_name, self.base_url) from e
        if response.status_code >= 400:
            raise DownstreamServiceError(
                self.service_name, response.status_code, response.text
            )
        return response

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
