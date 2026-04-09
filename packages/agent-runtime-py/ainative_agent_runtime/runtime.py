"""
ainative-agent-runtime — AgentRuntime
Built by AINative Dev Team
Refs #246

Embeddable agent runtime for Python. Mirrors the TypeScript AgentRuntime.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional


# Event type
RuntimeEvent = str
EventCallback = Callable[[Any], None]


class AgentRuntime:
    """
    Embeddable agent runtime that executes multi-turn agent loops.

    Args:
        storage: A StorageAdapter instance (local or cloud).
        llm_provider: An LLMProvider instance.
        tools: Optional list of tool definitions (dicts with name, description, execute).
        max_turns: Maximum number of turns before halting (default: 10).
    """

    def __init__(
        self,
        storage: Any,
        llm_provider: Any,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_turns: int = 10,
    ) -> None:
        self._storage = storage
        self._llm = llm_provider
        self._global_tools: List[Dict[str, Any]] = tools or []
        self.max_turns = max_turns
        self._listeners: Dict[str, List[EventCallback]] = defaultdict(list)

    # ─── Event Emitter ────────────────────────────────────────────────────────

    def on(self, event: RuntimeEvent, callback: EventCallback) -> None:
        """Register a listener for the given event."""
        self._listeners[event].append(callback)

    def _emit(self, event: RuntimeEvent, data: Any) -> None:
        for cb in self._listeners.get(event, []):
            cb(data)

    # ─── step() ───────────────────────────────────────────────────────────────

    async def step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single agent turn: think → select tool → execute → record.

        Args:
            context: dict with keys 'messages', 'tools', optionally 'options'.

        Returns:
            A dict representing a TurnResult.
        """
        messages = context.get("messages", [])
        tools: List[Dict[str, Any]] = context.get("tools", [])
        options = context.get("options", None)

        # Build LLM tool definitions (strip execute callable)
        llm_tool_defs = [
            {"name": t["name"], "description": t["description"], "parameters": t.get("parameters")}
            for t in tools
        ]

        llm_response = await self._llm.chat_with_tools(messages, llm_tool_defs, options)

        tool_calls_result = []
        for tc in llm_response.get("tool_calls", []):
            self._emit("tool_call", tc)

            tool = next((t for t in tools if t["name"] == tc["name"]), None)
            executed = dict(tc)

            if tool:
                try:
                    executed["result"] = await tool["execute"](tc.get("args", {}))
                except Exception as exc:
                    executed["error"] = str(exc)
            else:
                executed["error"] = f'Tool "{tc["name"]}" not found'

            self._emit("tool_result", executed)
            tool_calls_result.append(executed)

        return {
            "turn_number": 0,  # caller updates this
            "thought": llm_response.get("content", ""),
            "tool_calls": tool_calls_result,
            "messages": messages,
        }

    # ─── run() ────────────────────────────────────────────────────────────────

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the full agent loop for a task, up to max_turns.

        Args:
            task: dict with id, description, tools, metadata.

        Returns:
            A dict representing a RunResult.
        """
        all_tools = self._global_tools + task.get("tools", [])
        turns = []
        task_id = task.get("id", "unknown")

        messages = [
            {"role": "system", "content": task.get("system_prompt", "You are a helpful AI assistant.")},
            {"role": "user", "content": task.get("description", "")},
        ]

        status = "complete"
        final_answer: Optional[str] = None
        error_message: Optional[str] = None

        try:
            for turn_num in range(self.max_turns):
                self._emit("turn_start", {"turn": turn_num, "task_id": task_id})

                turn_result = await self.step({"messages": messages, "tools": all_tools})
                turn_result["turn_number"] = turn_num + 1
                turns.append(turn_result)
                self._emit("turn_end", turn_result)

                thought = turn_result.get("thought", "")
                tool_calls = turn_result.get("tool_calls", [])

                if thought:
                    messages.append({"role": "assistant", "content": thought})

                for tc in tool_calls:
                    messages.append({
                        "role": "tool",
                        "content": f"Error: {tc['error']}" if tc.get("error") else str(tc.get("result", "")),
                        "tool_call_id": tc.get("id"),
                    })

                # LLM produced text and no tool calls → done
                if not tool_calls and thought:
                    final_answer = thought
                    status = "complete"
                    break

                if turn_num == self.max_turns - 1:
                    status = "max_turns_reached"

        except Exception as exc:
            status = "error"
            error_message = str(exc)
            self._emit("error", {"task_id": task_id, "error": error_message})

        result = {
            "task_id": task_id,
            "status": status,
            "turns": turns,
            "final_answer": final_answer,
            "error": error_message,
        }

        # Persist
        try:
            await self._storage.store_record("agent_runs", {
                "task_id": task_id,
                "status": status,
                "turns_count": len(turns),
                "final_answer": final_answer,
                "error": error_message,
            })
        except Exception:
            pass  # Storage errors do not fail the run

        if status != "error":
            self._emit("complete", result)

        return result
