"""
ainative-agent-runtime — CloudStorageAdapter (Python)
Built by AINative Dev Team
Refs #246

Wraps the ainative-agent-sdk (Python) for cloud ZeroDB storage.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CloudStorageAdapter:
    """
    Storage adapter wrapping the AINative Agent SDK for cloud operations.

    Args:
        client: An initialized AINative SDK client with a `.memory` module.
        namespace: Optional namespace prefix (default: 'default').
    """

    def __init__(self, client: Any, namespace: str = "default") -> None:
        self._client = client
        self._namespace = namespace
        # Local record store until SDK exposes generic table APIs
        self._records: Dict[str, List[Dict[str, Any]]] = {}

    async def store_memory(
        self,
        content: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, str]:
        result = await self._client.memory.remember(
            content,
            namespace=self._namespace,
            metadata=metadata,
        )
        return {"id": result["id"]}

    async def recall_memory(self, query: str, limit: int) -> List[Dict[str, Any]]:
        result = await self._client.memory.recall(
            query,
            namespace=self._namespace,
            top_k=limit,
        )
        return [
            {
                "id": m["id"],
                "content": m["content"],
                "metadata": m.get("metadata", {}),
                "score": m.get("score", 0.0),
                "created_at": m["created_at"],
            }
            for m in result.get("memories", [])
        ]

    async def store_record(
        self,
        table: str,
        data: Dict[str, Any],
    ) -> Dict[str, str]:
        record_id = f"{table}-{uuid.uuid4()}"
        now = _now()
        record = {**data, "_id": record_id, "_table": table, "_created_at": now}
        self._records.setdefault(table, []).append(record)
        return {"id": record_id}

    async def query_records(
        self,
        table: str,
        filter_: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        rows = self._records.get(table, [])
        filter_keys = list(filter_.keys())

        def matches(row: Dict[str, Any]) -> bool:
            if not filter_keys:
                return True
            return all(row.get(k) == filter_[k] for k in filter_keys)

        return [
            {
                "id": str(r.get("_id", "")),
                "data": r,
                "created_at": str(r.get("_created_at", _now())),
                "updated_at": str(r.get("_created_at", _now())),
            }
            for r in rows
            if matches(r)
        ]
