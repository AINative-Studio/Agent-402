# ZeroDB Platform Developer Guide (Aligned to AINative `/v1/public` Endpoints)

> **Last Updated:** December 13, 2025
> **Base URL:** `https://api.ainative.studio`
> **API Prefix:** `/v1/public`

## 📚 Quick Navigation

| Section          | Description                                      | Time      |
| ---------------- | ------------------------------------------------ | --------- |
| Quick Start      | Create/list project → embed/store → search       | 5 min     |
| Prerequisites    | Account, API key, project id                     | 2 min     |
| Common Use Cases | RAG, CRUD Tables, Event tracking                 | 10 min    |
| API Reference    | Project + Embeddings + Database (Vectors/Tables) | Reference |
| Troubleshooting  | Common errors + fixes                            | Reference |
| Best Practices   | Production patterns                              | 10 min    |

---

## 🚀 Quick Start (5 minutes)

### Step 1: Get your API key

1. Sign up at `https://ainative.studio`
2. Go to **Settings → API Keys**
3. Create an API key

**Header used across all requests**

```bash
-H "X-API-Key: YOUR_API_KEY"
```

---

### Step 2: Get a Project ID

#### Option A — Create a project

**Endpoint:** `POST /v1/public/projects`

```bash
curl -X POST "https://api.ainative.studio/v1/public/projects" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Project",
    "description": "Getting started with ZeroDB",
    "tier": "free",
    "database_enabled": true
  }'
```

✅ Copy the returned `id` (this is your `PROJECT_ID`)

#### Option B — List existing projects

**Endpoint:** `GET /v1/public/projects`

```bash
curl "https://api.ainative.studio/v1/public/projects" \
  -H "X-API-Key: YOUR_API_KEY"
```

✅ Copy any `id` with `"status": "ACTIVE"`.

---

### Step 3: Embed + store a document (vector DB)

**Endpoint:** `POST /v1/public/{project_id}/embeddings/embed-and-store`

```bash
curl -X POST "https://api.ainative.studio/v1/public/YOUR_PROJECT_ID/embeddings/embed-and-store" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "doc_1",
        "text": "ZeroDB is a unified database platform with PostgreSQL, vectors, and AI.",
        "metadata": {
          "category": "documentation",
          "tags": ["database", "ai"]
        }
      }
    ],
    "namespace": "knowledge_base",
    "upsert": true
  }'
```

✅ Success check: `"success": true` + `"dimensions": 384` (default)

---

### Step 4: Semantic search

**Endpoint:** `POST /v1/public/{project_id}/embeddings/search`

```bash
curl -X POST "https://api.ainative.studio/v1/public/YOUR_PROJECT_ID/embeddings/search" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is ZeroDB?",
    "top_k": 5,
    "namespace": "knowledge_base"
  }'
```

✅ Success check: `"results": [...]`

---

## 🎯 Critical Requirements (Hard Rules)

These are the rules your snippets must follow or you’ll hit common failures:

1. **Embeddings default model is 384-dim**

   * Default: `BAAI/bge-small-en-v1.5` → **384 dims**
2. **If you pass `model`, use the SAME `model` for store + search**
3. **Vector write endpoints require `/database/` prefix**

   * ✅ `/v1/public/{project_id}/database/vectors/...`
   * ❌ `/v1/public/{project_id}/vectors/...`
4. **Table row inserts require `row_data`**

   * ✅ `{ "row_data": { ... } }`
   * ❌ `{ "rows": ... }` or `{ "data": ... }`

---

## 🎯 Multi-Dimension Vector Support

ZeroDB supports embedding models with multiple dimensions.

| Dimensions | Model                    | Notes                |
| ---------: | ------------------------ | -------------------- |
|        384 | `BAAI/bge-small-en-v1.5` | Default              |
|        768 | `BAAI/bge-base-en-v1.5`  | Higher quality       |
|       1024 | `BAAI/bge-large-en-v1.5` | Premium quality      |
|       1536 | OpenAI/Custom            | Legacy compatibility |

**Model consistency rule (required):** Store + search must use the same model.

---

## 💡 Common Use Cases

### Use Case 1: RAG (Embed+Store → Search)

