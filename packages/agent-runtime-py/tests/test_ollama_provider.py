"""
ainative-agent-runtime — OllamaProvider tests (Python)
Built by AINative Dev Team
Refs #248

RED phase: All tests written before implementation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json


def make_ollama_response(content: str, tool_calls=None):
    return {
        "model": "llama3.2",
        "message": {
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls or [],
        },
        "done": True,
    }


class DescribeOllamaProvider:
    """Tests for the OllamaProvider class."""

    # ─── Constructor ──────────────────────────────────────────────────────────

    class DescribeConstructor:
        def it_uses_default_base_url_and_model(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider
            provider = OllamaProvider()
            assert provider.base_url == "http://localhost:11434"
            assert provider.model == "llama3.2"

        def it_accepts_custom_base_url(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider
            provider = OllamaProvider(base_url="http://remote:11434")
            assert provider.base_url == "http://remote:11434"

        def it_accepts_custom_model(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider
            provider = OllamaProvider(model="mistral")
            assert provider.model == "mistral"

    # ─── chat() ───────────────────────────────────────────────────────────────

    class DescribeChat:
        @pytest.mark.asyncio
        async def it_posts_to_api_chat_endpoint(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=make_ollama_response("Hello!"))

            with patch("aiohttp.ClientSession") as MockSession:
                session_instance = MagicMock()
                MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

                ctx = MagicMock()
                ctx.__aenter__ = AsyncMock(return_value=mock_response)
                ctx.__aexit__ = AsyncMock(return_value=False)
                session_instance.post = MagicMock(return_value=ctx)

                provider = OllamaProvider()
                result = await provider.chat([{"role": "user", "content": "Hello"}])

                session_instance.post.assert_called_once()
                call_url = session_instance.post.call_args[0][0]
                assert call_url == "http://localhost:11434/api/chat"

        @pytest.mark.asyncio
        async def it_sends_stream_false_in_body(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider

            captured = {}

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=make_ollama_response("ok"))

            with patch("aiohttp.ClientSession") as MockSession:
                session_instance = MagicMock()
                MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

                ctx = MagicMock()
                ctx.__aenter__ = AsyncMock(return_value=mock_response)
                ctx.__aexit__ = AsyncMock(return_value=False)

                def capture_post(url, **kwargs):
                    captured["body"] = json.loads(kwargs.get("data", "{}"))
                    return ctx

                session_instance.post = MagicMock(side_effect=capture_post)

                provider = OllamaProvider()
                await provider.chat([{"role": "user", "content": "hi"}])
                assert captured["body"]["stream"] is False

        @pytest.mark.asyncio
        async def it_returns_content_from_response(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=make_ollama_response("The answer is 42."))

            with patch("aiohttp.ClientSession") as MockSession:
                session_instance = MagicMock()
                MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
                ctx = MagicMock()
                ctx.__aenter__ = AsyncMock(return_value=mock_response)
                ctx.__aexit__ = AsyncMock(return_value=False)
                session_instance.post = MagicMock(return_value=ctx)

                provider = OllamaProvider()
                result = await provider.chat([{"role": "user", "content": "What is the answer?"}])
                assert result["content"] == "The answer is 42."

        @pytest.mark.asyncio
        async def it_returns_empty_tool_calls_for_plain_text_response(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=make_ollama_response("Just text."))

            with patch("aiohttp.ClientSession") as MockSession:
                session_instance = MagicMock()
                MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
                ctx = MagicMock()
                ctx.__aenter__ = AsyncMock(return_value=mock_response)
                ctx.__aexit__ = AsyncMock(return_value=False)
                session_instance.post = MagicMock(return_value=ctx)

                provider = OllamaProvider()
                result = await provider.chat([{"role": "user", "content": "Hi"}])
                assert result["tool_calls"] == []

        @pytest.mark.asyncio
        async def it_raises_on_non_ok_response(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider

            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")

            with patch("aiohttp.ClientSession") as MockSession:
                session_instance = MagicMock()
                MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
                ctx = MagicMock()
                ctx.__aenter__ = AsyncMock(return_value=mock_response)
                ctx.__aexit__ = AsyncMock(return_value=False)
                session_instance.post = MagicMock(return_value=ctx)

                provider = OllamaProvider()
                with pytest.raises(RuntimeError):
                    await provider.chat([{"role": "user", "content": "hi"}])

    # ─── chat_with_tools() ────────────────────────────────────────────────────

    class DescribeChatWithTools:
        tools = [
            {
                "name": "get_weather",
                "description": "Get current weather",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ]

        @pytest.mark.asyncio
        async def it_converts_ollama_tool_calls_to_tool_call_format(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=make_ollama_response(
                "",
                tool_calls=[{"function": {"name": "get_weather", "arguments": {"city": "Austin"}}}],
            ))

            with patch("aiohttp.ClientSession") as MockSession:
                session_instance = MagicMock()
                MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
                ctx = MagicMock()
                ctx.__aenter__ = AsyncMock(return_value=mock_response)
                ctx.__aexit__ = AsyncMock(return_value=False)
                session_instance.post = MagicMock(return_value=ctx)

                provider = OllamaProvider()
                result = await provider.chat_with_tools(
                    [{"role": "user", "content": "Weather in Austin?"}],
                    self.tools,
                )
                assert len(result["tool_calls"]) == 1
                assert result["tool_calls"][0]["name"] == "get_weather"
                assert result["tool_calls"][0]["args"] == {"city": "Austin"}

        @pytest.mark.asyncio
        async def it_assigns_unique_ids_to_tool_calls(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=make_ollama_response(
                "",
                tool_calls=[
                    {"function": {"name": "get_weather", "arguments": {"city": "Austin"}}},
                    {"function": {"name": "get_weather", "arguments": {"city": "Dallas"}}},
                ],
            ))

            with patch("aiohttp.ClientSession") as MockSession:
                session_instance = MagicMock()
                MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
                ctx = MagicMock()
                ctx.__aenter__ = AsyncMock(return_value=mock_response)
                ctx.__aexit__ = AsyncMock(return_value=False)
                session_instance.post = MagicMock(return_value=ctx)

                provider = OllamaProvider()
                result = await provider.chat_with_tools(
                    [{"role": "user", "content": "Weather in TX?"}],
                    self.tools,
                )
                ids = [tc["id"] for tc in result["tool_calls"]]
                assert len(set(ids)) == len(ids)

        @pytest.mark.asyncio
        async def it_returns_content_and_empty_tool_calls_without_tool_use(self):
            from ainative_agent_runtime.adapters.ollama_provider import OllamaProvider

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=make_ollama_response("The weather is sunny."))

            with patch("aiohttp.ClientSession") as MockSession:
                session_instance = MagicMock()
                MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
                ctx = MagicMock()
                ctx.__aenter__ = AsyncMock(return_value=mock_response)
                ctx.__aexit__ = AsyncMock(return_value=False)
                session_instance.post = MagicMock(return_value=ctx)

                provider = OllamaProvider()
                result = await provider.chat_with_tools(
                    [{"role": "user", "content": "How are you?"}],
                    self.tools,
                )
                assert result["content"] == "The weather is sunny."
                assert result["tool_calls"] == []
