# Agent Lifecycle Events API Specification

**Version:** v1
**Last Updated:** 2026-01-11
**GitHub Issue:** #41
**Epic:** Epic 8 Story 5

---

## Overview

The Agent Lifecycle Events API enables agent systems to emit and track lifecycle events for autonomous operations. This supports audit trails, debugging, and workflow replay capabilities as specified in PRD §5 (Agent Personas), §6 (Audit Trail), and §10 (Replayability).

**Base Endpoint:** `POST /v1/public/{project_id}/database/events`

---

## Agent Event Types

The following agent lifecycle event types are supported:

| Event Type | Description | Use Case |
|------------|-------------|----------|
| `agent_decision` | Agent makes a decision with reasoning | Compliance approvals, risk assessments |
| `agent_tool_call` | Agent invokes a tool or external API | X402 requests, database queries |
| `agent_error` | Agent encounters an error | Error tracking, debugging |
| `agent_start` | Agent begins a task | Task initialization, workflow tracking |
| `agent_complete` | Agent completes a task | Task finalization, duration metrics |

---

## Authentication

All event creation requests require authentication via `X-API-Key` header.

```bash
X-API-Key: your_api_key_here
```

**Security Note:** API keys must only be used in server-side code. See [SECURITY.md](/SECURITY.md) for client-side patterns.

---

## Event Schema Reference

### 1. agent_decision

**Purpose:** Record agent decisions with reasoning and context.

**Data Schema:**
```json
{
  "agent_id": "string (required)",
  "decision": "string (required)",
  "reasoning": "string (required)",
  "context": "object (optional)"
}
```

**Example Request:**
```bash
curl -X POST "https://api.ainative.studio/v1/public/{project_id}/database/events" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent_decision",
    "data": {
      "agent_id": "compliance_agent",
      "decision": "approve_transaction",
      "reasoning": "Risk score 0.15 is below threshold 0.5, all KYC checks passed",
      "context": {
        "risk_score": 0.15,
        "kyc_status": "verified",
        "transaction_amount": 1000.00,
        "customer_id": "cust_123456"
      }
    },
    "timestamp": "2026-01-11T10:30:00Z",
    "correlation_id": "task_abc123"
  }'
```

**Example Response (201 Created):**
```json
{
  "id": "evt_1234567890abcdef",
  "event_type": "agent_decision",
  "data": {
    "agent_id": "compliance_agent",
    "decision": "approve_transaction",
    "reasoning": "Risk score 0.15 is below threshold 0.5, all KYC checks passed",
    "context": {
      "risk_score": 0.15,
      "kyc_status": "verified",
      "transaction_amount": 1000.00,
      "customer_id": "cust_123456"
    }
  },
  "timestamp": "2026-01-11T10:30:00.000Z",
  "created_at": "2026-01-11T10:30:01.234Z"
}
```

**Use Cases:**
- Compliance approvals in fintech workflows
- Risk assessment decisions
- Agent-driven trade executions
- Automated underwriting decisions

---

### 2. agent_tool_call

**Purpose:** Track tool invocations by agents for audit and debugging.

**Data Schema:**
```json
{
  "agent_id": "string (required)",
  "tool_name": "string (required)",
  "parameters": "object (required)",
  "result": "object (optional)"
}
```

**Example Request:**
```bash
curl -X POST "https://api.ainative.studio/v1/public/{project_id}/database/events" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent_tool_call",
    "data": {
      "agent_id": "transaction_agent",
      "tool_name": "x402.request",
      "parameters": {
        "endpoint": "/x402",
        "method": "POST",
        "payload": {
          "did": "did:ethr:0xabc123",
          "amount": 500.00
        }
      },
      "result": {
        "status": "success",
        "transaction_id": "txn_xyz789",
        "verification": "signature_valid"
      }
    },
    "correlation_id": "task_abc123"
  }'
```

