"""
Tests for the real ZeroDBClient (not the MockZeroDBClient fixture).

Issue #328: In mock mode (no ZERODB_API_KEY / ZERODB_PROJECT_ID set) the
production client must NOT make HTTP calls. Previously query_rows fell
through to the real API at api.ainative.studio, got a 404 on the absent
mock_project tables, and bubbled up as 500s on /marketplace/browse and
/marketplace/search.

Built by AINative Dev Team
Refs #328
"""
from __future__ import annotations

import pytest

from app.services.zerodb_client import ZeroDBClient


def _fresh_mock_client() -> ZeroDBClient:
    """Construct a ZeroDBClient with no credentials (forces mock mode)."""
    return ZeroDBClient(api_key=None, project_id=None)


class DescribeZeroDBClientMockMode:
    """ZeroDBClient must short-circuit HTTP calls when no credentials are set."""

    def it_enters_mock_mode_without_credentials(self, monkeypatch):
        monkeypatch.delenv("ZERODB_API_KEY", raising=False)
        monkeypatch.delenv("ZERODB_PROJECT_ID", raising=False)

        client = ZeroDBClient()
        assert client._mock_mode is True

    @pytest.mark.asyncio
    async def it_query_rows_returns_empty_result_without_http(self, monkeypatch):
        """
        Issue #328 regression — query_rows must return {"rows": [], "total": 0}
        in mock mode instead of calling the real ZeroDB API.
        """
        monkeypatch.delenv("ZERODB_API_KEY", raising=False)
        monkeypatch.delenv("ZERODB_PROJECT_ID", raising=False)

        # Fail hard if httpx is used — mock mode must not make network calls.
        import httpx

        def _boom(*args, **kwargs):
            raise AssertionError("mock mode must not open an httpx.AsyncClient")

        monkeypatch.setattr(httpx, "AsyncClient", _boom)

        client = _fresh_mock_client()
        result = await client.query_rows(
            "marketplace_listings",
            filter={"active": True},
            limit=20,
        )

        assert result == {"rows": [], "total": 0}

    @pytest.mark.asyncio
    async def it_query_rows_empty_result_for_any_table(self, monkeypatch):
        """Short-circuit applies uniformly regardless of table name."""
        monkeypatch.delenv("ZERODB_API_KEY", raising=False)
        monkeypatch.delenv("ZERODB_PROJECT_ID", raising=False)

        client = _fresh_mock_client()

        for table in ("marketplace_listings", "agent_installations", "anything_else"):
            result = await client.query_rows(table, filter={})
            assert result["rows"] == []
            assert result["total"] == 0
