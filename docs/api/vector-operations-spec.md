# Vector Operations API Specification

**Version:** v1.0
**Last Updated:** 2026-01-10
**Epic:** Epic 6 - Vector Operations API
**Base URL:** `https://api.ainative.studio/v1/public/database`

---

## 🚨 CRITICAL WARNING: /database/ Prefix Required

**ALL vector operations MUST include `/database/` in the path.**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ✅ CORRECT:   /v1/public/database/vectors/upsert      │
│  ❌ INCORRECT: /v1/public/vectors/upsert               │
│                                                         │
│  Missing /database/ will ALWAYS return 404 Not Found   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**📖 MUST READ:** [DATABASE_PREFIX_WARNING.md](/docs/api/DATABASE_PREFIX_WARNING.md)

This comprehensive guide covers:
- Why `/database/` is required
- Correct vs incorrect endpoint paths
- Common mistakes and how to avoid them
- Language-specific examples (Python, JavaScript, Go, cURL)
- Troubleshooting 404 errors

**Per DX Contract §4:** This prefix requirement is permanent and guaranteed behavior.

---

## Overview

The Vector Operations API provides direct access to vector storage and retrieval. This is for advanced use cases where you want to:

1. **Store pre-computed vectors** (you already have the embeddings)
2. **Perform vector search** with your own query vectors
3. **Manage vectors directly** without embedding generation
4. **Integrate with external embedding services**

**For automatic embedding generation,** use the Embeddings API instead:
- [Embeddings API](/docs/api/embeddings-api-spec.md) - Generate embeddings
- [Embeddings Store & Search](/docs/api/embeddings-store-search-spec.md) - Store with auto-embedding

---

## Authentication

All endpoints require authentication via the `X-API-Key` header.

**IMPORTANT:** API keys must only be used in server-side environments. See [SECURITY.md](/SECURITY.md) for details.

```bash
curl -X POST "https://api.ainative.studio/v1/public/database/vectors/upsert" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json"
```

---

## Endpoint Paths Reference

**Quick Reference - All Paths Include /database/:**

| Operation | Correct Path | Status |
|-----------|-------------|--------|
| Upsert vectors | `POST /v1/public/database/vectors/upsert` | ✅ |
| Search vectors | `POST /v1/public/database/vectors/search` | ✅ |
| Get vector | `GET /v1/public/database/vectors/{id}` | ✅ |
| Delete vector | `DELETE /v1/public/database/vectors/{id}` | ✅ |
| List vectors | `GET /v1/public/database/vectors` | ✅ |

**WRONG Paths (Will Return 404):**

| Operation | Wrong Path | Error |
|-----------|-----------|-------|
| Upsert vectors | `POST /v1/public/vectors/upsert` | ❌ 404 |
| Search vectors | `POST /v1/public/vectors/search` | ❌ 404 |
| Get vector | `GET /v1/public/vectors/{id}` | ❌ 404 |

---

## Endpoints

### 1. Upsert Vectors

Store or update vectors with metadata.

**Endpoint:** `POST /v1/public/database/vectors/upsert`

**⚠️ CRITICAL:** This path MUST include `/database/` prefix.

**Authentication:** Required (`X-API-Key` header)

**Request Body:**

```json
{
  "vectors": [
    {
      "id": "vec-001",
      "values": [0.123, -0.456, 0.789, "... (1536 dimensions)"],
      "metadata": {
        "source": "external_embedding_service",
        "model": "custom-model-v1",
        "timestamp": "2026-01-10T12:00:00Z"
      }
    }
  ],
  "namespace": "custom_vectors"
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vectors` | array | **Yes** | Array of vectors to upsert |
| `vectors[].id` | string | **Yes** | Unique vector identifier |
| `vectors[].values` | array[float] | **Yes** | Vector embedding (must be 1536 dimensions) |
| `vectors[].metadata` | object | No | Optional metadata for filtering |
| `namespace` | string | No | Namespace for organization (defaults to `default`) |

**Success Response (200 OK):**

```json
{
  "upserted_count": 1,
  "namespace": "custom_vectors",
  "vectors": [
    {
      "id": "vec-001",
      "status": "created",
      "dimensions": 1536
    }
  ]
}
```

