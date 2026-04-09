"""
ainative-agent-runtime — LocalStorageAdapter (Python)
Built by AINative Dev Team
Refs #247

Pure in-memory storage implementing the StorageAdapter protocol.
SQLite integration is reserved for a future milestone.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _term_overlap_score(query: str, content: str) -> float:
    """Simple term-overlap similarity (mirrors the TS implementation)."""
    q_terms = set(query.lower().split())
    if not q_terms:
        return 0.0
    c_terms = content.lower().split()
    hits = sum(1 for t in c_terms if t in q_terms)
    return hits / len(q_terms)


class LocalStorageAdapter:
    """
    In-process storage adapter backed by Python lists.

    Args:
        db_path: Path to SQLite file or ':memory:' (currently in-memory only).
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._memories: List[Dict[str, Any]] = []
        self._records: List[Dict[str, Any]] = []
        self._closed = False

    # ─── StorageAdapter protocol ──────────────────────────────────────────────

    async def store_memory(
        self,
        content: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, str]:
        record_id = str(uuid.uuid4())
        self._memories.append({
            "id": record_id,
            "content": content,
            "metadata": dict(metadata),
            "synced": False,
            "created_at": _now(),
        })
        return {"id": record_id}

    async def recall_memory(self, query: str, limit: int) -> List[Dict[str, Any]]:
        scored = [
            {
                "id": row["id"],
                "content": row["content"],
                "metadata": row["metadata"],
                "score": _term_overlap_score(query, row["content"]),
                "created_at": row["created_at"],
            }
            for row in self._memories
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    async def store_record(
        self,
        table: str,
        data: Dict[str, Any],
    ) -> Dict[str, str]:
        record_id = str(uuid.uuid4())
        now = _now()
        self._records.append({
            "id": record_id,
            "table_name": table,
            "data": dict(data),
            "synced": False,
            "created_at": now,
            "updated_at": now,
        })
        return {"id": record_id}

    async def query_records(
        self,
        table: str,
        filter_: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        rows = [r for r in self._records if r["table_name"] == table]
        filter_keys = list(filter_.keys())

        def matches(row: Dict[str, Any]) -> bool:
            if not filter_keys:
                return True
            return all(row["data"].get(k) == filter_[k] for k in filter_keys)

        return [
            {
                "id": r["id"],
                "data": r["data"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
            if matches(r)
        ]

    # ─── Sync Queue ───────────────────────────────────────────────────────────

    async def get_unsynced_count(self) -> int:
        mem = sum(1 for m in self._memories if not m["synced"])
        rec = sum(1 for r in self._records if not r["synced"])
        return mem + rec

    async def mark_synced(self, ids: List[str]) -> None:
        id_set = set(ids)
        for row in self._memories:
            if row["id"] in id_set:
                row["synced"] = True
        for row in self._records:
            if row["id"] in id_set:
                row["synced"] = True

    async def get_pending_changes(self) -> List[Dict[str, Any]]:
        changes: List[Dict[str, Any]] = []

        for row in self._memories:
            if not row["synced"]:
                changes.append({
                    "id": row["id"],
                    "type": "memory",
                    "content": row["content"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"],
                })

        for row in self._records:
            if not row["synced"]:
                changes.append({
                    "id": row["id"],
                    "type": "record",
                    "table": row["table_name"],
                    "data": row["data"],
                    "created_at": row["created_at"],
                })

        return changes

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def close(self) -> None:
        self._closed = True
        self._memories.clear()
        self._records.clear()
