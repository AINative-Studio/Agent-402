"""
Tests for POST /v1/public/{project_id}/memory/remember (Refs #292, #309).

Covers:
- End-to-end handler: validates, scores importance, categorizes, persists
  via AgentMemoryService.store_memory, returns RememberResponse.
- Service-layer helpers: score_importance heuristic, categorize keyword
  routing, importance hint override.
- Error paths: persistence failure → 5xx with clear error body.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.cognitive_memory import router as cognitive_memory_router
from app.schemas.cognitive_memory import CognitiveMemoryType, MemoryCategory
from app.services.cognitive_memory_service import CognitiveMemoryService


DEFAULT_PID = "proj_test_s1"


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(cognitive_memory_router)
    return app


def _canned_stored_record(
    memory_id: str = "mem_s1_abc", agent_id: str = "agent_abc", content: str = "hello"
) -> Dict[str, Any]:
    return {
        "memory_id": memory_id,
        "agent_id": agent_id,
        "run_id": "run_1",
        "memory_type": "decision",
        "content": content,
        "metadata": {},
        "namespace": "default",
        "timestamp": "2026-04-17T00:00:00Z",
        "project_id": DEFAULT_PID,
        "embedding_id": None,
    }


class DescribeRememberEndpoint:
    """End-to-end happy path and error handling."""

    def it_stores_memory_and_returns_enriched_response(self, monkeypatch):
        app = _build_app()
        fake = AsyncMock(return_value=_canned_stored_record())
        monkeypatch.setattr(
            "app.api.cognitive.remember.agent_memory_service.store_memory",
            fake,
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={
                "agent_id": "agent_abc",
                "content": "Approved transaction TX-12345 based on compliance rules",
                "memory_type": "semantic",
            },
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["memory_id"] == "mem_s1_abc"
        assert body["agent_id"] == "agent_abc"
        assert body["memory_type"] == "semantic"
        assert 0.0 <= body["importance"] <= 1.0
        assert body["category"] in {
            "decision", "observation", "knowledge", "plan",
            "interaction", "error", "other",
        }
        assert body["hcs_anchor_pending"] is True

    def it_forwards_enriched_metadata_to_store(self, monkeypatch):
        app = _build_app()
        captured: Dict[str, Any] = {}

        async def _capture(**kwargs):
            captured.update(kwargs)
            return _canned_stored_record()

        monkeypatch.setattr(
            "app.api.cognitive.remember.agent_memory_service.store_memory",
            _capture,
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={
                "agent_id": "agent_abc",
                "run_id": "run_1",
                "content": "Decided to approve transaction",
                "memory_type": "episodic",
                "namespace": "ns_test",
                "metadata": {"transaction_id": "TX-1"},
            },
        )

        assert response.status_code == 201, response.text
        assert captured["project_id"] == DEFAULT_PID
        assert captured["agent_id"] == "agent_abc"
        assert captured["run_id"] == "run_1"
        assert captured["memory_type"] == "episodic"
        assert captured["namespace"] == "ns_test"
        # Enriched metadata: original fields preserved, importance + category added
        md = captured["metadata"]
        assert md["transaction_id"] == "TX-1"
        assert "importance" in md
        assert "category" in md
        assert 0.0 <= md["importance"] <= 1.0

    def it_honors_importance_hint(self, monkeypatch):
        app = _build_app()
        captured: Dict[str, Any] = {}

        async def _capture(**kwargs):
            captured.update(kwargs)
            return _canned_stored_record()

        monkeypatch.setattr(
            "app.api.cognitive.remember.agent_memory_service.store_memory",
            _capture,
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={
                "agent_id": "agent_abc",
                "content": "x",
                "importance_hint": 0.91,
            },
        )

        assert response.status_code == 201, response.text
        assert response.json()["importance"] == pytest.approx(0.91)
        assert captured["metadata"]["importance"] == pytest.approx(0.91)

    def it_defaults_run_id_when_omitted(self, monkeypatch):
        """`run_id` is optional; service must receive a non-empty string."""
        app = _build_app()
        captured: Dict[str, Any] = {}

        async def _capture(**kwargs):
            captured.update(kwargs)
            return _canned_stored_record()

        monkeypatch.setattr(
            "app.api.cognitive.remember.agent_memory_service.store_memory",
            _capture,
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={"agent_id": "agent_abc", "content": "hi"},
        )

        assert response.status_code == 201
        assert captured["run_id"]  # non-empty default assigned

    def it_returns_502_when_store_fails(self, monkeypatch):
        from app.core.errors import APIError

        async def _raise(**_):
            raise APIError(
                detail="zerodb down",
                status_code=502,
                error_code="ZERODB_ERROR",
            )

        app = _build_app()
        monkeypatch.setattr(
            "app.api.cognitive.remember.agent_memory_service.store_memory",
            _raise,
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={"agent_id": "agent_abc", "content": "x"},
        )

        assert response.status_code == 502
        body = response.json()
        # APIError.detail/error_code propagate through the handler
        assert "zerodb" in str(body).lower() or "ZERODB" in str(body)


class DescribeScoreImportanceHeuristic:
    """Deterministic 0.0–1.0 scoring based on type + length + metadata."""

    def it_scores_higher_for_procedural_than_working(self):
        svc = CognitiveMemoryService()

        s_proc = svc.score_importance(
            CognitiveMemoryType.PROCEDURAL, "x" * 50
        )
        s_working = svc.score_importance(
            CognitiveMemoryType.WORKING, "x" * 50
        )

        assert s_proc > s_working

    def it_scores_semantic_and_episodic_in_the_middle(self):
        svc = CognitiveMemoryService()

        s_sem = svc.score_importance(CognitiveMemoryType.SEMANTIC, "fact")
        s_epi = svc.score_importance(CognitiveMemoryType.EPISODIC, "event")
        s_work = svc.score_importance(CognitiveMemoryType.WORKING, "temp")
        s_proc = svc.score_importance(CognitiveMemoryType.PROCEDURAL, "how-to")

        assert s_work < s_epi <= s_sem < s_proc

    def it_adds_length_bonus(self):
        svc = CognitiveMemoryService()

        short = svc.score_importance(CognitiveMemoryType.SEMANTIC, "short")
        long_ = svc.score_importance(
            CognitiveMemoryType.SEMANTIC, "x" * 600
        )

        assert long_ > short

    def it_boosts_when_metadata_flags_critical(self):
        svc = CognitiveMemoryService()

        base = svc.score_importance(
            CognitiveMemoryType.EPISODIC, "event", metadata={}
        )
        critical = svc.score_importance(
            CognitiveMemoryType.EPISODIC,
            "event",
            metadata={"priority": "critical"},
        )

        assert critical > base

    def it_caps_importance_at_1_0(self):
        svc = CognitiveMemoryService()

        score = svc.score_importance(
            CognitiveMemoryType.PROCEDURAL,
            "x" * 5000,
            metadata={"priority": "critical", "urgent": True},
        )

        assert score == 1.0

    def it_importance_hint_overrides_heuristic(self):
        svc = CognitiveMemoryService()

        score = svc.score_importance(
            CognitiveMemoryType.WORKING, "x", importance_hint=0.73
        )

        assert score == pytest.approx(0.73)

    def it_importance_hint_is_clipped(self):
        svc = CognitiveMemoryService()

        assert svc.score_importance(
            CognitiveMemoryType.WORKING, "x", importance_hint=-1
        ) == 0.0
        assert svc.score_importance(
            CognitiveMemoryType.WORKING, "x", importance_hint=2
        ) == 1.0


class DescribeCategorizeHeuristic:
    """Deterministic keyword-based classification."""

    def it_returns_decision_for_decision_keywords(self):
        svc = CognitiveMemoryService()

        for text in [
            "Decided to approve TX-1",
            "I will reject the request",
            "approved transaction",
        ]:
            assert svc.categorize(text, CognitiveMemoryType.EPISODIC) == MemoryCategory.DECISION

    def it_returns_error_for_error_keywords(self):
        svc = CognitiveMemoryService()

        for text in [
            "Error: database timeout",
            "exception raised in handler",
            "payment failed with code 5",
        ]:
            assert svc.categorize(text, CognitiveMemoryType.EPISODIC) == MemoryCategory.ERROR

    def it_returns_plan_for_plan_keywords(self):
        svc = CognitiveMemoryService()

        for text in [
            "plan: roll out v2 next week",
            "will schedule the migration",
            "roadmap shows feature in Q3",
        ]:
            assert svc.categorize(text, CognitiveMemoryType.EPISODIC) == MemoryCategory.PLAN

    def it_returns_observation_for_observation_keywords(self):
        svc = CognitiveMemoryService()

        for text in [
            "observed a latency spike at 12:00",
            "noticed that token usage is up",
            "metric: requests/sec = 42",
        ]:
            assert svc.categorize(text, CognitiveMemoryType.EPISODIC) == MemoryCategory.OBSERVATION

    def it_returns_interaction_for_interaction_keywords(self):
        svc = CognitiveMemoryService()

        for text in [
            "User asked about pricing",
            "agent said: 'ok'",
            "replied in chat",
        ]:
            assert svc.categorize(text, CognitiveMemoryType.EPISODIC) == MemoryCategory.INTERACTION

    def it_returns_knowledge_for_semantic_plain_facts(self):
        svc = CognitiveMemoryService()

        category = svc.categorize(
            "The rate limit is 100 requests per minute",
            CognitiveMemoryType.SEMANTIC,
        )

        assert category == MemoryCategory.KNOWLEDGE

    def it_returns_other_when_no_keywords_match(self):
        svc = CognitiveMemoryService()

        category = svc.categorize("blah", CognitiveMemoryType.WORKING)

        assert category == MemoryCategory.OTHER


class DescribeHCSAnchorHook:
    """S5 (#313) wires CognitiveMemoryService.anchor_to_hcs into /remember.

    Anchoring is best-effort: the /remember call always returns 201 (the
    memory is durable in ZeroDB regardless of HCS availability). The
    `hcs_anchor_pending` flag reflects whether the HCS anchor succeeded.
    """

    @pytest.mark.asyncio
    async def it_computes_sha256_content_hash(self):
        svc = CognitiveMemoryService()

        h = svc.content_hash("hello")

        # SHA-256("hello") is a well-known value
        assert h == (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )

    @pytest.mark.asyncio
    async def it_calls_anchor_memory_with_content_hash(self):
        svc = CognitiveMemoryService()
        mock_anchoring = SimpleNamespace(
            anchor_memory=AsyncMock(return_value={"sequence_number": 1})
        )

        result = await svc.anchor_to_hcs(
            memory_id="mem_1",
            content="hello",
            agent_id="agent_abc",
            namespace="ns_test",
            anchoring_service=mock_anchoring,
        )

        mock_anchoring.anchor_memory.assert_awaited_once()
        kwargs = mock_anchoring.anchor_memory.call_args.kwargs
        assert kwargs["memory_id"] == "mem_1"
        assert kwargs["agent_id"] == "agent_abc"
        assert kwargs["namespace"] == "ns_test"
        assert kwargs["content_hash"] == svc.content_hash("hello")
        assert result == {"sequence_number": 1}

    @pytest.mark.asyncio
    async def it_returns_none_when_anchor_fails(self):
        svc = CognitiveMemoryService()

        async def _boom(**_):
            raise RuntimeError("HCS down")

        mock_anchoring = SimpleNamespace(anchor_memory=_boom)

        result = await svc.anchor_to_hcs(
            memory_id="mem_1",
            content="hello",
            agent_id="agent_abc",
            namespace="default",
            anchoring_service=mock_anchoring,
        )

        assert result is None

    def it_marks_hcs_anchor_pending_true_when_anchor_fails(self, monkeypatch):
        app = _build_app()
        monkeypatch.setattr(
            "app.api.cognitive.remember.agent_memory_service.store_memory",
            AsyncMock(return_value=_canned_stored_record()),
        )

        async def _failed_anchor(**_):
            return None

        monkeypatch.setattr(
            "app.api.cognitive.remember.get_cognitive_memory_service",
            lambda: _StubCognitive(anchor_result=None),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={"agent_id": "agent_abc", "content": "hi"},
        )

        assert response.status_code == 201
        assert response.json()["hcs_anchor_pending"] is True

    def it_marks_hcs_anchor_pending_false_when_anchor_succeeds(self, monkeypatch):
        app = _build_app()
        monkeypatch.setattr(
            "app.api.cognitive.remember.agent_memory_service.store_memory",
            AsyncMock(return_value=_canned_stored_record()),
        )
        monkeypatch.setattr(
            "app.api.cognitive.remember.get_cognitive_memory_service",
            lambda: _StubCognitive(anchor_result={"sequence_number": 42}),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={"agent_id": "agent_abc", "content": "hi"},
        )

        assert response.status_code == 201
        assert response.json()["hcs_anchor_pending"] is False


class _StubCognitive:
    """Cognitive service stand-in that records anchor_to_hcs calls."""

    def __init__(self, anchor_result):
        self._anchor_result = anchor_result

    def score_importance(self, *, memory_type, content, metadata=None, importance_hint=None):
        if importance_hint is not None:
            return max(0.0, min(1.0, float(importance_hint)))
        return 0.5

    def categorize(self, *, content, memory_type):
        return MemoryCategory.OTHER

    async def anchor_to_hcs(self, **kwargs):
        return self._anchor_result
