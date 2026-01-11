# Epic 12, Issue 1: Agent Profiles API

## Summary

Implemented API endpoints for CrewAI agent profile management as specified in PRD Section 5 (Agent Personas). This feature enables creating, listing, and retrieving agent profiles within projects.

## Implementation Details

### Files Created

| File | Purpose |
|------|---------|
| `backend/app/models/agent.py` | Agent domain model with `AgentScope` enum |
| `backend/app/schemas/agents.py` | Pydantic schemas for request/response validation |
| `backend/app/services/agent_store.py` | In-memory data store with demo agents |
| `backend/app/services/agent_service.py` | Business logic layer for agent operations |
| `backend/app/api/agents.py` | FastAPI router with API endpoints |

### Files Modified

| File | Change |
|------|--------|
| `backend/app/main.py` | Registered agents router |
| `backend/app/core/errors.py` | Added `AgentNotFoundError` and `DuplicateAgentDIDError` |

## API Endpoints

### POST /v1/public/{project_id}/agents

Create a new agent profile within a project.

**Request Body:**
```json
{
  "did": "did:web:agent.example.com:researcher-01",
  "role": "researcher",
  "name": "Research Agent Alpha",
  "description": "Specialized agent for financial research",
  "scope": "PROJECT"
}
```

**Response (201 Created):**
```json
{
  "id": "agent_abc123xyz",
  "did": "did:web:agent.example.com:researcher-01",
  "role": "researcher",
  "name": "Research Agent Alpha",
  "description": "Specialized agent for financial research",
  "scope": "PROJECT",
  "project_id": "proj_demo_u1_001",
  "created_at": "2025-01-10T00:00:00Z",
  "updated_at": "2025-01-10T00:00:00Z"
}
```

### GET /v1/public/{project_id}/agents

List all agents in a project.

**Response (200 OK):**
```json
{
  "agents": [
    {
      "id": "agent_demo_001",
      "did": "did:web:ainative.dev:agents:researcher-alpha",
      "role": "researcher",
      "name": "Research Agent Alpha",
      "description": "Specialized agent for financial research",
      "scope": "PROJECT",
      "project_id": "proj_demo_u1_001",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

### GET /v1/public/{project_id}/agents/{agent_id}

Get a single agent by ID.

**Response (200 OK):**
```json
{
  "id": "agent_demo_001",
  "did": "did:web:ainative.dev:agents:researcher-alpha",
  "role": "researcher",
  "name": "Research Agent Alpha",
  "description": "Specialized agent for financial research",
  "scope": "PROJECT",
  "project_id": "proj_demo_u1_001",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

## Agent Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Auto | Unique agent identifier |
| `did` | string | Yes | Decentralized Identifier |
| `role` | string | Yes | Agent role (e.g., researcher, analyst) |
| `name` | string | Yes | Human-readable agent name |
| `description` | string | No | Agent description and purpose |
| `scope` | enum | No | Operational scope (PROJECT, GLOBAL, RESTRICTED) |
| `project_id` | string | Auto | Project this agent belongs to |
| `created_at` | datetime | Auto | Timestamp of creation |
| `updated_at` | datetime | Auto | Timestamp of last update |

## Error Responses

| Status | Error Code | Description |
|--------|------------|-------------|
| 401 | INVALID_API_KEY | Invalid or missing API key |
| 403 | UNAUTHORIZED | Not authorized to access project |
| 404 | PROJECT_NOT_FOUND | Project does not exist |
| 404 | AGENT_NOT_FOUND | Agent does not exist |
| 409 | DUPLICATE_AGENT_DID | Agent with DID already exists in project |

## Demo Data

The implementation includes predefined demo agents for testing:

| Agent ID | DID | Role | Project |
|----------|-----|------|---------|
| agent_demo_001 | did:web:ainative.dev:agents:researcher-alpha | researcher | proj_demo_u1_001 |
| agent_demo_002 | did:web:ainative.dev:agents:analyst-beta | analyst | proj_demo_u1_001 |
| agent_demo_003 | did:web:ainative.dev:agents:executor-gamma | executor | proj_demo_u1_002 |
| agent_demo_004 | did:web:ainative.dev:agents:orchestrator-delta | orchestrator | proj_demo_u2_001 |
| agent_demo_005 | did:web:ainative.dev:agents:compliance-epsilon | compliance | proj_demo_u2_002 |

## Acceptance Criteria

- [x] POST /v1/public/{project_id}/agents creates agent profiles
- [x] Agent schema includes: did, role, name, description, scope, created_at
- [x] GET /v1/public/{project_id}/agents lists agents
- [x] GET /v1/public/{project_id}/agents/{agent_id} gets a single agent
- [x] Service layer follows existing patterns
- [x] API endpoints follow existing code patterns
- [x] Schemas follow existing patterns
- [x] Router registered in main.py

## PRD References

- PRD Section 5: Agent Personas
- PRD Section 9: Demo setup with deterministic data
- DX Contract Section 7: Error semantics

---

Built by AINative Dev Team
