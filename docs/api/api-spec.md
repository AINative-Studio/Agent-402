# ZeroDB API Specification - Projects Endpoints

**Version:** v1
**Last Updated:** 2026-01-10
**Base URL:** `https://api.ainative.studio/v1/public`

---

## ⚠️ CRITICAL SECURITY WARNING

> **NEVER use your API key in client-side code, mobile apps, or any publicly accessible environment.**

**Your API key provides full access to your ZeroDB project.** Exposing it client-side allows anyone to:
- Access all your data (vectors, tables, agent memory)
- Delete your project
- Consume your API quota
- Violate regulatory compliance (SOC 2, GDPR, PCI DSS)

**✅ Correct Pattern:**
```
[Client App] → [Your Backend] → [ZeroDB API]
     ↓             ↓                  ↓
  JWT Token   API Key (secure)   Validated
```

**❌ Dangerous Pattern:**
```javascript
// NEVER DO THIS - API key exposed in browser
const API_KEY = 'zerodb_sk_abc123';
fetch('https://api.ainative.studio/...', {
  headers: { 'X-API-Key': API_KEY }
});
```

**📚 Read [SECURITY.md](/SECURITY.md) for complete best practices, secure patterns, and implementation examples.**

---

## Projects API

### Overview

The Projects API allows developers to create and manage ZeroDB projects. Each project serves as a container for databases, embeddings, tables, and events.

---

## Project Status Lifecycle

All projects have a `status` field that indicates their current state:

| Status       | Description                                    | Transitions To        |
| ------------ | ---------------------------------------------- | --------------------- |
| `ACTIVE`     | Project is operational and accepting requests  | `SUSPENDED`, `DELETED` |
| `SUSPENDED`  | Project is temporarily disabled                | `ACTIVE`, `DELETED`    |
| `DELETED`    | Project is marked for deletion (soft delete)   | (terminal state)       |

**Default Status:** All newly created projects default to `ACTIVE`.

**Guaranteed Behavior (DX Contract):**
- The `status` field MUST be present in all project response payloads
- Newly created projects MUST have `status: "ACTIVE"`
- The status field MUST NOT be omitted, null, or empty

---

## Authentication

All API requests require authentication via the `X-API-Key` header.

### ⚠️ Server-Side Only

**API keys MUST only be used in server-side environments:**

| Environment | Safe to Use API Key? | Recommended Auth Method |
|-------------|---------------------|-------------------------|
| Backend Server (Node.js, Python, Go) | ✅ YES | X-API-Key header |
| Serverless Functions (AWS Lambda, Vercel) | ✅ YES | X-API-Key from env vars |
| CI/CD Pipelines | ✅ YES | X-API-Key from secrets |
| React/Vue/Angular Frontend | ❌ NO | Backend proxy + JWT |
| Mobile Apps (iOS/Android) | ❌ NO | Backend proxy + user tokens |
| Electron/Desktop Apps | ❌ NO | Backend proxy or OAuth |
| Browser Extensions | ❌ NO | Backend proxy + session tokens |

### Request Format

```bash
# Set environment variables first
export API_KEY="your_api_key_here"
export BASE_URL="https://api.ainative.studio"

# Make request using environment variables
curl -X GET "$BASE_URL/v1/public/projects" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json"
```

### Client-Side Applications

**For web and mobile apps, implement a backend proxy:**

```python
# ✅ Your secure backend endpoint
@app.post('/api/search')
async def search_proxy(query: str, user: User = Depends(get_current_user)):
    # Verify user authentication first
    # Then make request to ZeroDB with YOUR API key
    response = await httpx.post(
        'https://api.ainative.studio/v1/public/embeddings/search',
        headers={'X-API-Key': os.getenv('ZERODB_API_KEY')},
        json={'query': query}
    )
    return response.json()
```

```javascript
// ✅ Frontend calls YOUR backend, not ZeroDB directly
async function search(query) {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userJwtToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query })
  });
  return response.json();
}
```

**See [SECURITY.md](/SECURITY.md) for complete implementation examples.**

---

## Endpoints

### 1. Create Project

Creates a new ZeroDB project.

**Endpoint:** `POST /v1/public/projects`

**Authentication:** Required (`X-API-Key` header)

**Request Body:**

