"""
ainative-agent-runtime — CloudStorageAdapter tests (Python)
Built by AINative Dev Team
Refs #246

RED phase: Written before implementation run.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


def make_client():
    client = MagicMock()
    client.memory = MagicMock()
    client.memory.remember = AsyncMock(return_value={"id": "cloud-mem-1"})
    client.memory.recall = AsyncMock(return_value={
        "memories": [
            {
                "id": "cloud-mem-1",
                "content": "Cloud memory",
                "metadata": {"tag": "cloud"},
                "score": 0.95,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
    })
    return client


class DescribeCloudStorageAdapter:
    """Tests for the CloudStorageAdapter class."""

    class DescribeStoreMemory:
        @pytest.mark.asyncio
        async def it_delegates_to_sdk_and_returns_id(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            client = make_client()
            adapter = CloudStorageAdapter(client=client)
            result = await adapter.store_memory("test content", {"key": "val"})
            assert result["id"] == "cloud-mem-1"
            client.memory.remember.assert_called_once_with(
                "test content",
                namespace="default",
                metadata={"key": "val"},
            )

        @pytest.mark.asyncio
        async def it_uses_configured_namespace(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            client = make_client()
            adapter = CloudStorageAdapter(client=client, namespace="my-ns")
            await adapter.store_memory("hello", {})
            client.memory.remember.assert_called_once_with(
                "hello",
                namespace="my-ns",
                metadata={},
            )

    class DescribeRecallMemory:
        @pytest.mark.asyncio
        async def it_calls_sdk_recall_with_correct_args(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            client = make_client()
            adapter = CloudStorageAdapter(client=client)
            await adapter.recall_memory("search query", 5)
            client.memory.recall.assert_called_once_with(
                "search query",
                namespace="default",
                top_k=5,
            )

        @pytest.mark.asyncio
        async def it_maps_sdk_result_to_memory_entries(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            client = make_client()
            adapter = CloudStorageAdapter(client=client)
            results = await adapter.recall_memory("query", 10)
            assert len(results) == 1
            assert results[0]["id"] == "cloud-mem-1"
            assert results[0]["score"] == 0.95

        @pytest.mark.asyncio
        async def it_defaults_missing_score_to_zero(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            client = make_client()
            client.memory.recall = AsyncMock(return_value={
                "memories": [{"id": "m-2", "content": "No score", "metadata": {}, "created_at": "2026-01-01T00:00:00Z"}]
            })
            adapter = CloudStorageAdapter(client=client)
            results = await adapter.recall_memory("query", 1)
            assert results[0]["score"] == 0.0

    class DescribeStoreRecord:
        @pytest.mark.asyncio
        async def it_returns_a_generated_id(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            client = make_client()
            adapter = CloudStorageAdapter(client=client)
            result = await adapter.store_record("agents", {"name": "Bot"})
            assert result["id"] is not None
            assert isinstance(result["id"], str)

        @pytest.mark.asyncio
        async def it_assigns_unique_ids_to_separate_records(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            client = make_client()
            adapter = CloudStorageAdapter(client=client)
            r1 = await adapter.store_record("tasks", {"a": 1})
            r2 = await adapter.store_record("tasks", {"a": 2})
            assert r1["id"] != r2["id"]

    class DescribeQueryRecords:
        @pytest.mark.asyncio
        async def it_returns_empty_list_for_unknown_table(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            adapter = CloudStorageAdapter(client=make_client())
            results = await adapter.query_records("nonexistent", {})
            assert results == []

        @pytest.mark.asyncio
        async def it_returns_all_records_with_empty_filter(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            adapter = CloudStorageAdapter(client=make_client())
            await adapter.store_record("logs", {"msg": "a"})
            await adapter.store_record("logs", {"msg": "b"})
            results = await adapter.query_records("logs", {})
            assert len(results) == 2

        @pytest.mark.asyncio
        async def it_filters_by_matching_field(self):
            from ainative_agent_runtime.adapters.cloud_storage import CloudStorageAdapter
            adapter = CloudStorageAdapter(client=make_client())
            await adapter.store_record("users", {"role": "admin", "name": "Alice"})
            await adapter.store_record("users", {"role": "viewer", "name": "Bob"})
            results = await adapter.query_records("users", {"role": "admin"})
            assert len(results) == 1
