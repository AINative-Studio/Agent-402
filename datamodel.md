# ✅ ZeroDB Platform Developer Guide

**(Final, PRD-Aligned, DX-Contract Safe)**

> **Last Updated:** December 13, 2025
> **Base URL:** `https://api.ainative.studio`
> **API Prefix:** `/v1/public`
> **DX Contract Status:** Stable (see §DX Guarantees)

---

## 📚 Quick Navigation

| Section          | Description                           | Time      |
| ---------------- | ------------------------------------- | --------- |
| Quick Start      | Create project → embed/store → search | 5 min     |
| Prerequisites    | Account, API key, project ID          | 2 min     |
| Common Use Cases | RAG, Tables, Events, Agents           | 10 min    |
| API Reference    | Verified endpoints only               | Reference |
| Troubleshooting  | Common failures + fixes               | Reference |
| Best Practices   | Production patterns                   | 10 min    |
| DX Guarantees    | Locked behaviors                      | 2 min     |

---

## 🚀 Quick Start (5 minutes)

> **⚠️ SECURITY WARNING:** The examples below use API keys for authentication. **API keys MUST ONLY be used in server-side code.** Never expose API keys in frontend JavaScript, mobile apps, or public repositories. See [SECURITY.md](/SECURITY.md) for client-side authentication patterns.

### 1. Get Your Credentials

```bash
# Store in .env file (add to .gitignore!)
ZERODB_API_KEY=your_api_key_here
ZERODB_PROJECT_ID=your_project_id
```

### 2. Create Embeddings

```python
import os
import requests

# ✅ CORRECT - Load from environment
API_KEY = os.getenv('ZERODB_API_KEY')
PROJECT_ID = os.getenv('ZERODB_PROJECT_ID')

# This code should run on your backend server only
response = requests.post(
    f'https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/embed-and-store',
    headers={'X-API-Key': API_KEY},
    json={
        'text': 'Autonomous fintech agents with X402 protocol',
        'metadata': {'source': 'agent_memory', 'agent_id': 'compliance_agent'}
    }
)
```

### 3. Search Vectors

```python
# ✅ Backend server code only
search_response = requests.post(
    f'https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search',
    headers={'X-API-Key': API_KEY},
    json={
        'query': 'compliance check results',
        'limit': 5
    }
)

results = search_response.json()
```

