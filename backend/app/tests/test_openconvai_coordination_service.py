"""
Tests for OpenConvAI HCS-10 Coordination Service.

Issue #205: CrewAI Multi-Agent Coordination via HCS-10.

TDD Red phase: tests define the contract for OpenConvAICoordinationService
before the implementation is written.

Built by AINative Dev Team
Refs #205
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKFLOW_ID = "wf-test-001"
ANALYST_DID = "did:hedera:testnet:z6MkAnalyst"
COMPLIANCE_DID = "did:hedera:testnet:z6MkCompliance"
TRANSACTION_DID = "did:hedera:testnet:z6MkTransaction"

SAMPLE_STAGES = [
    {
        "name": "analyst_review",
        "agent_did": ANALYST_DID,
        "inputs": {"query": "BTC market analysis"},
    },
    {
        "name": "compliance_check",
        "agent_did": COMPLIANCE_DID,
        "inputs": {"risk_threshold": 0.5},
    },
    {
        "name": "transaction_execute",
        "agent_did": TRANSACTION_DID,
        "inputs": {"amount": 100},
    },
]


@pytest.fixture
def mock_messaging_service():
    """Mock OpenConvAIMessagingService."""
    svc = AsyncMock()
    svc.send_message = AsyncMock(return_value={
        "transaction_id": "0.0.12345@9999.000000000",
        "status": "SUCCESS",
        "conversation_id": "conv-coord-001",
    })
    svc.create_conversation = AsyncMock(return_value={
        "conversation_id": "conv-coord-001",
        "status": "active",
        "participants": [ANALYST_DID, COMPLIANCE_DID, TRANSACTION_DID],
    })
    return svc


@pytest.fixture
def coordination_service(mock_messaging_service):
    """OpenConvAICoordinationService with mocked messaging service."""
    from app.services.openconvai_coordination_service import (
        OpenConvAICoordinationService,
    )
    return OpenConvAICoordinationService(messaging_service=mock_messaging_service)


# ---------------------------------------------------------------------------
# DescribeCoordinateWorkflow
# ---------------------------------------------------------------------------

class DescribeCoordinateWorkflow:
    """Tests for OpenConvAICoordinationService.coordinate_workflow."""

    @pytest.mark.asyncio
    async def it_returns_a_workflow_status_with_the_workflow_id(
        self, coordination_service
    ):
        """coordinate_workflow returns a dict with workflow_id."""
        result = await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        assert result["workflow_id"] == WORKFLOW_ID

    @pytest.mark.asyncio
    async def it_initialises_all_stages_with_pending_status(
        self, coordination_service
    ):
        """coordinate_workflow initialises every stage with status 'pending'."""
        result = await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        for stage_name in ["analyst_review", "compliance_check", "transaction_execute"]:
            assert stage_name in result["stages"]
            assert result["stages"][stage_name]["status"] == "pending"

    @pytest.mark.asyncio
    async def it_sends_coordination_messages_for_each_stage(
        self, coordination_service, mock_messaging_service
    ):
        """coordinate_workflow sends an HCS-10 coordination message per stage."""
        await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        # One coordination message per stage
        assert mock_messaging_service.send_message.await_count >= len(SAMPLE_STAGES)

    @pytest.mark.asyncio
    async def it_sends_coordination_message_type(
        self, coordination_service, mock_messaging_service
    ):
        """coordinate_workflow uses message_type='coordination' for stage messages."""
        await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        calls = mock_messaging_service.send_message.call_args_list
        coordination_calls = [
            c for c in calls
            if c[1].get("message_type") == "coordination"
            or (len(c[0]) > 2 and c[0][2] == "coordination")
        ]
        assert len(coordination_calls) > 0

    @pytest.mark.asyncio
    async def it_sets_overall_status_to_initiated(
        self, coordination_service
    ):
        """coordinate_workflow returns status 'initiated' immediately."""
        result = await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        assert result["status"] == "initiated"


# ---------------------------------------------------------------------------
# DescribeSubmitStageResult
# ---------------------------------------------------------------------------

class DescribeSubmitStageResult:
    """Tests for OpenConvAICoordinationService.submit_stage_result."""

    @pytest.mark.asyncio
    async def it_records_the_stage_result_and_updates_status(
        self, coordination_service
    ):
        """submit_stage_result returns a record with stage_name and 'completed' status."""
        await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        result = await coordination_service.submit_stage_result(
            workflow_id=WORKFLOW_ID,
            stage_name="analyst_review",
            agent_did=ANALYST_DID,
            result={"quality_score": 0.95, "recommendation": "proceed"},
        )
        assert result["stage_name"] == "analyst_review"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def it_sends_a_coordination_message_for_stage_completion(
        self, coordination_service, mock_messaging_service
    ):
        """submit_stage_result sends an HCS-10 message announcing stage completion."""
        await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        call_count_before = mock_messaging_service.send_message.await_count
        await coordination_service.submit_stage_result(
            workflow_id=WORKFLOW_ID,
            stage_name="analyst_review",
            agent_did=ANALYST_DID,
            result={"quality_score": 0.95},
        )
        assert mock_messaging_service.send_message.await_count > call_count_before

    @pytest.mark.asyncio
    async def it_stores_the_result_payload_on_the_stage(
        self, coordination_service
    ):
        """submit_stage_result stores result in the returned record."""
        await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        result = await coordination_service.submit_stage_result(
            workflow_id=WORKFLOW_ID,
            stage_name="analyst_review",
            agent_did=ANALYST_DID,
            result={"quality_score": 0.95},
        )
        assert result["result"]["quality_score"] == 0.95


# ---------------------------------------------------------------------------
# DescribeGetWorkflowStatus
# ---------------------------------------------------------------------------

class DescribeGetWorkflowStatus:
    """Tests for OpenConvAICoordinationService.get_workflow_status."""

    @pytest.mark.asyncio
    async def it_returns_workflow_id_and_all_stage_statuses(
        self, coordination_service
    ):
        """get_workflow_status returns complete stage map for the workflow."""
        await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        status = await coordination_service.get_workflow_status(WORKFLOW_ID)
        assert status["workflow_id"] == WORKFLOW_ID
        assert "stages" in status
        assert len(status["stages"]) == len(SAMPLE_STAGES)

    @pytest.mark.asyncio
    async def it_reflects_completed_stages_after_submission(
        self, coordination_service
    ):
        """get_workflow_status shows 'completed' after submit_stage_result."""
        await coordination_service.coordinate_workflow(
            workflow_id=WORKFLOW_ID,
            stages=SAMPLE_STAGES,
        )
        await coordination_service.submit_stage_result(
            workflow_id=WORKFLOW_ID,
            stage_name="analyst_review",
            agent_did=ANALYST_DID,
            result={"quality_score": 0.95},
        )
        status = await coordination_service.get_workflow_status(WORKFLOW_ID)
        assert status["stages"]["analyst_review"]["status"] == "completed"

    @pytest.mark.asyncio
    async def it_raises_for_unknown_workflow_id(
        self, coordination_service
    ):
        """get_workflow_status raises ValueError for unknown workflow_id."""
        with pytest.raises((ValueError, KeyError)):
            await coordination_service.get_workflow_status("nonexistent-wf")
