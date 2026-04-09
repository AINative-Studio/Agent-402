"""
ainative-agent-runtime — OllamaProvider (Python)
Built by AINative Dev Team
Refs #248

Wraps the Ollama /api/chat endpoint to match the LLMProvider protocol.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

import aiohttp


class OllamaProvider:
    """
    LLM provider adapter for locally-running Ollama instances.

    Args:
        base_url: Base URL of the Ollama server (default: http://localhost:11434).
        model: Model name to use (default: llama3.2).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.name = f"ollama:{model}"

    # ─── Internal HTTP helper ─────────────────────────────────────────────────

    async def _post_chat(self, body: Dict[str, Any]) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                data=json.dumps(body),
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Ollama error {response.status}: {text}")
                return await response.json()

    # ─── chat() ───────────────────────────────────────────────────────────────

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if options and options.get("temperature") is not None:
            body["options"] = {"temperature": options["temperature"]}

        data = await self._post_chat(body)
        return {
            "content": data["message"].get("content", ""),
            "tool_calls": [],
        }

    # ─── chat_with_tools() ────────────────────────────────────────────────────

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ollama_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("parameters"),
                },
            }
            for t in tools
        ]

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": ollama_tools,
            "stream": False,
        }
        if options and options.get("temperature") is not None:
            body["options"] = {"temperature": options["temperature"]}

        data = await self._post_chat(body)
        raw_calls = data["message"].get("tool_calls") or []

        tool_calls = [
            {
                "id": str(uuid.uuid4()),
                "name": tc["function"]["name"],
                "args": tc["function"].get("arguments", {}),
            }
            for tc in raw_calls
        ]

        return {
            "content": data["message"].get("content", ""),
            "tool_calls": tool_calls,
        }