```json
{
  "name": "string (required, 1-100 chars)",
  "description": "string (optional, max 500 chars)",
  "tier": "string (optional, enum: ['free', 'starter', 'pro', 'enterprise'], default: 'free')",
  "database_enabled": "boolean (optional, default: true)"
}
```

**Success Response (201 Created):**

```json
{
  "id": "proj_abc123xyz456",
  "name": "My Fintech Agent Project",
  "description": "Agent-native fintech workflow with X402",
  "status": "ACTIVE",
  "tier": "free",
  "database_enabled": true,
  "created_at": "2026-01-10T12:00:00Z",
  "updated_at": "2026-01-10T12:00:00Z"
}
```

**Response Fields:**

| Field              | Type      | Description                                      |
| ------------------ | --------- | ------------------------------------------------ |
| `id`               | string    | Unique project identifier                        |
| `name`             | string    | Project name                                     |
| `description`      | string    | Project description (may be null)                |
| `status`           | string    | Current project status (always "ACTIVE" on create) |
| `tier`             | string    | Project tier (free, starter, pro, enterprise)    |
| `database_enabled` | boolean   | Whether database features are enabled            |
| `created_at`       | string    | ISO 8601 timestamp of creation                   |
| `updated_at`       | string    | ISO 8601 timestamp of last update                |

**Error Responses:**

```json
// 400 Bad Request - Invalid tier
{
  "detail": "Invalid tier specified. Must be one of: free, starter, pro, enterprise",
  "error_code": "INVALID_TIER"
}

// 400 Bad Request - Project limit exceeded
{
  "detail": "Project limit exceeded for your account tier. Current limit: 5 projects.",
  "error_code": "PROJECT_LIMIT_EXCEEDED"
}

// 401 Unauthorized - Invalid API key
{
  "detail": "Invalid API key",
  "error_code": "INVALID_API_KEY"
}

// 422 Unprocessable Entity - Validation error
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Example Request:**

```bash
curl -X POST "$BASE_URL/v1/public/projects" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Autonomous Fintech Agents",
    "description": "CrewAI agents with X402 protocol integration",
    "tier": "free",
    "database_enabled": true
  }'
```

---

### 2. List Projects

Retrieves all projects for the authenticated user.

**Endpoint:** `GET /v1/public/projects`

**Authentication:** Required (`X-API-Key` header)

**Query Parameters:**

| Parameter | Type    | Description                              | Default |
| --------- | ------- | ---------------------------------------- | ------- |
| `limit`   | integer | Maximum number of projects to return     | 100     |
| `offset`  | integer | Number of projects to skip (pagination)  | 0       |
| `status`  | string  | Filter by status (ACTIVE, SUSPENDED, etc) | (all)   |

**Success Response (200 OK):**

```json
{
  "items": [
    {
      "id": "proj_abc123xyz456",
      "name": "Autonomous Fintech Agents",
      "description": "CrewAI agents with X402 protocol integration",
      "status": "ACTIVE",
      "tier": "free",
      "database_enabled": true,
      "created_at": "2026-01-10T12:00:00Z",
      "updated_at": "2026-01-10T12:00:00Z"
    },
    {
      "id": "proj_def789uvw012",
      "name": "Test Project",
      "description": null,
      "status": "ACTIVE",
      "tier": "starter",
      "database_enabled": false,
      "created_at": "2026-01-09T10:30:00Z",
      "updated_at": "2026-01-09T10:30:00Z"
    }
  ],
  "total": 2,
  "limit": 100,
  "offset": 0
}
```

**Response Fields:**

| Field    | Type    | Description                                |
| -------- | ------- | ------------------------------------------ |
| `items`  | array   | Array of project objects                   |
| `total`  | integer | Total number of projects                   |
| `limit`  | integer | Limit applied to this response             |
| `offset` | integer | Offset applied to this response            |

**Each project object contains:**
- All fields from the Create Project response
- **MUST include `status` field**

**Error Responses:**

```json
// 401 Unauthorized - Invalid API key
{
  "detail": "Invalid API key",
  "error_code": "INVALID_API_KEY"
}
```

**Example Request:**

```bash
curl -X GET "$BASE_URL/v1/public/projects?limit=10&offset=0" \
  -H "X-API-Key: $API_KEY"
```

**Example Request with Status Filter:**

```bash
curl -X GET "$BASE_URL/v1/public/projects?status=ACTIVE" \
  -H "X-API-Key: $API_KEY"
