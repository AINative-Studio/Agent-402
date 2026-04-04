"""
Async HTTP client for ainative-agent SDK.

Uses httpx for all transport. Handles auth, error mapping, and
request/response serialisation.

Built by AINative Dev Team.
"""
from __future__ import annotations

from typing import Any

import httpx

from .errors import (
    AINativeError,
    AuthError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

_DEFAULT_BASE_URL = "https://api.ainative.studio/api/v1"
_DEFAULT_TIMEOUT = 30.0


class AsyncHTTPClient:
    """
    Thin wrapper around httpx.AsyncClient.

    Provides:
    - Auth header injection (API-key or JWT)
    - Status-code → exception mapping
    - JSON request/response helpers
    """

    def __init__(
        self,
        api_key: str | None = None,
        jwt: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        if api_key is None and jwt is None:
            raise ValueError("Either api_key or jwt must be provided.")

        self._api_key = api_key
        self._jwt = jwt
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._own_client = httpx_client is None
        self._client: httpx.AsyncClient = httpx_client or httpx.AsyncClient(
            timeout=self._timeout
        )

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        if self._jwt:
            return {"Authorization": f"Bearer {self._jwt}"}
        return {"Authorization": f"Bearer {self._api_key}"}

    # ------------------------------------------------------------------
    # Low-level request
    # ------------------------------------------------------------------

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """
        Perform an HTTP request and return the parsed JSON body.

        Raises an appropriate AINativeError subclass on non-2xx status.
        """
        url = f"{self._base_url}/{path.lstrip('/')}"
        merged_headers = {**self._auth_headers(), **(headers or {})}

        response = await self._client.request(
            method=method,
            url=url,
            headers=merged_headers,
            json=json,
            params=params,
            content=content,
        )

        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.is_success:
            if response.content:
                try:
                    return response.json()
                except Exception:
                    return response.content
            return None

        body: str = response.text
        status = response.status_code

        if status in (401, 403):
            raise AuthError(
                f"Authentication failed: {body}", status_code=status, response_body=body
            )
        if status == 404:
            raise NotFoundError(
                f"Resource not found: {body}", status_code=status, response_body=body
            )
        if status == 422:
            raise ValidationError(
                f"Validation error: {body}", status_code=status, response_body=body
            )
        if status == 429:
            raise RateLimitError(
                f"Rate limit exceeded: {body}", status_code=status, response_body=body
            )
        if status >= 500:
            raise ServerError(
                f"Server error {status}: {body}", status_code=status, response_body=body
            )
        raise AINativeError(
            f"Unexpected error {status}: {body}", status_code=status, response_body=body
        )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, *, json: Any = None, content: bytes | None = None,
                   headers: dict[str, str] | None = None) -> Any:
        return await self.request("POST", path, json=json, content=content, headers=headers)

    async def put(self, path: str, *, json: Any = None) -> Any:
        return await self.request("PUT", path, json=json)

    async def patch(self, path: str, *, json: Any = None) -> Any:
        return await self.request("PATCH", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self.request("DELETE", path)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncHTTPClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()
