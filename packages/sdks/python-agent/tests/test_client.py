"""
Tests for ainative_agent.client.AsyncHTTPClient.

Describes: AsyncHTTPClient authentication, request dispatch, and error mapping.

Built by AINative Dev Team.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from ainative_agent.client import AsyncHTTPClient
from ainative_agent.errors import (
    AINativeError,
    AuthError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from tests.conftest import TEST_API_KEY, TEST_BASE_URL, make_response


# ---------------------------------------------------------------------------
# describe: AsyncHTTPClient initialisation
# ---------------------------------------------------------------------------


class DescribeInit:
    def it_raises_when_neither_api_key_nor_jwt_provided(self):
        with pytest.raises(ValueError, match="api_key or jwt"):
            AsyncHTTPClient()

    def it_accepts_api_key_only(self, mock_httpx_client):
        client = AsyncHTTPClient(api_key="sk-abc", httpx_client=mock_httpx_client)
        assert client._api_key == "sk-abc"

    def it_accepts_jwt_only(self, mock_httpx_client):
        client = AsyncHTTPClient(jwt="eyJ.abc", httpx_client=mock_httpx_client)
        assert client._jwt == "eyJ.abc"

    def it_stores_custom_base_url(self, mock_httpx_client):
        client = AsyncHTTPClient(
            api_key="k",
            base_url="https://custom.example.com",
            httpx_client=mock_httpx_client,
        )
        assert client._base_url == "https://custom.example.com"

    def it_strips_trailing_slash_from_base_url(self, mock_httpx_client):
        client = AsyncHTTPClient(
            api_key="k",
            base_url="https://custom.example.com/",
            httpx_client=mock_httpx_client,
        )
        assert client._base_url == "https://custom.example.com"


# ---------------------------------------------------------------------------
# describe: AsyncHTTPClient._auth_headers
# ---------------------------------------------------------------------------


class DescribeAuthHeaders:
    def it_uses_bearer_with_api_key(self, mock_httpx_client):
        client = AsyncHTTPClient(api_key="sk-test", httpx_client=mock_httpx_client)
        headers = client._auth_headers()
        assert headers["Authorization"] == "Bearer sk-test"

    def it_prefers_jwt_over_api_key_when_both_present(self, mock_httpx_client):
        client = AsyncHTTPClient(
            api_key="sk-test", jwt="eyJ.tok", httpx_client=mock_httpx_client
        )
        headers = client._auth_headers()
        assert headers["Authorization"] == "Bearer eyJ.tok"


# ---------------------------------------------------------------------------
# describe: AsyncHTTPClient request dispatch
# ---------------------------------------------------------------------------


class DescribeRequest:
    async def it_sends_get_request_with_correct_url(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body={"ok": True})
        result = await http_client.get("/agents")
        call_args = mock_httpx_client.request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert "/agents" in call_args.kwargs["url"]

    async def it_sends_post_request_with_json_body(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body={"id": "a1"})
        await http_client.post("/agents", json={"name": "bot"})
        call_args = mock_httpx_client.request.call_args
        assert call_args.kwargs["method"] == "POST"
        assert call_args.kwargs["json"] == {"name": "bot"}

    async def it_injects_auth_header_on_every_request(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body={})
        await http_client.get("/agents")
        headers = mock_httpx_client.request.call_args.kwargs["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")

    async def it_returns_none_when_response_has_no_content(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(204, content=b"")
        result = await http_client.delete("/agents/a1")
        assert result is None

    async def it_returns_bytes_for_binary_response(self, http_client, mock_httpx_client):
        raw_bytes = b"binary data"
        mock_httpx_client.request.return_value = make_response(200, content=raw_bytes)
        result = await http_client.get("/files/f1/download")
        assert result == raw_bytes


# ---------------------------------------------------------------------------
# describe: AsyncHTTPClient error mapping
# ---------------------------------------------------------------------------


class DescribeErrorMapping:
    async def it_raises_auth_error_on_401(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(401, text_body="Unauthorized")
        with pytest.raises(AuthError) as exc_info:
            await http_client.get("/agents")
        assert exc_info.value.status_code == 401

    async def it_raises_auth_error_on_403(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(403, text_body="Forbidden")
        with pytest.raises(AuthError) as exc_info:
            await http_client.get("/agents")
        assert exc_info.value.status_code == 403

    async def it_raises_not_found_error_on_404(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(404, text_body="Not found")
        with pytest.raises(NotFoundError) as exc_info:
            await http_client.get("/agents/missing")
        assert exc_info.value.status_code == 404

    async def it_raises_validation_error_on_422(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(422, text_body="Invalid")
        with pytest.raises(ValidationError) as exc_info:
            await http_client.post("/agents", json={})
        assert exc_info.value.status_code == 422

    async def it_raises_rate_limit_error_on_429(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(429, text_body="Too many requests")
        with pytest.raises(RateLimitError) as exc_info:
            await http_client.get("/agents")
        assert exc_info.value.status_code == 429

    async def it_raises_server_error_on_500(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(500, text_body="Internal error")
        with pytest.raises(ServerError) as exc_info:
            await http_client.get("/agents")
        assert exc_info.value.status_code == 500

    async def it_raises_server_error_on_503(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(503, text_body="Service unavailable")
        with pytest.raises(ServerError) as exc_info:
            await http_client.get("/agents")
        assert exc_info.value.status_code == 503

    async def it_raises_base_ainative_error_on_other_4xx(self, http_client, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(409, text_body="Conflict")
        with pytest.raises(AINativeError) as exc_info:
            await http_client.get("/agents")
        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# describe: AsyncHTTPClient context manager
# ---------------------------------------------------------------------------


class DescribeContextManager:
    async def it_can_be_used_as_async_context_manager(self, mock_httpx_client):
        async with AsyncHTTPClient(api_key="k", httpx_client=mock_httpx_client) as client:
            assert client is not None