```

---

### 3. Get Project Details

Retrieves details for a specific project.

**Endpoint:** `GET /v1/public/projects/{project_id}`

**Authentication:** Required (`X-API-Key` header)

**Path Parameters:**

| Parameter    | Type   | Description              |
| ------------ | ------ | ------------------------ |
| `project_id` | string | The project identifier   |

**Success Response (200 OK):**

```json
{
  "id": "proj_abc123xyz456",
  "name": "Autonomous Fintech Agents",
  "description": "CrewAI agents with X402 protocol integration",
  "status": "ACTIVE",
  "tier": "free",
  "database_enabled": true,
  "created_at": "2026-01-10T12:00:00Z",
  "updated_at": "2026-01-10T12:00:00Z",
  "usage": {
    "vectors_stored": 1250,
    "tables_created": 4,
    "events_logged": 89,
    "storage_mb": 12.5
  }
}
```

**Error Responses:**

```json
// 404 Not Found - Project does not exist
{
  "detail": "Project not found",
  "error_code": "PROJECT_NOT_FOUND"
}

// 401 Unauthorized - Invalid API key
{
  "detail": "Invalid API key",
  "error_code": "INVALID_API_KEY"
}
```

**Example Request:**

```bash
curl -X GET "$BASE_URL/v1/public/projects/$PROJECT_ID" \
  -H "X-API-Key: $API_KEY"
```

---

## Status Field Guarantees

Per the ZeroDB DX Contract and PRD Section 9:

1. **Presence:** The `status` field MUST appear in ALL project responses:
   - Create project (POST /projects)
   - List projects (GET /projects)
   - Get project details (GET /projects/{id})
   - Any future project-related endpoints

2. **Creation Default:** Newly created projects MUST have `status: "ACTIVE"`

3. **Non-null:** The status field MUST NEVER be null or undefined

4. **Type Safety:** The status value MUST be a string enum

5. **Consistency:** The same project queried multiple times MUST return the same status unless explicitly changed

---

## Testing Requirements

All implementations MUST validate:

1. Create project returns `status: "ACTIVE"`
2. List projects includes `status` for each project
3. Get project details includes `status`
4. Status field is never null, undefined, or omitted
5. Status transitions are logged and auditable

**Smoke Test Validation:**

```python
# Example validation in smoke_test.py
def test_project_status_field():
    # Create project
    response = create_project(name="Test Project")
    assert "status" in response, "status field missing from create response"
    assert response["status"] == "ACTIVE", "new project must have ACTIVE status"

    # List projects
    projects = list_projects()
    for project in projects["items"]:
        assert "status" in project, "status field missing from list response"
        assert project["status"] in ["ACTIVE", "SUSPENDED", "DELETED"]

    # Get project details
    details = get_project(project_id=response["id"])
    assert "status" in details, "status field missing from get response"
    assert details["status"] == "ACTIVE"
```

---

## Integration with Agent Workflows

When CrewAI agents or autonomous systems create projects programmatically:

1. They can rely on `status: "ACTIVE"` being present in the response
2. They should verify project status before performing operations
3. They should handle suspended projects gracefully
4. All project status changes should be logged to the events table

**Example Agent Integration:**

```python
# Agent code snippet
project = zerodb_client.create_project(
    name="Agent Workflow Project",
    description="Created by compliance_agent"
)

# Contract guarantee: status field is always present
assert project["status"] == "ACTIVE"

# Log to events table
zerodb_client.create_event({
    "event_type": "project_created",
    "data": {
        "project_id": project["id"],
        "agent_id": "compliance_agent",
        "status": project["status"]
    }
})
```

---

## Version History

| Version | Date       | Changes                                           |
| ------- | ---------- | ------------------------------------------------- |
| v1.0    | 2026-01-10 | Initial specification with status field guarantees |

---

## Related Documentation

- [ZeroDB Developer Guide](/datamodel.md)
- [Agent Lifecycle Events API](/docs/api/agent-lifecycle-events.md)
- [DX Contract](/DX-Contract.md)
- [PRD Section 5: Agent Personas](/prd.md#5-agent-personas-mvp)
- [PRD Section 9: Deliverables](/prd.md#9-system-architecture-mvp)
- [Backlog Epic 1: Public Projects API](/backlog.md#epic-1--public-projects-api-create--list)
- [Backlog Epic 8: Events API](/backlog.md#epic-8--events-api)
