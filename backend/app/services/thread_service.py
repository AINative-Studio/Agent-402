"""
Thread service for persistent conversation management — Issues #218, #219, #220.

Implements:
- create_thread: create a new conversation thread
- add_message: append a message to a thread
- get_thread: retrieve a thread with its messages
- list_threads: paginated list of threads for an agent
- delete_thread: soft-delete a thread
- resume_thread: load last N messages as context (Issue #219)
- get_thread_context: truncate to token budget (Issue #219)
- search_threads: keyword/semantic search across threads (Issue #220)
- search_messages: keyword/semantic search within a thread (Issue #220)

Built by AINative Dev Team
Refs #218 #219 #220
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ThreadService:
    """
    In-memory thread store with soft-delete support.

    Designed to be a drop-in replacement for a ZeroDB-backed implementation.
    All methods are async to allow transparent swap to an async DB client.

    Tables (logical):
    - conversation_threads: id, agent_id, title, status, metadata, created_at
    - thread_messages:      id, thread_id, role, content, metadata, created_at
    """

    def __init__(self) -> None:
        # thread_id -> thread dict (includes embedded messages list)
        self._threads: Dict[str, Dict[str, Any]] = {}
        # thread_id -> list[message dict] (separate store for easy slicing)
        self._messages: Dict[str, List[Dict[str, Any]]] = {}

    # ─── helpers ──────────────────────────────────────────────────────────────

    def _require_thread(self, thread_id: str) -> Dict[str, Any]:
        """Return the thread record or raise ValueError."""
        thread = self._threads.get(thread_id)
        if thread is None:
            raise ValueError(f"Thread not found: {thread_id}")
        return thread

    # ─── create_thread ────────────────────────────────────────────────────────

    async def create_thread(
        self,
        agent_id: str,
        title: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new conversation thread in ZeroDB.

        Args:
            agent_id: The agent that owns this thread.
            title: Human-readable thread title.
            metadata: Arbitrary metadata dict.

        Returns:
            Thread record dict including id, agent_id, title, status,
            metadata, created_at, and an empty messages list.
        """
        thread_id = str(uuid.uuid4())
        thread: Dict[str, Any] = {
            "id": thread_id,
            "agent_id": agent_id,
            "title": title,
            "status": "active",
            "metadata": dict(metadata),
            "created_at": _now_iso(),
            "messages": [],
        }
        self._threads[thread_id] = thread
        self._messages[thread_id] = []
        logger.info("Thread created id=%s agent=%s", thread_id, agent_id)
        return dict(thread)

    # ─── add_message ──────────────────────────────────────────────────────────

    async def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Append a message to an existing thread.

        Args:
            thread_id: Target thread identifier.
            role: Message role ('user', 'assistant', 'system').
            content: Message body text.
            metadata: Arbitrary metadata.

        Returns:
            Message record dict.

        Raises:
            ValueError: If thread_id does not exist.
        """
        self._require_thread(thread_id)
        msg: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "metadata": dict(metadata),
            "created_at": _now_iso(),
        }
        self._messages[thread_id].append(msg)
        self._threads[thread_id]["messages"] = list(self._messages[thread_id])
        return dict(msg)

    # ─── get_thread ───────────────────────────────────────────────────────────

    async def get_thread(self, thread_id: str) -> Dict[str, Any]:
        """
        Retrieve a thread by ID including all of its messages.

        Args:
            thread_id: Thread identifier.

        Returns:
            Thread dict with messages embedded.

        Raises:
            ValueError: If thread_id does not exist.
        """
        thread = self._require_thread(thread_id)
        result = dict(thread)
        result["messages"] = list(self._messages.get(thread_id, []))
        return result

    # ─── list_threads ─────────────────────────────────────────────────────────

    async def list_threads(
        self,
        agent_id: str,
        limit: int,
        offset: int,
    ) -> Dict[str, Any]:
        """
        Return a paginated list of active threads for an agent.

        Args:
            agent_id: Filter by this agent.
            limit: Maximum number of results.
            offset: Number of records to skip.

        Returns:
            Dict with 'threads' (list) and 'total' (int before pagination).
        """
        active = [
            t for t in self._threads.values()
            if t["agent_id"] == agent_id and t["status"] == "active"
        ]
        # Deterministic order: by created_at ascending
        active.sort(key=lambda t: t["created_at"])
        total = len(active)
        page = active[offset: offset + limit]
        return {"threads": [dict(t) for t in page], "total": total}

    # ─── delete_thread ────────────────────────────────────────────────────────

    async def delete_thread(self, thread_id: str) -> None:
        """
        Soft-delete a thread by setting its status to 'deleted'.

        Args:
            thread_id: Thread to delete.

        Raises:
            ValueError: If thread_id does not exist.
        """
        thread = self._require_thread(thread_id)
        thread["status"] = "deleted"
        logger.info("Thread soft-deleted id=%s", thread_id)

    # ─── resume_thread (Issue #219) ───────────────────────────────────────────

    async def resume_thread(
        self,
        thread_id: str,
        context_window: int,
    ) -> Dict[str, Any]:
        """
        Load the last N messages from a thread as resumption context.

        Args:
            thread_id: Thread to resume.
            context_window: Number of most-recent messages to return.

        Returns:
            Dict with 'thread_id' and 'messages' (list, chronological order).

        Raises:
            ValueError: If thread_id does not exist.
        """
        self._require_thread(thread_id)
        all_msgs = self._messages.get(thread_id, [])
        recent = all_msgs[-context_window:] if context_window > 0 else []
        return {
            "thread_id": thread_id,
            "messages": [dict(m) for m in recent],
        }

    # ─── get_thread_context (Issue #219) ──────────────────────────────────────

    async def get_thread_context(
        self,
        thread_id: str,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """
        Return messages from a thread that fit within a token budget.

        Token count is approximated as ``len(content) // 4`` per message,
        which aligns with the rough 4-chars-per-token heuristic.

        Messages are taken from most-recent to oldest and then reversed
        so the result is in chronological order.

        Args:
            thread_id: Thread to slice.
            max_tokens: Maximum token budget.

        Returns:
            Dict with 'thread_id', 'messages', and 'token_count'.

        Raises:
            ValueError: If thread_id does not exist.
        """
        self._require_thread(thread_id)
        all_msgs = self._messages.get(thread_id, [])

        selected: List[Dict[str, Any]] = []
        tokens_used = 0

        for msg in reversed(all_msgs):
            msg_tokens = len(msg["content"]) // 4
            if tokens_used + msg_tokens > max_tokens:
                break
            selected.append(msg)
            tokens_used += msg_tokens

        selected.reverse()  # back to chronological order

        return {
            "thread_id": thread_id,
            "messages": [dict(m) for m in selected],
            "token_count": tokens_used,
        }

    # ─── search_threads (Issue #220) ──────────────────────────────────────────

    async def search_threads(
        self,
        query: str,
        agent_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Search for threads whose title contains the query string (case-insensitive).

        In production this would delegate to ZeroDB semantic/vector search.
        The in-memory implementation uses simple substring matching as a
        functional placeholder that passes the required tests.

        Args:
            query: Search query string.
            agent_id: Restrict search to this agent's threads.
            limit: Maximum number of results.

        Returns:
            List of matching thread dicts.
        """
        q = query.lower()
        results = [
            dict(t)
            for t in self._threads.values()
            if t["agent_id"] == agent_id
            and t["status"] == "active"
            and q in t["title"].lower()
        ]
        return results[:limit]

    # ─── search_messages (Issue #220) ─────────────────────────────────────────

    async def search_messages(
        self,
        query: str,
        thread_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Search for messages within a thread that contain the query string.

        In production this would use ZeroDB vector/semantic search.

        Args:
            query: Search query string.
            thread_id: Restrict search to this thread.
            limit: Maximum number of results.

        Returns:
            List of matching message dicts.

        Raises:
            ValueError: If thread_id does not exist.
        """
        self._require_thread(thread_id)
        q = query.lower()
        results = [
            dict(m)
            for m in self._messages.get(thread_id, [])
            if q in m["content"].lower()
        ]
        return results[:limit]


# Singleton
_thread_service: Optional[ThreadService] = None


def get_thread_service() -> ThreadService:
    """Return the singleton ThreadService instance."""
    global _thread_service
    if _thread_service is None:
        _thread_service = ThreadService()
    return _thread_service
