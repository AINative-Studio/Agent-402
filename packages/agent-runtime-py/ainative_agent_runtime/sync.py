"""
ainative-agent-runtime — SyncManager (Python)
Built by AINative Dev Team
Refs #247

Periodically pushes local changes to cloud storage.
Conflict resolution: last-write-wins by created_at timestamp.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional


class SyncManager:
    """
    Background sync manager that pushes local changes to cloud storage.

    Args:
        local_storage: A LocalStorageAdapter instance.
        cloud_storage: A StorageAdapter instance (cloud).
        sync_interval: Milliseconds between sync cycles (default: 30000).
    """

    def __init__(
        self,
        local_storage: Any,
        cloud_storage: Any,
        sync_interval: int = 30000,
    ) -> None:
        self._local = local_storage
        self._cloud = cloud_storage
        self.sync_interval = sync_interval
        self.is_running = False
        self._task: Optional[asyncio.Task] = None  # type: ignore[type-arg]

    # ─── start_sync ───────────────────────────────────────────────────────────

    async def start_sync(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.ensure_future(self._sync_loop())

    async def _sync_loop(self) -> None:
        interval_sec = self.sync_interval / 1000
        while self.is_running:
            await asyncio.sleep(interval_sec)
            if self.is_running:
                await self.force_push()

    # ─── stop_sync ────────────────────────────────────────────────────────────

    async def stop_sync(self) -> None:
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    # ─── force_push ───────────────────────────────────────────────────────────

    async def force_push(self) -> None:
        """Push all pending local changes to cloud. Mark each synced on success."""
        pending = await self._local.get_pending_changes()
        if not pending:
            return

        synced_ids = []
        for change in pending:
            try:
                if change["type"] == "memory":
                    await self._cloud.store_memory(
                        change.get("content", ""),
                        change.get("metadata", {}),
                    )
                elif change["type"] == "record" and change.get("table"):
                    await self._cloud.store_record(
                        change["table"],
                        change.get("data", {}),
                    )
                synced_ids.append(change["id"])
            except Exception:
                # Leave failed items in queue for next sync attempt
                pass

        if synced_ids:
            await self._local.mark_synced(synced_ids)

    # ─── get_queue_size ───────────────────────────────────────────────────────

    async def get_queue_size(self) -> int:
        return await self._local.get_unsynced_count()