**Example Response (201 Created):**
```json
{
  "id": "evt_2345678901bcdefg",
  "event_type": "agent_tool_call",
  "data": {
    "agent_id": "transaction_agent",
    "tool_name": "x402.request",
    "parameters": {
      "endpoint": "/x402",
      "method": "POST",
      "payload": {
        "did": "did:ethr:0xabc123",
        "amount": 500.00
      }
    },
    "result": {
      "status": "success",
      "transaction_id": "txn_xyz789",
      "verification": "signature_valid"
    }
  },
  "timestamp": "2026-01-11T10:30:02.000Z",
  "created_at": "2026-01-11T10:30:02.567Z"
}
```

**Use Cases:**
- X402 protocol request tracking
- Database query logging
- External API call monitoring
- Tool usage analytics

---

### 3. agent_error

**Purpose:** Log errors encountered during agent execution for debugging.

**Data Schema:**
```json
{
  "agent_id": "string (required)",
  "error_type": "string (required)",
  "error_message": "string (required)",
  "context": "object (optional)"
}
```

**Example Request:**
```bash
curl -X POST "https://api.ainative.studio/v1/public/{project_id}/database/events" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent_error",
    "data": {
      "agent_id": "analyst_agent",
      "error_type": "API_TIMEOUT",
      "error_message": "Market data API request timed out after 30 seconds",
      "context": {
        "endpoint": "/market/quotes",
        "symbols": ["BTC-USD", "ETH-USD"],
        "timeout_ms": 30000,
        "retry_attempt": 3
      }
    },
    "correlation_id": "task_abc123"
  }'
```

**Example Response (201 Created):**
```json
{
  "id": "evt_3456789012cdefgh",
  "event_type": "agent_error",
  "data": {
    "agent_id": "analyst_agent",
    "error_type": "API_TIMEOUT",
    "error_message": "Market data API request timed out after 30 seconds",
    "context": {
      "endpoint": "/market/quotes",
      "symbols": ["BTC-USD", "ETH-USD"],
      "timeout_ms": 30000,
      "retry_attempt": 3
    }
  },
  "timestamp": "2026-01-11T10:30:15.000Z",
  "created_at": "2026-01-11T10:30:15.123Z"
}
```

**Common Error Types:**
- `API_TIMEOUT`: External API timeout
- `SIGNATURE_VERIFICATION_FAILED`: DID signature invalid
- `INSUFFICIENT_FUNDS`: Wallet balance too low
- `RATE_LIMIT_EXCEEDED`: API rate limit hit
- `DATA_VALIDATION_ERROR`: Invalid data format

**Use Cases:**
- Error tracking and monitoring
- Debugging agent failures
- Retry logic analysis
- System health monitoring

---

### 4. agent_start

**Purpose:** Record agent task initialization with configuration.

**Data Schema:**
```json
{
  "agent_id": "string (required)",
  "task": "string (required)",
  "config": "object (optional)"
}
```

**Example Request:**
```bash
curl -X POST "https://api.ainative.studio/v1/public/{project_id}/database/events" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent_start",
    "data": {
      "agent_id": "compliance_agent",
      "task": "kyc_verification",
      "config": {
        "verification_level": "enhanced",
        "document_types": ["passport", "utility_bill"],
        "sanctions_screening": true,
        "aml_checks": true
      }
    },
    "correlation_id": "task_def456"
  }'
```

**Example Response (201 Created):**
```json
{
  "id": "evt_4567890123defghi",
  "event_type": "agent_start",
  "data": {
    "agent_id": "compliance_agent",
    "task": "kyc_verification",
    "config": {
      "verification_level": "enhanced",
      "document_types": ["passport", "utility_bill"],
      "sanctions_screening": true,
      "aml_checks": true
    }
  },
  "timestamp": "2026-01-11T10:29:00.000Z",
  "created_at": "2026-01-11T10:29:00.100Z"
}
```

