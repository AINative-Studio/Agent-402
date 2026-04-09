"""
ainative-agent-runtime — Pydantic type models
Built by AINative Dev Team
Refs #246 #247 #248
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ─── Message ──────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: Optional[str] = None


# ─── Tool Call ────────────────────────────────────────────────────────────────

class ToolCall(BaseModel):
    id: str
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None


# ─── Turn Result ──────────────────────────────────────────────────────────────

class TurnResult(BaseModel):
    turn_number: int
    thought: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    messages: List[Message] = Field(default_factory=list)


# ─── Agent Task ───────────────────────────────────────────────────────────────

class AgentTask(BaseModel):
    id: str
    description: str
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    system_prompt: Optional[str] = None


# ─── Run Result ───────────────────────────────────────────────────────────────

class RunResult(BaseModel):
    task_id: str
    status: Literal["complete", "max_turns_reached", "error"]
    turns: List[TurnResult] = Field(default_factory=list)
    final_answer: Optional[str] = None
    error: Optional[str] = None


# ─── LLM Provider Types ───────────────────────────────────────────────────────

class LLMChatOptions(BaseModel):
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None


class LLMResponse(BaseModel):
    content: str
    tool_calls: List[ToolCall] = Field(default_factory=list)


# ─── Storage Types ────────────────────────────────────────────────────────────

class MemoryEntry(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    created_at: str


class RecordEntry(BaseModel):
    id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


# ─── Sync Change ──────────────────────────────────────────────────────────────

class SyncChange(BaseModel):
    id: str
    type: Literal["memory", "record"]
    content: Optional[str] = None
    table: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


# ─── Provider Health ─────────────────────────────────────────────────────────

class ProviderHealth(BaseModel):
    name: str
    healthy: bool
    latency_ms: float
    error: Optional[str] = None
