"""
ainative-agent-runtime — AgentRuntime tests (Python)
Built by AINative Dev Team
Refs #246

RED phase: All tests written before implementation.
BDD style: DescribeX / it_* pattern.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_storage():
    storage = MagicMock()
    storage.store_memory = AsyncMock(return_value={"id": "mem-1"})
    storage.recall_memory = AsyncMock(return_value=[])
    storage.store_record = AsyncMock(return_value={"id": "rec-1"})
    storage.query_records = AsyncMock(return_value=[])
    return storage


def make_llm(content="Done.", tool_calls=None):
    llm = MagicMock()
    response = {"content": content, "tool_calls": tool_calls or []}
    llm.chat = AsyncMock(return_value=response)
    llm.chat_with_tools = AsyncMock(return_value=response)
    return llm


def make_task(task_id="task-1", description="Test task", tools=None, metadata=None):
    return {
        "id": task_id,
        "description": description,
        "tools": tools or [],
        "metadata": metadata or {},
    }


# ─── DescribeAgentRuntime ─────────────────────────────────────────────────────

class DescribeAgentRuntime:
    """Tests for the AgentRuntime class."""

    # ─── Constructor ──────────────────────────────────────────────────────────

    class DescribeConstructor:
        def it_creates_runtime_with_required_config(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm())
            assert runtime is not None

        def it_defaults_max_turns_to_10(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm())
            assert runtime.max_turns == 10

        def it_accepts_custom_max_turns(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm(), max_turns=5)
            assert runtime.max_turns == 5

        def it_accepts_optional_tools_list(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            tool = {"name": "search", "description": "search", "execute": AsyncMock()}
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm(), tools=[tool])
            assert runtime is not None

    # ─── run() ────────────────────────────────────────────────────────────────

    class DescribeRun:
        @pytest.mark.asyncio
        async def it_resolves_with_task_id_in_result(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm(), max_turns=1)
            result = await runtime.run(make_task(task_id="task-42"))
            assert result["task_id"] == "task-42"

        @pytest.mark.asyncio
        async def it_returns_status_complete_on_success(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm(), max_turns=1)
            result = await runtime.run(make_task())
            assert result["status"] == "complete"

        @pytest.mark.asyncio
        async def it_stops_at_max_turns_and_returns_max_turns_reached(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            llm = make_llm(content="", tool_calls=[{"id": "tc-1", "name": "search", "args": {"q": "test"}}])
            tool = {"name": "search", "description": "search", "execute": AsyncMock(return_value="result")}
            runtime = AgentRuntime(storage=make_storage(), llm_provider=llm, max_turns=3, tools=[tool])
            result = await runtime.run(make_task(tools=[tool]))
            assert result["status"] == "max_turns_reached"
            assert len(result["turns"]) == 3

        @pytest.mark.asyncio
        async def it_returns_error_status_when_llm_raises(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            llm = make_llm()
            llm.chat_with_tools = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
            runtime = AgentRuntime(storage=make_storage(), llm_provider=llm, max_turns=1)
            result = await runtime.run(make_task())
            assert result["status"] == "error"
            assert "LLM unavailable" in result.get("error", "")

        @pytest.mark.asyncio
        async def it_stores_final_result_in_storage(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            storage = make_storage()
            runtime = AgentRuntime(storage=storage, llm_provider=make_llm(), max_turns=1)
            await runtime.run(make_task(task_id="task-99"))
            storage.store_record.assert_called()
            call_args = storage.store_record.call_args
            assert call_args[0][0] == "agent_runs"
            assert call_args[0][1]["task_id"] == "task-99"

    # ─── step() ───────────────────────────────────────────────────────────────

    class DescribeStep:
        @pytest.mark.asyncio
        async def it_calls_llm_chat_with_tools_with_messages(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            llm = make_llm()
            runtime = AgentRuntime(storage=make_storage(), llm_provider=llm)
            messages = [{"role": "user", "content": "hello"}]
            await runtime.step({"messages": messages, "tools": []})
            llm.chat_with_tools.assert_called_once_with(messages, [], None)

        @pytest.mark.asyncio
        async def it_returns_turn_result_with_thought(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            llm = make_llm(content="My thought.")
            runtime = AgentRuntime(storage=make_storage(), llm_provider=llm)
            turn = await runtime.step({"messages": [], "tools": []})
            assert turn["thought"] == "My thought."

        @pytest.mark.asyncio
        async def it_executes_tool_call_from_llm_response(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            tool_fn = AsyncMock(return_value="42")
            tool = {"name": "calculator", "description": "math", "execute": tool_fn}
            llm = make_llm(content="", tool_calls=[{"id": "tc-1", "name": "calculator", "args": {"expr": "6*7"}}])
            runtime = AgentRuntime(storage=make_storage(), llm_provider=llm, tools=[tool])
            turn = await runtime.step({"messages": [], "tools": [tool]})
            tool_fn.assert_called_once_with({"expr": "6*7"})
            assert turn["tool_calls"][0]["result"] == "42"

        @pytest.mark.asyncio
        async def it_records_tool_error_when_tool_raises(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            tool_fn = AsyncMock(side_effect=ValueError("tool error"))
            tool = {"name": "fail-tool", "description": "fails", "execute": tool_fn}
            llm = make_llm(content="", tool_calls=[{"id": "tc-2", "name": "fail-tool", "args": {}}])
            runtime = AgentRuntime(storage=make_storage(), llm_provider=llm, tools=[tool])
            turn = await runtime.step({"messages": [], "tools": [tool]})
            assert "tool error" in turn["tool_calls"][0]["error"]

        @pytest.mark.asyncio
        async def it_records_error_for_unknown_tool(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            llm = make_llm(content="", tool_calls=[{"id": "tc-3", "name": "missing-tool", "args": {}}])
            runtime = AgentRuntime(storage=make_storage(), llm_provider=llm)
            turn = await runtime.step({"messages": [], "tools": []})
            assert "missing-tool" in turn["tool_calls"][0]["error"]

    # ─── Events ───────────────────────────────────────────────────────────────

    class DescribeEvents:
        @pytest.mark.asyncio
        async def it_emits_turn_start_at_beginning_of_each_turn(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm(), max_turns=1)
            events = []
            runtime.on("turn_start", lambda d: events.append(d))
            await runtime.run(make_task())
            assert len(events) >= 1

        @pytest.mark.asyncio
        async def it_emits_turn_end_after_each_completed_turn(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm(), max_turns=1)
            events = []
            runtime.on("turn_end", lambda d: events.append(d))
            await runtime.run(make_task())
            assert len(events) == 1

        @pytest.mark.asyncio
        async def it_emits_complete_on_success(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm(), max_turns=1)
            events = []
            runtime.on("complete", lambda d: events.append(d))
            await runtime.run(make_task())
            assert len(events) == 1

        @pytest.mark.asyncio
        async def it_emits_error_on_failure(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            llm = make_llm()
            llm.chat_with_tools = AsyncMock(side_effect=RuntimeError("boom"))
            runtime = AgentRuntime(storage=make_storage(), llm_provider=llm, max_turns=1)
            events = []
            runtime.on("error", lambda d: events.append(d))
            await runtime.run(make_task())
            assert len(events) == 1

        @pytest.mark.asyncio
        async def it_supports_multiple_listeners_on_same_event(self):
            from ainative_agent_runtime.runtime import AgentRuntime
            runtime = AgentRuntime(storage=make_storage(), llm_provider=make_llm(), max_turns=1)
            a, b = [], []
            runtime.on("complete", lambda d: a.append(d))
            runtime.on("complete", lambda d: b.append(d))
            await runtime.run(make_task())
            assert len(a) == 1
            assert len(b) == 1
