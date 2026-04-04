"""
Tests for HCS Anchoring API endpoints (Issues #200, #201, #202, #203).

Covers all four REST endpoints:
- POST /anchor/memory
- POST /anchor/compliance
- GET  /anchor/{memory_id}/verify
- POST /anchor/consolidation

TDD Cycle: RED -> GREEN -> REFACTOR
BDD-style: class DescribeX / def it_does_something

Uses FastAPI dependency_overrides for clean service isolation,
consistent with the established pattern in this codebase.

Built by AINative Dev Team
Refs #200, #201, #202, #203
"""
from __future__ import annotations

import hashlib
from typing import Optional, Dict, Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.hcs_anchoring import router
from app.services.hcs_anchoring_service import HCSAnchoringService, HCSAnchoringError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _make_test_app() -> FastAPI:
    """Build a minimal FastAPI app that includes the HCS anchoring router."""
    app = FastAPI()
    app.include_router(router)
    return app


# ===========================================================================
# POST /anchor/memory
# ===========================================================================

class DescribePostAnchorMemory:
    """Tests for POST /anchor/memory (Issue #200)."""

    def it_returns_201_with_sequence_number_on_success(self):
        """
        Arrange: mock service returns anchor result with sequence_number.
        Act: POST /anchor/memory with valid body.
        Assert: HTTP 201, body contains sequence_number.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_memory.return_value = {
            "memory_id": "mem_api_001",
            "sequence_number": 42,
            "timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/anchor/memory",
            json={
                "memory_id": "mem_api_001",
                "content_hash": _sha256("content"),
                "agent_id": "agent_001",
                "namespace": "default",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["sequence_number"] == 42

    def it_returns_memory_id_in_anchor_memory_response(self):
        """
        Arrange: mock service returns memory_id in result.
        Act: POST /anchor/memory.
        Assert: response body contains memory_id.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_memory.return_value = {
            "memory_id": "mem_id_check",
            "sequence_number": 1,
            "timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/anchor/memory",
            json={
                "memory_id": "mem_id_check",
                "content_hash": _sha256("x"),
                "agent_id": "a",
                "namespace": "ns",
            },
        )

        assert response.status_code == 201
        assert response.json()["memory_id"] == "mem_id_check"

    def it_returns_422_when_required_fields_are_missing(self):
        """
        Arrange: POST body missing content_hash and agent_id.
        Act: POST /anchor/memory with incomplete body.
        Assert: HTTP 422.
        """
        app = _make_test_app()
        client = TestClient(app)

        response = client.post(
            "/anchor/memory",
            json={"memory_id": "mem_only"},
        )

        assert response.status_code == 422

    def it_returns_502_when_service_raises_hcs_anchoring_error(self):
        """
        Arrange: service.anchor_memory raises HCSAnchoringError.
        Act: POST /anchor/memory.
        Assert: HTTP 502.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_memory.side_effect = HCSAnchoringError("HCS unavailable")

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/anchor/memory",
            json={
                "memory_id": "mem_fail",
                "content_hash": _sha256("fail"),
                "agent_id": "agent_fail",
                "namespace": "default",
            },
        )

        assert response.status_code == 502

    def it_passes_all_fields_to_service_anchor_memory(self):
        """
        Arrange: mock service records what it was called with.
        Act: POST /anchor/memory with known field values.
        Assert: service.anchor_memory was called with correct arguments.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_memory.return_value = {
            "memory_id": "mem_passthrough",
            "sequence_number": 9,
            "timestamp": "2026-04-03T00:00:00Z",
        }
        known_hash = _sha256("known content")

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        client.post(
            "/anchor/memory",
            json={
                "memory_id": "mem_passthrough",
                "content_hash": known_hash,
                "agent_id": "agent_pass",
                "namespace": "ns_pass",
            },
        )

        mock_service.anchor_memory.assert_called_once_with(
            memory_id="mem_passthrough",
            content_hash=known_hash,
            agent_id="agent_pass",
            namespace="ns_pass",
        )


# ===========================================================================
# POST /anchor/compliance
# ===========================================================================

