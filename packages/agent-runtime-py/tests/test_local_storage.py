"""
ainative-agent-runtime — LocalStorageAdapter tests (Python)
Built by AINative Dev Team
Refs #247

RED phase: All tests written before implementation.
"""

import pytest


class DescribeLocalStorageAdapter:
    """Tests for the LocalStorageAdapter class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
        self.adapter = LocalStorageAdapter(db_path=":memory:")
        yield
        import asyncio
        asyncio.get_event_loop().run_until_complete(self.adapter.close())

    # ─── store_memory ─────────────────────────────────────────────────────────

    class DescribeStoreMemory:
        @pytest.fixture(autouse=True)
        def setup(self, tmp_path):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            self.adapter = LocalStorageAdapter(db_path=":memory:")

        @pytest.mark.asyncio
        async def it_returns_an_id(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            result = await adapter.store_memory("The sky is blue", {})
            assert result["id"] is not None
            assert isinstance(result["id"], str)
            await adapter.close()

        @pytest.mark.asyncio
        async def it_preserves_content(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_memory("Important fact about cats", {})
            recalled = await adapter.recall_memory("cats", 1)
            assert recalled[0]["content"] == "Important fact about cats"
            await adapter.close()

        @pytest.mark.asyncio
        async def it_stores_metadata(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_memory("Memory with metadata", {"tag": "test", "priority": 1})
            recalled = await adapter.recall_memory("metadata", 1)
            assert recalled[0]["metadata"]["tag"] == "test"
            await adapter.close()

        @pytest.mark.asyncio
        async def it_assigns_created_at_timestamp(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_memory("Timestamped memory", {})
            recalled = await adapter.recall_memory("Timestamped", 1)
            assert recalled[0]["created_at"] is not None
            await adapter.close()

    # ─── recall_memory ────────────────────────────────────────────────────────

    class DescribeRecallMemory:
        @pytest.mark.asyncio
        async def it_returns_empty_list_when_no_memories(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            results = await adapter.recall_memory("anything", 5)
            assert results == []
            await adapter.close()

        @pytest.mark.asyncio
        async def it_returns_at_most_limit_results(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_memory("Alpha memory", {})
            await adapter.store_memory("Beta memory", {})
            await adapter.store_memory("Gamma memory", {})
            results = await adapter.recall_memory("memory", 2)
            assert len(results) <= 2
            await adapter.close()

        @pytest.mark.asyncio
        async def it_returns_results_sorted_by_score_descending(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_memory("The quick brown fox", {})
            await adapter.store_memory("A totally unrelated sentence about chairs", {})
            await adapter.store_memory("The fox jumped quickly", {})
            results = await adapter.recall_memory("fox quick", 3)
            for i in range(1, len(results)):
                assert results[i - 1]["score"] >= results[i]["score"]
            await adapter.close()

        @pytest.mark.asyncio
        async def it_returns_complete_memory_entry_shape(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_memory("Complete memory entry", {"key": "value"})
            results = await adapter.recall_memory("complete", 1)
            mem = results[0]
            assert "id" in mem
            assert "content" in mem
            assert "metadata" in mem
            assert "score" in mem
            assert "created_at" in mem
            await adapter.close()

    # ─── store_record ─────────────────────────────────────────────────────────

    class DescribeStoreRecord:
        @pytest.mark.asyncio
        async def it_returns_an_id(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            result = await adapter.store_record("agents", {"name": "Agent-1"})
            assert result["id"] is not None
            await adapter.close()

        @pytest.mark.asyncio
        async def it_assigns_unique_ids(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            r1 = await adapter.store_record("tasks", {"desc": "Task A"})
            r2 = await adapter.store_record("tasks", {"desc": "Task B"})
            assert r1["id"] != r2["id"]
            await adapter.close()

        @pytest.mark.asyncio
        async def it_adds_created_at_and_updated_at(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_record("logs", {"msg": "hello"})
            records = await adapter.query_records("logs", {})
            assert "created_at" in records[0]
            assert "updated_at" in records[0]
            await adapter.close()

    # ─── query_records ────────────────────────────────────────────────────────

    class DescribeQueryRecords:
        @pytest.mark.asyncio
        async def it_returns_all_records_with_empty_filter(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_record("items", {"name": "alpha"})
            await adapter.store_record("items", {"name": "beta"})
            results = await adapter.query_records("items", {})
            assert len(results) == 2
            await adapter.close()

        @pytest.mark.asyncio
        async def it_returns_empty_list_for_unknown_table(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            results = await adapter.query_records("nonexistent", {})
            assert results == []
            await adapter.close()

        @pytest.mark.asyncio
        async def it_filters_by_single_field(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_record("users", {"role": "admin", "name": "Alice"})
            await adapter.store_record("users", {"role": "viewer", "name": "Bob"})
            results = await adapter.query_records("users", {"role": "admin"})
            assert len(results) == 1
            assert results[0]["data"]["role"] == "admin"
            await adapter.close()

    # ─── Sync Queue ───────────────────────────────────────────────────────────

    class DescribeSyncQueue:
        @pytest.mark.asyncio
        async def it_returns_zero_unsynced_count_when_fresh(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            count = await adapter.get_unsynced_count()
            assert count == 0
            await adapter.close()

        @pytest.mark.asyncio
        async def it_increments_unsynced_count_after_store_memory(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_memory("unsynced memory", {})
            count = await adapter.get_unsynced_count()
            assert count == 1
            await adapter.close()

        @pytest.mark.asyncio
        async def it_reduces_unsynced_count_after_mark_synced(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            result = await adapter.store_memory("to sync", {})
            await adapter.mark_synced([result["id"]])
            count = await adapter.get_unsynced_count()
            assert count == 0
            await adapter.close()

        @pytest.mark.asyncio
        async def it_returns_pending_changes(self):
            from ainative_agent_runtime.adapters.local_storage import LocalStorageAdapter
            adapter = LocalStorageAdapter(db_path=":memory:")
            await adapter.store_memory("pending memory", {})
            await adapter.store_record("pending_table", {"data": "pending"})
            pending = await adapter.get_pending_changes()
            assert len(pending) == 2
            await adapter.close()
