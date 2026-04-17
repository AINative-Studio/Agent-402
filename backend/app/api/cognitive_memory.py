"""
ZeroMemory Cognitive API — parent router (Refs #292).

Aggregates the four cognitive endpoints into a single router so
`app.main` only needs to include one router. Each endpoint owns its own
file under `app.api.cognitive`, enabling worktree-safe parallel work on
S1–S4 without file conflicts.

Endpoints (after S1–S4 land):
- POST /v1/public/{project_id}/memory/remember   (S1, #309)
- POST /v1/public/{project_id}/memory/recall     (S2, #310)
- POST /v1/public/{project_id}/memory/reflect    (S3, #311)
- GET  /v1/public/{project_id}/memory/profile/{agent_id} (S4, #312)

Workshop alias via WorkshopPrefixMiddleware convention mapping:
- /api/v1/memory/remember -> /v1/public/{workshop_default_project_id}/memory/remember
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.cognitive import profile, recall, reflect, remember

router = APIRouter()
router.include_router(remember.router)
router.include_router(recall.router)
router.include_router(reflect.router)
router.include_router(profile.router)
