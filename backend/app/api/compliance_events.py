"""
Compliance Events API endpoints.
Implements Epic 12 Issue 3: Write outcomes to compliance_events.

Per PRD Section 6 (ZeroDB Integration):
- POST /v1/public/{project_id}/compliance-events - Log compliance outcomes
- GET /v1/public/{project_id}/compliance-events - List events with filters
- GET /v1/public/{project_id}/compliance-events/{event_id} - Get single event

Event Types (per Issue 3 requirements):
- KYC_CHECK: Know Your Customer verification
- KYT_CHECK: Know Your Transaction analysis
- RISK_ASSESSMENT: Risk scoring outcomes
- COMPLIANCE_DECISION: Final compliance decisions
- AUDIT_LOG: Audit trail entries

DX Contract Compliance:
- All endpoints require X-API-Key authentication
- All errors return { detail, error_code }
- Validation errors use HTTP 422
"""
from typing import Optional
from fastapi import APIRouter, Depends, status, Path, Query
from app.core.auth import get_current_user
from app.core.errors import APIError
from app.schemas.project import ErrorResponse
from app.schemas.compliance_events import (
    ComplianceEventType,
    ComplianceOutcome,
    ComplianceEventCreate,
    ComplianceEventResponse,
    ComplianceEventListResponse,
    ComplianceEventFilter
)
from app.services.compliance_service import compliance_service


router = APIRouter(
    prefix="/v1/public",
    tags=["compliance"]
)


@router.post(
    "/{project_id}/compliance-events",
    response_model=ComplianceEventResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Successfully created compliance event",
            "model": ComplianceEventResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Log compliance event",
    description="""
    Log a compliance event outcome to the compliance_events table.

    **Authentication:** Requires X-API-Key header

    **Epic 12 Issue 3:** As a compliance agent, I can write outcomes to compliance_events.

    **Event Types:**
    - KYC_CHECK: Know Your Customer verification results
    - KYT_CHECK: Know Your Transaction analysis results
    - RISK_ASSESSMENT: Risk scoring and assessment outcomes
    - COMPLIANCE_DECISION: Final compliance decisions
    - AUDIT_LOG: Audit trail entries for compliance actions

    **Outcomes:**
    - PASS: Compliance check passed
    - FAIL: Compliance check failed
    - PENDING: Awaiting further review
    - ESCALATED: Escalated for manual review
    - ERROR: Error during processing

    **Risk Score:**
    - Range: 0.0 (low risk) to 1.0 (high risk)
    - Used for risk-based decision making

    **Per PRD Section 6 (ZeroDB Integration):**
    - Events are stored with full auditability
    - Supports compliance tracking and reporting
    - Enables decision provenance
    """
)
async def create_compliance_event(
    project_id: str = Path(..., description="Project ID"),
    request: ComplianceEventCreate = ...,
    current_user: str = Depends(get_current_user)
) -> ComplianceEventResponse:
    """
    Create a new compliance event.

    Epic 12 Issue 3 Implementation:
    - Accepts agent_id, event_type, outcome, risk_score, details, run_id
    - Generates unique event_id and timestamp
    - Stores event in compliance_events table
    - Returns full event data including generated fields

    Args:
        project_id: Project identifier
        request: Compliance event data
        current_user: Authenticated user ID

    Returns:
        ComplianceEventResponse with created event data
    """
    event = compliance_service.create_event(
        project_id=project_id,
        event_data=request
    )
    return event


@router.get(
    "/{project_id}/compliance-events",
    response_model=ComplianceEventListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved compliance events",
            "model": ComplianceEventListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    },
    summary="List compliance events",
    description="""
    List compliance events with optional filtering.

    **Authentication:** Requires X-API-Key header

    **Filters:**
    - agent_id: Filter by agent
    - event_type: Filter by event type
    - outcome: Filter by outcome
    - run_id: Filter by workflow run
    - min_risk_score/max_risk_score: Filter by risk score range
    - start_time/end_time: Filter by time range (ISO 8601)

    **Pagination:**
    - limit: Maximum events to return (default: 100, max: 1000)
    - offset: Offset for pagination (default: 0)

    **Ordering:**
    - Events are returned in descending order by timestamp (most recent first)
    """
)
async def list_compliance_events(
    project_id: str = Path(..., description="Project ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    event_type: Optional[ComplianceEventType] = Query(None, description="Filter by event type"),
    outcome: Optional[ComplianceOutcome] = Query(None, description="Filter by outcome"),
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum risk score"),
    max_risk_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum risk score"),
    start_time: Optional[str] = Query(None, description="Start time (ISO 8601)"),
    end_time: Optional[str] = Query(None, description="End time (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: str = Depends(get_current_user)
) -> ComplianceEventListResponse:
    """
    List compliance events with filtering and pagination.

    Args:
        project_id: Project identifier
        agent_id: Optional agent filter
        event_type: Optional event type filter
        outcome: Optional outcome filter
        run_id: Optional run ID filter
        min_risk_score: Optional minimum risk score
        max_risk_score: Optional maximum risk score
        start_time: Optional start time filter
        end_time: Optional end time filter
        limit: Maximum events to return
        offset: Pagination offset
        current_user: Authenticated user ID

    Returns:
        ComplianceEventListResponse with events and pagination info
    """
    # Build filter object
    filters = ComplianceEventFilter(
        agent_id=agent_id,
        event_type=event_type,
        outcome=outcome,
        run_id=run_id,
        min_risk_score=min_risk_score,
        max_risk_score=max_risk_score,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )

    # Get filtered events
    events, total = compliance_service.list_events(
        project_id=project_id,
        filters=filters
    )

    return ComplianceEventListResponse(
        events=events,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{project_id}/compliance-events/{event_id}",
    response_model=ComplianceEventResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved compliance event",
            "model": ComplianceEventResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Event not found",
            "model": ErrorResponse
        }
    },
    summary="Get compliance event",
    description="""
    Get a single compliance event by ID.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Full event data including all fields
    - 404 if event not found
    """
)
async def get_compliance_event(
    project_id: str = Path(..., description="Project ID"),
    event_id: str = Path(..., description="Event ID"),
    current_user: str = Depends(get_current_user)
) -> ComplianceEventResponse:
    """
    Get a single compliance event by ID.

    Args:
        project_id: Project identifier
        event_id: Event identifier
        current_user: Authenticated user ID

    Returns:
        ComplianceEventResponse with event data

    Raises:
        APIError: If event not found (404)
    """
    event = compliance_service.get_event(
        project_id=project_id,
        event_id=event_id
    )

    if not event:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="EVENT_NOT_FOUND",
            detail=f"Compliance event not found: {event_id}"
        )

    return event
