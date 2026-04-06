"""
RED tests for realtime API endpoints — Issues #212, #218, #219, #220.

Covers SSE streaming endpoint and thread management REST endpoints.
Built by AINative Dev Team
Refs #212 #218 #219 #220
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Optional, Dict, List, Any


# ===========================================================================
# Issue #212 — SSE streaming endpoint
# ===========================================================================

class DescribeSSEStreamEndpoint:
    """Tests for GET /api/v1/events/tasks/{task_id}/stream."""

    def it_returns_200_for_valid_task_id(self, client, auth_headers_user1):
        with patch("app.api.sse_events.get_sse_service") as mock_svc_fn:
            mock_svc = MagicMock()
            mock_svc_fn.return_value = mock_svc

            async def fake_stream(task_id):
                yield (
                    'data: {"task_id": "t1", "step": 1, "total_steps": 2, '
                    '"message": "ok", "timestamp": "2026-01-01T00:00:00Z"}\n\n'
                )

            mock_svc.subscribe_task = fake_stream
            response = client.get(
                "/api/v1/events/tasks/t1/stream",
                headers=auth_headers_user1
            )
        assert response.status_code == 200

    def it_returns_text_event_stream_content_type(self, client, auth_headers_user1):
        with patch("app.api.sse_events.get_sse_service") as mock_svc_fn:
            mock_svc = MagicMock()
            mock_svc_fn.return_value = mock_svc

            async def fake_stream(task_id):
                yield 'data: {"task_id": "t2"}\n\n'

            mock_svc.subscribe_task = fake_stream
            response = client.get(
                "/api/v1/events/tasks/t2/stream",
                headers=auth_headers_user1
            )
        assert "text/event-stream" in response.headers.get("content-type", "")

    def it_requires_authentication(self, client):
        response = client.get("/api/v1/events/tasks/t3/stream")
        assert response.status_code == 401


# ===========================================================================
# Issues #218–#220 — Thread management REST API
# ===========================================================================

class DescribeThreadsAPICreate:
    """Tests for POST /api/v1/threads."""

    def it_creates_a_thread_via_post(self, client, auth_headers_user1):
        with patch("app.api.threads.get_thread_service") as mock_fn:
            mock_svc = AsyncMock()
            mock_fn.return_value = mock_svc
            mock_svc.create_thread.return_value = {
                "id": "thread-123",
                "agent_id": "agent-1",
                "title": "New Thread",
                "metadata": {},
                "status": "active",
                "created_at": "2026-01-01T00:00:00Z",
                "messages": [],
            }
            response = client.post(
                "/api/v1/threads",
                headers=auth_headers_user1,
                json={"agent_id": "agent-1", "title": "New Thread"}
            )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "thread-123"

    def it_requires_authentication(self, client):
        response = client.post(
            "/api/v1/threads",
            json={"agent_id": "agent-x", "title": "T"}
        )
        assert response.status_code == 401


class DescribeThreadsAPIGet:
    """Tests for GET /api/v1/threads/{thread_id}."""

    def it_gets_a_thread_by_id(self, client, auth_headers_user1):
        with patch("app.api.threads.get_thread_service") as mock_fn:
            mock_svc = AsyncMock()
            mock_fn.return_value = mock_svc
            mock_svc.get_thread.return_value = {
                "id": "thread-456",
                "agent_id": "agent-2",
                "title": "Existing Thread",
                "status": "active",
                "messages": [],
                "created_at": "2026-01-01T00:00:00Z",
            }
            response = client.get(
                "/api/v1/threads/thread-456",
                headers=auth_headers_user1
            )
        assert response.status_code == 200
        assert response.json()["id"] == "thread-456"

    def it_returns_404_for_unknown_thread(self, client, auth_headers_user1):
        with patch("app.api.threads.get_thread_service") as mock_fn:
            mock_svc = AsyncMock()
            mock_fn.return_value = mock_svc
            mock_svc.get_thread.side_effect = ValueError("Thread not found")
            response = client.get(
                "/api/v1/threads/ghost",
                headers=auth_headers_user1
            )
        assert response.status_code == 404


class DescribeThreadsAPIList:
    """Tests for GET /api/v1/threads."""

    def it_lists_threads_for_agent(self, client, auth_headers_user1):
        with patch("app.api.threads.get_thread_service") as mock_fn:
            mock_svc = AsyncMock()
            mock_fn.return_value = mock_svc
            mock_svc.list_threads.return_value = {
                "threads": [
                    {"id": "t1", "title": "A"},
                    {"id": "t2", "title": "B"},
                ],
                "total": 2,
            }
            response = client.get(
                "/api/v1/threads?agent_id=agent-3",
                headers=auth_headers_user1
            )
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def it_requires_authentication(self, client):
        response = client.get("/api/v1/threads?agent_id=agent-x")
        assert response.status_code == 401


class DescribeThreadsAPIMessages:
    """Tests for POST /api/v1/threads/{thread_id}/messages."""

    def it_adds_message_to_thread(self, client, auth_headers_user1):
        with patch("app.api.threads.get_thread_service") as mock_fn:
            mock_svc = AsyncMock()
            mock_fn.return_value = mock_svc
            mock_svc.add_message.return_value = {
                "id": "msg-1",
                "thread_id": "thread-789",
                "role": "user",
                "content": "Hello!",
                "metadata": {},
                "created_at": "2026-01-01T00:00:00Z",
            }
            response = client.post(
                "/api/v1/threads/thread-789/messages",
                headers=auth_headers_user1,
                json={"role": "user", "content": "Hello!"}
            )
        assert response.status_code == 201


class DescribeThreadsAPIDelete:
    """Tests for DELETE /api/v1/threads/{thread_id}."""

    def it_deletes_a_thread(self, client, auth_headers_user1):
        with patch("app.api.threads.get_thread_service") as mock_fn:
            mock_svc = AsyncMock()
            mock_fn.return_value = mock_svc
            mock_svc.delete_thread.return_value = None
            response = client.delete(
                "/api/v1/threads/thread-del",
                headers=auth_headers_user1
            )
        assert response.status_code == 204


class DescribeThreadsAPIResume:
    """Tests for GET /api/v1/threads/{thread_id}/resume (Issue #219)."""

    def it_resumes_a_thread(self, client, auth_headers_user1):
        with patch("app.api.threads.get_thread_service") as mock_fn:
            mock_svc = AsyncMock()
            mock_fn.return_value = mock_svc
            mock_svc.resume_thread.return_value = {
                "thread_id": "thread-res",
                "messages": [{"role": "user", "content": "Hi"}],
            }
            response = client.get(
                "/api/v1/threads/thread-res/resume",
                headers=auth_headers_user1
            )
        assert response.status_code == 200


class DescribeThreadsAPISearch:
    """Tests for GET /api/v1/threads/search (Issue #220)."""

    def it_searches_threads(self, client, auth_headers_user1):
        with patch("app.api.threads.get_thread_service") as mock_fn:
            mock_svc = AsyncMock()
            mock_fn.return_value = mock_svc
            mock_svc.search_threads.return_value = [
                {"id": "t1", "title": "Payment chat"}
            ]
            response = client.get(
                "/api/v1/threads/search?query=payment&agent_id=agent-s",
                headers=auth_headers_user1
            )
        assert response.status_code == 200
