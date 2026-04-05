"""
Thread management REST API — Issues #218, #219, #220.

Endpoints:
  POST   /api/v1/threads                       — create thread
  GET    /api/v1/threads                       — list threads for agent
  GET    /api/v1/threads/search               — search threads
  GET    /api/v1/threads/{thread_id}           — get thread
  DELETE /api/v1/threads/{thread_id}           — soft-delete thread
  POST   /api/v1/threads/{thread_id}/messages  — add message
  GET    /api/v1/threads/{thread_id}/resume    — resume (last N messages)

Built by AINative Dev Team
Refs #218 #219 #220
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import Response

from app.core.errors import InvalidAPIKeyError
from app.schemas.threads import (
    ThreadCreateRequest,
    MessageAddRequest,
    ThreadResponse,
    MessageResponse,
    ThreadListResponse,
    ThreadContextResponse,
)
from app.services.thread_service import get_thread_service, ThreadService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/threads",
    tags=["Conversation Threads"],
)


def _require_auth(x_api_key: Optional[str]) -> None:
    if not x_api_key or not x_api_key.strip():
        raise InvalidAPIKeyError()


# ─── CREATE ───────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_thread(
    body: ThreadCreateRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> dict:
    """Create a new conversation thread."""
    _require_auth(x_api_key)
    service = get_thread_service()
    return await service.create_thread(
        agent_id=body.agent_id,
        title=body.title,
        metadata=body.metadata or {},
    )


# ─── SEARCH (before /{thread_id} to avoid route conflict) ────────────────────

@router.get("/search")
async def search_threads(
    query: str = Query(..., description="Search query"),
    agent_id: str = Query(..., description="Agent ID to search within"),
    limit: int = Query(default=10, ge=1, le=100),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> list:
    """Search for threads by keyword or semantic similarity."""
    _require_auth(x_api_key)
    service = get_thread_service()
    return await service.search_threads(query=query, agent_id=agent_id, limit=limit)


# ─── LIST ─────────────────────────────────────────────────────────────────────

@router.get("")
async def list_threads(
    agent_id: str = Query(..., description="Agent ID"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> dict:
    """List conversation threads for an agent with pagination."""
    _require_auth(x_api_key)
    service = get_thread_service()
    return await service.list_threads(agent_id=agent_id, limit=limit, offset=offset)


# ─── GET ──────────────────────────────────────────────────────────────────────

@router.get("/{thread_id}")
async def get_thread(
    thread_id: str,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> dict:
    """Retrieve a thread by ID including all messages."""
    _require_auth(x_api_key)
    service = get_thread_service()
    try:
        return await service.get_thread(thread_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ─── DELETE ───────────────────────────────────────────────────────────────────

@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: str,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Response:
    """Soft-delete a thread."""
    _require_auth(x_api_key)
    service = get_thread_service()
    try:
        await service.delete_thread(thread_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── ADD MESSAGE ──────────────────────────────────────────────────────────────

@router.post("/{thread_id}/messages", status_code=status.HTTP_201_CREATED)
async def add_message(
    thread_id: str,
    body: MessageAddRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> dict:
    """Append a message to an existing thread."""
    _require_auth(x_api_key)
    service = get_thread_service()
    try:
        return await service.add_message(
            thread_id=thread_id,
            role=body.role,
            content=body.content,
            metadata=body.metadata or {},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ─── RESUME ───────────────────────────────────────────────────────────────────

@router.get("/{thread_id}/resume")
async def resume_thread(
    thread_id: str,
    context_window: int = Query(
        default=10,
        ge=1,
        description="Number of most-recent messages to return",
    ),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> dict:
    """Load the last N messages from a thread as resumption context."""
    _require_auth(x_api_key)
    service = get_thread_service()
    try:
        return await service.resume_thread(
            thread_id=thread_id,
            context_window=context_window,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