class DescribePostAnchorCompliance:
    """Tests for POST /anchor/compliance (Issue #201)."""

    def it_returns_201_with_sequence_number_on_success(self):
        """
        Arrange: mock service returns compliance anchor result.
        Act: POST /anchor/compliance.
        Assert: HTTP 201, sequence_number present.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_compliance_event.return_value = {
            "event_id": "evt_api_001",
            "sequence_number": 77,
            "timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/anchor/compliance",
            json={
                "event_id": "evt_api_001",
                "event_type": "KYC_CHECK",
                "classification": "PASS",
                "risk_score": 0.1,
                "agent_id": "compliance_agent",
            },
        )

        assert response.status_code == 201
        assert response.json()["sequence_number"] == 77

    def it_returns_event_id_in_compliance_anchor_response(self):
        """
        Arrange: mock service returns event_id.
        Act: POST /anchor/compliance.
        Assert: response body contains event_id.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_compliance_event.return_value = {
            "event_id": "evt_id_check",
            "sequence_number": 3,
            "timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/anchor/compliance",
            json={
                "event_id": "evt_id_check",
                "event_type": "KYT_CHECK",
                "classification": "FAIL",
                "risk_score": 0.9,
                "agent_id": "kyt_agent",
            },
        )

        assert response.status_code == 201
        assert response.json()["event_id"] == "evt_id_check"

    def it_returns_422_when_required_compliance_fields_are_missing(self):
        """
        Arrange: POST body missing event_type.
        Act: POST /anchor/compliance.
        Assert: HTTP 422.
        """
        app = _make_test_app()
        client = TestClient(app)

        response = client.post(
            "/anchor/compliance",
            json={"event_id": "evt_only"},
        )

        assert response.status_code == 422

    def it_returns_502_when_compliance_service_raises_hcs_anchoring_error(self):
        """
        Arrange: service raises HCSAnchoringError.
        Act: POST /anchor/compliance.
        Assert: HTTP 502.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_compliance_event.side_effect = HCSAnchoringError("HCS timeout")

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/anchor/compliance",
            json={
                "event_id": "evt_fail",
                "event_type": "AUDIT_LOG",
                "classification": "ERROR",
                "risk_score": 0.0,
                "agent_id": "agent_fail",
            },
        )

        assert response.status_code == 502

    def it_passes_all_fields_to_service_anchor_compliance_event(self):
        """
        Arrange: mock service records call arguments.
        Act: POST /anchor/compliance with known field values.
        Assert: service.anchor_compliance_event called with correct args.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_compliance_event.return_value = {
            "event_id": "evt_pass",
            "sequence_number": 12,
            "timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        client.post(
            "/anchor/compliance",
            json={
                "event_id": "evt_pass",
                "event_type": "RISK_ASSESSMENT",
                "classification": "PENDING",
                "risk_score": 0.5,
                "agent_id": "risk_agent",
            },
        )

        mock_service.anchor_compliance_event.assert_called_once_with(
            event_id="evt_pass",
            event_type="RISK_ASSESSMENT",
            classification="PENDING",
            risk_score=0.5,
            agent_id="risk_agent",
        )


# ===========================================================================
# GET /anchor/{memory_id}/verify
# ===========================================================================

class DescribeGetAnchorVerify:
    """Tests for GET /anchor/{memory_id}/verify (Issue #202)."""

    def it_returns_200_with_verified_true_when_integrity_passes(self):
        """
        Arrange: service returns verified=True.
        Act: GET /anchor/mem_001/verify?current_content=good
        Assert: HTTP 200, verified == True.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.verify_memory_integrity.return_value = {
            "verified": True,
            "match": True,
            "anchor_hash": _sha256("good"),
            "current_hash": _sha256("good"),
            "anchor_timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get(
            "/anchor/mem_001/verify",
            params={"current_content": "good"},
        )

        assert response.status_code == 200
        assert response.json()["verified"] is True

    def it_returns_200_with_verified_false_when_integrity_fails(self):
        """
        Arrange: service returns verified=False.
        Act: GET /anchor/mem_002/verify?current_content=tampered
        Assert: HTTP 200, verified == False.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.verify_memory_integrity.return_value = {
            "verified": False,
            "match": False,
            "anchor_hash": _sha256("original"),
            "current_hash": _sha256("tampered"),
            "anchor_timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get(
            "/anchor/mem_002/verify",
            params={"current_content": "tampered"},
        )

        assert response.status_code == 200
        assert response.json()["verified"] is False

    def it_returns_200_with_no_anchor_found_reason_when_anchor_missing(self):
        """
        Arrange: service returns no_anchor_found reason.
        Act: GET /anchor/mem_missing/verify?current_content=content
        Assert: HTTP 200, reason == "no_anchor_found".
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.verify_memory_integrity.return_value = {
            "verified": False,
            "reason": "no_anchor_found",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get(
            "/anchor/mem_missing/verify",
            params={"current_content": "content"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is False
        assert data["reason"] == "no_anchor_found"

    def it_returns_422_when_current_content_query_param_is_missing(self):
        """
        Arrange: GET without current_content query param.
        Act: GET /anchor/mem_001/verify.
        Assert: HTTP 422.
        """
        app = _make_test_app()
        client = TestClient(app)

        response = client.get("/anchor/mem_001/verify")

        assert response.status_code == 422

    def it_passes_memory_id_and_content_to_service(self):
        """
        Arrange: mock service records call arguments.
        Act: GET /anchor/mem_check/verify?current_content=test_content
        Assert: service.verify_memory_integrity called with correct args.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.verify_memory_integrity.return_value = {
            "verified": True,
            "match": True,
            "anchor_hash": _sha256("test_content"),
            "current_hash": _sha256("test_content"),
            "anchor_timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        client.get(
            "/anchor/mem_check/verify",
            params={"current_content": "test_content"},
        )

        mock_service.verify_memory_integrity.assert_called_once_with(
            memory_id="mem_check",
            current_content="test_content",
        )


