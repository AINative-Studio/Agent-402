"""
Memory Decay API Router — Issues #208, #209, #210.

Endpoints:
  POST /memory/decay/run          — run a decay cycle for a project
  GET  /memory/{id}/importance    — compute current importance for one memory
  POST /memory/decay/promote      — trigger promotion check for a project

NOTE: This router is NOT registered in main.py.
      Wire it up explicitly when ready to expose these endpoints.

Built by AINative Dev Team.
Refs #208, #209, #210.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.schemas.memory_decay import DecayCycleResult, PromotionResult
from app.services.memory_decay_worker import MemoryDecayWorker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory-decay"])

# Shared worker instance — replace with DI/singleton pattern as needed
_worker = MemoryDecayWorker()


class RunDecayRequest(BaseModel):
    """Request body for POST /memory/decay/run."""

    project_id: str = Field(..., description="Project to run the decay cycle against")


class ImportanceResponse(BaseModel):
    """Response body for GET /memory/{id}/importance."""

    memory_id: str
    importance: float
    tier: str


class PromoteRequest(BaseModel):
    """Request body for POST /memory/decay/promote."""

    project_id: str = Field(..., description="Project to evaluate promotions for")


@router.post("/decay/run", response_model=DecayCycleResult, status_code=200)
async def run_decay_cycle(body: RunDecayRequest) -> DecayCycleResult:
    """
    Run a decay cycle for all memories in the given project.

    Returns a summary of processed memories, updated scores, and
    memories flagged for eviction.
    """
    try:
        result = await _worker.run_decay_cycle(body.project_id)
        return result
    except Exception as exc:
        logger.error("Decay cycle failed for project %s: %s", body.project_id, exc)
        raise HTTPException(status_code=500, detail="Decay cycle failed") from exc


@router.get("/{memory_id}/importance", response_model=ImportanceResponse)
async def get_memory_importance(
    memory_id: str,
    tier: str = Query("working", description="Memory tier"),
    initial_importance: float = Query(1.0, description="Initial importance score"),
    age_days: float = Query(0.0, description="Age of the memory in days"),
) -> ImportanceResponse:
    """
    Compute the current importance score for a single memory.

    Accepts the memory attributes as query parameters to avoid requiring
    a storage round-trip (useful for preview/debug purposes).
    """
    from datetime import datetime, timedelta, timezone

    created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    memory: Dict[str, Any] = {
        "memory_id": memory_id,
        "tier": tier,
        "initial_importance": initial_importance,
        "created_at": created_at.isoformat(),
        "recent_accesses": [],
    }
    try:
        importance = await _worker.calculate_importance(memory)
        return ImportanceResponse(
            memory_id=memory_id,
            importance=importance,
            tier=tier,
        )
    except Exception as exc:
        logger.error("Importance calculation failed for %s: %s", memory_id, exc)
        raise HTTPException(
            status_code=500, detail="Importance calculation failed"
        ) from exc


@router.post("/decay/promote", status_code=200)
async def run_promotions(body: PromoteRequest) -> Dict[str, Any]:
    """
    Evaluate all memories for a project and promote eligible ones.

    Returns a list of promotion results.
    """
    try:
        results = await _worker.check_promotions(body.project_id)
        return {
            "project_id": body.project_id,
            "promotions": [r.model_dump() for r in results],
            "promoted_count": sum(1 for r in results if r.promoted),
        }
    except Exception as exc:
        logger.error("Promotion check failed for project %s: %s", body.project_id, exc)
        raise HTTPException(status_code=500, detail="Promotion check failed") from exc
