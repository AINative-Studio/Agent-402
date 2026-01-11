# Vector Upsert API - Quick Start Guide

**Issue #27:** Direct vector upsert operations

**Endpoint:** `POST /database/vectors/upsert`

**Story Points:** 2 | **Status:** ✅ Implemented

---

## Quick Reference

### Endpoint Details

```
POST /database/vectors/upsert
```

**Authentication:** X-API-Key (required)

**Content-Type:** application/json

---

## Environment Variables

```bash
# Set standard environment variables
export API_KEY="your_api_key"
export PROJECT_ID="proj_demo_001"
export BASE_URL="http://localhost:8000"
```

## Minimal Example

```bash
curl -X POST "$BASE_URL/database/vectors/upsert" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vector_embedding": [0.1, 0.2, 0.3, ...],
    "document": "Your document text here"
  }'
```

Note: Replace `...` with actual 384, 768, 1024, or 1536 float values

---

## Request Body

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `vector_embedding` | `float[]` | Array of floats (384, 768, 1024, or 1536 elements) |
| `document` | `string` | Source document text (non-empty) |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vector_id` | `string` | auto-generated | Custom vector ID (for updates) |
| `metadata` | `object` | `{}` | JSON metadata for classification |
| `namespace` | `string` | `"default"` | Logical namespace for isolation |

---

## Response Body

```json
{
  "vector_id": "vec_abc123",
  "created": true,
  "dimensions": 384,
  "namespace": "default",
  "metadata": {},
  "stored_at": "2026-01-10T12:34:56.789Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `vector_id` | `string` | Unique identifier (generated or provided) |
| `created` | `boolean` | `true` = insert, `false` = update |
| `dimensions` | `integer` | Vector dimensionality (384/768/1024/1536) |
| `namespace` | `string` | Namespace where vector was stored |
| `metadata` | `object` | Metadata stored with vector |
| `stored_at` | `string` | ISO timestamp |

---

## Upsert Behavior

### Scenario 1: Insert (No vector_id)
```json
{
  "vector_embedding": [0.1, ...],  // 384 floats
  "document": "New document"
}
```
**Result:** New vector created with auto-generated ID
- `created: true`
- `vector_id: "vec_abc123"`

### Scenario 2: Insert (New vector_id)
```json
{
  "vector_id": "my_custom_id",
  "vector_embedding": [0.1, ...],
  "document": "New document"
}
```
**Result:** New vector created with custom ID
- `created: true`
- `vector_id: "my_custom_id"`

### Scenario 3: Update (Existing vector_id)
```json
{
  "vector_id": "my_custom_id",  // Already exists
  "vector_embedding": [0.2, ...],
  "document": "Updated document"
}
```
**Result:** Existing vector updated
- `created: false`
- `vector_id: "my_custom_id"`

---

## Supported Dimensions

| Dimensions | Model Example | Use Case |
|------------|---------------|----------|
| **384** | BAAI/bge-small-en-v1.5 | Default, lightweight |
| **768** | BAAI/bge-base-en-v1.5 | Balanced quality |
| **1024** | BAAI/bge-large-en-v1.5 | High quality |
| **1536** | OpenAI ada-002, text-embedding-3-small | OpenAI embeddings |

**⚠️ Important:** Only these four dimensions are supported. Other sizes return `DIMENSION_MISMATCH` error.

---

## Python Example

```python
import requests
import os

# Use environment variables
API_KEY = os.getenv('API_KEY', 'your_api_key')
PROJECT_ID = os.getenv('PROJECT_ID', 'proj_demo_001')
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')

# Create a 384-dimensional vector
vector = [0.1] * 384

response = requests.post(
    f"{BASE_URL}/database/vectors/upsert",
    headers={
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "vector_embedding": vector,
        "document": "My document text",
        "metadata": {
            "source": "my_app",
            "agent_id": "agent_001"
        },
        "namespace": "my_namespace"
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Vector ID: {data['vector_id']}")
    print(f"Created: {data['created']}")
else:
    print(f"Error: {response.json()}")
```

---

## JavaScript Example

```javascript
// Use environment variables (Node.js)
const API_KEY = process.env.API_KEY || "your_api_key";
const PROJECT_ID = process.env.PROJECT_ID || "proj_demo_001";
const BASE_URL = process.env.BASE_URL || "http://localhost:8000";

// Create a 384-dimensional vector
const vector = Array(384).fill(0.1);

const response = await fetch(`${BASE_URL}/database/vectors/upsert`, {
  method: 'POST',
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    vector_embedding: vector,
    document: "My document text",
    metadata: {
      source: "my_app",
      agent_id: "agent_001"
    },
    namespace: "my_namespace"
  })
});

const data = await response.json();
console.log("Vector ID:", data.vector_id);
console.log("Created:", data.created);
```

---

## Common Errors

### 401 Unauthorized
```json
{
  "detail": "Invalid or missing API key",
  "error_code": "INVALID_API_KEY"
}
```
**Fix:** Provide valid `X-API-Key` header

### 422 Dimension Mismatch
```json
{
  "detail": "Vector dimensions (512) not supported. Supported dimensions: 384, 768, 1024, 1536"
}
```
**Fix:** Use exactly 384, 768, 1024, or 1536 floats

### 422 Empty Document
```json
{
  "detail": [
    {
      "loc": ["body", "document"],
      "msg": "Document cannot be empty or whitespace",
      "type": "value_error"
    }
  ]
}
```
**Fix:** Provide non-empty document string

### 422 Missing Field
```json
{
  "detail": [
    {
      "loc": ["body", "vector_embedding"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
**Fix:** Include all required fields (vector_embedding, document)

---

## Advanced Features

### Namespace Isolation

Use namespaces to logically separate vectors:

```python
# Agent 1's memory
requests.post(url, json={
    "vector_embedding": vector,
    "document": "Agent 1 memory",
    "namespace": "agent_1_memory"
})

# Agent 2's memory (isolated)
requests.post(url, json={
    "vector_embedding": vector,
    "document": "Agent 2 memory",
    "namespace": "agent_2_memory"
})
```

### Metadata for Classification

Use metadata for filtering and classification:

```python
requests.post(url, json={
    "vector_embedding": vector,
    "document": "Compliance check result",
    "metadata": {
        "agent_id": "compliance_agent",
        "task_type": "kyc_check",
        "confidence": 0.95,
        "timestamp": "2026-01-10T12:00:00Z",
        "tags": ["fintech", "compliance", "kyc"]
    }
})
```

### Idempotent Updates

Use custom vector_id for idempotent updates:

```python
vector_id = "user_profile_vec_12345"

# First call: creates vector
response1 = requests.post(url, json={
    "vector_id": vector_id,
    "vector_embedding": vector,
    "document": "User profile v1"
})
# created: true

# Second call: updates vector (idempotent)
response2 = requests.post(url, json={
    "vector_id": vector_id,
    "vector_embedding": updated_vector,
    "document": "User profile v2"
})
# created: false
```

---

## List Vectors

Retrieve all vectors in a namespace:

```bash
curl -X GET "$BASE_URL/database/vectors/my_namespace" \
  -H "X-API-Key: $API_KEY"
```

Response:
```json
{
  "vectors": [
    {
      "vector_id": "vec_001",
      "dimensions": 384,
      "document": "Document text",
      "metadata": {},
      "stored_at": "2026-01-10T12:34:56.789Z"
    }
  ],
  "namespace": "default",
  "total": 1
}
```

**Note:** Embedding vectors are not included in list response (too large).

---

## Best Practices

### 1. Use Consistent Dimensions
```python
# ❌ Bad: Mixing dimensions in same namespace
upsert(vector_384, namespace="my_data")
upsert(vector_768, namespace="my_data")  # Incompatible!

# ✅ Good: Separate namespaces for different models
upsert(vector_384, namespace="model_384")
upsert(vector_768, namespace="model_768")
```

### 2. Use Descriptive vector_id
```python
# ❌ Bad: Generic IDs
vector_id = "vec_001"

# ✅ Good: Descriptive IDs
vector_id = "user_profile_12345"
vector_id = "compliance_check_2026_01_10"
vector_id = "agent_memory_transaction_abc123"
```

### 3. Structure Metadata
```python
# ✅ Good: Structured metadata for filtering
metadata = {
    "entity_type": "user_profile",
    "entity_id": "12345",
    "source": "signup_flow",
    "created_by": "agent_001",
    "version": 2,
    "tags": ["kyc", "verified"]
}
```

### 4. Use Namespaces for Isolation
```python
# ✅ Good: Separate by environment/tenant/agent
namespace = f"prod_agent_{agent_id}"
namespace = f"test_environment"
namespace = f"tenant_{tenant_id}_vectors"
```

---

## DX Contract Guarantees

### ✅ Endpoint Prefix
- **MUST** use `/database/` prefix
- `/vectors/upsert` → ❌ 404 Not Found
- `/database/vectors/upsert` → ✅ 200 OK

### ✅ Dimension Validation
- Only 384, 768, 1024, 1536 supported
- Other sizes → 422 DIMENSION_MISMATCH

### ✅ Authentication
- All endpoints require X-API-Key
- Invalid key → 401 INVALID_API_KEY

### ✅ Error Format
- All errors return `{detail, error_code}`
- Validation errors use HTTP 422

### ✅ Idempotency
- Same vector_id + data = same result
- Safe to retry failed requests

---

## Testing

Run the smoke test:
```bash
cd backend
python3 test_vector_upsert_manual.py
```

Run the test suite:
```bash
cd backend
python3 -m pytest app/tests/test_vectors_api.py -v
```

---

## Related Documentation

- [Full Implementation Summary](/backend/ISSUE_27_IMPLEMENTATION_SUMMARY.md)
- [DX Contract](/DX-Contract.md)
- [PRD](/prd.md)
- [API Specification](/docs/api/api-spec.md)

---

## Support

For issues or questions:
1. Check error message for specific guidance
2. Verify dimension size (384/768/1024/1536)
3. Ensure `/database/` prefix is used
4. Validate X-API-Key header is present
5. Consult [Implementation Summary](/backend/ISSUE_27_IMPLEMENTATION_SUMMARY.md)
