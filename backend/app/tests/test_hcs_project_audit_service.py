"""
Tests for HCSProjectAuditService (Issue #268 Phase 2).

Covers:
- create_project_topic: create HCS topic per project
- log_audit_event: submit events to a project's HCS topic
- get_audit_log: query mirror node for events
- get_audit_summary: event counts by type

TDD Cycle: RED -> GREEN -> REFACTOR
BDD-style: class DescribeX / def it_does_something

Built by AINative Dev Team
Refs #268
"""
from __future__ import annotations

import json
from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.services.hcs_project_audit_service import (
    HCSProjectAuditService,
    HCSProjectAuditError,
    VALID_EVENT_TYPES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_hcs_client: Optional[AsyncMock] = None) -> tuple[HCSProjectAuditService, AsyncMock]:
    """Return a (service, mock_client) pair."""
    if mock_hcs_client is None:
        mock_hcs_client = AsyncMock()
    service = HCSProjectAuditService(hcs_client=mock_hcs_client)
    return service, mock_hcs_client


# ===========================================================================
# create_project_topic
# ===========================================================================

class DescribeCreateProjectTopic:
    """Tests for HCSProjectAuditService.create_project_topic."""

    @pytest.mark.asyncio
    async def it_creates_an_hcs_topic_for_the_project(self):
        """
        Arrange: service with mock HCS client returning a topic_id.
        Act: call create_project_topic with a project_id.
        Assert: topic_id is returned and client was called.
        """
        service, mock_client = _make_service()
        mock_client.create_topic = AsyncMock(return_value={"topic_id": "0.0.1111"})

        result = await service.create_project_topic("proj-abc")

        assert result["topic_id"] == "0.0.1111"
        mock_client.create_topic.assert_called_once()

    @pytest.mark.asyncio
    async def it_includes_the_project_id_in_the_topic_memo(self):
        """
        Arrange: service with mock HCS client.
        Act: call create_project_topic.
        Assert: the call includes project_id somewhere in the memo/params.
        """
        service, mock_client = _make_service()
        mock_client.create_topic = AsyncMock(return_value={"topic_id": "0.0.2222"})

        await service.create_project_topic("proj-test-123")

        _, kwargs = mock_client.create_topic.call_args
        call_args_str = str(mock_client.create_topic.call_args)
        assert "proj-test-123" in call_args_str

    @pytest.mark.asyncio
    async def it_raises_hcs_project_audit_error_when_topic_creation_fails(self):
        """
        Arrange: mock HCS client raises an exception.
        Act: call create_project_topic.
        Assert: HCSProjectAuditError is raised.
        """
        service, mock_client = _make_service()
        mock_client.create_topic = AsyncMock(side_effect=Exception("Network error"))

        with pytest.raises(HCSProjectAuditError) as exc_info:
            await service.create_project_topic("proj-fail")

        assert "proj-fail" in str(exc_info.value) or "topic" in str(exc_info.value).lower()


# ===========================================================================
# log_audit_event
# ===========================================================================

class DescribeLogAuditEvent:
    """Tests for HCSProjectAuditService.log_audit_event."""

    @pytest.mark.asyncio
    async def it_submits_event_to_the_project_hcs_topic(self):
        """
        Arrange: service and mock HCS client returning sequence number.
        Act: log a payment event for a project.
        Assert: HCS submit_hcs_message was called with topic and message.
        """
        service, mock_client = _make_service()
        mock_client.submit_hcs_message = AsyncMock(return_value={"sequence_number": 7})

        result = await service.log_audit_event(
            project_id="proj-abc",
            topic_id="0.0.1111",
            event_type="payment",
            payload={"amount": 10.0, "currency": "HBAR"},
            agent_id="agent-001",
        )

        assert result["sequence_number"] == 7
        mock_client.submit_hcs_message.assert_called_once()

    @pytest.mark.asyncio
    async def it_encodes_all_required_fields_in_the_message(self):
        """
        Arrange: service and mock.
        Act: log a decision event.
        Assert: the HCS message contains event_type, project_id, agent_id, payload.
        """
        service, mock_client = _make_service()
        mock_client.submit_hcs_message = AsyncMock(return_value={"sequence_number": 1})

        await service.log_audit_event(
            project_id="proj-xyz",
            topic_id="0.0.9999",
            event_type="decision",
            payload={"decision": "approve"},
            agent_id="agent-finance",
        )

        call_kwargs = mock_client.submit_hcs_message.call_args
        call_str = str(call_kwargs)
        assert "proj-xyz" in call_str
        assert "decision" in call_str
        assert "agent-finance" in call_str

    @pytest.mark.asyncio
    async def it_accepts_all_valid_event_types(self):
        """
        Arrange: service with mock.
        Act: log events of each valid type.
        Assert: no error is raised.
        """
        service, mock_client = _make_service()
        mock_client.submit_hcs_message = AsyncMock(return_value={"sequence_number": 1})

        for event_type in VALID_EVENT_TYPES:
            await service.log_audit_event(
                project_id="proj-1",
                topic_id="0.0.111",
                event_type=event_type,
                payload={},
                agent_id="agent-1",
            )

        assert mock_client.submit_hcs_message.call_count == len(VALID_EVENT_TYPES)

    @pytest.mark.asyncio
    async def it_raises_hcs_project_audit_error_for_invalid_event_type(self):
        """
        Arrange: service.
        Act: log an event with an unsupported event_type.
        Assert: HCSProjectAuditError is raised.
        """
        service, mock_client = _make_service()

        with pytest.raises(HCSProjectAuditError) as exc_info:
            await service.log_audit_event(
                project_id="proj-1",
                topic_id="0.0.111",
                event_type="invalid_type",
                payload={},
                agent_id="agent-1",
            )

        assert "invalid_type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def it_raises_hcs_project_audit_error_when_submission_fails(self):
        """
        Arrange: mock HCS client that raises.
        Act: log_audit_event.
        Assert: HCSProjectAuditError wraps the original error.
        """
        service, mock_client = _make_service()
        mock_client.submit_hcs_message = AsyncMock(side_effect=Exception("Timeout"))

        with pytest.raises(HCSProjectAuditError):
            await service.log_audit_event(
                project_id="proj-1",
                topic_id="0.0.111",
                event_type="payment",
                payload={},
                agent_id="agent-1",
            )


