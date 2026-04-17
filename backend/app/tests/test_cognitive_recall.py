"""
Tests for POST /v1/public/{project_id}/memory/recall (Refs #292, #310).

Covers:
- End-to-end: handler calls `AgentMemoryService.search_memories`, applies
  recency + importance weighting, sorts by composite score, returns
  `RecallResponse`.
- Service helpers: `compute_recency_weight` exponential decay, agent_id
  filtering, missing importance defaults to 0.5.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.cognitive_memory import router as cognitive_memory_router
from app.schemas.cognitive_memory import RecallWeights
from app.services.cognitive_memory_service import CognitiveMemoryService

DEFAULT_PID = "proj_test_s2"


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(cognitive_memory_router)
    return app


def _memory(
    memory_id: str,
    content: str,
    similarity: float = 0.8,
    importance: float = 0.5,
    timestamp: str = "2026-04-17T00:00:00Z",
    agent_id: str = "agent_abc",
    category: str = "other",
    memory_type: str = "working",
) -> Dict[str, Any]:
    return {
        "memory_id": memory_id,
        "agent_id": agent_id,
        "run_id": "run_1",
        "memory_type": memory_type,
        "content": content,
        "metadata": {
            "importance": importance,
            "category": category,
            "cognitive_memory_type": memory_type,
        },
        "namespace": "default",
        "timestamp": timestamp,
        "project_id": DEFAULT_PID,
        "embedding_id": None,
        "similarity_score": similarity,
    }


class DescribeRecallEndpoint:

    def it_returns_memories_sorted_by_composite_score(self, monkeypatch):
        app = _build_app()
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        results = [
            _memory("mem_low_sim", "rate limit", similarity=0.3, importance=0.5, timestamp=now_iso),
            _memory("mem_high_sim", "rate limit details", similarity=0.9, importance=0.5, timestamp=now_iso),
            _memory("mem_mid", "rate", similarity=0.6, importance=0.5, timestamp=now_iso),
        ]

        monkeypatch.setattr(
            "app.api.cognitive.recall.agent_memory_service.search_memories",
            AsyncMock(return_value=results),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": "what is the rate limit?", "limit": 5},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        ids = [m["memory_id"] for m in body["memories"]]
        assert ids == ["mem_high_sim", "mem_mid", "mem_low_sim"]
        # All composite scores must be in [0, 1.5] range (weights sum ~1)
        for m in body["memories"]:
            assert 0.0 <= m["composite_score"]
            assert m["similarity_score"] >= 0.0
            assert 0.0 <= m["recency_weight"] <= 1.0

    def it_filters_results_by_agent_id_when_provided(self, monkeypatch):
        app = _build_app()
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        results = [
            _memory("mem_a", "x", agent_id="agent_abc", timestamp=now_iso),
            _memory("mem_b", "y", agent_id="other_agent", timestamp=now_iso),
        ]

        monkeypatch.setattr(
            "app.api.cognitive.recall.agent_memory_service.search_memories",
            AsyncMock(return_value=results),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": "q", "agent_id": "agent_abc"},
        )

        assert response.status_code == 200
        ids = [m["memory_id"] for m in response.json()["memories"]]
        assert ids == ["mem_a"]

    def it_honors_limit(self, monkeypatch):
        app = _build_app()
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        results = [
            _memory(f"mem_{i}", "x", similarity=0.9 - 0.1 * i, timestamp=now_iso)
            for i in range(8)
        ]

        monkeypatch.setattr(
            "app.api.cognitive.recall.agent_memory_service.search_memories",
            AsyncMock(return_value=results),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": "q", "limit": 3},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["memories"]) == 3

    def it_defaults_missing_importance_to_05(self, monkeypatch):
        app = _build_app()
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        # Memory without importance in metadata (legacy agent-memory record).
        legacy = _memory("mem_legacy", "x", timestamp=now_iso)
        legacy["metadata"] = {}

        monkeypatch.setattr(
            "app.api.cognitive.recall.agent_memory_service.search_memories",
            AsyncMock(return_value=[legacy]),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": "q"},
        )

        assert response.status_code == 200
        assert response.json()["memories"][0]["importance"] == 0.5

    def it_accepts_custom_weights(self, monkeypatch):
        app = _build_app()
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        results = [
            _memory("mem_1", "x", similarity=0.9, importance=0.2, timestamp=now_iso),
            _memory("mem_2", "y", similarity=0.5, importance=1.0, timestamp=now_iso),
        ]

        monkeypatch.setattr(
            "app.api.cognitive.recall.agent_memory_service.search_memories",
            AsyncMock(return_value=results),
        )

        client = TestClient(app)
        # Importance weight dominates — mem_2 (importance=1.0) ranks first.
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={
                "query": "q",
                "weights": {
                    "similarity": 0.1,
                    "recency": 0.1,
                    "importance": 0.8,
                    "half_life_days": 7.0,
                },
            },
        )

        assert response.status_code == 200
        ids = [m["memory_id"] for m in response.json()["memories"]]
        assert ids[0] == "mem_2"

    def it_returns_empty_when_no_matches(self, monkeypatch):
        app = _build_app()
        monkeypatch.setattr(
            "app.api.cognitive.recall.agent_memory_service.search_memories",
            AsyncMock(return_value=[]),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": "q"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["memories"] == []
        assert body["query"] == "q"

    def it_passes_namespace_and_limit_to_service(self, monkeypatch):
        app = _build_app()
        captured: Dict[str, Any] = {}

        async def _capture(**kwargs):
            captured.update(kwargs)
            return []

        monkeypatch.setattr(
            "app.api.cognitive.recall.agent_memory_service.search_memories",
            _capture,
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": "what", "namespace": "ns_test", "limit": 25},
        )

        assert response.status_code == 200
        assert captured["project_id"] == DEFAULT_PID
        assert captured["query"] == "what"
        assert captured["namespace"] == "ns_test"
        assert captured["top_k"] == 25


class DescribeRecencyWeightDecay:
    """Exponential recency decay: 0.5 ** (age_days / half_life_days)."""

    def it_returns_1_for_now(self):
        svc = CognitiveMemoryService()
        now = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)
        ts = "2026-04-17T12:00:00Z"

        assert svc.compute_recency_weight(ts, half_life_days=7.0, now=now) == pytest.approx(1.0)

    def it_halves_at_half_life(self):
        svc = CognitiveMemoryService()
        now = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)
        seven_days_ago = (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")

        weight = svc.compute_recency_weight(seven_days_ago, half_life_days=7.0, now=now)

        assert weight == pytest.approx(0.5, rel=0.01)

    def it_quarter_at_two_half_lives(self):
        svc = CognitiveMemoryService()
        now = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)
        fourteen_days_ago = (now - timedelta(days=14)).isoformat().replace("+00:00", "Z")

        weight = svc.compute_recency_weight(fourteen_days_ago, half_life_days=7.0, now=now)

        assert weight == pytest.approx(0.25, rel=0.01)

    def it_near_zero_for_very_old(self):
        svc = CognitiveMemoryService()
        now = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)
        ancient = (now - timedelta(days=365)).isoformat().replace("+00:00", "Z")

        weight = svc.compute_recency_weight(ancient, half_life_days=7.0, now=now)

        assert 0.0 <= weight < 0.001

    def it_returns_1_for_none_timestamp(self):
        svc = CognitiveMemoryService()

        assert svc.compute_recency_weight(None) == 1.0

    def it_returns_1_for_malformed_timestamp(self):
        svc = CognitiveMemoryService()

        assert svc.compute_recency_weight("not a timestamp") == 1.0

    def it_supports_configurable_half_life(self):
        svc = CognitiveMemoryService()
        now = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)
        one_day_ago = (now - timedelta(days=1)).isoformat().replace("+00:00", "Z")

        w_7d = svc.compute_recency_weight(one_day_ago, half_life_days=7.0, now=now)
        w_1d = svc.compute_recency_weight(one_day_ago, half_life_days=1.0, now=now)

        # Shorter half-life => faster decay => lower weight at same age
        assert w_1d < w_7d


class DescribeComposeRelevance:
    """Weighted sum used by /recall to rank memories."""

    def it_default_weights_sum_to_1(self):
        w = RecallWeights()
        assert w.similarity + w.recency + w.importance == pytest.approx(1.0)

    def it_returns_weighted_sum(self):
        svc = CognitiveMemoryService()
        weights = RecallWeights(similarity=0.5, recency=0.25, importance=0.25, half_life_days=7.0)

        score = svc.compose_relevance(
            similarity=0.8, recency=0.4, importance=0.6, weights=weights
        )

        assert score == pytest.approx(0.8 * 0.5 + 0.4 * 0.25 + 0.6 * 0.25)
