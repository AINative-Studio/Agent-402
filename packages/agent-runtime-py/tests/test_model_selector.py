"""
ainative-agent-runtime — ModelSelector tests (Python)
Built by AINative Dev Team
Refs #248

RED phase: All tests written before implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


def make_provider(name: str, healthy: bool = True):
    provider = MagicMock()
    provider.name = name
    if healthy:
        provider.chat = AsyncMock(return_value={"content": "ok", "tool_calls": []})
    else:
        provider.chat = AsyncMock(side_effect=RuntimeError(f"{name} is down"))
    provider.chat_with_tools = AsyncMock(return_value={"content": "ok", "tool_calls": []})
    return provider


def make_task(task_id="task-1", description="Test task", metadata=None):
    return {
        "id": task_id,
        "description": description,
        "tools": [],
        "metadata": metadata or {},
    }


class DescribeModelSelector:
    """Tests for the ModelSelector class."""

    # ─── Constructor ──────────────────────────────────────────────────────────

    class DescribeConstructor:
        def it_creates_selector_with_providers(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            selector = ModelSelector(providers=[make_provider("local")])
            assert selector is not None

        def it_accepts_empty_providers_list(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            selector = ModelSelector(providers=[])
            assert selector is not None

    # ─── select() ─────────────────────────────────────────────────────────────

    class DescribeSelect:
        @pytest.mark.asyncio
        async def it_returns_first_available_provider_for_simple_task(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            local = make_provider("local")
            cloud = make_provider("cloud")
            selector = ModelSelector(providers=[local, cloud])
            chosen = await selector.select(make_task())
            assert chosen is local

        @pytest.mark.asyncio
        async def it_falls_back_to_cloud_when_local_is_unhealthy(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            local = make_provider("local", healthy=False)
            cloud = make_provider("cloud")
            selector = ModelSelector(providers=[local, cloud])
            await selector.health_check()
            chosen = await selector.select(make_task())
            assert chosen is cloud

        @pytest.mark.asyncio
        async def it_raises_when_no_providers_available(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            selector = ModelSelector(providers=[])
            with pytest.raises(RuntimeError):
                await selector.select(make_task())

        @pytest.mark.asyncio
        async def it_returns_cloud_provider_for_high_complexity_tasks(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            local = make_provider("local")
            cloud = make_provider("cloud")
            selector = ModelSelector(providers=[local, cloud], complexity_threshold=5)
            complex_task = make_task(metadata={"complexity": 8})
            chosen = await selector.select(complex_task)
            assert chosen is cloud

        @pytest.mark.asyncio
        async def it_returns_local_provider_for_low_complexity_tasks(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            local = make_provider("local")
            cloud = make_provider("cloud")
            selector = ModelSelector(providers=[local, cloud], complexity_threshold=5)
            simple_task = make_task(metadata={"complexity": 2})
            chosen = await selector.select(simple_task)
            assert chosen is local

    # ─── health_check() ───────────────────────────────────────────────────────

    class DescribeHealthCheck:
        @pytest.mark.asyncio
        async def it_returns_status_for_each_provider(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            local = make_provider("local")
            cloud = make_provider("cloud")
            selector = ModelSelector(providers=[local, cloud])
            status = await selector.health_check()
            assert len(status) == 2

        @pytest.mark.asyncio
        async def it_marks_healthy_provider(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            local = make_provider("local")
            selector = ModelSelector(providers=[local])
            status = await selector.health_check()
            assert status[0]["healthy"] is True

        @pytest.mark.asyncio
        async def it_marks_unhealthy_provider_when_chat_raises(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            local = make_provider("local", healthy=False)
            selector = ModelSelector(providers=[local])
            status = await selector.health_check()
            assert status[0]["healthy"] is False

        @pytest.mark.asyncio
        async def it_includes_provider_name_in_status(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            provider = make_provider("ollama-local")
            selector = ModelSelector(providers=[provider])
            status = await selector.health_check()
            assert status[0]["name"] == "ollama-local"

        @pytest.mark.asyncio
        async def it_includes_latency_ms_in_status(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            provider = make_provider("local")
            selector = ModelSelector(providers=[provider])
            status = await selector.health_check()
            assert isinstance(status[0]["latency_ms"], (int, float))
            assert status[0]["latency_ms"] >= 0

        @pytest.mark.asyncio
        async def it_updates_health_state_used_by_select(self):
            from ainative_agent_runtime.model_selector import ModelSelector
            local = make_provider("local", healthy=False)
            cloud = make_provider("cloud")
            selector = ModelSelector(providers=[local, cloud])
            await selector.health_check()
            chosen = await selector.select(make_task())
            assert chosen is cloud
