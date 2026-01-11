# Append-Only Guarantee

## Overview

The Agent-402 API enforces **append-only semantics** on critical agent-related tables to ensure **non-repudiation** and **audit trail integrity**. This is a fundamental security and compliance feature required by PRD Section 10.

---

## What is Append-Only?

Append-only means that records can only be:
- **Created** (INSERT/POST)
- **Read** (SELECT/GET)

Records **cannot** be:
- **Updated** (UPDATE/PUT/PATCH)
- **Deleted** (DELETE)

This guarantees that once a record is written, it becomes an immutable part of the audit trail.

---

## Protected Tables

| Table | Purpose | Why Immutable? |
|-------|---------|----------------|
| `agents` | Agent registration and configuration | Agent identity is forensically significant |
| `agent_memory` | Agent recall and learning data | Learning history must be reproducible |
| `compliance_events` | Regulatory audit trail | Compliance events are legal records |
| `x402_requests` | X.402 payment transactions | Financial transactions require non-repudiation |

---

## API Behavior

### Allowed Operations

| HTTP Method | Purpose | Result |
|-------------|---------|--------|
| `GET` | Read records | 200 OK with data |
| `POST` | Create new records | 201 Created |

### Blocked Operations

| HTTP Method | Purpose | Result |
|-------------|---------|--------|
| `PUT` | Full record update | 403 Forbidden |
| `PATCH` | Partial record update | 403 Forbidden |
| `DELETE` | Record deletion | 403 Forbidden |

---

## Error Response

When a blocked operation is attempted, the API returns:

**HTTP Status:** `403 Forbidden`

**Response Body:**
```json
{
  "detail": "Cannot update records in 'agents' table. This table is append-only for audit trail integrity. Per PRD Section 10: Agent records are immutable for non-repudiation.",
  "error_code": "IMMUTABLE_RECORD"
}
```

### Error Code

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `IMMUTABLE_RECORD` | 403 | Attempted to modify or delete an immutable record |

---

## Response Metadata

Responses from append-only table endpoints include immutability metadata:

```json
{
  "id": "agent-123",
  "did": "did:key:z6Mk...",
  "name": "FinanceAgent",
  "metadata": {
    "immutable": true,
    "append_only": true,
    "prd_reference": "PRD Section 10 (Non-repudiation)"
  }
}
```

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `immutable` | boolean | Always `true` for protected tables |
| `append_only` | boolean | Always `true` for protected tables |
| `prd_reference` | string | Reference to PRD section |

---

## Affected Endpoints

### Agents API (`/v1/public/{project_id}/database/agents`)

| Endpoint | Method | Status |
|----------|--------|--------|
| `/agents` | GET | Allowed |
| `/agents` | POST | Allowed |
| `/agents/{agent_id}` | GET | Allowed |
| `/agents/{agent_id}` | PUT | Blocked |
| `/agents/{agent_id}` | PATCH | Blocked |
| `/agents/{agent_id}` | DELETE | Blocked |

### Agent Memory API (`/v1/public/{project_id}/database/agent_memory`)

| Endpoint | Method | Status |
|----------|--------|--------|
| `/agent_memory` | GET | Allowed |
| `/agent_memory` | POST | Allowed |
| `/agent_memory/{memory_id}` | GET | Allowed |
| `/agent_memory/{memory_id}` | PUT | Blocked |
| `/agent_memory/{memory_id}` | PATCH | Blocked |
| `/agent_memory/{memory_id}` | DELETE | Blocked |

### Compliance Events API (`/v1/public/{project_id}/database/compliance_events`)

| Endpoint | Method | Status |
|----------|--------|--------|
| `/compliance_events` | GET | Allowed |
| `/compliance_events` | POST | Allowed |
| `/compliance_events/{event_id}` | GET | Allowed |
| `/compliance_events/{event_id}` | PUT | Blocked |
| `/compliance_events/{event_id}` | PATCH | Blocked |
| `/compliance_events/{event_id}` | DELETE | Blocked |

### X402 Requests API (`/v1/public/{project_id}/database/x402_requests`)

| Endpoint | Method | Status |
|----------|--------|--------|
| `/x402_requests` | GET | Allowed |
| `/x402_requests` | POST | Allowed |
| `/x402_requests/{request_id}` | GET | Allowed |
| `/x402_requests/{request_id}` | PUT | Blocked |
| `/x402_requests/{request_id}` | PATCH | Blocked |
| `/x402_requests/{request_id}` | DELETE | Blocked |

---

## Why Append-Only?

### 1. Non-Repudiation

Per PRD Section 10, agent actions must be non-repudiable. This means:
- An agent cannot deny performing an action
- Actions are cryptographically linked to agent identity
- Audit trails cannot be tampered with

### 2. Compliance Requirements

Financial and regulatory compliance requires:
- Complete audit trails
- No data deletion
- Forensic reconstructability
- Tamper-evident records

### 3. Reproducibility

For AI agents:
- Decision-making must be reproducible
- Learning history must be preserved
- Memory states must be recoverable

### 4. Security

Append-only prevents:
- Evidence tampering
- Fraudulent record modification
- Deletion of incriminating data

---

## Workarounds for "Updates"

Since records cannot be updated, use these patterns instead:

### Pattern 1: Superseding Records

Create a new record that supersedes the old one:

```json
{
  "agent_id": "agent-123",
  "action": "update_config",
  "supersedes": "config-record-456",
  "new_config": {
    "risk_tolerance": "medium"
  }
}
```

### Pattern 2: Status Events

Add status change events instead of modifying status:

```json
{
  "agent_id": "agent-123",
  "event_type": "status_change",
  "previous_status": "active",
  "new_status": "suspended",
  "reason": "Manual suspension by admin"
}
```

### Pattern 3: Correction Records

For corrections, add a correction record:

```json
{
  "agent_id": "agent-123",
  "event_type": "correction",
  "corrects": "event-789",
  "reason": "Data entry error",
  "corrected_values": {
    "amount": 100.00
  }
}
```

---

## Implementation Details

### Middleware Layer

The `ImmutableMiddleware` intercepts all HTTP requests and blocks mutating methods (PUT, PATCH, DELETE) on protected endpoints before they reach route handlers.

### Service Layer

The `@immutable_table` decorator can be applied to service methods to enforce immutability at the business logic level.

### Database Layer

For production deployments, consider implementing:
- Database triggers to prevent UPDATE/DELETE
- Row-level security policies
- Immutable ledger tables

---

## Checking Immutability

### Programmatic Check

```python
from app.middleware import is_immutable_table

if is_immutable_table("agents"):
    print("Agents table is immutable")
```

### List All Immutable Tables

```python
from app.middleware import get_immutable_tables

tables = get_immutable_tables()
# Returns: ["agents", "agent_memory", "compliance_events", "x402_requests"]
```

---

## Best Practices

1. **Design for Append-Only**: When creating new features, assume records cannot be modified
2. **Use Events**: Model state changes as events rather than mutations
3. **Soft Deletes**: If "deletion" is needed, add a "deleted" event
4. **Version Records**: Use version numbers or timestamps for superseding
5. **Audit Everything**: Log all operations, even failed ones

---

## Related Documentation

- [PRD Section 10](/docs/prd.md#section-10) - Non-repudiation requirements
- [DX Contract Section 7](/docs/dx-contract.md#section-7) - Error semantics
- [Issue Implementation](/docs/issues/ISSUE_EPIC12_6_APPEND_ONLY.md) - Technical details

---

Built by AINative Dev Team
