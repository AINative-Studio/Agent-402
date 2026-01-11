# Events API Quick Start

**Endpoint:** `POST /v1/public/database/events`

**Purpose:** Post events for audit trail, compliance tracking, and workflow replay

---

## Environment Setup

```bash
# Set standard environment variables
export API_KEY="your_api_key_here"
export PROJECT_ID="proj_abc123"
export BASE_URL="http://localhost:8000"
```

## 🚀 Basic Usage

```bash
curl -X POST "$BASE_URL/v1/public/database/events" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent_decision",
    "data": {
      "agent_id": "analyst-001",
      "decision": "approve",
      "confidence": 0.95
    }
  }'
```

**Response (HTTP 201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "agent_decision",
  "data": {
    "agent_id": "analyst-001",
    "decision": "approve",
    "confidence": 0.95
  },
  "timestamp": "2025-01-11T22:30:45Z",
  "created_at": "2025-01-11T22:30:45.123456Z"
}
```

---

## 📋 Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | string | Yes | Event category (1-255 chars) |
| `data` | object | Yes | Event payload (any JSON object) |
| `timestamp` | string | No | ISO8601 timestamp (auto-generated if omitted) |

---

## 🎯 Common Event Types

### Agent Decision
```json
{
  "event_type": "agent_decision",
  "data": {
    "agent_id": "analyst-001",
    "run_id": "run-123",
    "decision": "approve_transaction",
    "confidence": 0.95,
    "reasoning": "All checks passed"
  }
}
```

### Compliance Check
```json
{
  "event_type": "compliance_check",
  "data": {
    "subject": "user-12345",
    "check_type": "kyc",
    "status": "passed",
    "risk_score": 0.15
  }
}
```

### Agent Tool Call
```json
{
  "event_type": "agent_tool_call",
  "data": {
    "agent_id": "transaction-agent",
    "tool_name": "x402.request",
    "parameters": {"action": "submit"},
    "result": "success"
  }
}
```

### X402 Request
```json
{
  "event_type": "x402_request",
  "data": {
    "did": "did:example:123",
    "signature": "0x1234abcd",
    "verified": true
  }
}
```

---

## 🔒 Authentication

**Required Header:**
```http
X-API-Key: your-api-key
```

**Error (HTTP 401):**
```json
{
  "detail": "Invalid or missing API key. Please provide a valid X-API-Key header.",
  "error_code": "INVALID_API_KEY"
}
```

---

## ⏰ Timestamp Format

**Accepted Formats:**
- `2025-01-11T22:00:00Z` (Zulu time)
- `2025-01-11T22:00:00+00:00` (with offset)
- `2025-01-11T22:00:00` (no timezone)

**Invalid Format (HTTP 422):**
```json
{
  "detail": "Invalid timestamp '2025-01-11 22:00:00'. Expected ISO8601 format (e.g., '2025-01-11T22:00:00Z' or '2025-01-11T22:00:00+00:00'). Error: Missing 'T' separator between date and time",
  "error_code": "INVALID_TIMESTAMP"
}
```

---

## ❌ Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_API_KEY` | 401 | Missing or invalid API key |
| `INVALID_TIMESTAMP` | 422 | Invalid timestamp format |
| Validation error | 422 | Missing required field or invalid type |

---

## 🔄 Workflow Replay Pattern

Use `run_id` to link events for replay:

```bash
# Step 1: Agent Decision
curl -X POST "$BASE_URL/v1/public/database/events" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent_decision",
    "data": {"run_id": "run-001", "step": 1, "decision": "start"}
  }'

# Step 2: Compliance Check
curl -X POST "$BASE_URL/v1/public/database/events" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "compliance_check",
    "data": {"run_id": "run-001", "step": 2, "status": "passed"}
  }'

# Step 3: Execution
curl -X POST "$BASE_URL/v1/public/database/events" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent_tool_call",
    "data": {"run_id": "run-001", "step": 3, "result": "success"}
  }'
```

All events with `run_id: "run-001"` can be queried for workflow replay.

---

## 🐍 Python Example

```python
import requests
import os

# Use standard environment variables
API_KEY = os.getenv('API_KEY', 'your_api_key_here')
PROJECT_ID = os.getenv('PROJECT_ID', 'proj_abc123')
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')

def post_event(event_type, data, timestamp=None):
    url = f"{BASE_URL}/v1/public/database/events"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "event_type": event_type,
        "data": data
    }

    if timestamp:
        payload["timestamp"] = timestamp

    response = requests.post(url, headers=headers, json=payload)
    return response.json()

# Usage
event = post_event(
    event_type="agent_decision",
    data={
        "agent_id": "analyst-001",
        "decision": "approve",
        "confidence": 0.95
    }
)

print(f"Event ID: {event['id']}")
```

---

## 🧪 Test Your Implementation

```bash
# Run the demo script
python3 demo_events_api.py

# Run tests
python3 -m pytest tests/test_events_api.py -v

# Start the server
uvicorn app.main:app --reload

# View API docs
open http://localhost:8000/docs
```

---

## 📚 Complete Documentation

- **Full API Spec:** `/docs/issues/ISSUE_37_IMPLEMENTATION_SUMMARY.md`
- **Tests:** `/tests/test_events_api.py`
- **Demo Script:** `/demo_events_api.py`
- **Interactive Docs:** `http://localhost:8000/docs`

---

## ⚡ Key Points

- ✅ Events are **immutable** (append-only)
- ✅ Timestamp is **optional** (auto-generated if omitted)
- ✅ Event types are **flexible** (no predefined list)
- ✅ Data can be **any valid JSON object**
- ✅ All events require **X-API-Key authentication**
- ✅ Endpoint uses **/database/ prefix** per DX Contract

---

**Need Help?**
- View examples: `http://localhost:8000/docs`
- Run demo: `python3 demo_events_api.py`
- Contact: support@ainative.studio
