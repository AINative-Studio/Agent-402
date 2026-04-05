"""
RED tests for SSE Service — Issue #212.

Covers SSEService: subscribe_task async generator, publish_progress,
publish_completion, and SSE format compliance.
Built by AINative Dev Team
Refs #212
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Dict, List, Any

import pytest


# ===========================================================================
# Issue #212 — SSE Service
# ===========================================================================

class DescribeSSEServiceSubscribeTask:
    """Tests for SSEService.subscribe_task async generator (Issue #212)."""

    @pytest.mark.asyncio
    async def it_yields_sse_formatted_events_for_task(self):
        from app.services.sse_service import SSEService
        service = SSEService()
        await service.publish_progress("task-001", 1, 3, "Step 1 done")
        events = []
        async for event in service.subscribe_task("task-001"):
            events.append(event)
            break
        assert len(events) == 1
        assert events[0].startswith("data: ")
        assert events[0].endswith("\n\n")

    @pytest.mark.asyncio
    async def it_yields_valid_json_in_data_field(self):
        from app.services.sse_service import SSEService
        service = SSEService()
        await service.publish_progress("task-002", 1, 2, "Running")
        async for event in service.subscribe_task("task-002"):
            json_str = event[6:].strip()
            data = json.loads(json_str)
            assert "task_id" in data
            assert data["task_id"] == "task-002"
            break

    @pytest.mark.asyncio
    async def it_yields_events_with_required_fields(self):
        from app.services.sse_service import SSEService
        service = SSEService()
        await service.publish_progress("task-003", 2, 5, "Processing")
        async for event in service.subscribe_task("task-003"):
            json_str = event[6:].strip()
            data = json.loads(json_str)
            assert "task_id" in data
            assert "step" in data
            assert "total_steps" in data
            assert "message" in data
            assert "timestamp" in data
            break

    @pytest.mark.asyncio
    async def it_yields_completion_event_when_task_completes(self):
        from app.services.sse_service import SSEService
        service = SSEService()
        await service.publish_completion("task-004", {"output": "done"})
        events = []
        async for event in service.subscribe_task("task-004"):
            events.append(event)
            break
        assert len(events) == 1
        json_str = events[0][6:].strip()
        data = json.loads(json_str)
        assert data["task_id"] == "task-004"


class DescribeSSEServicePublishProgress:
    """Tests for SSEService.publish_progress (Issue #212)."""

    @pytest.mark.asyncio
    async def it_queues_a_progress_event_for_task(self):
        from app.services.sse_service import SSEService
        service = SSEService()
        await service.publish_progress("task-005", 1, 4, "Step 1")
        async for event in service.subscribe_task("task-005"):
            json_str = event[6:].strip()
            data = json.loads(json_str)
            assert data["step"] == 1
            assert data["total_steps"] == 4
            assert data["message"] == "Step 1"
            break

    @pytest.mark.asyncio
    async def it_queues_sequential_progress_events(self):
        from app.services.sse_service import SSEService
        service = SSEService()
        await service.publish_progress("task-006", 1, 3, "Step 1")
        await service.publish_progress("task-006", 2, 3, "Step 2")
        steps = []
        count = 0
        async for event in service.subscribe_task("task-006"):
            json_str = event[6:].strip()
            data = json.loads(json_str)
            steps.append(data["step"])
            count += 1
            if count >= 2:
                break
        assert steps == [1, 2]

    @pytest.mark.asyncio
    async def it_adds_iso_timestamp_to_event(self):
        from app.services.sse_service import SSEService
        service = SSEService()
        await service.publish_progress("task-007", 1, 1, "Done")
        async for event in service.subscribe_task("task-007"):
            json_str = event[6:].strip()
            data = json.loads(json_str)
            # Should parse without error
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            break


class DescribeSSEServicePublishCompletion:
    """Tests for SSEService.publish_completion (Issue #212)."""

    @pytest.mark.asyncio
    async def it_queues_a_completion_event_with_result(self):
        from app.services.sse_service import SSEService
        service = SSEService()
        await service.publish_completion("task-008", {"answer": 42})
        async for event in service.subscribe_task("task-008"):
            json_str = event[6:].strip()
            data = json.loads(json_str)
            assert data["task_id"] == "task-008"
            assert data["result"] == {"answer": 42}
            assert data["status"] == "completed"
            break

    @pytest.mark.asyncio
    async def it_marks_task_as_completed_in_completion_event(self):
        from app.services.sse_service import SSEService
        service = SSEService()
        await service.publish_completion("task-009", {})
        async for event in service.subscribe_task("task-009"):
            json_str = event[6:].strip()
            data = json.loads(json_str)
            assert data["status"] == "completed"
            break
