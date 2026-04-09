"""
ainative-agent-runtime — SyncManager tests (Python)
Built by AINative Dev Team
Refs #247

RED phase: All tests written before implementation.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


def make_local():
    local = MagicMock()
    local.get_unsynced_count = AsyncMock(return_value=0)
    local.get_pending_changes = AsyncMock(return_value=[])
    local.mark_synced = AsyncMock(return_value=None)
    return local


def make_cloud():
    cloud = MagicMock()
    cloud.store_memory = AsyncMock(return_value={"id": "cloud-mem-1"})
    cloud.store_record = AsyncMock(return_value={"id": "cloud-rec-1"})
    cloud.recall_memory = AsyncMock(return_value=[])
    cloud.query_records = AsyncMock(return_value=[])
    return cloud


class DescribeSyncManager:
    """Tests for the SyncManager class."""

    # ─── Constructor ──────────────────────────────────────────────────────────

    class DescribeConstructor:
        def it_creates_sync_manager_with_local_and_cloud(self):
            from ainative_agent_runtime.sync import SyncManager
            manager = SyncManager(
                local_storage=make_local(),
                cloud_storage=make_cloud(),
                sync_interval=5000,
            )
            assert manager is not None

        def it_defaults_sync_interval_to_30000(self):
            from ainative_agent_runtime.sync import SyncManager
            manager = SyncManager(
                local_storage=make_local(),
                cloud_storage=make_cloud(),
            )
            assert manager.sync_interval == 30000

    # ─── start_sync / stop_sync ───────────────────────────────────────────────

    class DescribeStartStopSync:
        @pytest.mark.asyncio
        async def it_sets_is_running_true_after_start(self):
            from ainative_agent_runtime.sync import SyncManager
            manager = SyncManager(local_storage=make_local(), cloud_storage=make_cloud(), sync_interval=5000)
            await manager.start_sync()
            assert manager.is_running is True
            await manager.stop_sync()

        @pytest.mark.asyncio
        async def it_sets_is_running_false_after_stop(self):
            from ainative_agent_runtime.sync import SyncManager
            manager = SyncManager(local_storage=make_local(), cloud_storage=make_cloud(), sync_interval=5000)
            await manager.start_sync()
            await manager.stop_sync()
            assert manager.is_running is False

        @pytest.mark.asyncio
        async def it_does_not_raise_when_start_called_twice(self):
            from ainative_agent_runtime.sync import SyncManager
            manager = SyncManager(local_storage=make_local(), cloud_storage=make_cloud(), sync_interval=5000)
            await manager.start_sync()
            await manager.start_sync()  # should not raise
            await manager.stop_sync()

    # ─── force_push ───────────────────────────────────────────────────────────

    class DescribeForcePush:
        @pytest.mark.asyncio
        async def it_pushes_pending_memory_items_to_cloud(self):
            from ainative_agent_runtime.sync import SyncManager
            local = make_local()
            cloud = make_cloud()
            local.get_pending_changes = AsyncMock(return_value=[
                {"id": "mem-1", "type": "memory", "content": "Hello world",
                 "metadata": {}, "created_at": "2026-01-01T00:00:00Z"}
            ])
            manager = SyncManager(local_storage=local, cloud_storage=cloud, sync_interval=5000)
            await manager.force_push()
            cloud.store_memory.assert_called_once_with("Hello world", {})

        @pytest.mark.asyncio
        async def it_pushes_pending_record_items_to_cloud(self):
            from ainative_agent_runtime.sync import SyncManager
            local = make_local()
            cloud = make_cloud()
            local.get_pending_changes = AsyncMock(return_value=[
                {"id": "rec-1", "type": "record", "table": "agents",
                 "data": {"name": "Bot"}, "created_at": "2026-01-01T00:00:00Z"}
            ])
            manager = SyncManager(local_storage=local, cloud_storage=cloud, sync_interval=5000)
            await manager.force_push()
            cloud.store_record.assert_called_once_with("agents", {"name": "Bot"})

        @pytest.mark.asyncio
        async def it_marks_items_synced_after_successful_push(self):
            from ainative_agent_runtime.sync import SyncManager
            local = make_local()
            cloud = make_cloud()
            local.get_pending_changes = AsyncMock(return_value=[
                {"id": "mem-1", "type": "memory", "content": "test",
                 "metadata": {}, "created_at": "2026-01-01T00:00:00Z"}
            ])
            manager = SyncManager(local_storage=local, cloud_storage=cloud, sync_interval=5000)
            await manager.force_push()
            local.mark_synced.assert_called_once_with(["mem-1"])

        @pytest.mark.asyncio
        async def it_does_nothing_when_no_pending_changes(self):
            from ainative_agent_runtime.sync import SyncManager
            local = make_local()
            cloud = make_cloud()
            local.get_pending_changes = AsyncMock(return_value=[])
            manager = SyncManager(local_storage=local, cloud_storage=cloud, sync_interval=5000)
            await manager.force_push()
            cloud.store_memory.assert_not_called()
            cloud.store_record.assert_not_called()

    # ─── get_queue_size ───────────────────────────────────────────────────────

    class DescribeGetQueueSize:
        @pytest.mark.asyncio
        async def it_returns_zero_when_no_pending_changes(self):
            from ainative_agent_runtime.sync import SyncManager
            local = make_local()
            local.get_unsynced_count = AsyncMock(return_value=0)
            manager = SyncManager(local_storage=local, cloud_storage=make_cloud(), sync_interval=5000)
            size = await manager.get_queue_size()
            assert size == 0

        @pytest.mark.asyncio
        async def it_returns_count_from_local_storage(self):
            from ainative_agent_runtime.sync import SyncManager
            local = make_local()
            local.get_unsynced_count = AsyncMock(return_value=7)
            manager = SyncManager(local_storage=local, cloud_storage=make_cloud(), sync_interval=5000)
            size = await manager.get_queue_size()
            assert size == 7
