# API Examples - Copy-Paste Ready

**Version:** 1.0
**Last Updated:** 2026-01-11
**Purpose:** Minimal, working examples for every API endpoint

## Setup

Before using any examples, set your environment variables:

```bash
export API_KEY="your_api_key_here"
export PROJECT_ID="proj_abc123"
export BASE_URL="https://api.ainative.studio"
```

---

## Table of Contents

1. [Projects API](#projects-api)
2. [Agents API](#agents-api)
3. [Agent Memory API](#agent-memory-api)
4. [Events API](#events-api)
5. [Embeddings API](#embeddings-api)
6. [Vector Operations API](#vector-operations-api)
7. [Compliance Events API](#compliance-events-api)
8. [X402 Requests API](#x402-requests-api)
9. [Runs API](#runs-api)

---

## Projects API

### GET /v1/public/projects

List all projects for authenticated user.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/projects" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "projects": [
    {
      "id": "proj_abc123",
      "name": "My Project",
      "status": "ACTIVE",
      "tier": "free"
    }
  ],
  "total": 1
}
```

---

### GET /v1/public/projects/{project_id}

Get a single project by ID.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/projects/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my-agent-project",
  "description": "Agent memory and compliance tracking",
  "tier": "free",
  "status": "ACTIVE",
  "database_enabled": true,
  "created_at": "2025-12-13T22:41:00Z",
  "updated_at": "2025-12-13T22:41:00Z"
}
```

**Error Responses:**

404 Not Found - Project doesn't exist:
```json
{
  "detail": "Project not found: 550e8400-e29b-41d4-a716-446655440000",
  "error_code": "PROJECT_NOT_FOUND"
}
```

403 Forbidden - User doesn't own the project:
```json
{
  "detail": "Not authorized to access this resource",
  "error_code": "UNAUTHORIZED"
}
```

422 Unprocessable Entity - Invalid UUID format:
```json
{
  "detail": "Invalid UUID format: not-a-valid-uuid",
  "error_code": "HTTP_ERROR"
}
```

---

## Agents API

### POST /v1/public/{project_id}/agents

Create a new agent profile.

**Example:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/agents" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "did": "did:agent:compliance_001",
    "role": "compliance_analyst",
    "name": "Compliance Agent Alpha",
    "description": "KYC/AML compliance verification agent"
  }'
```

**Response:**
```json
{
  "id": "agent_xyz789",
  "did": "did:agent:compliance_001",
  "role": "compliance_analyst",
  "name": "Compliance Agent Alpha",
  "description": "KYC/AML compliance verification agent",
  "scope": "PROJECT",
  "project_id": "proj_abc123",
  "created_at": "2026-01-11T10:00:00Z",
  "updated_at": "2026-01-11T10:00:00Z"
}
```

---

### GET /v1/public/{project_id}/agents

List all agents in a project.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/agents" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "agents": [
    {
      "id": "agent_xyz789",
      "did": "did:agent:compliance_001",
      "role": "compliance_analyst",
      "name": "Compliance Agent Alpha",
      "scope": "PROJECT",
      "project_id": "proj_abc123"
    }
  ],
  "total": 1
}
```

---

### GET /v1/public/{project_id}/agents/{agent_id}

Get a single agent by ID.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/agents/agent_xyz789" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "id": "agent_xyz789",
  "did": "did:agent:compliance_001",
  "role": "compliance_analyst",
  "name": "Compliance Agent Alpha",
  "description": "KYC/AML compliance verification agent",
  "scope": "PROJECT",
  "project_id": "proj_abc123",
  "created_at": "2026-01-11T10:00:00Z",
  "updated_at": "2026-01-11T10:00:00Z"
}
```

---

## Agent Memory API

### POST /v1/public/{project_id}/agent-memory

Create an agent memory entry.

**Example:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/agent-memory" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_xyz789",
    "run_id": "run_abc123",
    "memory_type": "decision",
    "content": "Approved transaction after KYC verification passed",
    "namespace": "default"
  }'
```

**Response:**
```json
{
  "memory_id": "mem_def456",
  "agent_id": "agent_xyz789",
  "run_id": "run_abc123",
  "memory_type": "decision",
  "namespace": "default",
  "timestamp": "2026-01-11T10:05:00Z",
  "created": true
}
```

---

### GET /v1/public/{project_id}/agent-memory

List agent memories with optional filters.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/agent-memory?agent_id=agent_xyz789&limit=10" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "memories": [
    {
      "memory_id": "mem_def456",
      "agent_id": "agent_xyz789",
      "run_id": "run_abc123",
      "memory_type": "decision",
      "content": "Approved transaction after KYC verification passed",
      "metadata": {},
      "namespace": "default",
      "timestamp": "2026-01-11T10:05:00Z",
      "project_id": "proj_abc123"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0,
  "filters_applied": {
    "agent_id": "agent_xyz789"
  }
}
```

---

### GET /v1/public/{project_id}/agent-memory/{memory_id}

Get a single agent memory entry.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/agent-memory/mem_def456" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "memory_id": "mem_def456",
  "agent_id": "agent_xyz789",
  "run_id": "run_abc123",
  "memory_type": "decision",
  "content": "Approved transaction after KYC verification passed",
  "metadata": {},
  "namespace": "default",
  "timestamp": "2026-01-11T10:05:00Z",
  "project_id": "proj_abc123"
}
```

---

## Events API

### POST /v1/public/{project_id}/database/events

Create an event in the event stream.

**Example:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/database/events" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent_decision",
    "data": {
      "agent_id": "agent_xyz789",
      "decision": "approve_transaction",
      "confidence": 0.95
    }
  }'
```

**Response:**
```json
{
  "id": "evt_1234567890abcdef",
  "event_type": "agent_decision",
  "data": {
    "agent_id": "agent_xyz789",
    "decision": "approve_transaction",
    "confidence": 0.95
  },
  "timestamp": "2026-01-11T10:30:00.000Z",
  "created_at": "2026-01-11T10:30:01.234Z"
}
```

---

## Embeddings API

### POST /v1/public/{project_id}/embeddings/generate

Generate an embedding vector for text.

**Example:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/embeddings/generate" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is the risk assessment for this transaction?"
  }'
```

**Response:**
```json
{
  "embedding": [0.123, -0.456, 0.789, ...],
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "text": "What is the risk assessment for this transaction?",
  "processing_time_ms": 45
}
```

---

### POST /v1/public/{project_id}/embeddings/embed-and-store

Generate embedding and store in vector database.

**Example:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/embeddings/embed-and-store" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Customer completed KYC verification successfully",
    "metadata": {
      "customer_id": "cust_123",
      "verification_type": "KYC"
    }
  }'
```

**Response:**
```json
{
  "vectors_stored": 1,
  "vector_id": "vec_abc123",
  "namespace": "default",
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "text": "Customer completed KYC verification successfully",
  "created": true,
  "processing_time_ms": 67,
  "stored_at": "2026-01-11T10:35:00Z"
}
```

---

### POST /v1/public/{project_id}/embeddings/search

Search for similar vectors using semantic similarity.

**Example:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/embeddings/search" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find KYC verification records",
    "top_k": 5,
    "similarity_threshold": 0.7
  }'
```

**Response:**
```json
{
  "results": [
    {
      "vector_id": "vec_abc123",
      "namespace": "default",
      "text": "Customer completed KYC verification successfully",
      "similarity": 0.89,
      "model": "BAAI/bge-small-en-v1.5",
      "dimensions": 384,
      "metadata": {
        "customer_id": "cust_123",
        "verification_type": "KYC"
      },
      "created_at": "2026-01-11T10:35:00Z"
    }
  ],
  "query": "Find KYC verification records",
  "namespace": "default",
  "model": "BAAI/bge-small-en-v1.5",
  "total_results": 1,
  "processing_time_ms": 23
}
```

---

### GET /v1/public/embeddings/models

List supported embedding models.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/embeddings/models"
```

**Response:**
```json
[
  {
    "name": "BAAI/bge-small-en-v1.5",
    "dimensions": 384,
    "description": "Fast and efficient model for general use",
    "is_default": true
  },
  {
    "name": "BAAI/bge-base-en-v1.5",
    "dimensions": 768,
    "description": "Balanced model with higher accuracy",
    "is_default": false
  },
  {
    "name": "BAAI/bge-large-en-v1.5",
    "dimensions": 1024,
    "description": "High accuracy model for critical applications",
    "is_default": false
  }
]
```

---

## Vector Operations API

### POST /v1/public/{project_id}/database/vectors/upsert

Upsert a vector embedding with raw vector data.

**Example:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/database/vectors/upsert" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vector_embedding": [0.1, 0.2, 0.3, ...],
    "dimensions": 384,
    "document": "Pre-computed embedding from external model",
    "metadata": {
      "source": "external_model",
      "model_version": "1.0"
    },
    "namespace": "default"
  }'
```

**Response:**
```json
{
  "vector_id": "vec_def456",
  "dimensions": 384,
  "namespace": "default",
  "metadata": {
    "source": "external_model",
    "model_version": "1.0"
  },
  "created": true,
  "processing_time_ms": 12,
  "stored_at": "2026-01-11T10:40:00Z"
}
```

---

## Compliance Events API

### POST /v1/public/{project_id}/compliance-events

Log a compliance event outcome.

**Example:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/compliance-events" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_xyz789",
    "event_type": "KYC_CHECK",
    "outcome": "PASS",
    "risk_score": 0.15,
    "details": {
      "customer_id": "cust_123",
      "verification_method": "document_upload",
      "documents_verified": ["passport", "utility_bill"]
    },
    "run_id": "run_abc123"
  }'
```

**Response:**
```json
{
  "event_id": "comp_evt_789",
  "project_id": "proj_abc123",
  "agent_id": "agent_xyz789",
  "event_type": "KYC_CHECK",
  "outcome": "PASS",
  "risk_score": 0.15,
  "details": {
    "customer_id": "cust_123",
    "verification_method": "document_upload",
    "documents_verified": ["passport", "utility_bill"]
  },
  "run_id": "run_abc123",
  "timestamp": "2026-01-11T10:45:00Z"
}
```

---

### GET /v1/public/{project_id}/compliance-events

List compliance events with filters.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/compliance-events?event_type=KYC_CHECK&outcome=PASS&limit=10" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "events": [
    {
      "event_id": "comp_evt_789",
      "project_id": "proj_abc123",
      "agent_id": "agent_xyz789",
      "event_type": "KYC_CHECK",
      "outcome": "PASS",
      "risk_score": 0.15,
      "details": {
        "customer_id": "cust_123"
      },
      "run_id": "run_abc123",
      "timestamp": "2026-01-11T10:45:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

---

### GET /v1/public/{project_id}/compliance-events/{event_id}

Get a single compliance event by ID.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/compliance-events/comp_evt_789" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "event_id": "comp_evt_789",
  "project_id": "proj_abc123",
  "agent_id": "agent_xyz789",
  "event_type": "KYC_CHECK",
  "outcome": "PASS",
  "risk_score": 0.15,
  "details": {
    "customer_id": "cust_123",
    "verification_method": "document_upload",
    "documents_verified": ["passport", "utility_bill"]
  },
  "run_id": "run_abc123",
  "timestamp": "2026-01-11T10:45:00Z"
}
```

---

## X402 Requests API

### POST /v1/public/{project_id}/x402-requests

Create an X402 signed request.

**Example:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/x402-requests" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_xyz789",
    "task_id": "task_pay_001",
    "run_id": "run_abc123",
    "request_payload": {
      "amount": 100.00,
      "currency": "USD",
      "recipient": "merchant_456",
      "description": "Payment for services"
    },
    "signature": "0x1234567890abcdef...",
    "status": "PENDING"
  }'
```

**Response:**
```json
{
  "request_id": "x402_req_123",
  "project_id": "proj_abc123",
  "agent_id": "agent_xyz789",
  "task_id": "task_pay_001",
  "run_id": "run_abc123",
  "request_payload": {
    "amount": 100.00,
    "currency": "USD",
    "recipient": "merchant_456",
    "description": "Payment for services"
  },
  "signature": "0x1234567890abcdef...",
  "status": "PENDING",
  "timestamp": "2026-01-11T10:50:00Z",
  "linked_memory_ids": [],
  "linked_compliance_ids": []
}
```

---

### GET /v1/public/{project_id}/x402-requests

List X402 requests with filters.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/x402-requests?agent_id=agent_xyz789&status=PENDING&limit=10" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "requests": [
    {
      "request_id": "x402_req_123",
      "project_id": "proj_abc123",
      "agent_id": "agent_xyz789",
      "task_id": "task_pay_001",
      "run_id": "run_abc123",
      "request_payload": {
        "amount": 100.00,
        "currency": "USD"
      },
      "signature": "0x1234567890abcdef...",
      "status": "PENDING",
      "timestamp": "2026-01-11T10:50:00Z",
      "linked_memory_ids": [],
      "linked_compliance_ids": []
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

---

### GET /v1/public/{project_id}/x402-requests/{request_id}

Get a single X402 request with linked records.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/x402-requests/x402_req_123" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "request_id": "x402_req_123",
  "project_id": "proj_abc123",
  "agent_id": "agent_xyz789",
  "task_id": "task_pay_001",
  "run_id": "run_abc123",
  "request_payload": {
    "amount": 100.00,
    "currency": "USD",
    "recipient": "merchant_456",
    "description": "Payment for services"
  },
  "signature": "0x1234567890abcdef...",
  "status": "PENDING",
  "timestamp": "2026-01-11T10:50:00Z",
  "linked_memory_ids": ["mem_def456"],
  "linked_compliance_ids": ["comp_evt_789"],
  "linked_memories": [
    {
      "memory_id": "mem_def456",
      "agent_id": "agent_xyz789",
      "content": "Approved transaction after KYC verification passed"
    }
  ],
  "linked_compliance_events": [
    {
      "event_id": "comp_evt_789",
      "event_type": "KYC_CHECK",
      "outcome": "PASS"
    }
  ]
}
```

---

## Runs API

### GET /v1/public/{project_id}/runs

List all agent runs for a project.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/runs?page=1&page_size=20" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "runs": [
    {
      "run_id": "run_abc123",
      "project_id": "proj_abc123",
      "agent_id": "agent_xyz789",
      "status": "COMPLETED",
      "started_at": "2026-01-11T10:00:00Z",
      "completed_at": "2026-01-11T10:55:00Z",
      "memory_count": 5,
      "event_count": 3,
      "request_count": 1
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### GET /v1/public/{project_id}/runs/{run_id}

Get detailed information for a specific run.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/runs/run_abc123" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "run_id": "run_abc123",
  "project_id": "proj_abc123",
  "agent_id": "agent_xyz789",
  "status": "COMPLETED",
  "agent_profile": {
    "did": "did:agent:compliance_001",
    "role": "compliance_analyst",
    "name": "Compliance Agent Alpha"
  },
  "started_at": "2026-01-11T10:00:00Z",
  "completed_at": "2026-01-11T10:55:00Z",
  "duration_ms": 3300000,
  "memory_count": 5,
  "event_count": 3,
  "request_count": 1
}
```

---

### GET /v1/public/{project_id}/runs/{run_id}/replay

Get complete replay data for deterministic agent run replay.

**Example:**
```bash
curl -X GET "$BASE_URL/v1/public/$PROJECT_ID/runs/run_abc123/replay" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "run_id": "run_abc123",
  "project_id": "proj_abc123",
  "agent_profile": {
    "did": "did:agent:compliance_001",
    "role": "compliance_analyst",
    "name": "Compliance Agent Alpha"
  },
  "agent_memory": [
    {
      "memory_id": "mem_def456",
      "content": "Approved transaction after KYC verification passed",
      "timestamp": "2026-01-11T10:05:00Z"
    }
  ],
  "compliance_events": [
    {
      "event_id": "comp_evt_789",
      "event_type": "KYC_CHECK",
      "outcome": "PASS",
      "timestamp": "2026-01-11T10:45:00Z"
    }
  ],
  "x402_requests": [
    {
      "request_id": "x402_req_123",
      "task_id": "task_pay_001",
      "status": "PENDING",
      "timestamp": "2026-01-11T10:50:00Z"
    }
  ],
  "validation": {
    "agent_profile_exists": true,
    "all_records_linked": true,
    "chronological_order": true
  }
}
```

---

## Notes

1. **All endpoints require authentication** via the `X-API-Key` header
2. **Vector operations require `/database/` prefix** per DX Contract
3. **All timestamps are in ISO 8601 format** with UTC timezone
4. **All examples use environment variables** for easy copy-paste
5. **Response field order is stable** per DX Contract guarantees

## Related Documentation

- [API Specification](./api-spec.md)
- [Quick Start Guide](../quick-reference/QUICKSTART.md)
- [Security Best Practices](./API_KEY_SECURITY.md)
- [Database Prefix Warning](./DATABASE_PREFIX_WARNING.md)