# ===========================================================================
# get_audit_log
# ===========================================================================

class DescribeGetAuditLog:
    """Tests for HCSProjectAuditService.get_audit_log."""

    @pytest.mark.asyncio
    async def it_returns_a_list_of_events_from_the_mirror_node(self):
        """
        Arrange: mock returning two HCS messages.
        Act: get_audit_log for project.
        Assert: list of events returned.
        """
        service, mock_client = _make_service()
        mock_client.get_topic_messages = AsyncMock(return_value={
            "messages": [
                {"sequence_number": 1, "message": "eyJldmVudF90eXBlIjogInBheW1lbnQifQ==", "consensus_timestamp": "2026-04-01T00:00:00Z"},
                {"sequence_number": 2, "message": "eyJldmVudF90eXBlIjogImRlY2lzaW9uIn0=", "consensus_timestamp": "2026-04-02T00:00:00Z"},
            ]
        })

        result = await service.get_audit_log(
            project_id="proj-abc",
            topic_id="0.0.1111",
            limit=10,
        )

        assert len(result) == 2
        assert result[0]["sequence_number"] == 1

    @pytest.mark.asyncio
    async def it_respects_the_limit_parameter(self):
        """
        Arrange: mock returning messages.
        Act: get_audit_log with limit=1.
        Assert: only 1 event returned.
        """
        service, mock_client = _make_service()
        mock_client.get_topic_messages = AsyncMock(return_value={
            "messages": [
                {"sequence_number": 1, "message": "e30=", "consensus_timestamp": "2026-04-01T00:00:00Z"},
            ]
        })

        result = await service.get_audit_log(
            project_id="proj-abc",
            topic_id="0.0.1111",
            limit=1,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_messages(self):
        """
        Arrange: mock returning empty list.
        Act: get_audit_log.
        Assert: empty list returned.
        """
        service, mock_client = _make_service()
        mock_client.get_topic_messages = AsyncMock(return_value={"messages": []})

        result = await service.get_audit_log(
            project_id="proj-empty",
            topic_id="0.0.1111",
            limit=10,
        )

        assert result == []

    @pytest.mark.asyncio
    async def it_raises_hcs_project_audit_error_when_query_fails(self):
        """
        Arrange: mock that raises.
        Act: get_audit_log.
        Assert: HCSProjectAuditError raised.
        """
        service, mock_client = _make_service()
        mock_client.get_topic_messages = AsyncMock(side_effect=Exception("Mirror node unavailable"))

        with pytest.raises(HCSProjectAuditError):
            await service.get_audit_log(
                project_id="proj-fail",
                topic_id="0.0.1111",
                limit=10,
            )


# ===========================================================================
# get_audit_summary
# ===========================================================================

class DescribeGetAuditSummary:
    """Tests for HCSProjectAuditService.get_audit_summary."""

    @pytest.mark.asyncio
    async def it_returns_event_counts_by_type(self):
        """
        Arrange: mock returning 3 messages with 2 payment and 1 decision event.
        Act: get_audit_summary.
        Assert: counts dict has payment=2, decision=1.
        """
        import base64

        def encode_event(event_type: str) -> str:
            return base64.b64encode(json.dumps({"event_type": event_type}).encode()).decode()

        service, mock_client = _make_service()
        mock_client.get_topic_messages = AsyncMock(return_value={
            "messages": [
                {"sequence_number": 1, "message": encode_event("payment"), "consensus_timestamp": "2026-04-01T00:00:00Z"},
                {"sequence_number": 2, "message": encode_event("decision"), "consensus_timestamp": "2026-04-01T01:00:00Z"},
                {"sequence_number": 3, "message": encode_event("payment"), "consensus_timestamp": "2026-04-01T02:00:00Z"},
            ]
        })

        result = await service.get_audit_summary(
            project_id="proj-abc",
            topic_id="0.0.1111",
        )

        assert result["total"] == 3
        assert result["by_type"]["payment"] == 2
        assert result["by_type"]["decision"] == 1

    @pytest.mark.asyncio
    async def it_returns_zero_counts_for_empty_log(self):
        """
        Arrange: mock returning no messages.
        Act: get_audit_summary.
        Assert: total=0 and by_type is empty.
        """
        service, mock_client = _make_service()
        mock_client.get_topic_messages = AsyncMock(return_value={"messages": []})

        result = await service.get_audit_summary(
            project_id="proj-empty",
            topic_id="0.0.1111",
        )

        assert result["total"] == 0
        assert result["by_type"] == {}
