"""
Tests for ZeroDBClient mock-mode behavior.

Closes #345 (and subsumes #328): in mock mode the client must service
CRUD operations from an in-memory store and NEVER issue HTTP requests.
These tests run against the real `ZeroDBClient` class (not the
`MockZeroDBClient` fixture) to verify that a credential-less production
boot can still service requests without 404s.

Refs #345 #328
Built by AINative Dev Team
"""
import os
from typing import Any, Dict

import httpx
import pytest

from app.services.zerodb_client import ZeroDBClient


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> ZeroDBClient:
    """Instantiate ZeroDBClient with no credentials so it enters mock mode."""
    monkeypatch.delenv("ZERODB_API_KEY", raising=False)
    monkeypatch.delenv("ZERODB_PROJECT_ID", raising=False)
    client = ZeroDBClient(api_key=None, project_id=None)
    assert client._mock_mode is True, "test precondition: client must be in mock mode"
    return client


@pytest.fixture
def http_blocker(monkeypatch: pytest.MonkeyPatch) -> Dict[str, int]:
    """Replace httpx.AsyncClient with a spy that fails loudly on any use."""
    counter = {"calls": 0}

    class _BlockingAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            counter["calls"] += 1

        async def __aenter__(self) -> "_BlockingAsyncClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def _boom(self, *args: Any, **kwargs: Any) -> Any:
            raise AssertionError(
                "mock-mode client must not perform HTTP requests"
            )

        get = _boom
        post = _boom
        put = _boom
        delete = _boom
        patch = _boom
        request = _boom

    monkeypatch.setattr(httpx, "AsyncClient", _BlockingAsyncClient)
    return counter


class TestMockModeDetection:
    def test_no_credentials_enters_mock_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ZERODB_API_KEY", raising=False)
        monkeypatch.delenv("ZERODB_PROJECT_ID", raising=False)
        client = ZeroDBClient(api_key=None, project_id=None)
        assert client._mock_mode is True

    def test_with_credentials_is_not_mock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ZERODB_API_KEY", raising=False)
        monkeypatch.delenv("ZERODB_PROJECT_ID", raising=False)
        client = ZeroDBClient(api_key="real_key", project_id="proj_real")
        assert client._mock_mode is False


class TestInsertRowMockMode:
    @pytest.mark.asyncio
    async def test_insert_row_does_not_call_http(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        result = await mock_client.insert_row("agents", {"name": "A"})
        assert http_blocker["calls"] == 0
        assert result.get("success") is True
        assert "row_id" in result

    @pytest.mark.asyncio
    async def test_insert_row_returns_inserted_data(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        result = await mock_client.insert_row(
            "agents", {"project_id": "proj_1", "name": "Agent X"}
        )
        assert result["row_data"]["project_id"] == "proj_1"
        assert result["row_data"]["name"] == "Agent X"

    @pytest.mark.asyncio
    async def test_insert_row_generates_unique_ids(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        a = await mock_client.insert_row("agents", {"name": "A"})
        b = await mock_client.insert_row("agents", {"name": "B"})
        assert a["row_id"] != b["row_id"]


class TestQueryRowsMockMode:
    @pytest.mark.asyncio
    async def test_query_empty_table_returns_empty(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        result = await mock_client.query_rows("nothing_here", filter={})
        assert http_blocker["calls"] == 0
        assert result["rows"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_query_round_trips_inserted_rows(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        await mock_client.insert_row("agents", {"project_id": "p1", "name": "A"})
        await mock_client.insert_row("agents", {"project_id": "p1", "name": "B"})
        await mock_client.insert_row("agents", {"project_id": "p2", "name": "C"})

        result = await mock_client.query_rows(
            "agents", filter={"project_id": {"$eq": "p1"}}
        )
        assert result["total"] == 2
        assert all(r["project_id"] == "p1" for r in result["rows"])

    @pytest.mark.asyncio
    async def test_marketplace_listings_query_returns_empty_not_404(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        """Regression for #328: marketplace browse must not 500 in mock mode."""
        result = await mock_client.query_rows("marketplace_listings", filter={})
        assert result["rows"] == []
        assert result["total"] == 0


class TestGetRowMockMode:
    @pytest.mark.asyncio
    async def test_get_row_returns_inserted_row(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        inserted = await mock_client.insert_row("agents", {"name": "A"})
        row_id = inserted["row_id"]

        fetched = await mock_client.get_row("agents", str(row_id))
        assert fetched["row_data"]["name"] == "A"
        assert http_blocker["calls"] == 0

    @pytest.mark.asyncio
    async def test_get_row_missing_raises(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        with pytest.raises(Exception):
            await mock_client.get_row("agents", "nonexistent-id")


class TestUpdateRowMockMode:
    @pytest.mark.asyncio
    async def test_update_row_persists_changes(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        inserted = await mock_client.insert_row("agents", {"name": "Old"})
        row_id = str(inserted["row_id"])

        updated = await mock_client.update_row(
            "agents", row_id, {"name": "New", "status": "active"}
        )
        assert updated["row_data"]["name"] == "New"

        fetched = await mock_client.get_row("agents", row_id)
        assert fetched["row_data"]["name"] == "New"
        assert http_blocker["calls"] == 0


class TestDeleteRowMockMode:
    @pytest.mark.asyncio
    async def test_delete_row_removes_row(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        inserted = await mock_client.insert_row("agents", {"name": "A"})
        row_id = str(inserted["row_id"])

        result = await mock_client.delete_row("agents", row_id)
        assert result.get("success") is True

        query = await mock_client.query_rows("agents", filter={})
        assert query["total"] == 0
        assert http_blocker["calls"] == 0


class TestListRowsMockMode:
    @pytest.mark.asyncio
    async def test_list_rows_paginates(
        self, mock_client: ZeroDBClient, http_blocker: Dict[str, int]
    ) -> None:
        for i in range(5):
            await mock_client.insert_row("items", {"index": i})

        result = await mock_client.list_rows("items", skip=0, limit=2)
        assert len(result["rows"]) == 2
        assert result["total"] == 5
        assert http_blocker["calls"] == 0


class TestRealModeStillHitsHttp:
    """Guard: supplying credentials MUST still issue HTTP calls."""

    @pytest.mark.asyncio
    async def test_insert_row_with_credentials_calls_http(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ZERODB_API_KEY", raising=False)
        monkeypatch.delenv("ZERODB_PROJECT_ID", raising=False)
        client = ZeroDBClient(api_key="real_key", project_id="proj_real")
        assert client._mock_mode is False

        called = {"count": 0}

        class _FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> Dict[str, Any]:
                return {"success": True, "row_id": "real-1"}

        class _FakeAsyncClient:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def __aenter__(self) -> "_FakeAsyncClient":
                return self

            async def __aexit__(self, *args: Any) -> None:
                return None

            async def post(self, *args: Any, **kwargs: Any) -> _FakeResponse:
                called["count"] += 1
                return _FakeResponse()

        monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

        result = await client.insert_row("agents", {"name": "A"})
        assert called["count"] == 1
        assert result["row_id"] == "real-1"
