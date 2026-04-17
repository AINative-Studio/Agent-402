"""
Scaffold tests for the ZeroMemory Cognitive API (#292 S0, #308).

Covers:
- 501 stub behavior for all four endpoints.
- Request-schema validation (422 on bad input).
- Workshop alias routing via convention mapping (/api/v1/memory/* -> /v1/public/{pid}/memory/*).
- Service helper smoke (deterministic placeholder outputs).

S1–S4 (#309–#312) will replace the stub status with real 200/201 responses
and extend these tests with domain-specific assertions.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.cognitive_memory import router as cognitive_memory_router
from app.middleware.workshop_prefix import WorkshopPrefixMiddleware
from app.schemas.cognitive_memory import (
    CognitiveMemoryType,
    MemoryCategory,
    ProfileResponse,
    RecallWeights,
)
from app.services.cognitive_memory_service import (
    CognitiveMemoryService,
    get_cognitive_memory_service,
)

DEFAULT_PID = "proj_test_s0"


def _build_app(workshop_mode: bool = False) -> FastAPI:
    app = FastAPI()
    app.include_router(cognitive_memory_router)
    if workshop_mode:
        app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id=DEFAULT_PID,
        )
    return app


class DescribeCognitiveMemoryStubs:
    """Stubs for endpoints not yet implemented (S2-S4)."""

    # /remember is implemented in S1 (#309); see test_cognitive_remember.py
    # for its coverage. Remaining stubs below.

    def it_recall_returns_501(self):
        app = _build_app()
        client = TestClient(app)

        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": "rate limit?"},
        )

        assert response.status_code == 501

    def it_reflect_returns_501(self):
        app = _build_app()
        client = TestClient(app)

        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/reflect",
            json={"agent_id": "agent_abc"},
        )

        assert response.status_code == 501

    def it_profile_returns_501(self):
        app = _build_app()
        client = TestClient(app)

        response = client.get(
            f"/v1/public/{DEFAULT_PID}/memory/profile/agent_abc"
        )

        assert response.status_code == 501


class DescribeCognitiveMemorySchemaValidation:
    """Pydantic schemas reject invalid input (422)."""

    def it_rejects_remember_with_empty_content(self):
        app = _build_app()
        client = TestClient(app)

        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={"agent_id": "agent_abc", "content": ""},
        )

        assert response.status_code == 422

    def it_rejects_remember_with_missing_agent_id(self):
        app = _build_app()
        client = TestClient(app)

        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={"content": "no agent"},
        )

        assert response.status_code == 422

    def it_rejects_remember_with_out_of_range_importance_hint(self):
        app = _build_app()
        client = TestClient(app)

        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/remember",
            json={
                "agent_id": "agent_abc",
                "content": "x",
                "importance_hint": 2.0,
            },
        )

        assert response.status_code == 422

    def it_rejects_recall_with_empty_query(self):
        app = _build_app()
        client = TestClient(app)

        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": ""},
        )

        assert response.status_code == 422

    def it_rejects_recall_with_limit_out_of_range(self):
        app = _build_app()
        client = TestClient(app)

        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": "x", "limit": 999},
        )

        assert response.status_code == 422

    def it_accepts_recall_with_default_weights(self):
        """Recall request validates without explicit weights."""
        app = _build_app()
        client = TestClient(app)

        response = client.post(
            f"/v1/public/{DEFAULT_PID}/memory/recall",
            json={"query": "what is the rate limit"},
        )

        # Passes validation, hits 501 stub — confirms schema accepts it.
        assert response.status_code == 501


class DescribeWorkshopAliasRouting:
    """/api/v1/memory/* must resolve via convention mapping."""

    # /api/v1/memory/remember routing is covered in test_cognitive_remember.py
    # against the real (non-stub) handler. Remaining stubs below.

    def it_routes_api_v1_memory_recall_to_stub(self):
        app = _build_app(workshop_mode=True)
        client = TestClient(app)

        response = client.post(
            "/api/v1/memory/recall",
            json={"query": "q"},
        )

        assert response.status_code == 501

    def it_routes_api_v1_memory_reflect_to_stub(self):
        app = _build_app(workshop_mode=True)
        client = TestClient(app)

        response = client.post("/api/v1/memory/reflect", json={})

        assert response.status_code == 501

    def it_routes_api_v1_memory_profile_to_stub(self):
        app = _build_app(workshop_mode=True)
        client = TestClient(app)

        response = client.get("/api/v1/memory/profile/agent_abc")

        assert response.status_code == 501


class DescribeCognitiveMemoryService:
    """S0 service stubs return deterministic placeholders."""

    def it_returns_singleton(self):
        s1 = get_cognitive_memory_service()
        s2 = get_cognitive_memory_service()

        assert s1 is s2
        assert isinstance(s1, CognitiveMemoryService)

    def it_score_importance_returns_default(self):
        svc = CognitiveMemoryService()

        score = svc.score_importance(
            CognitiveMemoryType.SEMANTIC, "facts about rate limit", metadata={}
        )

        # S1 (#309) replaced the 0.5 stub with a real heuristic; the value
        # now varies by type/length/metadata. Still bounded to [0,1].
        assert 0.0 <= score <= 1.0

    def it_score_importance_respects_hint_clipped_to_range(self):
        svc = CognitiveMemoryService()

        assert svc.score_importance(
            CognitiveMemoryType.WORKING, "x", importance_hint=0.9
        ) == 0.9
        assert svc.score_importance(
            CognitiveMemoryType.WORKING, "x", importance_hint=-0.2
        ) == 0.0
        assert svc.score_importance(
            CognitiveMemoryType.WORKING, "x", importance_hint=1.5
        ) == 1.0

    def it_categorize_returns_valid_category(self):
        svc = CognitiveMemoryService()

        # S1 (#309) replaced the always-OTHER stub with a keyword heuristic;
        # for non-matching text in WORKING type we still fall through to OTHER.
        assert svc.categorize("asdfghjkl", CognitiveMemoryType.WORKING) == MemoryCategory.OTHER

    def it_compute_recency_weight_returns_default(self):
        svc = CognitiveMemoryService()

        assert svc.compute_recency_weight("2026-04-01T00:00:00Z") == 1.0
        assert svc.compute_recency_weight(None) == 1.0

    def it_compose_relevance_with_default_weights(self):
        svc = CognitiveMemoryService()

        score = svc.compose_relevance(similarity=1.0, recency=1.0, importance=1.0)

        # Default weights: 0.6 + 0.3 + 0.1 = 1.0
        assert score == pytest.approx(1.0)

    def it_compose_relevance_with_custom_weights(self):
        svc = CognitiveMemoryService()

        weights = RecallWeights(similarity=0.5, recency=0.5, importance=0.0)
        score = svc.compose_relevance(
            similarity=0.8, recency=0.6, importance=0.9, weights=weights
        )

        assert score == pytest.approx(0.8 * 0.5 + 0.6 * 0.5 + 0.9 * 0.0)

    def it_synthesize_insights_returns_empty_buckets(self):
        svc = CognitiveMemoryService()

        insights = svc.synthesize_insights([])

        assert insights == {"patterns": [], "contradictions": [], "gaps": []}

    def it_build_profile_with_empty_memories(self):
        svc = CognitiveMemoryService()

        profile = svc.build_profile(agent_id="agent_abc", memories=[])

        assert isinstance(profile, ProfileResponse)
        assert profile.agent_id == "agent_abc"
        assert profile.memory_count == 0
        assert profile.categories == []
        assert profile.topics == []
        assert profile.expertise_areas == []
        assert profile.first_memory_at is None
        assert profile.last_memory_at is None

    def it_build_profile_counts_memory_list_length(self):
        svc = CognitiveMemoryService()
        fake_memories = [{"memory_id": f"m{i}"} for i in range(5)]

        profile = svc.build_profile(agent_id="a", memories=fake_memories)

        assert profile.memory_count == 5