**Error Responses:**

```json
// 400 Bad Request - Dimension mismatch
{
  "detail": "Vector dimension mismatch. Expected 1536, got 384",
  "error_code": "DIMENSION_MISMATCH"
}

// 401 Unauthorized
{
  "detail": "Invalid API key",
  "error_code": "INVALID_API_KEY"
}

// 404 Not Found - Missing /database/ prefix
{
  "detail": "Not Found"
}
```

**Example Request:**

```bash
# ✅ CORRECT - Includes /database/ prefix
curl -X POST "https://api.ainative.studio/v1/public/database/vectors/upsert" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [
      {
        "id": "vec-001",
        "values": [0.1, 0.2, 0.3, "... 1536 total"],
        "metadata": {"source": "custom"}
      }
    ],
    "namespace": "my_vectors"
  }'
```

```bash
# ❌ INCORRECT - Missing /database/ prefix (WILL FAIL)
curl -X POST "https://api.ainative.studio/v1/public/vectors/upsert" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"vectors": [...]}'
# Result: 404 Not Found
```

---

### 2. Search Vectors

Search vectors using similarity.

**Endpoint:** `POST /v1/public/database/vectors/search`

**⚠️ CRITICAL:** This path MUST include `/database/` prefix.

**Authentication:** Required (`X-API-Key` header)

**Request Body:**

```json
{
  "query_vector": [0.123, -0.456, 0.789, "... (1536 dimensions)"],
  "namespace": "custom_vectors",
  "top_k": 10,
  "similarity_threshold": 0.7,
  "filter": {
    "metadata.source": "external_embedding_service"
  },
  "include_metadata": true,
  "include_values": false
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query_vector` | array[float] | **Yes** | Query vector (must be 1536 dimensions) |
| `namespace` | string | No | Namespace to search (defaults to `default`) |
| `top_k` | integer | No | Max results to return (defaults to 10, max 100) |
| `similarity_threshold` | float | No | Minimum similarity score 0.0-1.0 (defaults to 0.0) |
| `filter` | object | No | Metadata filters (exact matching) |
| `include_metadata` | boolean | No | Include metadata in results (defaults to `true`) |
| `include_values` | boolean | No | Include vector values in results (defaults to `false`) |

**Success Response (200 OK):**

```json
{
  "results": [
    {
      "id": "vec-001",
      "score": 0.92,
      "metadata": {
        "source": "external_embedding_service",
        "model": "custom-model-v1"
      }
    },
    {
      "id": "vec-003",
      "score": 0.78,
      "metadata": {
        "source": "external_embedding_service",
        "model": "custom-model-v1"
      }
    }
  ],
  "total_results": 2,
  "namespace": "custom_vectors"
}
```

**Example Request:**

```bash
# ✅ CORRECT - Includes /database/ prefix
curl -X POST "https://api.ainative.studio/v1/public/database/vectors/search" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.1, 0.2, 0.3, "... 1536 total"],
    "namespace": "my_vectors",
    "top_k": 5,
    "similarity_threshold": 0.7
  }'
```

---

### 3. Get Vector by ID

Retrieve a specific vector.

**Endpoint:** `GET /v1/public/database/vectors/{vector_id}`

**⚠️ CRITICAL:** This path MUST include `/database/` prefix.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `vector_id` | string | The vector identifier |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `namespace` | string | Namespace (defaults to `default`) |
| `include_values` | boolean | Include vector values (defaults to `false`) |

**Success Response (200 OK):**

```json
{
  "id": "vec-001",
  "metadata": {
    "source": "external_embedding_service"
  },
  "namespace": "custom_vectors",
  "dimensions": 1536
}
```

**Example Request:**

```bash
# ✅ CORRECT - Includes /database/ prefix
curl -X GET "https://api.ainative.studio/v1/public/database/vectors/vec-001?namespace=my_vectors" \
  -H "X-API-Key: your_api_key"
```

---

### 4. Delete Vector

Delete a specific vector.

**Endpoint:** `DELETE /v1/public/database/vectors/{vector_id}`

