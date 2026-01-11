# Epic 12 Issue 4: X402 Requests Linked to Agent + Task

## Implementation Summary

**Issue:** As a system, X402 requests are linked to the agent + task that produced them.
**Story Points:** 3
**Status:** Implemented
**Built by:** AINative Dev Team

## PRD References

- **Section 6 (ZeroDB Integration):** X402 signed requests are logged with agent and task linkage
- **Section 8 (X402 Protocol):** X402 requests contain signed payment authorizations

## Requirements Implemented

### 1. POST /v1/public/{project_id}/x402-requests

Creates a new X402 signed request record linked to agent and task.

**Request Schema:**
- `agent_id` (required): DID or identifier of the agent creating the request
- `task_id` (required): Identifier of the task that produced the request
- `run_id` (required): Identifier of the agent run context
- `request_payload` (required): The X402 protocol payload (payment authorization)
- `signature` (required): Cryptographic signature of the request
- `status` (optional): Initial status (defaults to PENDING)
- `linked_memory_ids` (optional): Links to agent_memory records
- `linked_compliance_ids` (optional): Links to compliance_events records
- `metadata` (optional): Additional custom metadata

**Response:** Returns created request with unique `request_id` and `timestamp`.

### 2. GET /v1/public/{project_id}/x402-requests

Lists X402 requests with filtering and pagination.

**Query Parameters:**
- `agent_id`: Filter by agent identifier
- `task_id`: Filter by task identifier
- `run_id`: Filter by run identifier
- `status`: Filter by request status (PENDING, APPROVED, REJECTED, EXPIRED, COMPLETED)
- `limit`: Maximum results (1-1000, default 100)
- `offset`: Pagination offset (default 0)

**Response:** Paginated list of requests with total count.

### 3. GET /v1/public/{project_id}/x402-requests/{request_id}

Gets a single X402 request with all linked records.

**Response:** Full request details including:
- Complete X402 request data
- `linked_memories`: Full agent_memory records
- `linked_compliance_events`: Full compliance_events records

## File Locations

| File | Purpose |
|------|---------|
| `backend/app/schemas/x402_requests.py` | Pydantic schemas for request/response validation |
| `backend/app/services/x402_service.py` | Business logic and data operations |
| `backend/app/api/x402_requests.py` | FastAPI route handlers |
| `backend/app/main.py` | Router registration |

## Schema Details

### X402RequestStatus Enum

```python
class X402RequestStatus(str, Enum):
    PENDING = "PENDING"      # Request created but not yet processed
    APPROVED = "APPROVED"    # Request has been approved
    REJECTED = "REJECTED"    # Request has been rejected
    EXPIRED = "EXPIRED"      # Request has expired without processing
    COMPLETED = "COMPLETED"  # Request has been fully processed
```

### Key Data Models

- **X402RequestCreate**: Input schema for creating requests
- **X402RequestResponse**: Standard response with request details
- **X402RequestWithLinks**: Extended response including full linked records
- **X402RequestListResponse**: Paginated list response
- **X402RequestFilter**: Filter parameters for listing

## Service Layer

The `X402Service` class provides:

- `create_request()`: Creates new X402 request with all required fields
- `get_request()`: Retrieves request by ID, optionally with linked records
- `list_requests()`: Lists requests with filtering and pagination
- `update_request_status()`: Updates request status
- `add_memory_link()`: Links additional memory records
- `add_compliance_link()`: Links additional compliance events
- `get_requests_by_agent()`: Helper for agent-specific queries
- `get_requests_by_task()`: Helper for task-specific queries
- `get_requests_by_run()`: Helper for run-specific queries

## Error Handling

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| X402_REQUEST_NOT_FOUND | 404 | Request ID does not exist |
| INVALID_API_KEY | 401 | Missing or invalid authentication |
| VALIDATION_ERROR | 422 | Invalid request schema |

## Example Usage

### Create X402 Request

```bash
curl -X POST "http://localhost:8000/v1/public/proj_123/x402-requests" \
  -H "X-API-Key: test_api_key_001" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "did:ethr:0xabc123def456",
    "task_id": "task_payment_001",
    "run_id": "run_2026_01_10_001",
    "request_payload": {
      "type": "payment_authorization",
      "amount": "100.00",
      "currency": "USD",
      "recipient": "did:ethr:0xdef789abc012"
    },
    "signature": "0xsig123abc456def789...",
    "linked_memory_ids": ["mem_abc123"],
    "linked_compliance_ids": ["comp_evt_001"]
  }'
```

### List X402 Requests by Agent

```bash
curl -X GET "http://localhost:8000/v1/public/proj_123/x402-requests?agent_id=did:ethr:0xabc123def456&limit=50" \
  -H "X-API-Key: test_api_key_001"
```

### Get X402 Request with Links

```bash
curl -X GET "http://localhost:8000/v1/public/proj_123/x402-requests/x402_req_abc123" \
  -H "X-API-Key: test_api_key_001"
```

## Integration Points

### Agent Memory Linking

X402 requests can be linked to agent_memory records to provide decision provenance:
- Memory records contain the context/reasoning that led to the X402 request
- Enables audit trail for payment authorization decisions
- Supports compliance and regulatory requirements

### Compliance Events Linking

X402 requests can be linked to compliance_events records:
- Compliance checks performed before authorization
- Audit trail for regulatory compliance
- Supports non-repudiation requirements per PRD Section 10

## Implementation Notes

### MVP Storage

Currently uses in-memory storage simulation for fast development:
- `_request_store`: Dict[project_id, Dict[request_id, request_data]]
- Production will use ZeroDB for persistence

### ID Generation

Request IDs follow the pattern: `x402_req_{uuid_hex[:16]}`
- Unique and non-colliding
- Identifiable as X402 requests
- Consistent with other ID patterns in the system

### Sorting

Requests are sorted by timestamp descending (newest first) for listing operations.

## Testing Considerations

Key test scenarios:
1. Create X402 request with all required fields
2. Create X402 request with linked memory and compliance IDs
3. List requests with various filter combinations
4. Get single request with expanded linked records
5. Handle not-found errors appropriately
6. Validate required fields are enforced
7. Verify status enum validation
