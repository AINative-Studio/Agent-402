"""
Schemas for conversation thread management — Issues #218, #219, #220.

Defines request/response models for:
- Thread creation and listing
- Message management within threads
- Thread resume and search

Built by AINative Dev Team
Refs #218 #219 #220
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class ThreadCreateRequest(BaseModel):
    """Request payload for creating a new conversation thread."""

    agent_id: str = Field(..., description="Agent ID that owns this thread")
    title: str = Field(..., min_length=1, description="Human-readable thread title")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional metadata for the thread"
    )


class MessageAddRequest(BaseModel):
    """Request payload for appending a message to a thread."""

    role: str = Field(
        ...,
        description="Message role: 'user', 'assistant', or 'system'",
    )
    content: str = Field(..., min_length=1, description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional message metadata"
    )


class ThreadResponse(BaseModel):
    """Response schema for a conversation thread."""

    id: str
    agent_id: str
    title: str
    status: str
    metadata: Dict[str, Any]
    created_at: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)


class MessageResponse(BaseModel):
    """Response schema for a thread message."""

    id: str
    thread_id: str
    role: str
    content: str
    metadata: Dict[str, Any]
    created_at: str


class ThreadListResponse(BaseModel):
    """Paginated list of threads."""

    threads: List[Dict[str, Any]]
    total: int


class ThreadContextResponse(BaseModel):
    """Response for thread context (resume / token-budget slice)."""

    thread_id: str
    messages: List[Dict[str, Any]]
    token_count: Optional[int] = None
