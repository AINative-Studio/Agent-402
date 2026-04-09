"""
Hedera Audit API — per-project HCS audit trail endpoints (Issue #268 Phase 2).

Routes:
  POST /hedera/audit/{project_id}/log      — log an audit event
  GET  /hedera/audit/{project_id}          — retrieve audit log
  GET  /hedera/audit/{project_id}/summary  — event counts by type

Built by AINative Dev Team
Refs #268
"""
from __future__ import annotations

from typing import Optional, Any

from fastapi import APIRouter, Depends, Query, status, HTTPException

from app.schemas.hedera_mcp import (
    LogAuditEventRequest,
    LogAuditEventResponse,
    AuditEvent,
    AuditLogResponse,
    AuditSummary,
)
from app.services.hcs_project_audit_service import (
    HCSProjectAuditService,
    HCSProjectAuditError,
    get_hcs_project_audit_service,
)

router = APIRouter(
    prefix="/hedera/audit",
    tags=["hedera-audit"],
)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_audit_service() -> HCSProjectAuditService:
    """Dependency that returns the shared HCSProjectAuditService instance."""
    return get_hcs_project_audit_service()


# ---------------------------------------------------------------------------
# POST /hedera/audit/{project_id}/log
# ---------------------------------------------------------------------------

@router.post(
    "/{project_id}/log",
    response_model=LogAuditEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log an audit event to the project HCS topic",
    description="""
    Submit a structured audit event to the HCS topic associated with a project.

    **Event types:** payment, decision, handoff, memory_anchor, compliance

    **Issue #268 Phase 2:** HCS per-project audit trail.
    """,
)
async def log_audit_event(
    project_id: str,
    body: LogAuditEventRequest,
    service: HCSProjectAuditService = Depends(get_audit_service),
) -> LogAuditEventResponse:
    """Log an audit event to the project's HCS topic."""
    try:
        result = await service.log_audit_event(
            project_id=project_id,
            topic_id=body.topic_id,
            event_type=body.event_type,
            payload=body.payload,
            agent_id=body.agent_id,
        )
    except HCSProjectAuditError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return LogAuditEventResponse(
        sequence_number=result["sequence_number"],
        project_id=project_id,
        event_type=body.event_type,
    )


# ---------------------------------------------------------------------------
# GET /hedera/audit/{project_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{project_id}",
    response_model=AuditLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve audit log for a project",
    description="""
    Query the Hedera mirror node for audit events associated with a project's
    HCS topic.

    **Issue #268 Phase 2:** HCS per-project audit trail.
    """,
)
async def get_audit_log(
    project_id: str,
    topic_id: str = Query(..., description="HCS topic ID for this project"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max events to return"),
    since: Optional[str] = Query(default=None, description="ISO timestamp — return events after this"),
    service: HCSProjectAuditService = Depends(get_audit_service),
) -> AuditLogResponse:
    """Retrieve audit log for a project from its HCS topic."""
    try:
        events_raw = await service.get_audit_log(
            project_id=project_id,
            topic_id=topic_id,
            limit=limit,
            since=since,
        )
    except HCSProjectAuditError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    events = [
        AuditEvent(
            sequence_number=e.get("sequence_number", 0),
            event_type=e.get("event_type"),
            consensus_timestamp=e.get("consensus_timestamp"),
            raw_message=e.get("message"),
        )
        for e in events_raw
    ]

    return AuditLogResponse(
        project_id=project_id,
        topic_id=topic_id,
        events=events,
        count=len(events),
    )


# ---------------------------------------------------------------------------
# GET /hedera/audit/{project_id}/summary
# ---------------------------------------------------------------------------

@router.get(
    "/{project_id}/summary",
    response_model=AuditSummary,
    status_code=status.HTTP_200_OK,
    summary="Get audit event counts by type for a project",
    description="""
    Returns event count totals grouped by event type for the given project's
    HCS topic.

    **Issue #268 Phase 2:** HCS per-project audit trail.
    """,
)
async def get_audit_summary(
    project_id: str,
    topic_id: str = Query(..., description="HCS topic ID for this project"),
    service: HCSProjectAuditService = Depends(get_audit_service),
) -> AuditSummary:
    """Return event count summary for a project's audit log."""
    try:
        summary = await service.get_audit_summary(
            project_id=project_id,
            topic_id=topic_id,
        )
    except HCSProjectAuditError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return AuditSummary(
        project_id=project_id,
        topic_id=topic_id,
        total=summary["total"],
        by_type=summary["by_type"],
    )