# ===========================================================================
# POST /anchor/consolidation
# ===========================================================================

class DescribePostAnchorConsolidation:
    """Tests for POST /anchor/consolidation (Issue #203)."""

    def it_returns_201_with_sequence_number_on_success(self):
        """
        Arrange: mock service returns consolidation anchor result.
        Act: POST /anchor/consolidation.
        Assert: HTTP 201, sequence_number present.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_consolidation.return_value = {
            "consolidation_id": "cons_api_001",
            "sequence_number": 88,
            "timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/anchor/consolidation",
            json={
                "consolidation_id": "cons_api_001",
                "synthesis_hash": _sha256("synthesis"),
                "source_memory_ids": ["mem_a", "mem_b"],
                "model_used": "nous-codestral-22b",
            },
        )

        assert response.status_code == 201
        assert response.json()["sequence_number"] == 88

    def it_returns_consolidation_id_in_response(self):
        """
        Arrange: mock service returns consolidation_id.
        Act: POST /anchor/consolidation.
        Assert: response body contains consolidation_id.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_consolidation.return_value = {
            "consolidation_id": "cons_id_check",
            "sequence_number": 2,
            "timestamp": "2026-04-03T00:00:00Z",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/anchor/consolidation",
            json={
                "consolidation_id": "cons_id_check",
                "synthesis_hash": _sha256("s"),
                "source_memory_ids": [],
                "model_used": "model_v1",
            },
        )

        assert response.status_code == 201
        assert response.json()["consolidation_id"] == "cons_id_check"

    def it_returns_422_when_required_consolidation_fields_are_missing(self):
        """
        Arrange: POST body missing synthesis_hash.
        Act: POST /anchor/consolidation.
        Assert: HTTP 422.
        """
        app = _make_test_app()
        client = TestClient(app)

        response = client.post(
            "/anchor/consolidation",
            json={"consolidation_id": "cons_only"},
        )

        assert response.status_code == 422

    def it_returns_502_when_consolidation_service_raises_hcs_anchoring_error(self):
        """
        Arrange: service raises HCSAnchoringError.
        Act: POST /anchor/consolidation.
        Assert: HTTP 502.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_consolidation.side_effect = HCSAnchoringError("HCS error")

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/anchor/consolidation",
            json={
                "consolidation_id": "cons_fail",
                "synthesis_hash": _sha256("fail"),
                "source_memory_ids": ["mem_1"],
                "model_used": "model_err",
            },
        )

        assert response.status_code == 502

    def it_passes_all_fields_to_service_anchor_consolidation(self):
        """
        Arrange: mock service records call arguments.
        Act: POST /anchor/consolidation with known values.
        Assert: service.anchor_consolidation called with correct args.
        """
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        mock_service = AsyncMock()
        mock_service.anchor_consolidation.return_value = {
            "consolidation_id": "cons_pass",
            "sequence_number": 15,
            "timestamp": "2026-04-03T00:00:00Z",
        }
        known_hash = _sha256("synthesis output")

        app = _make_test_app()
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        client = TestClient(app)
        client.post(
            "/anchor/consolidation",
            json={
                "consolidation_id": "cons_pass",
                "synthesis_hash": known_hash,
                "source_memory_ids": ["mem_x", "mem_y"],
                "model_used": "nous-hermes-2",
            },
        )

        mock_service.anchor_consolidation.assert_called_once_with(
            consolidation_id="cons_pass",
            synthesis_hash=known_hash,
            source_memory_ids=["mem_x", "mem_y"],
            model_used="nous-hermes-2",
        )
