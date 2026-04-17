"""
Tests for POST /v1/public/{project_id}/memory/reflect (Refs #292, #311).

Covers:
- End-to-end: handler fetches memories, calls synthesize_insights, returns
  ReflectResponse.
- Service: synthesize_insights patterns/contradictions/gaps heuristics.

Heuristic summary:
- patterns: top-3 most frequent MemoryCategory values by count
- contradictions: pairs with "approve" vs "reject" keywords on shared
  content tokens (>= 1 overlap on meaningful words)
- gaps: expected categories (decision, plan, observation) with zero
  memories in the corpus
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.cognitive_memory import router as cognitive_memory_router
from app.schemas.cognitive_memory import MemoryCategory
from app.services.cognitive_memory_service import CognitiveMemoryService

DEFAULT_PID = "proj_test_s3"


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(cognitive_memory_router)
    return app


def _memory(
    memory_id: str,
    content: str,
    category: str = "other",
    timestamp: str = "2026-04-17T00:00:00Z",
    agent_id: str = "agent_abc",
) -> Dict[str, Any]:
    return {
        "memory_id": memory_id,
        "agent_id": agent_id,
        "run_id": "run_1",
        "memory_type": "episodic",
        "content": content,
        "metadata": {"category": category},
        "namespace": "default",
        "timestamp": timestamp,
        "project_id": DEFAULT_PID,
    }


class DescribeReflectEndpoint:
    """End-to-end /memory/reflect."""

    def it_returns_memory_count_and_buckets(self, monkeypatch):
        app = _build_app()
        memories = [
            _memory("m1", "Decided to approve TX-1", category="decision"),
            _memory("m2", "Decided to approve TX-2", category="decision"),
            _memory("m3", "Error: timeout", category="error"),
        ]
        monkeypatch.setattr(
            "app.api.cognitive.reflect.agent_memory_service.list_memories",
            AsyncMock(return_value=(memories, len(memories), {})),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/reflect",
            json={"agent_id": "agent_abc", "window_days": 30},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["memory_count"] == 3
        assert body["window_days"] == 30
        assert isinstance(body["patterns"], list)
        assert isinstance(body["contradictions"], list)
        assert isinstance(body["gaps"], list)

    def it_passes_agent_id_filter_to_list_memories(self, monkeypatch):
        app = _build_app()
        captured: Dict[str, Any] = {}

        async def _capture(**kwargs):
            captured.update(kwargs)
            return ([], 0, {})

        monkeypatch.setattr(
            "app.api.cognitive.reflect.agent_memory_service.list_memories",
            _capture,
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/reflect",
            json={"agent_id": "agent_xyz", "namespace": "ns_a"},
        )

        assert response.status_code == 200
        assert captured["project_id"] == DEFAULT_PID
        assert captured["agent_id"] == "agent_xyz"
        assert captured["namespace"] == "ns_a"

    def it_returns_empty_buckets_on_empty_corpus(self, monkeypatch):
        app = _build_app()
        monkeypatch.setattr(
            "app.api.cognitive.reflect.agent_memory_service.list_memories",
            AsyncMock(return_value=([], 0, {})),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/reflect",
            json={"agent_id": "agent_abc"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["memory_count"] == 0
        assert body["patterns"] == []
        assert body["contradictions"] == []
        # Gaps present for all expected categories when corpus is empty
        assert len(body["gaps"]) >= 1

    def it_filters_to_window_days(self, monkeypatch):
        app = _build_app()
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
        old = (now - timedelta(days=60)).isoformat().replace("+00:00", "Z")

        memories = [
            _memory("m_recent", "x", category="decision", timestamp=recent),
            _memory("m_old", "y", category="plan", timestamp=old),
        ]
        monkeypatch.setattr(
            "app.api.cognitive.reflect.agent_memory_service.list_memories",
            AsyncMock(return_value=(memories, 2, {})),
        )

        client = TestClient(app)
        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/reflect",
            json={"agent_id": "agent_abc", "window_days": 30},
        )

        assert response.status_code == 200
        # memory_count reflects pre-window total; patterns reflect window-filtered
        body = response.json()
        # Only the recent memory falls in the 30d window → patterns only show decision
        labels = [p["label"] for p in body["patterns"]]
        assert "decision" in labels
        assert "plan" not in labels


class DescribeSynthesizeInsightsPatterns:

    def it_returns_top_categories_sorted_by_count(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory("m1", "", category="decision"),
            _memory("m2", "", category="decision"),
            _memory("m3", "", category="plan"),
            _memory("m4", "", category="decision"),
            _memory("m5", "", category="observation"),
        ]

        result = svc.synthesize_insights(memories)
        patterns = result["patterns"]

        assert patterns[0].count == 3
        assert patterns[0].category == MemoryCategory.DECISION

    def it_returns_empty_patterns_on_empty_corpus(self):
        svc = CognitiveMemoryService()

        result = svc.synthesize_insights([])

        assert result["patterns"] == []

    def it_limits_patterns_to_top_3(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory(f"m{i}", "", category="decision") for i in range(4)
        ] + [
            _memory(f"p{i}", "", category="plan") for i in range(3)
        ] + [
            _memory(f"o{i}", "", category="observation") for i in range(2)
        ] + [
            _memory(f"e{i}", "", category="error") for i in range(1)
        ] + [
            _memory(f"i{i}", "", category="interaction") for i in range(1)
        ]

        result = svc.synthesize_insights(memories)

        assert len(result["patterns"]) <= 3


class DescribeSynthesizeInsightsContradictions:

    def it_flags_approve_vs_reject_on_same_topic(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory("m1", "Approved payment TX-123 to vendor Acme", category="decision"),
            _memory("m2", "Rejected payment TX-123 to vendor Acme", category="decision"),
        ]

        result = svc.synthesize_insights(memories)
        contradictions = result["contradictions"]

        assert len(contradictions) == 1
        ids = set(contradictions[0].memory_ids)
        assert ids == {"m1", "m2"}

    def it_no_contradiction_when_topics_differ(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory("m1", "Approved TX-111 vendor Acme", category="decision"),
            _memory("m2", "Rejected TX-999 vendor Globex", category="decision"),
        ]

        result = svc.synthesize_insights(memories)

        assert result["contradictions"] == []

    def it_no_contradiction_without_opposing_keywords(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory("m1", "Observed a spike in rate limits", category="observation"),
            _memory("m2", "Observed another spike in rate limits", category="observation"),
        ]

        result = svc.synthesize_insights(memories)

        assert result["contradictions"] == []


class DescribeSynthesizeInsightsGaps:

    def it_flags_missing_expected_categories(self):
        svc = CognitiveMemoryService()
        # Only `observation` present; decision & plan are missing.
        memories = [_memory("m1", "Noticed metric spike", category="observation")]

        result = svc.synthesize_insights(memories)
        gap_categories = [g.category for g in result["gaps"]]

        assert MemoryCategory.DECISION in gap_categories
        assert MemoryCategory.PLAN in gap_categories
        assert MemoryCategory.OBSERVATION not in gap_categories

    def it_no_gaps_when_all_expected_categories_present(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory("m1", "", category="decision"),
            _memory("m2", "", category="plan"),
            _memory("m3", "", category="observation"),
        ]

        result = svc.synthesize_insights(memories)

        assert result["gaps"] == []
