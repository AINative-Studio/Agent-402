# Epic 12 Issue 3: Compliance Events API

## Overview

**Issue:** As a compliance agent, I can write outcomes to `compliance_events`.
**Story Points:** 2
**PRD Reference:** Section 6 - ZeroDB Integration

## Implementation Summary

This issue implements a complete API for logging and retrieving compliance events, enabling compliance agents to record their outcomes with full auditability.

## Files Created/Modified

### New Files

1. **`backend/app/schemas/compliance_events.py`**
   - Pydantic schemas for request/response validation
   - `ComplianceEventType` enum: KYC_CHECK, KYT_CHECK, RISK_ASSESSMENT, COMPLIANCE_DECISION, AUDIT_LOG
   - `ComplianceOutcome` enum: PASS, FAIL, PENDING, ESCALATED, ERROR
   - `ComplianceEventCreate`: Request schema for creating events
   - `ComplianceEventResponse`: Response schema with full event data
   - `ComplianceEventListResponse`: Paginated list response
   - `ComplianceEventFilter`: Query filter parameters

2. **`backend/app/services/compliance_service.py`**
   - Business logic for compliance event operations
   - In-memory storage for MVP (production will use ZeroDB tables)
   - CRUD operations: create, get, list, delete
   - Filtering by agent, event type, outcome, risk score, time range
   - Project-level statistics

3. **`backend/app/api/compliance_events.py`**
   - FastAPI router with three endpoints
   - Full OpenAPI documentation
   - Authentication via X-API-Key

### Modified Files

4. **`backend/app/main.py`**
   - Added import for compliance_events router
   - Registered compliance_events_router

## API Endpoints

### POST /v1/public/{project_id}/compliance-events

Create a new compliance event.

**Request Body:**
```json
{
  "agent_id": "compliance_agent_001",
  "event_type": "KYC_CHECK",
  "outcome": "PASS",
  "risk_score": 0.15,
  "details": {
    "customer_id": "cust_12345",
    "verification_method": "document"
  },
  "run_id": "run_abc123"
}
```

**Response (201 Created):**
```json
{
  "event_id": "evt_abc123def456",
  "project_id": "proj_xyz789",
  "agent_id": "compliance_agent_001",
  "event_type": "KYC_CHECK",
  "outcome": "PASS",
  "risk_score": 0.15,
  "details": {...},
  "run_id": "run_abc123",
  "timestamp": "2026-01-10T12:34:56.789Z"
}
```

### GET /v1/public/{project_id}/compliance-events

List compliance events with optional filtering.

**Query Parameters:**
- `agent_id`: Filter by agent
- `event_type`: Filter by type (KYC_CHECK, KYT_CHECK, etc.)
- `outcome`: Filter by outcome (PASS, FAIL, etc.)
- `run_id`: Filter by workflow run
- `min_risk_score`: Minimum risk score (0.0-1.0)
- `max_risk_score`: Maximum risk score (0.0-1.0)
- `start_time`: Start time (ISO 8601)
- `end_time`: End time (ISO 8601)
- `limit`: Max results (default: 100, max: 1000)
- `offset`: Pagination offset

**Response (200 OK):**
```json
{
  "events": [...],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

### GET /v1/public/{project_id}/compliance-events/{event_id}

Get a single compliance event by ID.

**Response (200 OK):**
```json
{
  "event_id": "evt_abc123def456",
  "project_id": "proj_xyz789",
  "agent_id": "compliance_agent_001",
  ...
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Compliance event not found: evt_abc123def456",
  "error_code": "EVENT_NOT_FOUND"
}
```

## Event Types

| Type | Description |
|------|-------------|
| KYC_CHECK | Know Your Customer verification results |
| KYT_CHECK | Know Your Transaction analysis results |
| RISK_ASSESSMENT | Risk scoring and assessment outcomes |
| COMPLIANCE_DECISION | Final compliance decisions |
| AUDIT_LOG | Audit trail entries for compliance actions |

## Outcome Types

| Outcome | Description |
|---------|-------------|
| PASS | Compliance check passed |
| FAIL | Compliance check failed |
| PENDING | Awaiting further review |
| ESCALATED | Escalated for manual review |
| ERROR | Error during processing |

## Schema Details

### Required Fields (Create)
- `agent_id`: String (1-255 chars)
- `event_type`: ComplianceEventType enum
- `outcome`: ComplianceOutcome enum
- `risk_score`: Float (0.0-1.0)

### Optional Fields (Create)
- `details`: Object (default: {})
- `run_id`: String (max 255 chars)

### System-Generated Fields
- `event_id`: Unique identifier (format: `evt_{uuid}`)
- `timestamp`: ISO 8601 timestamp
- `project_id`: From URL path

## DX Contract Compliance

- All endpoints require X-API-Key authentication
- All errors return `{ detail, error_code }` format
- Validation errors use HTTP 422
- Not found errors use HTTP 404 with EVENT_NOT_FOUND error code

## Testing

Example curl commands:

```bash
# Create event
curl -X POST "http://localhost:8000/v1/public/proj_123/compliance-events" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "compliance_agent_001",
    "event_type": "KYC_CHECK",
    "outcome": "PASS",
    "risk_score": 0.15,
    "details": {"customer_id": "cust_123"}
  }'

# List events
curl "http://localhost:8000/v1/public/proj_123/compliance-events?event_type=KYC_CHECK" \
  -H "X-API-Key: your-api-key"

# Get single event
curl "http://localhost:8000/v1/public/proj_123/compliance-events/evt_abc123" \
  -H "X-API-Key: your-api-key"
```

## Future Enhancements

1. ZeroDB table integration (production storage)
2. Real-time event streaming
3. Aggregation and analytics endpoints
4. Event retention policies
5. Webhook notifications for high-risk events

---
Built by AINative Dev Team