**Use Cases:**
- Task initialization tracking
- Configuration audit trail
- Workflow start markers
- Duration calculation (paired with agent_complete)

---

### 5. agent_complete

**Purpose:** Record agent task completion with results and duration.

**Data Schema:**
```json
{
  "agent_id": "string (required)",
  "result": "object (required)",
  "duration_ms": "integer (required, >= 0)"
}
```

**Example Request:**
```bash
curl -X POST "https://api.ainative.studio/v1/public/{project_id}/database/events" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent_complete",
    "data": {
      "agent_id": "compliance_agent",
      "result": {
        "status": "completed",
        "checks_performed": 5,
        "checks_passed": 5,
        "checks_failed": 0,
        "final_decision": "approved",
        "risk_score": 0.12
      },
      "duration_ms": 2340
    },
    "correlation_id": "task_def456"
  }'
```

**Example Response (201 Created):**
```json
{
  "id": "evt_5678901234efghij",
  "event_type": "agent_complete",
  "data": {
    "agent_id": "compliance_agent",
    "result": {
      "status": "completed",
      "checks_performed": 5,
      "checks_passed": 5,
      "checks_failed": 0,
      "final_decision": "approved",
      "risk_score": 0.12
    },
    "duration_ms": 2340
  },
  "timestamp": "2026-01-11T10:29:02.340Z",
  "created_at": "2026-01-11T10:29:02.450Z"
}
```

**Use Cases:**
- Task completion tracking
- Performance metrics (duration)
- Success/failure analysis
- Workflow end markers

---

## Correlation and Tracking

### correlation_id

Use `correlation_id` to link related events across an agent workflow:

```json
{
  "correlation_id": "task_abc123"
}
```

**Example Workflow:**
1. `agent_start` with `correlation_id: "task_abc123"`
2. `agent_tool_call` with `correlation_id: "task_abc123"`
3. `agent_decision` with `correlation_id: "task_abc123"`
4. `agent_complete` with `correlation_id: "task_abc123"`

This enables:
- Workflow replay
- End-to-end tracing
- Performance analysis
- Debugging related events

### source Field

Optional `source` field identifies the event generator:

```json
{
  "source": "crewai"
}
```

**Common Sources:**
- `crewai`: CrewAI agent system
- `agent_system`: Generic agent system
- `manual`: Manual event creation
- `webhook`: Webhook-triggered event

---

## Response Format Guarantee

**Per DX Contract and Issue #40:**

All successful event creation returns this stable format:

```json
{
  "id": "evt_...",
  "event_type": "...",
  "data": {...},
  "timestamp": "2026-01-11T10:30:00.000Z",
  "created_at": "2026-01-11T10:30:01.234Z"
}
```

**Guarantees:**
- Fields always in same order
- HTTP 201 (Created) status
- Normalized ISO8601 timestamps with milliseconds
- `id` always present and unique
- `data` echoed from request
- `created_at` server-generated

---

## Error Responses

**400 Bad Request - Invalid Timestamp:**
```json
{
  "detail": "timestamp must be in ISO8601 format (e.g., '2026-01-10T18:30:00Z')",
  "error_code": "INVALID_TIMESTAMP"
}
```

**401 Unauthorized - Invalid API Key:**
```json
{
  "detail": "Invalid or missing API key",
  "error_code": "INVALID_API_KEY"
}
```

**422 Unprocessable Entity - Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "data", "agent_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Integration Examples

### CrewAI Integration

