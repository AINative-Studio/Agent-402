# Epic 12 Issue 2: Agent Memory Persistence

## Overview

This document describes the implementation of agent memory persistence for the Agent-402 project. The feature allows agents to persist their decisions, context, and state to a memory store that can be queried and retrieved later.

## PRD Reference

- **Section 6**: ZeroDB Integration
- **Epic 12**: Agent Observability and Compliance

## Requirements Implemented

1. **POST /v1/public/{project_id}/agent-memory** - Store agent decisions/memory
2. **GET /v1/public/{project_id}/agent-memory** - List memories with filters
3. **GET /v1/public/{project_id}/agent-memory/{memory_id}** - Get single memory entry
4. Namespace scoping for multi-agent isolation
5. Memory schema with required fields

## File Locations

| Component | File Path |
|-----------|-----------|
| API Endpoints | `backend/app/api/agent_memory.py` |
| Schemas | `backend/app/schemas/agent_memory.py` |
| Service | `backend/app/services/agent_memory_service.py` |
| Router Registration | `backend/app/main.py` |

## Memory Schema

The agent memory schema includes the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | string | Yes | Unique identifier for the agent |
| `run_id` | string | Yes | Identifier for the agent's execution run |
| `memory_type` | enum | Yes | Type of memory (decision, context, state, etc.) |
| `content` | string | Yes | The actual memory content |
| `metadata` | object | No | Optional metadata for classification |
| `namespace` | string | No | Namespace for multi-agent isolation (default: "default") |

### Memory Types

The following memory types are supported:

- `decision` - Agent decisions and choices
- `context` - Contextual information for agent reasoning
- `state` - Agent state snapshots
- `observation` - Observations from the environment
- `goal` - Agent goals and objectives
- `plan` - Planned actions and strategies
- `result` - Results of agent actions
- `error` - Error conditions and recovery

## API Endpoints

### POST /v1/public/{project_id}/agent-memory

Creates a new agent memory entry.

**Request Body:**
```json
{
  "agent_id": "compliance_agent_001",
  "run_id": "run_20260110_123456",
  "memory_type": "decision",
  "content": "Decided to approve transaction TX-12345 based on compliance rules",
  "metadata": {
    "transaction_id": "TX-12345",
    "decision_type": "approval",
    "confidence": 0.95
  },
  "namespace": "compliance_team"
}
```

**Response (201 Created):**
```json
{
  "memory_id": "mem_abc123def456",
  "agent_id": "compliance_agent_001",
  "run_id": "run_20260110_123456",
  "memory_type": "decision",
  "namespace": "compliance_team",
  "timestamp": "2026-01-10T12:34:56.789Z",
  "created": true
}
```

### GET /v1/public/{project_id}/agent-memory

Lists agent memory entries with optional filtering.

**Query Parameters:**
- `agent_id` (optional) - Filter by agent ID
- `run_id` (optional) - Filter by run ID
- `memory_type` (optional) - Filter by memory type
- `namespace` (optional) - Filter by namespace
- `limit` (optional) - Maximum results (default: 100, max: 1000)
- `offset` (optional) - Pagination offset (default: 0)

**Response (200 OK):**
```json
{
  "memories": [
    {
      "memory_id": "mem_abc123def456",
      "agent_id": "compliance_agent_001",
      "run_id": "run_20260110_123456",
      "memory_type": "decision",
      "content": "Decided to approve transaction TX-12345",
      "metadata": {"transaction_id": "TX-12345"},
      "namespace": "compliance_team",
      "timestamp": "2026-01-10T12:34:56.789Z",
      "project_id": "proj_xyz789"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0,
  "filters_applied": {
    "agent_id": "compliance_agent_001"
  }
}
```

### GET /v1/public/{project_id}/agent-memory/{memory_id}

Retrieves a single agent memory entry by ID.

**Response (200 OK):**
```json
{
  "memory_id": "mem_abc123def456",
  "agent_id": "compliance_agent_001",
  "run_id": "run_20260110_123456",
  "memory_type": "decision",
  "content": "Decided to approve transaction TX-12345 based on compliance rules",
  "metadata": {
    "transaction_id": "TX-12345",
    "decision_type": "approval",
    "confidence": 0.95
  },
  "namespace": "compliance_team",
  "timestamp": "2026-01-10T12:34:56.789Z",
  "project_id": "proj_xyz789"
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Agent memory not found: mem_abc123def456",
  "error_code": "MEMORY_NOT_FOUND"
}
```

## Namespace Isolation

Namespaces provide logical isolation for multi-agent systems:

- Each namespace is independent within a project
- Agents in different namespaces cannot access each other's memories
- Default namespace is "default" if not specified
- Namespace can be filtered in list operations

## Authentication

All endpoints require X-API-Key authentication as per DX Contract Section 2.

## Error Handling

The API follows the DX Contract Section 7 error format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_API_KEY` | 401 | Missing or invalid API key |
| `MEMORY_NOT_FOUND` | 404 | Memory entry does not exist |
| `VALIDATION_ERROR` | 422 | Request validation failed |

## Implementation Notes

### Service Layer

The `AgentMemoryService` class provides:

1. Memory ID generation with `mem_` prefix
2. In-memory storage for MVP (ZeroDB integration planned)
3. Filtering and pagination support
4. Namespace-scoped storage

### Storage Structure

MVP uses in-memory storage with the following structure:
```
project_id -> namespace -> memory_id -> memory_data
```

Production will integrate with ZeroDB MCP tools for persistent storage.

## Future Enhancements

1. ZeroDB MCP integration for persistent storage
2. Semantic search across memories
3. Memory retention policies
4. Memory encryption for sensitive data
5. Cross-project memory sharing

---

Built by AINative Dev Team
