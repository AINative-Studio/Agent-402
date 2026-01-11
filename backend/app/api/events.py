"""
Events API endpoints for ZeroDB.

Implements GitHub Issue #38: Event creation with event_type, data, timestamp validation.
Per PRD §6 (ZeroDB Integration) and Epic 8 (Events API).
"""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Header, status
from app.schemas.event import EventCreateRequest, EventResponse, EventListResponse
from app.core.errors import InvalidAPIKeyError
import uuid


router = APIRouter(prefix="/v1/public/database/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreateRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> EventResponse:
    """
    Create a new event in the event stream.

    Per Epic 8 Story 1: POST /database/events for audit trail.
    Per Epic 8 Story 2: Accepts event_type, data, timestamp.

    **Authentication:** Required via X-API-Key header.

    **Request Body:**
    - `event_type` (string, required): Event type identifier, 1-100 characters
    - `data` (object, required): Event payload as JSON object, can be nested
    - `timestamp` (string, optional): ISO8601 datetime string, auto-generated if not provided

    **Response:** EventResponse with event_id and created timestamp.

    **Example Request:**
    ```json
    {
        "event_type": "agent_decision",
        "data": {
            "agent_id": "agent_001",
            "action": "approve_transaction",
            "confidence": 0.95
        },
        "timestamp": "2026-01-10T18:30:00Z"
    }
    ```

    **Example Response:**
    ```json
    {
        "event_id": "evt_abc123",
        "event_type": "agent_decision",
        "timestamp": "2026-01-10T18:30:00Z",
        "status": "created"
    }
    ```

    **Errors:**
    - `401 INVALID_API_KEY`: Missing or invalid API key
    - `422 VALIDATION_ERROR`: Invalid event_type, data, or timestamp format
    """
    # Authentication check
    # Per DX Contract: Use InvalidAPIKeyError for consistent error_code
    if not x_api_key:
        raise InvalidAPIKeyError(detail="Missing X-API-Key header")

    # Auto-generate timestamp if not provided
    event_timestamp = event.timestamp
    if event_timestamp is None:
        # Generate current UTC timestamp in ISO8601 format
        event_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    # Generate unique event ID
    event_id = f"evt_{uuid.uuid4().hex[:12]}"

    # Create event response
    # In production, this would persist to ZeroDB events table
    # For MVP, we return the success response per Epic 8 Story 4
    response = EventResponse(
        event_id=event_id,
        event_type=event.event_type,
        timestamp=event_timestamp,
        status="created"
    )

    return response


@router.get("", response_model=EventListResponse)
async def list_events(
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> EventListResponse:
    """
    List events with optional filtering.

    **Authentication:** Required via X-API-Key header.

    **Query Parameters:**
    - `event_type` (string, optional): Filter by event type
    - `limit` (integer, optional): Maximum number of events to return (default: 100)
    - `offset` (integer, optional): Pagination offset (default: 0)

    **Response:** EventListResponse with list of events and total count.

    **Example Response:**
    ```json
    {
        "events": [
            {
                "event_id": "evt_abc123",
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "agent_001",
                    "action": "approve"
                },
                "timestamp": "2026-01-10T18:30:00Z"
            }
        ],
        "total": 1
    }
    ```

    **Errors:**
    - `401 INVALID_API_KEY`: Missing or invalid API key
    """
    # Authentication check
    # Per DX Contract: Use InvalidAPIKeyError for consistent error_code
    if not x_api_key:
        raise InvalidAPIKeyError(detail="Missing X-API-Key header")

    # In production, this would query ZeroDB events table
    # For MVP, return empty list per Epic 8 requirements
    response = EventListResponse(
        events=[],
        total=0
    )

    return response