**⚠️ CRITICAL:** This path MUST include `/database/` prefix.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `vector_id` | string | The vector identifier |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `namespace` | string | Namespace (defaults to `default`) |

**Success Response (200 OK):**

```json
{
  "deleted": true,
  "id": "vec-001",
  "namespace": "custom_vectors"
}
```

**Example Request:**

```bash
# ✅ CORRECT - Includes /database/ prefix
curl -X DELETE "https://api.ainative.studio/v1/public/database/vectors/vec-001?namespace=my_vectors" \
  -H "X-API-Key: your_api_key"
```

---

### 5. List Vectors

List all vectors in a namespace.

**Endpoint:** `GET /v1/public/database/vectors`

**⚠️ CRITICAL:** This path MUST include `/database/` prefix.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `namespace` | string | Namespace to list (defaults to `default`) |
| `limit` | integer | Max results (defaults to 100) |
| `offset` | integer | Pagination offset (defaults to 0) |

**Success Response (200 OK):**

```json
{
  "vectors": [
    {
      "id": "vec-001",
      "namespace": "custom_vectors",
      "dimensions": 1536
    },
    {
      "id": "vec-002",
      "namespace": "custom_vectors",
      "dimensions": 1536
    }
  ],
  "total": 2,
  "limit": 100,
  "offset": 0
}
```

**Example Request:**

```bash
# ✅ CORRECT - Includes /database/ prefix
curl -X GET "https://api.ainative.studio/v1/public/database/vectors?namespace=my_vectors&limit=10" \
  -H "X-API-Key: your_api_key"
```

---

## Common Mistakes

### Mistake 1: Forgetting /database/ prefix

```python
# ❌ WRONG - Missing /database/ prefix
response = requests.post(
    "https://api.ainative.studio/v1/public/vectors/upsert",  # WILL FAIL
    headers={"X-API-Key": api_key},
    json={"vectors": [...]}
)
# Result: 404 Not Found

# ✅ CORRECT - Include /database/ prefix
response = requests.post(
    "https://api.ainative.studio/v1/public/database/vectors/upsert",
    headers={"X-API-Key": api_key},
    json={"vectors": [...]}
)
```

### Mistake 2: Wrong dimension size

```python
# ❌ WRONG - Vector dimension mismatch (384 instead of 1536)
response = requests.post(
    "https://api.ainative.studio/v1/public/database/vectors/upsert",
    headers={"X-API-Key": api_key},
    json={
        "vectors": [{
            "id": "vec-001",
            "values": [0.1, 0.2, 0.3]  # Only 3 dimensions! Should be 1536
        }]
    }
)
# Result: 400 Bad Request - DIMENSION_MISMATCH

# ✅ CORRECT - Use 1536 dimensions
response = requests.post(
    "https://api.ainative.studio/v1/public/database/vectors/upsert",
    headers={"X-API-Key": api_key},
    json={
        "vectors": [{
            "id": "vec-001",
            "values": [0.1, 0.2, ...1536 values total...]
        }]
    }
)
```

### Mistake 3: Mixing embeddings and vector endpoints

```python
# These are DIFFERENT APIs with DIFFERENT paths:

# ❌ Embeddings API - NO /database/ prefix
# (This is for automatic embedding generation)
requests.post(
    "https://api.ainative.studio/v1/public/proj_123/embeddings/embed-and-store",
    ...
)

# ✅ Vector Operations API - YES /database/ prefix
# (This is for direct vector storage)
requests.post(
    "https://api.ainative.studio/v1/public/database/vectors/upsert",
    ...
)
```

---

## Language-Specific Examples

### Python

```python
import requests

BASE_URL = "https://api.ainative.studio/v1/public"
API_KEY = "your_api_key"

# ✅ CORRECT - Upsert vectors
def upsert_vectors(vectors, namespace="default"):
    """Upsert vectors with /database/ prefix."""
    response = requests.post(
        f"{BASE_URL}/database/vectors/upsert",  # Note: /database/ prefix
        headers={"X-API-Key": API_KEY},
        json={
            "vectors": vectors,
            "namespace": namespace
        }
    )
    response.raise_for_status()
    return response.json()

# Usage
vectors = [{
    "id": "vec-001",
    "values": [0.1] * 1536,  # 1536 dimensions required
    "metadata": {"source": "custom"}
}]

result = upsert_vectors(vectors, namespace="my_vectors")
print(f"Upserted {result['upserted_count']} vectors")
```

