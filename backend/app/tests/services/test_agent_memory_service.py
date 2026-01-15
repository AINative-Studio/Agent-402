"""
Unit tests for AgentMemoryService.

Tests service layer methods directly with mocked ZeroDB client
to ensure proper data handling and error cases.

Coverage focuses on:
- Memory ID generation
- Store memory method with various inputs
- Error handling for ZeroDB failures
- Semantic search functionality
- Namespace statistics
- Delete memory functionality
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import httpx
from app.services.agent_memory_service import AgentMemoryService
from app.core.errors import APIError


class TestAgentMemoryService:
    """Unit tests for AgentMemoryService."""

    @pytest.fixture
    def mock_zerodb_client(self):
        """Create a mock ZeroDB client."""
        client = Mock()
        client.insert_row = AsyncMock()
        client.query_rows = AsyncMock()
        client.delete_row = AsyncMock()
        client.embed_and_store = AsyncMock()
        client.semantic_search = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_zerodb_client):
        """Create service with mocked client."""
        return AgentMemoryService(client=mock_zerodb_client)

    def test_generate_memory_id(self, service):
        """Test memory ID generation format."""
        memory_id = service.generate_memory_id()

        assert memory_id.startswith("mem_")
        assert len(memory_id) == 20  # mem_ (4) + 16 hex chars

        # Generate multiple IDs to ensure uniqueness
        ids = [service.generate_memory_id() for _ in range(10)]
        assert len(set(ids)) == 10  # All unique

    @pytest.mark.asyncio
    async def test_store_memory_success(self, service, mock_zerodb_client):
        """Test successful memory storage."""
        mock_zerodb_client.insert_row.return_value = {"id": "row_123"}
        mock_zerodb_client.embed_and_store.return_value = {
            "vector_ids": ["vec_123"]
        }

        result = await service.store_memory(
            project_id="proj_test",
            agent_id="agent_001",
            run_id="run_001",
            memory_type="decision",
            content="Test decision",
            namespace="default",
            metadata={"priority": "high"}
        )

        assert result["memory_id"].startswith("mem_")
        assert result["agent_id"] == "agent_001"
        assert result["run_id"] == "run_001"
        assert result["memory_type"] == "decision"
        assert result["content"] == "Test decision"
        assert result["namespace"] == "default"
        assert result["metadata"]["priority"] == "high"
        assert result["embedding_id"] == "vec_123"
        assert "timestamp" in result

        # Verify insert was called
        mock_zerodb_client.insert_row.assert_called_once()
        call_args = mock_zerodb_client.insert_row.call_args[0]
        assert call_args[0] == "agent_memory"
        assert call_args[1]["agent_id"] == "agent_001"
        assert call_args[1]["namespace"] == "default"

    @pytest.mark.asyncio
    async def test_store_memory_embedding_failure_non_fatal(self, service, mock_zerodb_client):
        """Test that embedding failure doesn't fail storage."""
        mock_zerodb_client.insert_row.return_value = {"id": "row_123"}
        mock_zerodb_client.embed_and_store.side_effect = Exception("Embedding service down")

        result = await service.store_memory(
            project_id="proj_test",
            agent_id="agent_001",
            run_id="run_001",
            memory_type="decision",
            content="Test decision"
        )

        # Should succeed even though embedding failed
        assert result["memory_id"].startswith("mem_")
        assert result["embedding_id"] is None

    @pytest.mark.asyncio
    async def test_store_memory_zerodb_error(self, service, mock_zerodb_client):
        """Test error handling when ZeroDB insert fails."""
        mock_zerodb_client.insert_row.side_effect = httpx.HTTPStatusError(
            "Bad Gateway",
            request=Mock(),
            response=Mock(status_code=502)
        )

        with pytest.raises(APIError) as exc_info:
            await service.store_memory(
                project_id="proj_test",
                agent_id="agent_001",
                run_id="run_001",
                memory_type="decision",
                content="Test decision"
            )

        assert exc_info.value.status_code == 502
        assert exc_info.value.error_code == "ZERODB_ERROR"

    @pytest.mark.asyncio
    async def test_store_memory_generic_error(self, service, mock_zerodb_client):
        """Test generic error handling."""
        mock_zerodb_client.insert_row.side_effect = Exception("Unknown error")

        with pytest.raises(APIError) as exc_info:
            await service.store_memory(
                project_id="proj_test",
                agent_id="agent_001",
                run_id="run_001",
                memory_type="decision",
                content="Test decision"
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.error_code == "MEMORY_STORE_ERROR"

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, service, mock_zerodb_client):
        """Test get_memory when memory doesn't exist."""
        mock_zerodb_client.query_rows.return_value = {"rows": []}

        result = await service.get_memory("proj_test", "mem_nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_memory_zerodb_error(self, service, mock_zerodb_client):
        """Test get_memory with ZeroDB error."""
        mock_zerodb_client.query_rows.side_effect = httpx.HTTPStatusError(
            "Bad Gateway",
            request=Mock(),
            response=Mock(status_code=502)
        )

        with pytest.raises(APIError) as exc_info:
            await service.get_memory("proj_test", "mem_123")

        assert exc_info.value.status_code == 502
        assert exc_info.value.error_code == "ZERODB_ERROR"

    @pytest.mark.asyncio
    async def test_get_memory_generic_error_returns_none(self, service, mock_zerodb_client):
        """Test get_memory with generic error returns None."""
        mock_zerodb_client.query_rows.side_effect = Exception("Unknown error")

        result = await service.get_memory("proj_test", "mem_123")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_memories_zerodb_error(self, service, mock_zerodb_client):
        """Test list_memories with ZeroDB error."""
        mock_zerodb_client.query_rows.side_effect = httpx.HTTPStatusError(
            "Bad Gateway",
            request=Mock(),
            response=Mock(status_code=502)
        )

        with pytest.raises(APIError) as exc_info:
            await service.list_memories("proj_test")

        assert exc_info.value.status_code == 502
        assert exc_info.value.error_code == "ZERODB_ERROR"

    @pytest.mark.asyncio
    async def test_list_memories_generic_error_returns_empty(self, service, mock_zerodb_client):
        """Test list_memories with generic error returns empty list."""
        mock_zerodb_client.query_rows.side_effect = Exception("Unknown error")

        memories, total, filters = await service.list_memories("proj_test")

        assert memories == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, service, mock_zerodb_client):
        """Test successful memory deletion."""
        mock_zerodb_client.query_rows.return_value = {
            "rows": [{"id": "row_123", "memory_id": "mem_123"}]
        }
        mock_zerodb_client.delete_row.return_value = True

        result = await service.delete_memory("proj_test", "mem_123")

        assert result is True
        mock_zerodb_client.delete_row.assert_called_once_with("agent_memory", "row_123")

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, service, mock_zerodb_client):
        """Test deleting non-existent memory."""
        mock_zerodb_client.query_rows.return_value = {"rows": []}

        result = await service.delete_memory("proj_test", "mem_nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_memory_no_row_id(self, service, mock_zerodb_client):
        """Test delete when row has no ID field."""
        mock_zerodb_client.query_rows.return_value = {
            "rows": [{"memory_id": "mem_123"}]  # Missing id/row_id
        }

        result = await service.delete_memory("proj_test", "mem_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_memory_zerodb_error(self, service, mock_zerodb_client):
        """Test delete with ZeroDB error."""
        mock_zerodb_client.query_rows.side_effect = httpx.HTTPStatusError(
            "Bad Gateway",
            request=Mock(),
            response=Mock(status_code=502)
        )

        with pytest.raises(APIError) as exc_info:
            await service.delete_memory("proj_test", "mem_123")

        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_delete_memory_404_returns_false(self, service, mock_zerodb_client):
        """Test delete with 404 returns False."""
        mock_zerodb_client.query_rows.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=Mock(),
            response=Mock(status_code=404)
        )

        result = await service.delete_memory("proj_test", "mem_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_memory_generic_error(self, service, mock_zerodb_client):
        """Test delete with generic error."""
        mock_zerodb_client.query_rows.side_effect = Exception("Unknown error")

        result = await service.delete_memory("proj_test", "mem_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_namespace_stats_success(self, service, mock_zerodb_client):
        """Test namespace statistics retrieval."""
        mock_zerodb_client.query_rows.return_value = {
            "rows": [
                {"agent_id": "agent_001", "memory_type": "decision"},
                {"agent_id": "agent_001", "memory_type": "context"},
                {"agent_id": "agent_002", "memory_type": "decision"}
            ]
        }

        stats = await service.get_namespace_stats("proj_test", "default")

        assert stats["project_id"] == "proj_test"
        assert stats["namespace"] == "default"
        assert stats["memory_count"] == 3
        assert set(stats["agents"]) == {"agent_001", "agent_002"}
        assert set(stats["memory_types"]) == {"decision", "context"}

    @pytest.mark.asyncio
    async def test_get_namespace_stats_empty(self, service, mock_zerodb_client):
        """Test namespace statistics with no memories."""
        mock_zerodb_client.query_rows.return_value = {"rows": []}

        stats = await service.get_namespace_stats("proj_test", "default")

        assert stats["memory_count"] == 0
        assert stats["agents"] == []
        assert stats["memory_types"] == []

    @pytest.mark.asyncio
    async def test_get_namespace_stats_error(self, service, mock_zerodb_client):
        """Test namespace statistics with error."""
        mock_zerodb_client.query_rows.side_effect = Exception("Error")

        stats = await service.get_namespace_stats("proj_test", "default")

        assert stats["memory_count"] == 0

    @pytest.mark.asyncio
    async def test_search_memories_success(self, service, mock_zerodb_client):
        """Test semantic search over memories."""
        mock_zerodb_client.semantic_search.return_value = {
            "matches": [
                {
                    "metadata": {
                        "memory_id": "mem_123",
                        "project_id": "proj_test"
                    },
                    "score": 0.95
                }
            ]
        }
        mock_zerodb_client.query_rows.return_value = {
            "rows": [{
                "memory_id": "mem_123",
                "agent_id": "agent_001",
                "run_id": "run_001",
                "memory_type": "decision",
                "content": "Test content",
                "metadata": {},
                "namespace": "default",
                "created_at": "2026-01-15T00:00:00Z",
                "project_id": "proj_test"
            }]
        }

        results = await service.search_memories(
            "proj_test",
            "test query",
            namespace="default",
            top_k=5
        )

        assert len(results) == 1
        assert results[0]["memory_id"] == "mem_123"
        assert results[0]["similarity_score"] == 0.95

    @pytest.mark.asyncio
    async def test_search_memories_wrong_project(self, service, mock_zerodb_client):
        """Test semantic search filters by project."""
        mock_zerodb_client.semantic_search.return_value = {
            "matches": [
                {
                    "metadata": {
                        "memory_id": "mem_123",
                        "project_id": "other_project"  # Different project
                    },
                    "score": 0.95
                }
            ]
        }

        results = await service.search_memories("proj_test", "test query")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_memories_error(self, service, mock_zerodb_client):
        """Test semantic search with error."""
        mock_zerodb_client.semantic_search.side_effect = Exception("Search error")

        results = await service.search_memories("proj_test", "test query")

        assert results == []

    def test_row_to_memory_record(self, service):
        """Test row to memory record conversion."""
        row = {
            "memory_id": "mem_123",
            "agent_id": "agent_001",
            "run_id": "run_001",
            "memory_type": "decision",
            "content": "Test content",
            "metadata": {"key": "value"},
            "namespace": "custom",
            "created_at": "2026-01-15T00:00:00Z",
            "project_id": "proj_test",
            "embedding_id": "vec_123"
        }

        record = service._row_to_memory_record(row)

        assert record["memory_id"] == "mem_123"
        assert record["agent_id"] == "agent_001"
        assert record["namespace"] == "custom"
        assert record["metadata"]["key"] == "value"
        assert record["timestamp"] == "2026-01-15T00:00:00Z"

    def test_row_to_memory_record_defaults(self, service):
        """Test row to memory record with missing fields."""
        row = {
            "memory_id": "mem_123",
            "agent_id": "agent_001",
            "run_id": "run_001",
            "memory_type": "decision",
            "content": "Test content",
            "created_at": "2026-01-15T00:00:00Z",
            "project_id": "proj_test"
        }

        record = service._row_to_memory_record(row)

        assert record["namespace"] == "default"
        assert record["metadata"] == {}
        assert record["embedding_id"] is None
