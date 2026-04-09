"""
ainative-agent-runtime — Pydantic types tests (Python)
Built by AINative Dev Team
Refs #246 #247 #248

RED phase: Ensures Pydantic models can be instantiated and validated.
"""

import pytest
from datetime import datetime


class DescribeTypes:
    """Tests for Pydantic type models."""

    class DescribeMessage:
        def it_creates_message_with_role_and_content(self):
            from ainative_agent_runtime.types import Message
            msg = Message(role="user", content="Hello")
            assert msg.role == "user"
            assert msg.content == "Hello"

        def it_accepts_optional_tool_call_id(self):
            from ainative_agent_runtime.types import Message
            msg = Message(role="tool", content="result", tool_call_id="tc-1")
            assert msg.tool_call_id == "tc-1"

    class DescribeToolCall:
        def it_creates_tool_call_with_id_name_and_args(self):
            from ainative_agent_runtime.types import ToolCall
            tc = ToolCall(id="tc-1", name="search", args={"q": "test"})
            assert tc.id == "tc-1"
            assert tc.name == "search"
            assert tc.args == {"q": "test"}

        def it_has_optional_result_and_error(self):
            from ainative_agent_runtime.types import ToolCall
            tc = ToolCall(id="tc-2", name="calc", args={}, result=42, error=None)
            assert tc.result == 42
            assert tc.error is None

    class DescribeTurnResult:
        def it_creates_turn_result_with_required_fields(self):
            from ainative_agent_runtime.types import TurnResult
            turn = TurnResult(turn_number=1, thought="Thinking...", tool_calls=[], messages=[])
            assert turn.turn_number == 1
            assert turn.thought == "Thinking..."

    class DescribeAgentTask:
        def it_creates_agent_task_with_id_and_description(self):
            from ainative_agent_runtime.types import AgentTask
            task = AgentTask(id="t-1", description="Do something")
            assert task.id == "t-1"
            assert task.description == "Do something"

    class DescribeRunResult:
        def it_creates_run_result_with_task_id_and_status(self):
            from ainative_agent_runtime.types import RunResult
            result = RunResult(task_id="t-1", status="complete")
            assert result.task_id == "t-1"
            assert result.status == "complete"

        def it_validates_status_values(self):
            from ainative_agent_runtime.types import RunResult
            from pydantic import ValidationError
            with pytest.raises(ValidationError):
                RunResult(task_id="t-1", status="invalid_status")  # type: ignore

    class DescribeMemoryEntry:
        def it_creates_memory_entry_with_required_fields(self):
            from ainative_agent_runtime.types import MemoryEntry
            entry = MemoryEntry(
                id="m-1",
                content="Some text",
                score=0.9,
                created_at=datetime.now().isoformat(),
            )
            assert entry.id == "m-1"
            assert entry.score == 0.9

    class DescribeProviderHealth:
        def it_creates_provider_health_with_all_fields(self):
            from ainative_agent_runtime.types import ProviderHealth
            health = ProviderHealth(name="ollama", healthy=True, latency_ms=12.5)
            assert health.name == "ollama"
            assert health.healthy is True
            assert health.latency_ms == 12.5

    class DescribeSyncChange:
        def it_creates_memory_sync_change(self):
            from ainative_agent_runtime.types import SyncChange
            change = SyncChange(
                id="c-1",
                type="memory",
                content="some content",
                created_at=datetime.now().isoformat(),
            )
            assert change.type == "memory"

        def it_creates_record_sync_change(self):
            from ainative_agent_runtime.types import SyncChange
            change = SyncChange(
                id="c-2",
                type="record",
                table="agents",
                data={"name": "Bot"},
                created_at=datetime.now().isoformat(),
            )
            assert change.type == "record"
            assert change.table == "agents"
