"""
Server-Sent Events (SSE) service for task progress streaming — Issue #212.

Implements:
- subscribe_task: async generator yielding SSE-formatted event strings
- publish_progress: emit a progress event for a task
- publish_completion: emit a completion event for a task

SSE wire format per spec:
    data: <json>\n\n

Built by AINative Dev Team
Refs #212
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SSEService:
    """
    In-process SSE broker using per-task asyncio.Queue instances.

    Producers call publish_progress / publish_completion to enqueue events.
    Consumers iterate subscribe_task to receive them as SSE-formatted strings.

    One queue per task_id; queues are created lazily on first access.
    """

    def __init__(self) -> None:
        # Maps task_id -> asyncio.Queue of pre-serialised SSE event strings
        self._queues: Dict[str, asyncio.Queue] = {}

    def _get_or_create_queue(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._queues:
            self._queues[task_id] = asyncio.Queue()
        return self._queues[task_id]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _format_sse(data: Dict[str, Any]) -> str:
        """Encode a dict as an SSE data line."""
        return f"data: {json.dumps(data)}\n\n"

    async def publish_progress(
        self,
        task_id: str,
        step: int,
        total_steps: int,
        message: str,
    ) -> None:
        """
        Publish a progress update for a task.

        Args:
            task_id: Unique task identifier.
            step: Current step number (1-based).
            total_steps: Total number of steps in the task.
            message: Human-readable progress description.
        """
        event_data: Dict[str, Any] = {
            "task_id": task_id,
            "step": step,
            "total_steps": total_steps,
            "message": message,
            "timestamp": self._now_iso(),
        }
        queue = self._get_or_create_queue(task_id)
        await queue.put(self._format_sse(event_data))
        logger.debug(
            "SSE progress published task=%s step=%d/%d",
            task_id, step, total_steps,
        )

    async def publish_completion(
        self,
        task_id: str,
        result: Dict[str, Any],
    ) -> None:
        """
        Publish a final completion event for a task.

        Args:
            task_id: Unique task identifier.
            result: Task output/result payload.
        """
        event_data: Dict[str, Any] = {
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "timestamp": self._now_iso(),
        }
        queue = self._get_or_create_queue(task_id)
        await queue.put(self._format_sse(event_data))
        logger.debug("SSE completion published task=%s", task_id)

    async def subscribe_task(
        self,
        task_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE-formatted event strings for a task.

        Yields one string per queued event in FIFO order.
        Each yielded string has the form: ``data: <json>\\n\\n``

        Args:
            task_id: The task to subscribe to.

        Yields:
            SSE-formatted event strings.
        """
        queue = self._get_or_create_queue(task_id)
        while True:
            try:
                event = queue.get_nowait()
                yield event
            except asyncio.QueueEmpty:
                break


# Singleton
_sse_service: Optional[SSEService] = None


def get_sse_service() -> SSEService:
    """Return the singleton SSEService instance."""
    global _sse_service
    if _sse_service is None:
        _sse_service = SSEService()
    return _sse_service
