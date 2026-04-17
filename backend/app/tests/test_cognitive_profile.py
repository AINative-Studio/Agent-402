"""
Tests for GET /v1/public/{project_id}/memory/profile/{agent_id}
(Refs #292, #312).

Covers:
- End-to-end: handler fetches memories for the agent, calls
  build_profile, returns ProfileResponse.
- Service: build_profile — categories, topics, expertise areas,
  first/last timestamps.
"""
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.cognitive_memory import router as cognitive_memory_router
from app.schemas.cognitive_memory import MemoryCategory
from app.services.cognitive_memory_service import CognitiveMemoryService

DEFAULT_PID = "proj_test_s4"


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(cognitive_memory_router)
    return app


def _memory(
    memory_id: str,
    content: str,
    category: str = "other",
    importance: float = 0.5,
    timestamp: str = "2026-04-17T00:00:00Z",
    agent_id: str = "agent_abc",
) -> Dict[str, Any]:
    return {
        "memory_id": memory_id,
        "agent_id": agent_id,
        "run_id": "run_1",
        "memory_type": "episodic",
        "content": content,
        "metadata": {"category": category, "importance": importance},
        "namespace": "default",
        "timestamp": timestamp,
        "project_id": DEFAULT_PID,
    }


class DescribeProfileEndpoint:

    def it_returns_profile_with_stats(self, monkeypatch):
        app = _build_app()
        memories = [
            _memory("m1", "Approved payment", category="decision", timestamp="2026-04-10T00:00:00Z"),
            _memory("m2", "Rejected plan", category="decision", timestamp="2026-04-12T00:00:00Z"),
            _memory("m3", "Spike in traffic", category="observation", timestamp="2026-04-16T00:00:00Z"),
        ]
        monkeypatch.setattr(
            "app.api.cognitive.profile.agent_memory_service.list_memories",
            AsyncMock(return_value=(memories, 3, {})),
        )

        client = TestClient(app)
        response = client.get(
            f"/v1/public/{DEFAULT_PID}/memory/profile/agent_abc"
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["agent_id"] == "agent_abc"
        assert body["memory_count"] == 3
        # Timestamps reflect min/max seen
        assert body["first_memory_at"] == "2026-04-10T00:00:00Z"
        assert body["last_memory_at"] == "2026-04-16T00:00:00Z"
        # Categories include decision (2) and observation (1)
        cat_map = {c["category"]: c["count"] for c in body["categories"]}
        assert cat_map["decision"] == 2
        assert cat_map["observation"] == 1

    def it_passes_agent_id_filter_to_list_memories(self, monkeypatch):
        app = _build_app()
        captured: Dict[str, Any] = {}

        async def _capture(**kwargs):
            captured.update(kwargs)
            return ([], 0, {})

        monkeypatch.setattr(
            "app.api.cognitive.profile.agent_memory_service.list_memories",
            _capture,
        )

        client = TestClient(app)
        response = client.get(
            f"/v1/public/{DEFAULT_PID}/memory/profile/agent_xyz"
        )

        assert response.status_code == 200
        assert captured["project_id"] == DEFAULT_PID
        assert captured["agent_id"] == "agent_xyz"

    def it_returns_empty_profile_for_unknown_agent(self, monkeypatch):
        app = _build_app()
        monkeypatch.setattr(
            "app.api.cognitive.profile.agent_memory_service.list_memories",
            AsyncMock(return_value=([], 0, {})),
        )

        client = TestClient(app)
        response = client.get(
            f"/v1/public/{DEFAULT_PID}/memory/profile/nobody"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["agent_id"] == "nobody"
        assert body["memory_count"] == 0
        assert body["categories"] == []
        assert body["topics"] == []
        assert body["expertise_areas"] == []
        assert body["first_memory_at"] is None
        assert body["last_memory_at"] is None


class DescribeBuildProfileCategories:

    def it_counts_memories_per_category(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory("m1", "", category="decision"),
            _memory("m2", "", category="decision"),
            _memory("m3", "", category="plan"),
        ]

        profile = svc.build_profile("agent_abc", memories)

        cat_map = {c.category: c.count for c in profile.categories}
        assert cat_map[MemoryCategory.DECISION] == 2
        assert cat_map[MemoryCategory.PLAN] == 1


class DescribeBuildProfileTopics:

    def it_extracts_topics_from_content_tokens(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory("m1", "approved payment vendor acme invoice", importance=0.6),
            _memory("m2", "rejected payment vendor acme refund", importance=0.4),
            _memory("m3", "observed spike in payment gateway latency", importance=0.5),
        ]

        profile = svc.build_profile("agent_abc", memories)
        topic_counts = {t.topic: t.count for t in profile.topics}

        # "payment" appears in all 3
        assert topic_counts.get("payment") == 3
        # "vendor" appears in 2
        assert topic_counts.get("vendor") == 2
        # Stopwords filtered
        assert "in" not in topic_counts

    def it_topic_average_importance_is_correct(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory("m1", "payment approved", importance=1.0),
            _memory("m2", "payment rejected", importance=0.0),
        ]

        profile = svc.build_profile("agent_abc", memories)
        by_topic = {t.topic: t for t in profile.topics}

        # Payment's average importance = (1.0 + 0.0) / 2 = 0.5
        assert by_topic["payment"].average_importance == pytest.approx(0.5)

    def it_topics_sorted_by_count_desc(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory(f"m{i}", "payment approved", importance=0.5)
            for i in range(5)
        ] + [
            _memory(f"p{i}", "plan migration", importance=0.5)
            for i in range(2)
        ]

        profile = svc.build_profile("agent_abc", memories)
        topics = [t.topic for t in profile.topics]

        # "payment" count 5 before anything with count 2
        assert topics.index("payment") < topics.index("plan")


class DescribeBuildProfileExpertise:

    def it_returns_top_topics_by_count_times_importance(self):
        svc = CognitiveMemoryService()
        memories = [
            # High-expertise topic: 3 mentions × importance 0.9 = score 2.7
            _memory("h1", "hedera", importance=0.9),
            _memory("h2", "hedera", importance=0.9),
            _memory("h3", "hedera", importance=0.9),
            # Low-expertise topic: 5 mentions × importance 0.3 = score 1.5
            _memory("mp1", "marketplace listing", importance=0.3),
            _memory("mp2", "marketplace listing", importance=0.3),
            _memory("mp3", "marketplace listing", importance=0.3),
            _memory("mp4", "marketplace listing", importance=0.3),
            _memory("mp5", "marketplace listing", importance=0.3),
        ]

        profile = svc.build_profile("agent_abc", memories)

        # hedera (score 2.7) ranks above marketplace/listing (score 1.5)
        # despite lower count.
        assert profile.expertise_areas[0] == "hedera"
        assert profile.expertise_areas.index("hedera") < profile.expertise_areas.index("marketplace")

    def it_returns_empty_expertise_for_empty_corpus(self):
        svc = CognitiveMemoryService()

        profile = svc.build_profile("agent_abc", [])

        assert profile.expertise_areas == []


class DescribeBuildProfileTimestamps:

    def it_picks_min_and_max_timestamps(self):
        svc = CognitiveMemoryService()
        memories = [
            _memory("m1", "x", timestamp="2026-04-10T00:00:00Z"),
            _memory("m2", "y", timestamp="2026-04-01T00:00:00Z"),
            _memory("m3", "z", timestamp="2026-04-15T00:00:00Z"),
        ]

        profile = svc.build_profile("agent_abc", memories)

        assert profile.first_memory_at == "2026-04-01T00:00:00Z"
        assert profile.last_memory_at == "2026-04-15T00:00:00Z"

    def it_none_when_no_timestamps(self):
        svc = CognitiveMemoryService()

        profile = svc.build_profile("agent_abc", [])

        assert profile.first_memory_at is None
        assert profile.last_memory_at is None
