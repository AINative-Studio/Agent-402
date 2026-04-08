"""
Tests for Hedera Audit API (Issue #268 Phase 2).

Covers:
- POST /hedera/audit/{project_id}/log — log an audit event
- GET /hedera/audit/{project_id} — retrieve audit log
- GET /hedera/audit/{project_id}/summary — get event counts by type

TDD Cycle: RED -> GREEN -> REFACTOR
BDD-style: class DescribeX / def it_does_something

Built by AINative Dev Team
Refs #268
"""
from __future__ import annotations

import json
from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Import the router under test
from app.api.hedera_audit import router
from fastapi import FastAPI

# ---------------------------------------------------------------------------
# Test app setup
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(router)

client = TestClient(app, raise_server_exceptions=False)

API_KEY = "test-key"
HEADERS = {"X-API-Key": API_KEY}
PROJECT_ID = "proj-test-audit"
TOPIC_ID = "0.0.7777"


# ===========================================================================
# POST /hedera/audit/{project_id}/log
# ===========================================================================

class DescribeLogAuditEventEndpoint:
    """Tests for POST /hedera/audit/{project_id}/log."""

    def it_returns_201_with_sequence_number_on_success(self):
        """
        Arrange: mock HCSProjectAuditService returning sequence_number.
        Act: POST /hedera/audit/{project_id}/log with valid payload.
        Assert: HTTP 201 and sequence_number in response.
        """
        mock_service = AsyncMock()
        mock_service.log_audit_event = AsyncMock(return_value={"sequence_number": 5})

        with patch("app.api.hedera_audit.get_audit_service", return_value=mock_service):
            response = client.post(
                f"/hedera/audit/{PROJECT_ID}/log",
                json={
                    "topic_id": TOPIC_ID,
                    "event_type": "payment",
                    "payload": {"amount": 10.0},
                    "agent_id": "agent-001",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["sequence_number"] == 5

    def it_returns_400_for_invalid_event_type(self):
        """
        Arrange: mock service raising HCSProjectAuditError for bad event_type.
        Act: POST with invalid event_type.
        Assert: HTTP 400.
        """
        from app.services.hcs_project_audit_service import HCSProjectAuditError

        mock_service = AsyncMock()
        mock_service.log_audit_event = AsyncMock(
            side_effect=HCSProjectAuditError("Invalid event type: foobar")
        )

        with patch("app.api.hedera_audit.get_audit_service", return_value=mock_service):
            response = client.post(
                f"/hedera/audit/{PROJECT_ID}/log",
                json={
                    "topic_id": TOPIC_ID,
                    "event_type": "foobar",
                    "payload": {},
                    "agent_id": "agent-001",
                },
            )

        assert response.status_code == 400

    def it_returns_422_when_required_fields_missing(self):
        """
        Arrange: no mock needed — validation happens before service call.
        Act: POST with missing required fields.
        Assert: HTTP 422.
        """
        response = client.post(
            f"/hedera/audit/{PROJECT_ID}/log",
            json={"event_type": "payment"},  # missing topic_id, payload, agent_id
        )
        assert response.status_code == 422


# ===========================================================================
# GET /hedera/audit/{project_id}
# ===========================================================================

class DescribeGetAuditLogEndpoint:
    """Tests for GET /hedera/audit/{project_id}."""

    def it_returns_200_with_list_of_events(self):
        """
        Arrange: mock service returning 2 events.
        Act: GET /hedera/audit/{project_id}?topic_id=...
        Assert: HTTP 200 and events list in response.
        """
        mock_service = AsyncMock()
        mock_service.get_audit_log = AsyncMock(return_value=[
            {"sequence_number": 1, "event_type": "payment", "consensus_timestamp": "2026-04-01T00:00:00Z"},
            {"sequence_number": 2, "event_type": "decision", "consensus_timestamp": "2026-04-02T00:00:00Z"},
        ])

        with patch("app.api.hedera_audit.get_audit_service", return_value=mock_service):
            response = client.get(
                f"/hedera/audit/{PROJECT_ID}",
                params={"topic_id": TOPIC_ID},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2

    def it_returns_200_with_empty_list_when_no_events(self):
        """
        Arrange: mock service returning empty list.
        Act: GET /hedera/audit/{project_id}?topic_id=...
        Assert: HTTP 200 and empty events list.
        """
        mock_service = AsyncMock()
        mock_service.get_audit_log = AsyncMock(return_value=[])

        with patch("app.api.hedera_audit.get_audit_service", return_value=mock_service):
            response = client.get(
                f"/hedera/audit/{PROJECT_ID}",
                params={"topic_id": TOPIC_ID},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []

    def it_passes_limit_query_parameter_to_service(self):
        """
        Arrange: mock service.
        Act: GET /hedera/audit/{project_id}?topic_id=...&limit=5.
        Assert: service get_audit_log called with limit=5.
        """
        mock_service = AsyncMock()
        mock_service.get_audit_log = AsyncMock(return_value=[])

        with patch("app.api.hedera_audit.get_audit_service", return_value=mock_service):
            client.get(
                f"/hedera/audit/{PROJECT_ID}",
                params={"topic_id": TOPIC_ID, "limit": 5},
            )

        call_kwargs = mock_service.get_audit_log.call_args
        call_str = str(call_kwargs)
        assert "5" in call_str

    def it_returns_422_when_topic_id_missing(self):
        """
        Arrange: no mock needed.
        Act: GET without topic_id param.
        Assert: HTTP 422.
        """
        response = client.get(f"/hedera/audit/{PROJECT_ID}")
        assert response.status_code == 422


# ===========================================================================
# GET /hedera/audit/{project_id}/summary
# ===========================================================================

class DescribeGetAuditSummaryEndpoint:
    """Tests for GET /hedera/audit/{project_id}/summary."""

    def it_returns_200_with_total_and_by_type(self):
        """
        Arrange: mock service returning summary.
        Act: GET /hedera/audit/{project_id}/summary?topic_id=...
        Assert: HTTP 200 with total and by_type fields.
        """
        mock_service = AsyncMock()
        mock_service.get_audit_summary = AsyncMock(return_value={
            "total": 3,
            "by_type": {"payment": 2, "decision": 1},
        })

        with patch("app.api.hedera_audit.get_audit_service", return_value=mock_service):
            response = client.get(
                f"/hedera/audit/{PROJECT_ID}/summary",
                params={"topic_id": TOPIC_ID},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["by_type"]["payment"] == 2

    def it_returns_200_with_zero_total_for_empty_log(self):
        """
        Arrange: mock service returning zero summary.
        Act: GET /hedera/audit/{project_id}/summary?topic_id=...
        Assert: HTTP 200, total=0, by_type={}.
        """
        mock_service = AsyncMock()
        mock_service.get_audit_summary = AsyncMock(return_value={
            "total": 0,
            "by_type": {},
        })

        with patch("app.api.hedera_audit.get_audit_service", return_value=mock_service):
            response = client.get(
                f"/hedera/audit/{PROJECT_ID}/summary",
                params={"topic_id": TOPIC_ID},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["by_type"] == {}