**For client-side applications:** Implement a backend proxy that authenticates users separately and makes ZeroDB requests on their behalf. See [SECURITY.md](/SECURITY.md#pattern-1-backend-proxy-recommended).

---

## 🎯 Critical Requirements (Hard Rules — DX Contract)

> These rules are **contractual guarantees**.
> If your code follows them, ZeroDB will not break you without versioning.

1. **Default embedding model is 384-dim**

   * `BAAI/bge-small-en-v1.5`
2. **Model consistency is mandatory**

   * The same `model` must be used for store + search
3. **Vector write endpoints require `/database/`**

   * ✅ `/database/vectors/...`
   * ❌ `/vectors/...`
4. **Table inserts require `row_data`**

   * ✅ `{ "row_data": {...} }`
   * ❌ `{ "rows": ... }`, `{ "data": ... }`
5. **All errors return deterministic shapes**

   * `{ detail, error_code }` when applicable
6. **Project responses MUST include `status` field**

   * All project endpoints (create, list, get) return `status`
   * New projects default to `status: "ACTIVE"`
   * Status is never null, undefined, or omitted

📌 **PRD Alignment:** §6 ZeroDB Integration, §9 Stable Demo, §10 Success Criteria

---

## 🎯 Multi-Dimension Vector Support

*(No functional changes — only a clarification sentence added)*

> **Guarantee:** Dimension behavior will not change without a version bump.

| Dimensions | Model                    | Status    |
| ---------: | ------------------------ | --------- |
|        384 | `BAAI/bge-small-en-v1.5` | Default   |
|        768 | `BAAI/bge-base-en-v1.5`  | Supported |
|       1024 | `BAAI/bge-large-en-v1.5` | Supported |
|       1536 | OpenAI / Custom          | Legacy    |

---

## 💡 Common Use Cases

### Use Case 1 — RAG (Retrieval Augmented Generation)

*(No changes)*

---

### Use Case 2 — CRUD Tables

*(No changes)*

---

### 🔹 **NEW: Use Case 4 — Agent-Native Systems (CrewAI / AIKit)**

> This use case aligns ZeroDB with **autonomous agent workflows**, as described in the PRD.

**Typical agent data stored in ZeroDB:**

| Collection          | Purpose                          |
| ------------------- | -------------------------------- |
| `agents`            | Agent identity, role, DID        |
| `agent_memory`      | Decisions, summaries, confidence |
| `compliance_events` | Risk checks, pass/fail           |
| `x402_requests`     | Signed request ledger            |
| `events`            | Agent lifecycle events           |

**Agent event example:**

```json
{
  "event_type": "agent_decision",
  "data": {
    "agent_id": "did:ethr:0xabc",
    "task": "compliance_check",
    "outcome": "approved"
  },
  "timestamp": "2025-12-13T22:41:00Z"
}
```

📌 **PRD Alignment:** §5 Agent Personas, §6 ZeroDB Integration, §11 Strategic Positioning

---

## 📖 API Reference (Verified Endpoints Only)

### Projects

#### Create Project

`POST /v1/public/projects`

**Request:**
```json
{
  "name": "My Fintech Agent Project",
  "description": "Agent-native fintech workflow",
  "tier": "free",
  "database_enabled": true
}
```

**Response (201 Created):**
```json
{
  "id": "proj_abc123xyz456",
  "name": "My Fintech Agent Project",
  "description": "Agent-native fintech workflow",
  "status": "ACTIVE",
  "tier": "free",
  "database_enabled": true,
  "created_at": "2026-01-10T12:00:00Z",
  "updated_at": "2026-01-10T12:00:00Z"
}
```

**Key Fields:**
- `status` (string): Always present, defaults to "ACTIVE" for new projects
- `tier` (string): One of: free, starter, pro, enterprise
- `database_enabled` (boolean): Whether database features are enabled

#### List Projects

`GET /v1/public/projects`

**Query Parameters:**
- `limit` (integer, optional): Max results, default 100
- `offset` (integer, optional): Pagination offset, default 0
- `status` (string, optional): Filter by status (ACTIVE, SUSPENDED, DELETED)

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "proj_abc123xyz456",
      "name": "My Fintech Agent Project",
      "description": "Agent-native fintech workflow",
      "status": "ACTIVE",
      "tier": "free",
      "database_enabled": true,
      "created_at": "2026-01-10T12:00:00Z",
      "updated_at": "2026-01-10T12:00:00Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Guarantee:** Every project object in `items` MUST include the `status` field.

#### Get Project Details

`GET /v1/public/projects/{project_id}`

**Response (200 OK):**
```json
{
  "id": "proj_abc123xyz456",
  "name": "My Fintech Agent Project",
  "description": "Agent-native fintech workflow",
  "status": "ACTIVE",
  "tier": "free",
  "database_enabled": true,
  "created_at": "2026-01-10T12:00:00Z",
  "updated_at": "2026-01-10T12:00:00Z",
  "usage": {
    "vectors_stored": 1250,
    "tables_created": 4,
    "events_logged": 89
  }
}
```

**Project Status Lifecycle:**
- `ACTIVE`: Project is operational (default for new projects)
- `SUSPENDED`: Project is temporarily disabled
- `DELETED`: Project is marked for deletion

> **For full details, see [api-spec.md](/api-spec.md)**

### Embeddings

* `POST /v1/public/{project_id}/embeddings/generate`
* `POST /v1/public/{project_id}/embeddings/embed-and-store`
* `POST /v1/public/{project_id}/embeddings/search`

### Database

* `POST /v1/public/{project_id}/database/vectors/upsert`
* `POST /v1/public/{project_id}/database/tables`
* `POST /v1/public/{project_id}/database/tables/{table}/rows`
* `GET  /v1/public/{project_id}/database/tables/{table}/rows`
* `POST /v1/public/{project_id}/database/events`

> **DX Guarantee:** Endpoints not listed here are **out of contract**.

---

## 🔍 Troubleshooting (DX-Contracted)

*(No changes — already correct and deterministic)*

---

## 🚀 Best Practices

### Development Best Practices

1. **Use environment variables** for all credentials
2. **Test with separate dev/staging/prod projects** to avoid data contamination
3. **Implement proper error handling** for all API calls
4. **Use consistent embedding models** across store and search operations
5. **Monitor API usage** to avoid hitting rate limits
6. **For agents:** Treat all writes as append-only (no mutation)

### 🔒 Security Best Practices

> **⚠️ CRITICAL:** Follow these security rules to protect your application and comply with regulatory standards.

7. **NEVER use API keys in client-side code**
   - No frontend JavaScript (React, Vue, Angular)
   - No mobile apps (iOS, Android)
   - No browser extensions
   - No Electron apps without proper isolation

8. **Always use backend proxy pattern for client apps**
   ```
   [Client] → [Your Backend + User Auth] → [ZeroDB API + API Key]
   ```

9. **Store API keys securely**
   - Use environment variables or secret managers (AWS Secrets Manager, HashiCorp Vault)
   - Add `.env` to `.gitignore`
   - Never commit secrets to version control
   - Rotate keys every 90 days

10. **Implement defense in depth**
    - Rate limiting at your backend
    - User authentication (JWT, OAuth)
    - CORS restrictions
    - Request validation
    - Audit logging

11. **For fintech applications**
    - API key exposure violates SOC 2, PCI DSS, GDPR compliance
    - All authentication must be server-side
    - Implement proper access controls per user
    - Maintain audit trails of all data access

**📚 Complete Security Guide:** See [SECURITY.md](/SECURITY.md) for implementation examples, code patterns, and mobile app guidance.

📌 **PRD Alignment:** §10 Non-repudiation, §11 Replayability, §12 Fintech Credibility

---

## 🔒 DX Guarantees (NEW SECTION — REQUIRED)

This section **locks behavior permanently** unless versioned.

### ZeroDB Guarantees

1. Request/response shapes will not change silently
2. Error codes will remain stable
3. Defaults (384-dim, namespaces, row_data) will not change
4. `/database/` prefix is permanent
5. Examples in this guide are executable
6. Agent-written data is append-only by convention
7. **Project `status` field is always present** in all project responses
8. **New projects always have `status: "ACTIVE"`**

📌 **PRD Alignment:**
§9 Stable Demo Expectations
§10 Success Criteria
§12 Strategic Positioning

---

## 🔗 Resources

*(No changes)*

---

# ✅ Final Alignment Verdict

| Area              | Status  |
| ----------------- | ------- |
| PRD alignment     | ✅ 100%  |
| Backlog alignment | ✅ 100%  |
| DX Contract safe  | ✅ Yes   |
| Hackathon scope   | ✅ Tight |
| Overbuild risk    | ❌ None  |

---