```python
from crewai import Agent, Task
import requests
import os

class ComplianceAgent(Agent):
    def __init__(self):
        super().__init__(
            role="Compliance Officer",
            goal="Verify KYC and compliance requirements"
        )
        self.api_key = os.getenv("ZERODB_API_KEY")
        self.project_id = os.getenv("ZERODB_PROJECT_ID")
        self.base_url = "https://api.ainative.studio"

    async def log_decision(self, decision, reasoning, context, correlation_id):
        """Log agent decision to ZeroDB."""
        response = requests.post(
            f"{self.base_url}/v1/public/{self.project_id}/database/events",
            headers={"X-API-Key": self.api_key},
            json={
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "compliance_agent",
                    "decision": decision,
                    "reasoning": reasoning,
                    "context": context
                },
                "source": "crewai",
                "correlation_id": correlation_id
            }
        )
        return response.json()

    async def execute_task(self, task_data, correlation_id):
        # Log task start
        await self.log_event("agent_start", {
            "agent_id": "compliance_agent",
            "task": "kyc_verification",
            "config": {"level": "enhanced"}
        }, correlation_id)

        # Perform compliance checks
        result = self.perform_kyc_verification(task_data)

        # Log decision
        await self.log_decision(
            decision="approve" if result["passed"] else "reject",
            reasoning=result["reasoning"],
            context=result["details"],
            correlation_id=correlation_id
        )

        return result
```

### X402 Protocol Integration

```python
async def execute_x402_request(agent_id, did, payload, correlation_id):
    """Execute X402 request and log tool call."""

    # Log tool call start
    await log_event({
        "event_type": "agent_tool_call",
        "data": {
            "agent_id": agent_id,
            "tool_name": "x402.request",
            "parameters": {
                "endpoint": "/x402",
                "did": did,
                "payload": payload
            }
        },
        "correlation_id": correlation_id
    })

    # Execute X402 request
    try:
        result = await x402_client.request(did, payload)

        # Log successful result
        await log_event({
            "event_type": "agent_tool_call",
            "data": {
                "agent_id": agent_id,
                "tool_name": "x402.request",
                "parameters": {"endpoint": "/x402"},
                "result": result
            },
            "correlation_id": correlation_id
        })

        return result

    except Exception as e:
        # Log error
        await log_event({
            "event_type": "agent_error",
            "data": {
                "agent_id": agent_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "context": {"tool": "x402.request"}
            },
            "correlation_id": correlation_id
        })
        raise
```

---

## Best Practices

### 1. Always Use Correlation IDs
Link related events for workflow tracking:
```python
correlation_id = f"task_{uuid.uuid4().hex[:8]}"
```

### 2. Include Meaningful Context
Add context that aids debugging and audit:
```json
{
  "context": {
    "customer_id": "cust_123",
    "transaction_amount": 1000.00,
    "timestamp": "2026-01-11T10:30:00Z"
  }
}
```

### 3. Log Errors Immediately
Don't wait to batch - log errors when they happen:
```python
try:
    result = await risky_operation()
except Exception as e:
    await log_agent_error(agent_id, e)
    raise
```

### 4. Measure Duration Accurately
Use start/complete pairs:
```python
start_time = time.time()
await log_agent_start(agent_id, task_name)
result = await execute_task()
duration_ms = int((time.time() - start_time) * 1000)
await log_agent_complete(agent_id, result, duration_ms)
```

### 5. Normalize Timestamps
Use consistent timestamp format:
```python
from datetime import datetime, timezone

timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
```

---

## PRD Alignment

| PRD Section | Requirement | Implementation |
|-------------|-------------|----------------|
| §5 Agent Personas | Agent lifecycle tracking | 5 event types for full lifecycle |
| §6 Audit Trail | Persistent event logging | All events stored in ZeroDB |
| §10 Replayability | Immutable event stream | Events never modified, correlation IDs enable replay |
| §10 Explainability | Decision reasoning | `agent_decision` includes reasoning field |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-11 | Initial specification (Issue #41) |

---

## Related Documentation

- [Events API Specification](/docs/api/api-spec.md#events)
- [PRD Section 5: Agent Personas](/prd.md#5-agent-personas-mvp)
- [PRD Section 6: ZeroDB Integration](/prd.md#7-zerodb-integration-core-mvp-upgrade)
- [Security Best Practices](/SECURITY.md)
- [DX Contract](/DX-Contract.md)