### JavaScript

```javascript
const BASE_URL = "https://api.ainative.studio/v1/public";
const API_KEY = "your_api_key";

// ✅ CORRECT - Search vectors
async function searchVectors(queryVector, namespace = "default") {
  const response = await fetch(
    `${BASE_URL}/database/vectors/search`,  // Note: /database/ prefix
    {
      method: "POST",
      headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query_vector: queryVector,
        namespace: namespace,
        top_k: 10
      })
    }
  );

  if (!response.ok) {
    throw new Error(`Search failed: ${response.status}`);
  }

  return await response.json();
}

// Usage
const queryVector = new Array(1536).fill(0.1);
const results = await searchVectors(queryVector, "my_vectors");
console.log(`Found ${results.total_results} matches`);
```

---

## DX Contract Compliance

Per the ZeroDB DX Contract:

### §4: Endpoint Prefixing ✅

> "All vector and database operations **require** the `/database/` prefix. Missing `/database/` will always return 404 Not Found. This behavior is permanent."

**This guarantee means:**
- `/database/` prefix is MANDATORY for all vector operations
- Omitting `/database/` will ALWAYS return 404
- This will NEVER change without a version bump
- No exceptions or workarounds exist

### §7: Error Semantics ✅

All errors follow the standard format:
```json
{
  "detail": "...",
  "error_code": "..."
}
```

---

## Troubleshooting

### Getting 404 Not Found?

**Most common cause:** Missing `/database/` prefix in the path.

**Debug steps:**

1. **Print your full URL:**
   ```python
   url = f"{BASE_URL}/database/vectors/upsert"
   print(f"Request URL: {url}")
   # Should print: https://api.ainative.studio/v1/public/database/vectors/upsert
   ```

2. **Check for typos:**
   - "databases" ❌ (should be "database")
   - "db" ❌ (should be "database")
   - Wrong order: "/database/public/" ❌ (should be "/public/database/")

3. **Compare against working example:**
   ```bash
   # Copy this EXACT URL and test:
   curl -X GET "https://api.ainative.studio/v1/public/database/vectors" \
     -H "X-API-Key: your_api_key"
   ```

### Getting DIMENSION_MISMATCH?

All vectors must be exactly 1536 dimensions for ZeroDB vector operations.

```python
# ✅ CORRECT
values = [0.1] * 1536  # Exactly 1536 dimensions

# ❌ WRONG
values = [0.1] * 384   # Wrong dimension count
```

---

## Related Documentation

- **[DATABASE_PREFIX_WARNING.md](/docs/api/DATABASE_PREFIX_WARNING.md)** - Comprehensive prefix guide
- **[DX Contract §4](/DX-Contract.md)** - Endpoint prefixing guarantees
- **[Embeddings API](/docs/api/embeddings-api-spec.md)** - For automatic embedding generation
- **[Embeddings Store & Search](/docs/api/embeddings-store-search-spec.md)** - For document storage with auto-embedding

---

## Quick Reference Card

```
Vector Operations API - Quick Reference

Base Path (MANDATORY):
  /v1/public/database/

Operations:
  POST   /vectors/upsert     - Store/update vectors
  POST   /vectors/search     - Search by similarity
  GET    /vectors/{id}       - Get specific vector
  DELETE /vectors/{id}       - Delete vector
  GET    /vectors            - List all vectors

Requirements:
  ✅ Include /database/ prefix in ALL paths
  ✅ Vectors must be exactly 1536 dimensions
  ✅ X-API-Key header required
  ✅ Follow DX Contract error format

Common Errors:
  404 - Missing /database/ prefix in path
  400 - Vector dimension mismatch (not 1536)
  401 - Invalid or missing API key

Need Help?
  See: /docs/api/DATABASE_PREFIX_WARNING.md
```

---

**Remember:** ALL vector operations require the `/database/` prefix. No exceptions.
