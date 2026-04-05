"""
RED tests for Thread Service — Issues #218, #219, #220.

Covers ThreadService: create_thread, add_message, get_thread,
list_threads, delete_thread, resume_thread, get_thread_context,
search_threads, search_messages.
Built by AINative Dev Team
Refs #218 #219 #220
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any


# ===========================================================================
# Issue #218 — Thread Management
# ===========================================================================

class DescribeThreadServiceCreateThread:
    """Tests for ThreadService.create_thread (Issue #218)."""

    @pytest.mark.asyncio
    async def it_creates_a_thread_and_returns_a_dict_with_id(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        result = await service.create_thread("agent-1", "My Thread", {})
        assert "id" in result
        assert isinstance(result["id"], str)
        assert len(result["id"]) > 0

    @pytest.mark.asyncio
    async def it_stores_agent_id_in_created_thread(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        result = await service.create_thread("agent-2", "Thread A", {})
        assert result["agent_id"] == "agent-2"

    @pytest.mark.asyncio
    async def it_stores_title_in_created_thread(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        result = await service.create_thread("agent-3", "Important Session", {})
        assert result["title"] == "Important Session"

    @pytest.mark.asyncio
    async def it_stores_metadata_in_created_thread(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        metadata = {"project": "fintech-demo", "priority": "high"}
        result = await service.create_thread("agent-4", "Thread B", metadata)
        assert result["metadata"]["project"] == "fintech-demo"

    @pytest.mark.asyncio
    async def it_initializes_thread_with_active_status(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        result = await service.create_thread("agent-5", "Thread C", {})
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def it_includes_created_at_timestamp(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        result = await service.create_thread("agent-6", "Thread D", {})
        assert "created_at" in result
        assert result["created_at"] is not None

    @pytest.mark.asyncio
    async def it_initializes_with_empty_messages_list(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        result = await service.create_thread("agent-7", "Thread E", {})
        assert result.get("messages", []) == []


class DescribeThreadServiceAddMessage:
    """Tests for ThreadService.add_message (Issue #218)."""

    @pytest.mark.asyncio
    async def it_adds_a_message_to_an_existing_thread(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-8", "Thread F", {})
        thread_id = thread["id"]
        result = await service.add_message(thread_id, "user", "Hello!", {})
        assert "id" in result
        assert result["thread_id"] == thread_id

    @pytest.mark.asyncio
    async def it_stores_role_in_message(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-9", "Thread G", {})
        result = await service.add_message(thread["id"], "assistant", "Hi!", {})
        assert result["role"] == "assistant"

    @pytest.mark.asyncio
    async def it_stores_content_in_message(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-10", "Thread H", {})
        result = await service.add_message(thread["id"], "user", "What is 2+2?", {})
        assert result["content"] == "What is 2+2?"

    @pytest.mark.asyncio
    async def it_stores_metadata_in_message(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-11", "Thread I", {})
        meta = {"source": "api"}
        result = await service.add_message(thread["id"], "user", "Hi", meta)
        assert result["metadata"]["source"] == "api"

    @pytest.mark.asyncio
    async def it_raises_for_unknown_thread_id(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        with pytest.raises(ValueError, match="Thread not found"):
            await service.add_message("nonexistent-id", "user", "Hi", {})


class DescribeThreadServiceGetThread:
    """Tests for ThreadService.get_thread (Issue #218)."""

    @pytest.mark.asyncio
    async def it_retrieves_a_thread_by_id(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-12", "Thread J", {})
        fetched = await service.get_thread(thread["id"])
        assert fetched["id"] == thread["id"]
        assert fetched["title"] == "Thread J"

    @pytest.mark.asyncio
    async def it_includes_messages_in_retrieved_thread(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-13", "Thread K", {})
        await service.add_message(thread["id"], "user", "Hello", {})
        fetched = await service.get_thread(thread["id"])
        assert len(fetched["messages"]) == 1
        assert fetched["messages"][0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def it_raises_for_unknown_thread_id(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        with pytest.raises(ValueError, match="Thread not found"):
            await service.get_thread("ghost-id")


class DescribeThreadServiceListThreads:
    """Tests for ThreadService.list_threads (Issue #218)."""

    @pytest.mark.asyncio
    async def it_returns_threads_for_an_agent(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        await service.create_thread("agent-list-1", "T1", {})
        await service.create_thread("agent-list-1", "T2", {})
        result = await service.list_threads("agent-list-1", limit=10, offset=0)
        assert result["total"] == 2
        assert len(result["threads"]) == 2

    @pytest.mark.asyncio
    async def it_respects_limit_parameter(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        for i in range(5):
            await service.create_thread("agent-list-2", f"T{i}", {})
        result = await service.list_threads("agent-list-2", limit=3, offset=0)
        assert len(result["threads"]) == 3

    @pytest.mark.asyncio
    async def it_respects_offset_parameter(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        for i in range(4):
            await service.create_thread("agent-list-3", f"T{i}", {})
        result = await service.list_threads("agent-list-3", limit=10, offset=2)
        assert len(result["threads"]) == 2

    @pytest.mark.asyncio
    async def it_excludes_threads_from_other_agents(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        await service.create_thread("agent-list-4", "Mine", {})
        await service.create_thread("agent-other-x", "Not mine", {})
        result = await service.list_threads("agent-list-4", limit=10, offset=0)
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def it_returns_empty_list_for_agent_with_no_threads(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        result = await service.list_threads("nobody", limit=10, offset=0)
        assert result["threads"] == []
        assert result["total"] == 0


class DescribeThreadServiceDeleteThread:
    """Tests for ThreadService.delete_thread (Issue #218)."""

    @pytest.mark.asyncio
    async def it_soft_deletes_a_thread(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-del", "To Delete", {})
        await service.delete_thread(thread["id"])
        result = await service.list_threads("agent-del", limit=10, offset=0)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def it_marks_thread_status_as_deleted(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-del2", "To Delete 2", {})
        await service.delete_thread(thread["id"])
        try:
            fetched = await service.get_thread(thread["id"])
            assert fetched["status"] == "deleted"
        except ValueError:
            pass  # Also acceptable

    @pytest.mark.asyncio
    async def it_raises_for_unknown_thread_id(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        with pytest.raises(ValueError, match="Thread not found"):
            await service.delete_thread("ghost-thread")


# ===========================================================================
# Issue #219 — Resume Conversation
# ===========================================================================

class DescribeThreadServiceResumeThread:
    """Tests for ThreadService.resume_thread (Issue #219)."""

    @pytest.mark.asyncio
    async def it_returns_last_n_messages_as_context(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-res", "Resume", {})
        for i in range(5):
            await service.add_message(thread["id"], "user", f"Message {i}", {})
        context = await service.resume_thread(thread["id"], context_window=3)
        assert len(context["messages"]) == 3

    @pytest.mark.asyncio
    async def it_returns_most_recent_messages_in_order(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-res2", "Resume2", {})
        for i in range(4):
            await service.add_message(thread["id"], "user", f"Msg {i}", {})
        context = await service.resume_thread(thread["id"], context_window=2)
        assert context["messages"][0]["content"] == "Msg 2"
        assert context["messages"][1]["content"] == "Msg 3"

    @pytest.mark.asyncio
    async def it_includes_thread_id_in_result(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-res3", "R3", {})
        await service.add_message(thread["id"], "user", "Hi", {})
        context = await service.resume_thread(thread["id"], context_window=10)
        assert context["thread_id"] == thread["id"]


class DescribeThreadServiceGetThreadContext:
    """Tests for ThreadService.get_thread_context (Issue #219)."""

    @pytest.mark.asyncio
    async def it_returns_messages_within_token_budget(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-ctx", "Context", {})
        # Each "token" is roughly len(content)//4 — add messages
        await service.add_message(thread["id"], "user", "a" * 400, {})
        await service.add_message(thread["id"], "user", "b" * 400, {})
        await service.add_message(thread["id"], "user", "c" * 400, {})
        # With max_tokens=200, only ~2 messages fit (400//4 = 100 tokens each)
        context = await service.get_thread_context(thread["id"], max_tokens=200)
        assert len(context["messages"]) >= 1
        total_tokens = sum(len(m["content"]) // 4 for m in context["messages"])
        assert total_tokens <= 200

    @pytest.mark.asyncio
    async def it_includes_token_count_in_result(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-ctx2", "C2", {})
        await service.add_message(thread["id"], "user", "Hello world", {})
        context = await service.get_thread_context(thread["id"], max_tokens=1000)
        assert "token_count" in context


# ===========================================================================
# Issue #220 — Conversation Search
# ===========================================================================

class DescribeThreadServiceSearchThreads:
    """Tests for ThreadService.search_threads (Issue #220)."""

    @pytest.mark.asyncio
    async def it_returns_a_list_result(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        results = await service.search_threads("payment", "agent-srch", limit=10)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def it_finds_threads_by_title_keyword(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        await service.create_thread("agent-srch2", "Payment discussion", {})
        await service.create_thread("agent-srch2", "Memory config", {})
        results = await service.search_threads("Payment", "agent-srch2", limit=10)
        assert any(
            "payment" in r.get("title", "").lower()
            for r in results
        )

    @pytest.mark.asyncio
    async def it_respects_limit_parameter(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        for i in range(5):
            await service.create_thread("agent-srch3", f"topic {i}", {})
        results = await service.search_threads("topic", "agent-srch3", limit=3)
        assert len(results) <= 3


class DescribeThreadServiceSearchMessages:
    """Tests for ThreadService.search_messages (Issue #220)."""

    @pytest.mark.asyncio
    async def it_returns_a_list_result(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-msg-srch", "T", {})
        results = await service.search_messages("hello", thread["id"], limit=10)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def it_finds_messages_by_content_keyword(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-msg-srch2", "T2", {})
        await service.add_message(thread["id"], "user", "transfer payment now", {})
        await service.add_message(thread["id"], "user", "check the weather", {})
        results = await service.search_messages("payment", thread["id"], limit=10)
        assert len(results) >= 1
        assert any("payment" in r["content"].lower() for r in results)

    @pytest.mark.asyncio
    async def it_respects_limit_parameter(self):
        from app.services.thread_service import ThreadService
        service = ThreadService()
        thread = await service.create_thread("agent-msg-srch3", "T3", {})
        for i in range(5):
            await service.add_message(thread["id"], "user", f"keyword {i}", {})
        results = await service.search_messages("keyword", thread["id"], limit=2)
        assert len(results) <= 2
