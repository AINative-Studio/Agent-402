"""
Event API endpoints.

Implements event creation for audit trails and system tracking.
Per PRD §6 (ZeroDB Integration) and §10 (Success Criteria - Replayability).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import verify_api_key
from app.models.event import EventCreate, EventResponse
from app.services.event_service import event_service

router = APIRouter(prefix="/database/events", tags=["Events"])


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post an event for audit trail and system tracking",
    description="""
Post an event to the audit trail and system tracking ledger.

Events support compliance auditability, agent workflow tracking, and deterministic replay.
All events are append-only for non-repudiation.

**Event Types (Examples):**
- `agent_decision`: Agent decision-making events
- `agent_tool_call`: Agent tool invocation tracking
- `compliance_check`: Compliance validation results
- `x402_request`: X402 protocol request tracking
- Custom event types for specific workflows

**Timestamp Handling:**
- If `timestamp` is provided, it must be in ISO8601 format (e.g., '2025-01-11T22:00:00Z')
- If `timestamp` is omitted, the current server time is used
- The `created_at` field always reflects when the record was created in the system

**Use Cases:**
1. **Agent Memory**: Record agent decisions for cross-run memory and improvement
2. **Compliance Audit**: Track KYC/KYT checks and risk scores
3. **Workflow Replay**: Store events to enable deterministic workflow replay
4. **System Observability**: Monitor agent lifecycles and tool calls

**Example Request:**
```json
{
  "event_type": "agent_decision",
  "data": {
    "agent_id": "analyst-001",
    "decision": "approve_transaction",
    "confidence": 0.95,
    "reasoning": "All compliance checks passed"
  },
  "timestamp": "2025-01-11T22:00:00Z"
}
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "agent_decision",
  "data": {
    "agent_id": "analyst-001",
    "decision": "approve_transaction",
    "confidence": 0.95,
    "reasoning": "All compliance checks passed"
  },
  "timestamp": "2025-01-11T22:00:00Z",
  "created_at": "2025-01-11T22:00:01Z"
}
```

**Error Codes:**
- `INVALID_API_KEY`: Missing or invalid API key
- `INVALID_TIMESTAMP`: Invalid timestamp format (must be ISO8601)
""",
    responses={
        201: {
            "description": "Event created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "event_type": "agent_decision",
                        "data": {
                            "agent_id": "analyst-001",
                            "decision": "approve_transaction",
                            "confidence": 0.95
                        },
                        "timestamp": "2025-01-11T22:00:00Z",
                        "created_at": "2025-01-11T22:00:01Z"
                    }
                }
            }
        },
        401: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid or missing API key. Please provide a valid X-API-Key header.",
                        "error_code": "INVALID_API_KEY"
                    }
                }
            }
        },
        422: {
            "description": "Invalid timestamp format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid timestamp '2025-13-01T22:00:00Z'. Expected ISO8601 format (e.g., '2025-01-11T22:00:00Z' or '2025-01-11T22:00:00+00:00'). Error: month must be in 1..12",
                        "error_code": "INVALID_TIMESTAMP"
                    }
                }
            }
        }
    }
)
async def create_event(
    event_data: EventCreate,
    user_id: Annotated[str, Depends(verify_api_key)]
) -> EventResponse:
    """
    Create a new event for audit trail and system tracking.

    Events are append-only and immutable after creation, supporting:
    - Compliance auditability
    - Agent workflow replay
    - Non-repudiation
    - System observability

    Per PRD §6: Events are stored for audit trail and system tracking.
    Per PRD §10: Events enable deterministic workflow replay.
    """
    return event_service.create_event(user_id, event_data)