* Store docs: `POST /{project_id}/embeddings/embed-and-store`
* Retrieve: `POST /{project_id}/embeddings/search`

This is the canonical pattern for retrieval.

---

### Use Case 2: CRUD (Tables)

#### Create table

**Endpoint:** `POST /v1/public/{project_id}/database/tables`

```bash
curl -X POST "https://api.ainative.studio/v1/public/YOUR_PROJECT_ID/database/tables" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customers",
    "description": "Customer information",
    "schema": {
      "id": "UUID PRIMARY KEY",
      "name": "TEXT NOT NULL",
      "email": "TEXT UNIQUE",
      "tier": "TEXT",
      "created_at": "TIMESTAMP DEFAULT NOW()"
    }
  }'
```

#### Insert row (must use `row_data`)

**Endpoint:** `POST /v1/public/{project_id}/database/tables/{table}/rows`

```bash
curl -X POST "https://api.ainative.studio/v1/public/YOUR_PROJECT_ID/database/tables/customers/rows" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "row_data": {
      "name": "John Doe",
      "email": "john@example.com",
      "tier": "pro"
    }
  }'
```

#### List rows

**Endpoint:** `GET /v1/public/{project_id}/database/tables/{table}/rows`

```bash
curl "https://api.ainative.studio/v1/public/YOUR_PROJECT_ID/database/tables/customers/rows?limit=100" \
  -H "X-API-Key: YOUR_API_KEY"
```

---

### Use Case 3: Event Tracking

**Endpoint:** `POST /v1/public/{project_id}/database/events`

```python
import requests
from datetime import datetime

API_KEY = "your_api_key"
PROJECT_ID = "your_project_id"
BASE_URL = "https://api.ainative.studio/v1/public"
headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

payload = {
  "event_type": "page_view",
  "data": {"user_id": "user_123", "page": "/dashboard"},
  "timestamp": datetime.utcnow().isoformat() + "Z"
}

r = requests.post(f"{BASE_URL}/{PROJECT_ID}/database/events", headers=headers, json=payload)
print(r.status_code, r.json())
```

---

## 📖 API Reference (Endpoints included in this guide)

### Projects

* `POST /v1/public/projects`
* `GET /v1/public/projects`

### Embeddings

* `POST /v1/public/{project_id}/embeddings/generate`
* `POST /v1/public/{project_id}/embeddings/embed-and-store`
* `POST /v1/public/{project_id}/embeddings/search`

### Database

* `POST /v1/public/{project_id}/database/vectors/upsert`
* `POST /v1/public/{project_id}/database/tables`
* `POST /v1/public/{project_id}/database/tables/{table_name}/rows`
* `GET  /v1/public/{project_id}/database/tables/{table_name}/rows`
* `POST /v1/public/{project_id}/database/events`

> Note: Anything not listed above is intentionally omitted in this revision to avoid drifting from the pasted reference.

---

## 🔍 Troubleshooting (Endpoint-Accurate)

### 404 on vectors

**Cause:** missing `/database/` prefix
✅ Use:
`/v1/public/{project_id}/database/vectors/upsert`

### 422 “row_data required”

**Cause:** wrong field name
✅ Use:

```json
{ "row_data": { "name": "John" } }
```

### 500 model not found / wrong model

**Cause:** using unsupported `model` string
✅ Use one of:

* `BAAI/bge-small-en-v1.5`
* `BAAI/bge-base-en-v1.5`
* `BAAI/bge-large-en-v1.5`

### 500 dimension mismatch

**Cause:** inserting wrong vector length into vector endpoints
✅ Fix: generate embeddings with the same model, then upsert.

---

## 🚀 Best Practices

1. **Pick one model per namespace** and keep it consistent.
2. **Batch embedding generation** (up to 100 texts per request).
3. **Use namespaces** to separate concerns:

   * `knowledge_base`, `support_faq`, `legal_docs`, etc.
4. **Don’t expose API keys in frontend** (use server-side proxy).
5. **Add retries on 429/5xx** with exponential backoff.

---

## 🔗 Resources

* Interactive API docs: `https://api.ainative.studio/docs`
* Support: `support@ainative.studio`
* Status: `https://status.ainative.studio`

---
