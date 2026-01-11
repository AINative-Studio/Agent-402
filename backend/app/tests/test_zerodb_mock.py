"""
Tests for MockZeroDBClient fixture.
Verifies that the mock client works correctly and provides proper test isolation.
"""
import pytest
from app.tests.fixtures.zerodb_mock import MockZeroDBClient


class TestMockZeroDBClient:
    """Test suite for MockZeroDBClient."""

    @pytest.mark.asyncio
    async def test_insert_row_success(self, mock_zerodb_client):
        """Test that insert_row creates a row and returns success."""
        row_data = {
            "project_id": "proj_123",
            "name": "Test Agent",
            "status": "active"
        }

        result = await mock_zerodb_client.insert_row("agents", row_data)

        assert result["success"] is True
        assert "row_id" in result
        assert result["row_data"]["project_id"] == "proj_123"
        assert result["row_data"]["name"] == "Test Agent"

    @pytest.mark.asyncio
    async def test_query_rows_empty_table(self, mock_zerodb_client):
        """Test querying an empty table returns empty results."""
        result = await mock_zerodb_client.query_rows("nonexistent", filter={})

        assert result["rows"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_query_rows_with_filter(self, mock_zerodb_client):
        """Test querying rows with MongoDB-style filter."""
        # Insert test data
        await mock_zerodb_client.insert_row("agents", {"project_id": "proj_1", "name": "Agent A"})
        await mock_zerodb_client.insert_row("agents", {"project_id": "proj_1", "name": "Agent B"})
        await mock_zerodb_client.insert_row("agents", {"project_id": "proj_2", "name": "Agent C"})

        # Query for project_id = proj_1
        result = await mock_zerodb_client.query_rows(
            "agents",
            filter={"project_id": {"$eq": "proj_1"}}
        )

        assert result["total"] == 2
        assert len(result["rows"]) == 2
        assert all(row["project_id"] == "proj_1" for row in result["rows"])

    @pytest.mark.asyncio
    async def test_query_rows_pagination(self, mock_zerodb_client):
        """Test pagination works correctly."""
        # Insert 5 rows
        for i in range(5):
            await mock_zerodb_client.insert_row("items", {"index": i})

        # Get first 2 items
        result = await mock_zerodb_client.query_rows("items", filter={}, limit=2, skip=0)
        assert len(result["rows"]) == 2
        assert result["total"] == 5

        # Get next 2 items
        result = await mock_zerodb_client.query_rows("items", filter={}, limit=2, skip=2)
        assert len(result["rows"]) == 2
        assert result["total"] == 5

    @pytest.mark.asyncio
    async def test_update_row_success(self, mock_zerodb_client):
        """Test updating a row."""
        # Insert a row
        insert_result = await mock_zerodb_client.insert_row("agents", {"name": "Old Name"})
        row_id = insert_result["row_id"]

        # Update the row
        updated_result = await mock_zerodb_client.update_row(
            "agents",
            str(row_id),
            {"name": "New Name", "status": "updated"}
        )

        assert updated_result["success"] is True
        assert updated_result["row_data"]["name"] == "New Name"
        assert updated_result["row_data"]["status"] == "updated"

        # Verify update persisted
        query_result = await mock_zerodb_client.query_rows("agents", filter={})
        assert query_result["rows"][0]["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_delete_row_success(self, mock_zerodb_client):
        """Test deleting a row."""
        # Insert a row
        insert_result = await mock_zerodb_client.insert_row("agents", {"name": "To Delete"})
        row_id = insert_result["row_id"]

        # Delete the row
        delete_result = await mock_zerodb_client.delete_row("agents", str(row_id))
        assert delete_result["success"] is True

        # Verify deletion
        query_result = await mock_zerodb_client.query_rows("agents", filter={})
        assert query_result["total"] == 0

    @pytest.mark.asyncio
    async def test_embed_and_store(self, mock_zerodb_client):
        """Test embedding and storing vectors."""
        texts = ["Hello world", "Test document"]
        result = await mock_zerodb_client.embed_and_store(
            texts=texts,
            namespace="test_namespace"
        )

        assert result["success"] is True
        assert len(result["vector_ids"]) == 2
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_semantic_search(self, mock_zerodb_client):
        """Test semantic search returns results."""
        # Store some vectors first
        await mock_zerodb_client.embed_and_store(
            texts=["Document 1", "Document 2"],
            namespace="search_test"
        )

        # Search
        result = await mock_zerodb_client.semantic_search(
            query="test query",
            namespace="search_test",
            top_k=5
        )

        assert "matches" in result
        assert len(result["matches"]) <= 2  # We only stored 2

    def test_reset_clears_data(self, mock_zerodb_client):
        """Test that reset() clears all data and history."""
        # The fixture already calls reset, but let's verify explicitly
        mock_zerodb_client.data["test"] = [{"id": 1}]
        mock_zerodb_client.call_history.append({"method": "test"})

        mock_zerodb_client.reset()

        assert len(mock_zerodb_client.data) == 0
        assert len(mock_zerodb_client.call_history) == 0

    @pytest.mark.asyncio
    async def test_call_history_tracking(self, mock_zerodb_client):
        """Test that method calls are tracked in history."""
        await mock_zerodb_client.insert_row("test", {"data": "value"})
        await mock_zerodb_client.query_rows("test", filter={})

        assert mock_zerodb_client.get_call_count("insert_row") == 1
        assert mock_zerodb_client.get_call_count("query_rows") == 1

    @pytest.mark.asyncio
    async def test_filter_operators(self, mock_zerodb_client):
        """Test MongoDB-style filter operators."""
        # Insert test data with risk scores
        await mock_zerodb_client.insert_row("events", {"risk_score": 10})
        await mock_zerodb_client.insert_row("events", {"risk_score": 50})
        await mock_zerodb_client.insert_row("events", {"risk_score": 90})

        # Test $gte operator
        result = await mock_zerodb_client.query_rows(
            "events",
            filter={"risk_score": {"$gte": 50}}
        )
        assert result["total"] == 2

        # Test $lte operator
        result = await mock_zerodb_client.query_rows(
            "events",
            filter={"risk_score": {"$lte": 50}}
        )
        assert result["total"] == 2

        # Test range query
        result = await mock_zerodb_client.query_rows(
            "events",
            filter={"risk_score": {"$gte": 30, "$lte": 70}}
        )
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_data_persistence_within_test(self, mock_zerodb_client):
        """Test that data persists within a single test."""
        # Insert data
        await mock_zerodb_client.insert_row("persist_test", {"value": 1})

        # Query it back
        result = await mock_zerodb_client.query_rows("persist_test", filter={})
        assert result["total"] == 1
        assert result["rows"][0]["value"] == 1

        # Insert more data
        await mock_zerodb_client.insert_row("persist_test", {"value": 2})

        # Verify both rows exist
        result = await mock_zerodb_client.query_rows("persist_test", filter={})
        assert result["total"] == 2


class TestMockIsolation:
    """Test that each test gets a fresh mock client."""

    @pytest.mark.asyncio
    async def test_isolation_first(self, mock_zerodb_client):
        """First test - insert data."""
        await mock_zerodb_client.insert_row("isolation_test", {"test": 1})
        result = await mock_zerodb_client.query_rows("isolation_test", filter={})
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_isolation_second(self, mock_zerodb_client):
        """Second test - should not see data from first test."""
        result = await mock_zerodb_client.query_rows("isolation_test", filter={})
        assert result["total"] == 0  # Fresh mock client, no data
