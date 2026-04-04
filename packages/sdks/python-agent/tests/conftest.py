"""
Shared fixtures for ainative-agent test suite.

Built by AINative Dev Team.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from ainative_agent import AINativeSDK
from ainative_agent.client import AsyncHTTPClient

TEST_API_KEY = "sk-test-key-abc123"
TEST_BASE_URL = "https://api.ainative.studio/api/v1"


# ---------------------------------------------------------------------------
# Low-level mock HTTP client fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_httpx_client():
    """
    Returns a MagicMock that masquerades as an httpx.AsyncClient.
    Callers configure mock_httpx_client.request.return_value as needed.
    """
    client = MagicMock(spec=httpx.AsyncClient)
    client.request = AsyncMock()
    return client


def make_response(
    status_code: int = 200,
    json_body: Any = None,
    text_body: str = "",
    content: bytes | None = None,
) -> httpx.Response:
    """
    Build a minimal httpx.Response for unit-test use.
    """
    if content is not None:
        raw_content = content
    elif json_body is not None:
        raw_content = json.dumps(json_body).encode()
        text_body = json.dumps(json_body)
    else:
        raw_content = text_body.encode()

    return httpx.Response(
        status_code=status_code,
        content=raw_content,
        headers={"content-type": "application/json"} if json_body is not None else {},
        request=httpx.Request("GET", TEST_BASE_URL),
    )


@pytest.fixture
def http_client(mock_httpx_client: MagicMock) -> AsyncHTTPClient:
    """
    An AsyncHTTPClient that uses the mock httpx client.
    """
    return AsyncHTTPClient(
        api_key=TEST_API_KEY,
        base_url=TEST_BASE_URL,
        httpx_client=mock_httpx_client,
    )


@pytest.fixture
def sdk(mock_httpx_client: MagicMock) -> AINativeSDK:
    """
    A fully-wired AINativeSDK backed by the mock httpx client.
    """
    return AINativeSDK(
        api_key=TEST_API_KEY,
        base_url=TEST_BASE_URL,
        _http_client=mock_httpx_client,
    )
