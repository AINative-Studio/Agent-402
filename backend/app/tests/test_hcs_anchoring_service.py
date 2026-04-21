"""
Tests for HCS Anchoring Service (Issues #200, #201, #202, #203, #356).

Covers:
- Issue #200: Memory operation anchoring to HCS
- Issue #201: Compliance event anchoring to HCS
- Issue #202: Memory integrity verification against HCS anchors
- Issue #203: Consolidation output anchoring to HCS
- Issue #356: HCSAnchoringService passes topic_id to HederaClient.submit_hcs_message

TDD Cycle: RED -> GREEN -> REFACTOR
BDD-style: class DescribeX / def it_does_something

Built by AINative Dev Team
Refs #200, #201, #202, #203, #356
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.hcs_anchoring_service import HCSAnchoringService, HCSAnchoringError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(content: str) -> str:
    """Compute SHA-256 hex digest for given content."""
    return hashlib.sha256(content.encode()).hexdigest()


def _make_service() -> HCSAnchoringService:
    """Return a service wired to a fresh mock HCS client."""
    mock_hcs = AsyncMock()
    return HCSAnchoringService(hcs_client=mock_hcs)


# ===========================================================================
# Issue #200 — Memory Anchoring
# ===========================================================================

class DescribeAnchorMemory:
    """Tests for HCSAnchoringService.anchor_memory (Issue #200)."""

    @pytest.mark.asyncio
    async def it_submits_a_memory_anchor_message_to_hcs(self):
        """
        Arrange: service with a mock HCS client that returns a sequence number.
        Act: call anchor_memory with valid params.
        Assert: HCS submit was called with the expected message payload.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 42})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        content_hash = _sha256("test memory content")
        result = await service.anchor_memory(
            memory_id="mem_abc123",
            content_hash=content_hash,
            agent_id="agent_001",
            namespace="default",
        )

        mock_hcs.submit_hcs_message.assert_called_once()
        call_kwargs = mock_hcs.submit_hcs_message.call_args
        message = call_kwargs[1].get("message") or call_kwargs[0][0]

        assert message["type"] == "memory_anchor"
        assert message["memory_id"] == "mem_abc123"
        assert message["content_hash"] == content_hash
        assert message["agent_id"] == "agent_001"
        assert message["namespace"] == "default"
        assert "timestamp" in message

    @pytest.mark.asyncio
    async def it_returns_the_hcs_sequence_number(self):
        """
        Arrange: HCS client returns sequence_number 99.
        Act: call anchor_memory.
        Assert: returned dict contains sequence_number == 99.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 99})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        content_hash = _sha256("some content")
        result = await service.anchor_memory(
            memory_id="mem_xyz",
            content_hash=content_hash,
            agent_id="agent_002",
            namespace="ns_a",
        )

        assert result["sequence_number"] == 99

    @pytest.mark.asyncio
    async def it_returns_memory_id_in_anchor_result(self):
        """
        Arrange: any HCS client mock.
        Act: anchor_memory with memory_id = "mem_return_test".
        Assert: result["memory_id"] == "mem_return_test".
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 1})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.anchor_memory(
            memory_id="mem_return_test",
            content_hash=_sha256("data"),
            agent_id="agent_003",
            namespace="ns_b",
        )

        assert result["memory_id"] == "mem_return_test"

    @pytest.mark.asyncio
    async def it_raises_hcs_anchoring_error_when_hcs_client_fails(self):
        """
        Arrange: HCS client raises RuntimeError.
        Act: call anchor_memory.
        Assert: HCSAnchoringError is raised.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(side_effect=RuntimeError("HCS unavailable"))
        service = HCSAnchoringService(hcs_client=mock_hcs)

        with pytest.raises(HCSAnchoringError):
            await service.anchor_memory(
                memory_id="mem_fail",
                content_hash=_sha256("x"),
                agent_id="agent_err",
                namespace="default",
            )

    @pytest.mark.asyncio
    async def it_includes_timestamp_in_hcs_message(self):
        """
        Arrange: valid HCS mock.
        Act: anchor_memory.
        Assert: submitted message has non-empty timestamp string.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 5})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        await service.anchor_memory(
            memory_id="mem_ts",
            content_hash=_sha256("ts test"),
            agent_id="agent_ts",
            namespace="default",
        )

        call_kwargs = mock_hcs.submit_hcs_message.call_args
        message = call_kwargs[1].get("message") or call_kwargs[0][0]
        assert isinstance(message["timestamp"], str)
        assert len(message["timestamp"]) > 0


# ===========================================================================
# Issue #200 — Get Anchor
# ===========================================================================

class DescribeGetAnchor:
    """Tests for HCSAnchoringService.get_anchor (Issue #200)."""

    @pytest.mark.asyncio
    async def it_returns_anchor_record_when_found(self):
        """
        Arrange: HCS client returns a stored anchor for memory_id.
        Act: call get_anchor.
        Assert: returned dict contains memory_id and content_hash.
        """
        mock_hcs = AsyncMock()
        anchor_data = {
            "memory_id": "mem_found",
            "content_hash": _sha256("stored content"),
            "sequence_number": 10,
            "timestamp": "2026-04-03T00:00:00Z",
            "agent_id": "agent_x",
            "namespace": "default",
        }
        mock_hcs.get_hcs_message = AsyncMock(return_value=anchor_data)
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.get_anchor("mem_found")

        assert result is not None
        assert result["memory_id"] == "mem_found"
        assert "content_hash" in result

    @pytest.mark.asyncio
    async def it_returns_none_when_anchor_not_found(self):
        """
        Arrange: HCS client returns None (no anchor).
        Act: call get_anchor.
        Assert: returns None.
        """
        mock_hcs = AsyncMock()
        mock_hcs.get_hcs_message = AsyncMock(return_value=None)
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.get_anchor("mem_not_there")

        assert result is None


# ===========================================================================
# Issue #201 — Compliance Event Anchoring
# ===========================================================================

class DescribeAnchorComplianceEvent:
    """Tests for HCSAnchoringService.anchor_compliance_event (Issue #201)."""

    @pytest.mark.asyncio
    async def it_submits_a_compliance_anchor_message_to_hcs(self):
        """
        Arrange: mock HCS client.
        Act: anchor_compliance_event with valid params.
        Assert: submitted message type is "compliance_anchor".
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 77})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.anchor_compliance_event(
            event_id="evt_001",
            event_type="KYC_CHECK",
            classification="PASS",
            risk_score=0.1,
            agent_id="compliance_agent",
        )

        mock_hcs.submit_hcs_message.assert_called_once()
        call_kwargs = mock_hcs.submit_hcs_message.call_args
        message = call_kwargs[1].get("message") or call_kwargs[0][0]

        assert message["type"] == "compliance_anchor"

    @pytest.mark.asyncio
    async def it_includes_all_required_fields_in_compliance_message(self):
        """
        Arrange: mock HCS client.
        Act: anchor_compliance_event.
        Assert: message has event_id, event_hash, event_type, classification,
                risk_score, agent_id, timestamp.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 22})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        await service.anchor_compliance_event(
            event_id="evt_fields",
            event_type="KYT_CHECK",
            classification="FAIL",
            risk_score=0.85,
            agent_id="kyt_agent",
        )

        call_kwargs = mock_hcs.submit_hcs_message.call_args
        message = call_kwargs[1].get("message") or call_kwargs[0][0]

        assert "event_id" in message
        assert "event_hash" in message
        assert "event_type" in message
        assert "classification" in message
        assert "risk_score" in message
        assert "agent_id" in message
        assert "timestamp" in message

    @pytest.mark.asyncio
    async def it_computes_event_hash_from_event_fields(self):
        """
        Arrange: mock HCS client.
        Act: anchor_compliance_event twice with same params.
        Assert: event_hash is deterministic (same hash both times).
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 5})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        params = dict(
            event_id="evt_deterministic",
            event_type="RISK_ASSESSMENT",
            classification="PENDING",
            risk_score=0.5,
            agent_id="risk_agent",
        )

        await service.anchor_compliance_event(**params)
        first_message = (
            mock_hcs.submit_hcs_message.call_args[1].get("message")
            or mock_hcs.submit_hcs_message.call_args[0][0]
        )
        hash_1 = first_message["event_hash"]

        mock_hcs.submit_hcs_message.reset_mock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 6})

        await service.anchor_compliance_event(**params)
        second_message = (
            mock_hcs.submit_hcs_message.call_args[1].get("message")
            or mock_hcs.submit_hcs_message.call_args[0][0]
        )
        hash_2 = second_message["event_hash"]

        assert hash_1 == hash_2

    @pytest.mark.asyncio
    async def it_returns_sequence_number_from_compliance_anchor(self):
        """
        Arrange: HCS client returns sequence_number 55.
        Act: anchor_compliance_event.
        Assert: result["sequence_number"] == 55.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 55})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.anchor_compliance_event(
            event_id="evt_ret",
            event_type="AUDIT_LOG",
            classification="PASS",
            risk_score=0.0,
            agent_id="audit_agent",
        )

        assert result["sequence_number"] == 55

    @pytest.mark.asyncio
    async def it_raises_hcs_anchoring_error_when_compliance_submit_fails(self):
        """
        Arrange: HCS client raises Exception.
        Act: anchor_compliance_event.
        Assert: HCSAnchoringError is raised.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(side_effect=Exception("network error"))
        service = HCSAnchoringService(hcs_client=mock_hcs)

        with pytest.raises(HCSAnchoringError):
            await service.anchor_compliance_event(
                event_id="evt_fail",
                event_type="KYC_CHECK",
                classification="ERROR",
                risk_score=0.99,
                agent_id="agent_fail",
            )


# ===========================================================================
# Issue #202 — Memory Integrity Verification
# ===========================================================================

class DescribeVerifyMemoryIntegrity:
    """Tests for HCSAnchoringService.verify_memory_integrity (Issue #202)."""

    @pytest.mark.asyncio
    async def it_returns_verified_true_when_hashes_match(self):
        """
        Arrange: anchor has hash H; current content also hashes to H.
        Act: verify_memory_integrity.
        Assert: result["verified"] == True and result["match"] == True.
        """
        content = "exact same content"
        stored_hash = _sha256(content)

        mock_hcs = AsyncMock()
        mock_hcs.get_hcs_message = AsyncMock(return_value={
            "memory_id": "mem_match",
            "content_hash": stored_hash,
            "timestamp": "2026-04-03T00:00:00Z",
        })
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.verify_memory_integrity("mem_match", content)

        assert result["verified"] is True
        assert result["match"] is True

    @pytest.mark.asyncio
    async def it_returns_verified_false_when_hashes_differ(self):
        """
        Arrange: anchor stores hash for "original content";
                 current content is "tampered content".
        Act: verify_memory_integrity.
        Assert: result["verified"] == False and result["match"] == False.
        """
        original_hash = _sha256("original content")
        mock_hcs = AsyncMock()
        mock_hcs.get_hcs_message = AsyncMock(return_value={
            "memory_id": "mem_tampered",
            "content_hash": original_hash,
            "timestamp": "2026-04-03T00:00:00Z",
        })
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.verify_memory_integrity("mem_tampered", "tampered content")

        assert result["verified"] is False
        assert result["match"] is False

    @pytest.mark.asyncio
    async def it_returns_no_anchor_found_reason_when_anchor_is_missing(self):
        """
        Arrange: HCS client returns None for any memory_id.
        Act: verify_memory_integrity.
        Assert: result["verified"] == False and result["reason"] == "no_anchor_found".
        """
        mock_hcs = AsyncMock()
        mock_hcs.get_hcs_message = AsyncMock(return_value=None)
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.verify_memory_integrity("mem_missing", "some content")

        assert result["verified"] is False
        assert result["reason"] == "no_anchor_found"

    @pytest.mark.asyncio
    async def it_includes_both_hashes_in_successful_verification(self):
        """
        Arrange: anchor with known hash; current content.
        Act: verify_memory_integrity.
        Assert: result contains anchor_hash and current_hash.
        """
        content = "content for hash test"
        stored_hash = _sha256(content)
        mock_hcs = AsyncMock()
        mock_hcs.get_hcs_message = AsyncMock(return_value={
            "memory_id": "mem_hashes",
            "content_hash": stored_hash,
            "timestamp": "2026-04-03T00:00:00Z",
        })
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.verify_memory_integrity("mem_hashes", content)

        assert "anchor_hash" in result
        assert "current_hash" in result
        assert result["anchor_hash"] == stored_hash
        assert result["current_hash"] == _sha256(content)

    @pytest.mark.asyncio
    async def it_includes_anchor_timestamp_in_verification_result(self):
        """
        Arrange: anchor with timestamp "2026-04-03T00:00:00Z".
        Act: verify_memory_integrity.
        Assert: result["anchor_timestamp"] == "2026-04-03T00:00:00Z".
        """
        content = "timestamped content"
        stored_hash = _sha256(content)
        mock_hcs = AsyncMock()
        mock_hcs.get_hcs_message = AsyncMock(return_value={
            "memory_id": "mem_ts_verify",
            "content_hash": stored_hash,
            "timestamp": "2026-04-03T00:00:00Z",
        })
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.verify_memory_integrity("mem_ts_verify", content)

        assert result["anchor_timestamp"] == "2026-04-03T00:00:00Z"

    @pytest.mark.asyncio
    async def it_computes_sha256_of_current_content(self):
        """
        Arrange: anchor with hash that doesn't match.
        Act: verify_memory_integrity with known content.
        Assert: result["current_hash"] equals SHA-256 of that content.
        """
        known_content = "deterministic content for SHA test"
        expected_hash = _sha256(known_content)
        stored_hash = _sha256("different content")

        mock_hcs = AsyncMock()
        mock_hcs.get_hcs_message = AsyncMock(return_value={
            "memory_id": "mem_sha",
            "content_hash": stored_hash,
            "timestamp": "2026-01-01T00:00:00Z",
        })
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.verify_memory_integrity("mem_sha", known_content)

        assert result["current_hash"] == expected_hash


# ===========================================================================
# Issue #203 — Consolidation Output Anchoring
# ===========================================================================

class DescribeAnchorConsolidation:
    """Tests for HCSAnchoringService.anchor_consolidation (Issue #203)."""

    @pytest.mark.asyncio
    async def it_submits_a_consolidation_anchor_message_to_hcs(self):
        """
        Arrange: mock HCS client.
        Act: anchor_consolidation with valid params.
        Assert: submitted message type is "consolidation_anchor".
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 33})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        await service.anchor_consolidation(
            consolidation_id="cons_001",
            synthesis_hash=_sha256("synthesis output"),
            source_memory_ids=["mem_a", "mem_b"],
            model_used="nous-codestral-22b",
        )

        mock_hcs.submit_hcs_message.assert_called_once()
        call_kwargs = mock_hcs.submit_hcs_message.call_args
        message = call_kwargs[1].get("message") or call_kwargs[0][0]

        assert message["type"] == "consolidation_anchor"

    @pytest.mark.asyncio
    async def it_includes_all_required_fields_in_consolidation_message(self):
        """
        Arrange: mock HCS client.
        Act: anchor_consolidation.
        Assert: message has consolidation_id, synthesis_hash, source_memory_ids,
                model_used, timestamp.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 11})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        await service.anchor_consolidation(
            consolidation_id="cons_fields",
            synthesis_hash=_sha256("synthesis"),
            source_memory_ids=["mem_1", "mem_2", "mem_3"],
            model_used="nous-hermes-2",
        )

        call_kwargs = mock_hcs.submit_hcs_message.call_args
        message = call_kwargs[1].get("message") or call_kwargs[0][0]

        assert "consolidation_id" in message
        assert "synthesis_hash" in message
        assert "source_memory_ids" in message
        assert "model_used" in message
        assert "timestamp" in message

    @pytest.mark.asyncio
    async def it_preserves_source_memory_ids_list_in_message(self):
        """
        Arrange: source_memory_ids = ["mem_x", "mem_y"].
        Act: anchor_consolidation.
        Assert: message["source_memory_ids"] == ["mem_x", "mem_y"].
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 7})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        await service.anchor_consolidation(
            consolidation_id="cons_ids",
            synthesis_hash=_sha256("out"),
            source_memory_ids=["mem_x", "mem_y"],
            model_used="llama-3",
        )

        call_kwargs = mock_hcs.submit_hcs_message.call_args
        message = call_kwargs[1].get("message") or call_kwargs[0][0]

        assert message["source_memory_ids"] == ["mem_x", "mem_y"]

    @pytest.mark.asyncio
    async def it_returns_sequence_number_from_consolidation_anchor(self):
        """
        Arrange: HCS returns sequence_number 88.
        Act: anchor_consolidation.
        Assert: result["sequence_number"] == 88.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 88})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.anchor_consolidation(
            consolidation_id="cons_ret",
            synthesis_hash=_sha256("ret"),
            source_memory_ids=[],
            model_used="nous-codestral-22b",
        )

        assert result["sequence_number"] == 88

    @pytest.mark.asyncio
    async def it_returns_consolidation_id_in_anchor_result(self):
        """
        Arrange: anchor_consolidation with consolidation_id = "cons_known".
        Act: call method.
        Assert: result["consolidation_id"] == "cons_known".
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(return_value={"sequence_number": 1})
        service = HCSAnchoringService(hcs_client=mock_hcs)

        result = await service.anchor_consolidation(
            consolidation_id="cons_known",
            synthesis_hash=_sha256("data"),
            source_memory_ids=["mem_z"],
            model_used="model_v1",
        )

        assert result["consolidation_id"] == "cons_known"

    @pytest.mark.asyncio
    async def it_raises_hcs_anchoring_error_when_consolidation_submit_fails(self):
        """
        Arrange: HCS client raises Exception.
        Act: anchor_consolidation.
        Assert: HCSAnchoringError is raised.
        """
        mock_hcs = AsyncMock()
        mock_hcs.submit_hcs_message = AsyncMock(side_effect=Exception("timeout"))
        service = HCSAnchoringService(hcs_client=mock_hcs)

        with pytest.raises(HCSAnchoringError):
            await service.anchor_consolidation(
                consolidation_id="cons_fail",
                synthesis_hash=_sha256("fail"),
                source_memory_ids=[],
                model_used="model_err",
            )


# ===========================================================================
# Integration-style: full anchor -> verify round trip
# ===========================================================================

class DescribeAnchorAndVerifyRoundTrip:
    """Integration-style round-trip tests for anchor + verify (Issues #200, #202)."""

    @pytest.mark.asyncio
    async def it_verifies_integrity_after_anchoring_memory(self):
        """
        Arrange: anchor memory; configure HCS get_hcs_message to return the anchored data.
        Act: verify_memory_integrity with same content.
        Assert: verification passes.
        """
        content = "round trip content"
        content_hash = _sha256(content)

        submitted_messages: List[Dict[str, Any]] = []

        async def fake_submit(message: Dict[str, Any]) -> Dict[str, Any]:
            submitted_messages.append(message)
            return {"sequence_number": len(submitted_messages)}

        async def fake_get(memory_id: str) -> Optional[Dict[str, Any]]:
            for msg in submitted_messages:
                if msg.get("memory_id") == memory_id:
                    return {
                        "memory_id": msg["memory_id"],
                        "content_hash": msg["content_hash"],
                        "timestamp": msg["timestamp"],
                    }
            return None

        mock_hcs = MagicMock()
        mock_hcs.submit_hcs_message = fake_submit
        mock_hcs.get_hcs_message = fake_get

        service = HCSAnchoringService(hcs_client=mock_hcs)

        await service.anchor_memory(
            memory_id="mem_roundtrip",
            content_hash=content_hash,
            agent_id="agent_rt",
            namespace="default",
        )

        result = await service.verify_memory_integrity("mem_roundtrip", content)

        assert result["verified"] is True
        assert result["match"] is True

    @pytest.mark.asyncio
    async def it_detects_tampering_after_anchor(self):
        """
        Arrange: anchor with original content; verify with tampered content.
        Assert: verification fails with match == False.
        """
        original = "original untampered content"
        tampered = "tampered content"
        original_hash = _sha256(original)

        submitted_messages: List[Dict[str, Any]] = []

        async def fake_submit(message: Dict[str, Any]) -> Dict[str, Any]:
            submitted_messages.append(message)
            return {"sequence_number": 1}

        async def fake_get(memory_id: str) -> Optional[Dict[str, Any]]:
            for msg in submitted_messages:
                if msg.get("memory_id") == memory_id:
                    return {
                        "memory_id": msg["memory_id"],
                        "content_hash": msg["content_hash"],
                        "timestamp": msg["timestamp"],
                    }
            return None

        mock_hcs = MagicMock()
        mock_hcs.submit_hcs_message = fake_submit
        mock_hcs.get_hcs_message = fake_get

        service = HCSAnchoringService(hcs_client=mock_hcs)

        await service.anchor_memory(
            memory_id="mem_tamper_detect",
            content_hash=original_hash,
            agent_id="agent_tamper",
            namespace="default",
        )

        result = await service.verify_memory_integrity("mem_tamper_detect", tampered)

        assert result["verified"] is False
        assert result["match"] is False


# ===========================================================================
# Issue #356 — HCSAnchoringService passes topic_id to HederaClient
# ===========================================================================

class DescribeHCSAnchoringServiceTopicId:
    """
    Tests that HCSAnchoringService always passes ``topic_id`` to
    ``HederaClient.submit_hcs_message`` (Issue #356).

    The real ``HederaClient.submit_hcs_message`` signature is
    ``submit_hcs_message(topic_id, message)``. Prior to #356 the service
    called the client with only ``message=...``, causing Tutorial 01 Step
    10 to fail with ``TypeError: submit_hcs_message() missing 1 required
    positional argument: 'topic_id'``.
    """

    class DescribeAnchorMemory:
        @pytest.mark.asyncio
        async def it_passes_topic_id_from_constructor_to_client(self):
            """Constructor-provided anchor_topic_id must reach the HCS client."""
            mock_client = AsyncMock()
            mock_client.submit_hcs_message = AsyncMock(
                return_value={
                    "sequence_number": 42,
                    "consensus_timestamp": "1700000000.000000000",
                    "topic_id": "0.0.800042",
                }
            )
            service = HCSAnchoringService(
                hcs_client=mock_client, anchor_topic_id="0.0.800042"
            )

            await service.anchor_memory(
                memory_id="m1",
                agent_id="a1",
                content_hash="abc",
                namespace="default",
            )

            mock_client.submit_hcs_message.assert_called_once()
            kwargs = mock_client.submit_hcs_message.call_args.kwargs
            assert kwargs["topic_id"] == "0.0.800042"

        @pytest.mark.asyncio
        async def it_defaults_topic_id_from_env_var_when_set(self):
            """When ``HEDERA_ANCHOR_TOPIC_ID`` is set, use it."""
            mock_client = AsyncMock()
            mock_client.submit_hcs_message = AsyncMock(
                return_value={"sequence_number": 1}
            )

            with patch.dict(
                os.environ, {"HEDERA_ANCHOR_TOPIC_ID": "0.0.777777"}, clear=False
            ):
                service = HCSAnchoringService(hcs_client=mock_client)
                await service.anchor_memory(
                    memory_id="m2",
                    agent_id="a2",
                    content_hash="def",
                    namespace="default",
                )

            kwargs = mock_client.submit_hcs_message.call_args.kwargs
            assert kwargs["topic_id"] == "0.0.777777"

        @pytest.mark.asyncio
        async def it_falls_back_to_default_topic_id_when_env_unset(self):
            """When no env var and no constructor arg, use sensible default."""
            mock_client = AsyncMock()
            mock_client.submit_hcs_message = AsyncMock(
                return_value={"sequence_number": 1}
            )

            env_without_topic = {
                k: v for k, v in os.environ.items()
                if k != "HEDERA_ANCHOR_TOPIC_ID"
            }
            with patch.dict(os.environ, env_without_topic, clear=True):
                service = HCSAnchoringService(hcs_client=mock_client)
                await service.anchor_memory(
                    memory_id="m3",
                    agent_id="a3",
                    content_hash="ghi",
                    namespace="default",
                )

            kwargs = mock_client.submit_hcs_message.call_args.kwargs
            assert kwargs["topic_id"] == "0.0.800001"

        @pytest.mark.asyncio
        async def it_still_passes_the_message_payload_alongside_topic_id(self):
            """The message payload must remain intact alongside topic_id."""
            mock_client = AsyncMock()
            mock_client.submit_hcs_message = AsyncMock(
                return_value={"sequence_number": 9}
            )
            service = HCSAnchoringService(
                hcs_client=mock_client, anchor_topic_id="0.0.800001"
            )

            await service.anchor_memory(
                memory_id="m4",
                agent_id="a4",
                content_hash="jkl",
                namespace="default",
            )

            kwargs = mock_client.submit_hcs_message.call_args.kwargs
            assert kwargs["topic_id"] == "0.0.800001"
            assert kwargs["message"]["type"] == "memory_anchor"
            assert kwargs["message"]["memory_id"] == "m4"

    class DescribeAnchorComplianceEvent:
        @pytest.mark.asyncio
        async def it_passes_topic_id_on_compliance_anchor(self):
            mock_client = AsyncMock()
            mock_client.submit_hcs_message = AsyncMock(
                return_value={"sequence_number": 7}
            )
            service = HCSAnchoringService(
                hcs_client=mock_client, anchor_topic_id="0.0.800099"
            )

            await service.anchor_compliance_event(
                event_id="evt_topic",
                event_type="KYC_CHECK",
                classification="PASS",
                risk_score=0.1,
                agent_id="compliance_agent",
            )

            kwargs = mock_client.submit_hcs_message.call_args.kwargs
            assert kwargs["topic_id"] == "0.0.800099"

    class DescribeAnchorConsolidation:
        @pytest.mark.asyncio
        async def it_passes_topic_id_on_consolidation_anchor(self):
            mock_client = AsyncMock()
            mock_client.submit_hcs_message = AsyncMock(
                return_value={"sequence_number": 3}
            )
            service = HCSAnchoringService(
                hcs_client=mock_client, anchor_topic_id="0.0.800222"
            )

            await service.anchor_consolidation(
                consolidation_id="cons_topic",
                synthesis_hash=_sha256("out"),
                source_memory_ids=["m_a", "m_b"],
                model_used="nous-codestral-22b",
            )

            kwargs = mock_client.submit_hcs_message.call_args.kwargs
            assert kwargs["topic_id"] == "0.0.800222"
