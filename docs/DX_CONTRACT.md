# ZeroDB Developer Experience Contract (DX Contract)

**Version:** 1.0.0
**Effective Date:** 2026-01-11
**Status:** Active
**Audience:** All ZeroDB API Consumers

---

## Document Purpose

This DX Contract is a **binding commitment** to developers consuming the ZeroDB API. It documents all API invariants, guarantees, and behavioral contracts that developers can rely on. These guarantees will not change without a major version bump (v2, v3, etc.).

**This is not documentation—this is a contract.** Every statement here is a promise that the ZeroDB API will uphold. If the API violates any guarantee in this contract, it is considered a bug and will be fixed with the highest priority.

---

## Table of Contents

1. [Introduction & Purpose](#§1-introduction--purpose)
2. [Authentication & Authorization Invariants](#§2-authentication--authorization-invariants)
3. [Request/Response Format Guarantees](#§3-requestresponse-format-guarantees)
4. [Error Handling Contract](#§4-error-handling-contract)
5. [Data Consistency & Validation Rules](#§5-data-consistency--validation-rules)
6. [Namespace & Scoping Semantics](#§6-namespace--scoping-semantics)
7. [Embedding & Vector Operations Contract](#§7-embedding--vector-operations-contract)
8. [Database Operations Guarantees](#§8-database-operations-guarantees)
9. [Versioning & Breaking Changes Policy](#§9-versioning--breaking-changes-policy)
10. [Performance & Rate Limiting Expectations](#§10-performance--rate-limiting-expectations)
11. [Agent & Compliance Guarantees](#§11-agent--compliance-guarantees)
12. [Append-Only & Non-Repudiation Contract](#§12-append-only--non-repudiation-contract)

---

## §1: Introduction & Purpose

### 1.1 Contract Scope

This DX Contract applies to all endpoints under the `/v1/public/` prefix. It defines:

- **What developers can rely on** (invariants and guarantees)
- **How the API will behave** (deterministic semantics)
- **What will never change** (stability commitments)
- **How we handle breaking changes** (versioning policy)

### 1.2 Why This Contract Exists

**Rationale:** AI agents and autonomous systems require deterministic, predictable APIs. Non-deterministic behavior breaks agent workflows, makes debugging impossible, and violates compliance requirements.

**Business Value:**
- Eliminates integration uncertainty
- Enables confident automation
- Supports regulatory compliance
- Reduces support burden through clear contracts

### 1.3 Enforcement

**Code Reference:**
- Test Suite: `/backend/app/tests/` (100+ tests verify contract compliance)
- Validation: Schema validation in `/backend/app/schemas/`
- Middleware: Authentication and error handling in `/backend/app/middleware/`

**How Guaranteed:**
- Every contract clause has corresponding automated tests
- CI/CD pipeline enforces contract compliance
- Contract violations are treated as P0 bugs

### 1.4 Example: Deterministic Behavior

```python
# GUARANTEED: This request will ALWAYS produce the same embedding
# for the same text input when using the same model
response = requests.post(
    f"{BASE_URL}/v1/public/embeddings/generate",
    headers={"X-API-Key": API_KEY},
    json={
        "text": "autonomous fintech agent",
        "model": "BAAI/bge-small-en-v1.5"
    }
)

# GUARANTEED: Response will ALWAYS include these exact fields
assert "embedding" in response.json()
assert "model" in response.json()
assert "dimensions" in response.json()
assert response.json()["dimensions"] == 384  # Always 384 for this model
```

---

## §2: Authentication & Authorization Invariants

### 2.1 Authentication Methods

**Guarantee:** All `/v1/public/*` endpoints accept **exactly two** authentication methods:

1. **X-API-Key header** (preferred for server-to-server)
2. **Bearer JWT token** (preferred for user-facing applications)

**Code Reference:** `/backend/app/middleware/api_key_auth.py`

**Example - X-API-Key:**
```bash
curl -H "X-API-Key: zerodb_sk_your_key_here" \
  https://api.ainative.studio/v1/public/projects
```

**Example - JWT Bearer Token:**
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  https://api.ainative.studio/v1/public/projects
```

### 2.2 API Key Validation Invariants

**Guarantee:** API key validation follows these exact rules:

| Scenario | HTTP Status | Error Code | Detail Message |
|----------|-------------|------------|----------------|
| Missing `X-API-Key` header | 401 | `INVALID_API_KEY` | "Missing X-API-Key header" |
| Empty API key (`X-API-Key: ""`) | 401 | `INVALID_API_KEY` | "Empty API key" |
| Whitespace-only API key | 401 | `INVALID_API_KEY` | "Empty API key" |
| Invalid/unknown API key | 401 | `INVALID_API_KEY` | "Invalid API key" |
| Malformed API key format | 401 | `INVALID_API_KEY` | "Invalid API key" |

**Why This Matters:** Security best practice dictates that all authentication failures return the same error code to prevent information leakage about which keys exist.

**Code Reference:** `/backend/app/middleware/api_key_auth.py:155-185`

**Example:**
```python
# Missing API key
response = requests.get(f"{BASE_URL}/v1/public/projects")
assert response.status_code == 401
assert response.json()["error_code"] == "INVALID_API_KEY"
assert response.json()["detail"] == "Missing X-API-Key header"
```

### 2.3 JWT Token Validation Invariants

**Guarantee:** JWT token validation follows these exact rules:

| Scenario | HTTP Status | Error Code | Detail Message |
|----------|-------------|------------|----------------|
| Missing `Authorization` header | 401 | `INVALID_API_KEY` | "Missing X-API-Key header" |
| Invalid JWT format | 401 | `INVALID_TOKEN` | "Invalid JWT token" |
| Expired JWT token | 401 | `TOKEN_EXPIRED` | "JWT token has expired" |
| Invalid signature | 401 | `INVALID_TOKEN` | "Invalid JWT token" |

**Code Reference:** `/backend/app/middleware/api_key_auth.py:189-219`, `/backend/app/core/jwt.py`

**Example:**
```python
# Expired token
response = requests.get(
    f"{BASE_URL}/v1/public/projects",
    headers={"Authorization": "Bearer expired_token_here"}
)
assert response.status_code == 401
assert response.json()["error_code"] == "TOKEN_EXPIRED"
```

### 2.4 Authentication Exemptions

**Guarantee:** The following endpoints do NOT require authentication:

- `/` (root)
- `/health` (health check)
- `/docs` (API documentation)
- `/redoc` (alternative documentation)
- `/openapi.json` (OpenAPI schema)
- `/v1/public/auth/login` (login to obtain token)
- `/v1/public/auth/refresh` (refresh token endpoint)
- `/v1/public/embeddings/models` (public model listing)

**Code Reference:** `/backend/app/middleware/api_key_auth.py:53-62`

**Why This Matters:** Public documentation and health checks must be accessible without authentication for monitoring and developer onboarding.

### 2.5 Project-Level Authorization

**Guarantee:** After authentication, all operations are scoped to `project_id`:

- Users can only access projects they own or have been granted access to
- `project_id` in URL path determines resource scope
- Cross-project access is strictly forbidden

**Example:**
```bash
# Access project I own - SUCCESS
GET /v1/public/{my_project_id}/database/vectors/search

# Access someone else's project - FAILURE (403 UNAUTHORIZED)
GET /v1/public/{other_project_id}/database/vectors/search
```

---

## §3: Request/Response Format Guarantees

### 3.1 Content-Type Requirements

**Guarantee:** All request bodies MUST be JSON with `Content-Type: application/json`.

**Code Reference:** FastAPI automatic validation

**Example:**
```bash
# CORRECT
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}' \
  https://api.ainative.studio/v1/public/embeddings/generate

# INCORRECT - Will return 422
curl -X POST \
  -H "Content-Type: text/plain" \
  -d 'text=test' \
  https://api.ainative.studio/v1/public/embeddings/generate
```

### 3.2 Response Format Guarantee

**Guarantee:** All successful responses (2xx) return JSON with documented fields.

**Field Stability Promise:**
- Required fields will NEVER be removed in v1
- New optional fields MAY be added (backward compatible)
- Field types will NEVER change in v1
- Field semantics will NEVER change in v1

**Example:**
```json
{
  "embedding": [0.123, 0.456, ...],  // GUARANTEED: Always present
  "model": "BAAI/bge-small-en-v1.5", // GUARANTEED: Always present
  "dimensions": 384,                  // GUARANTEED: Always present
  "text": "input text",               // GUARANTEED: Always present
  "processing_time_ms": 45,           // GUARANTEED: Always present
  "new_field": "value"                // ALLOWED: New optional fields may appear
}
```

### 3.3 Timestamp Format Guarantee

**Guarantee:** All timestamps are ISO8601 format (RFC 3339) in UTC.

**Supported Formats:**
- `2026-01-10T12:34:56Z` (UTC with Z suffix) ✓
- `2026-01-10T12:34:56.789Z` (with milliseconds) ✓
- `2026-01-10T12:34:56+00:00` (with timezone offset) ✓
- `2026-01-10T12:34:56-05:00` (with negative offset) ✓

**Code Reference:** `/backend/app/core/timestamp_validator.py`

**Validation:**
```python
# VALID timestamps
"2026-01-10T12:34:56Z"
"2026-01-10T12:34:56.789Z"
"2026-01-10T12:34:56+00:00"

# INVALID timestamps - Return 422 INVALID_TIMESTAMP
"2026-01-10"           # Missing time
"2026-01-10 12:34:56"  # Space instead of T
"1641820496"           # Unix timestamp
"Jan 10, 2026"         # Human format
```

**Example Error:**
```json
{
  "detail": "Invalid timestamp format. Expected ISO8601 format (RFC 3339). Valid examples: '2026-01-10T12:34:56Z', '2026-01-10T12:34:56.789Z', '2026-01-10T12:34:56+00:00', '2026-01-10T12:34:56-05:00'",
  "error_code": "INVALID_TIMESTAMP"
}
```

### 3.4 Processing Time Guarantee

**Guarantee:** All operation responses include `processing_time_ms` field.

**Semantics:**
- Measured in **milliseconds** (integer)
- Includes only API processing time (not network latency)
- Always >= 0
- Rounded to nearest millisecond

**Code Reference:** All API endpoints track processing time

**Example:**
```json
{
  "vector_id": "vec_abc123",
  "processing_time_ms": 12,  // GUARANTEED: Always present, always integer >= 0
  ...
}
```

### 3.5 Endpoint Prefix Guarantee

**Guarantee:** All database operations MUST include `/database/` prefix in path.

**Rationale:** Separates data plane operations from control plane operations.

**Examples:**
```bash
# CORRECT - Database operations
POST /v1/public/{project_id}/database/vectors/upsert
POST /v1/public/{project_id}/database/embeddings/embed-and-store
GET  /v1/public/{project_id}/database/events

# INCORRECT - Missing /database/ prefix returns 404
POST /v1/public/{project_id}/vectors/upsert  # 404 NOT FOUND
```

**Code Reference:** Route definitions in `/backend/app/api/`

---

## §4: Error Handling Contract

### 4.1 Error Response Format

**Guarantee:** ALL error responses (4xx, 5xx) return JSON with this exact structure:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE"
}
```

**Field Guarantees:**
- `detail`: ALWAYS present, NEVER null, NEVER empty string
- `error_code`: ALWAYS present, NEVER null, ALWAYS UPPERCASE_SNAKE_CASE

**Code Reference:** `/backend/app/core/errors.py:324-348`

**Why This Matters:** Machine-readable error codes enable programmatic error handling. Human-readable details enable debugging. Both MUST always be present.

### 4.2 Error Code Stability

**Guarantee:** Error codes are **STABLE** and **DOCUMENTED**. They will not change in v1.

**Standard Error Codes:**

| Error Code | HTTP Status | Meaning | Cause |
|------------|-------------|---------|-------|
| `INVALID_API_KEY` | 401 | Authentication failed | Missing/invalid API key |
| `INVALID_TOKEN` | 401 | JWT token invalid | Malformed or invalid JWT |
| `TOKEN_EXPIRED` | 401 | JWT token expired | JWT past expiration time |
| `UNAUTHORIZED` | 403 | Not authorized | User lacks permission for resource |
| `PROJECT_NOT_FOUND` | 404 | Project doesn't exist | Invalid project_id |
| `AGENT_NOT_FOUND` | 404 | Agent doesn't exist | Invalid agent_id |
| `INVALID_TIER` | 422 | Invalid tier value | Tier not in allowed set |
| `PROJECT_LIMIT_EXCEEDED` | 429 | Too many projects | User exceeded tier limit |
| `DIMENSION_MISMATCH` | 400 | Vector dimension mismatch | Array length != dimensions parameter |
| `INVALID_DIMENSION` | 400 | Unsupported dimension | Dimension not in {384, 768, 1024, 1536} |
| `EMPTY_VECTOR` | 400 | Empty vector array | vector_embedding is empty |
| `DIMENSION_CHANGE_NOT_ALLOWED` | 400 | Dimension change on update | Cannot change dimensions during upsert |
| `INVALID_TIMESTAMP` | 422 | Invalid timestamp format | Timestamp not ISO8601 |
| `IMMUTABLE_RECORD` | 403 | Record is immutable | Attempted update/delete on append-only table |
| `DUPLICATE_AGENT_DID` | 409 | Agent DID already exists | Attempted to create agent with existing DID |

**Code Reference:** `/backend/app/core/errors.py`, `/backend/app/schemas/errors.py`

### 4.3 HTTP Status Code Guarantees

**Guarantee:** HTTP status codes follow RESTful conventions consistently:

| Status Code | Meaning | When Used |
|-------------|---------|-----------|
| 200 | OK | Successful GET/search operations |
| 201 | Created | Successful POST/create operations |
| 400 | Bad Request | Invalid request data (validation failure) |
| 401 | Unauthorized | Authentication failure |
| 403 | Forbidden | Authorization failure or immutable record violation |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists (duplicate) |
| 422 | Unprocessable Entity | Semantic validation failure |
| 429 | Too Many Requests | Rate limit or quota exceeded |
| 500 | Internal Server Error | Unexpected server error |

**Validation Errors Use 422:** Per DX Contract, semantic validation errors (invalid model, invalid timestamp, etc.) use HTTP 422, not 400.

**Code Reference:** `/backend/app/core/errors.py`

### 4.4 Validation Error Format

**Guarantee:** Validation errors (422) include additional context in `detail` field.

**Example:**
```json
{
  "detail": "Vector dimension mismatch: declared dimensions=384, but vector_embedding has 512 elements. Array length must match dimensions parameter exactly.",
  "error_code": "DIMENSION_MISMATCH"
}
```

**Code Reference:** `/backend/app/core/dimension_validator.py:95-138`

### 4.5 Error Message Clarity

**Guarantee:** Error messages include:
- What went wrong
- Why it's wrong
- What the correct format/value should be
- Examples when applicable

**Example - Timestamp Error:**
```json
{
  "detail": "Invalid timestamp format. Expected ISO8601 format (RFC 3339). Valid examples: '2026-01-10T12:34:56Z', '2026-01-10T12:34:56.789Z', '2026-01-10T12:34:56+00:00', '2026-01-10T12:34:56-05:00'",
  "error_code": "INVALID_TIMESTAMP"
}
```

**Code Reference:** `/backend/app/core/timestamp_validator.py:310-321`

---

## §5: Data Consistency & Validation Rules

### 5.1 Dimension Validation Contract

**Guarantee:** Vector dimensions are strictly validated with deterministic behavior.

**Supported Dimensions:** ONLY `384`, `768`, `1024`, `1536`

**Validation Rules:**
1. `dimensions` parameter MUST be one of the supported values
2. `vector_embedding` array length MUST equal `dimensions` parameter EXACTLY
3. Validation occurs BEFORE any storage operation
4. Dimension changes during upsert are FORBIDDEN

**Code Reference:** `/backend/app/core/dimension_validator.py`

**Example - Valid:**
```json
{
  "vector_embedding": [0.1, 0.2, 0.3, ...],  // 384 elements
  "dimensions": 384
}
```

**Example - Invalid:**
```json
{
  "vector_embedding": [0.1, 0.2, 0.3, ...],  // 512 elements
  "dimensions": 384  // MISMATCH! Returns 400 DIMENSION_MISMATCH
}
```

**Error Response:**
```json
{
  "detail": "Vector dimension mismatch: declared dimensions=384, but vector_embedding has 512 elements. Array length must match dimensions parameter exactly.",
  "error_code": "DIMENSION_MISMATCH"
}
```

### 5.2 Embedding Model Guarantee

**Guarantee:** Default embedding model is **PERMANENTLY** `BAAI/bge-small-en-v1.5` (384 dimensions).

**What This Means:**
- When `model` parameter is omitted, `BAAI/bge-small-en-v1.5` is used
- This default will NEVER change in v1
- Response ALWAYS indicates which model was used (even if default)
- Model behavior is deterministic (same input → same output)

**Code Reference:** `/backend/app/core/embedding_models.py:8`

**Example:**
```bash
# Request WITHOUT model parameter
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -d '{"text": "test"}' \
  https://api.ainative.studio/v1/public/embeddings/generate

# Response ALWAYS shows which model was used
{
  "embedding": [...],
  "model": "BAAI/bge-small-en-v1.5",  // GUARANTEED: Default model
  "dimensions": 384,                   // GUARANTEED: 384 for default model
  "text": "test",
  "processing_time_ms": 45
}
```

### 5.3 Supported Models Contract

**Guarantee:** Supported models and their dimensions are documented and stable:

| Model | Dimensions | Description |
|-------|-----------|-------------|
| `BAAI/bge-small-en-v1.5` | 384 | Default - lightweight English model |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Alternative 384-dim model |
| `BAAI/bge-base-en-v1.5` | 768 | Higher quality embeddings |
| `sentence-transformers/all-mpnet-base-v2` | 768 | Alternative 768-dim model |
| `BAAI/bge-large-en-v1.5` | 1024 | Highest quality |
| `OpenAI text-embedding-ada-002` | 1536 | OpenAI compatibility |

**Model Validation:**
- Unsupported model names return 422 with `MODEL_NOT_FOUND` error code
- Model names are case-sensitive
- Model parameter is ALWAYS optional (defaults to `BAAI/bge-small-en-v1.5`)

**Code Reference:** `/backend/app/core/embedding_models.py:11-67`

### 5.4 Namespace Validation Contract

**Guarantee:** Namespace names are validated with these rules:

**Allowed Characters:**
- Alphanumeric: `a-z`, `A-Z`, `0-9`
- Hyphens: `-`
- Underscores: `_`
- Dots: `.`

**Constraints:**
- Maximum length: 128 characters
- Cannot be empty or whitespace-only
- Case-sensitive (`MyNamespace` ≠ `mynamespace`)
- No path traversal (`../`, `./`, etc.)

**Code Reference:** `/backend/app/services/vector_store_service.py:66-86`

**Valid Namespaces:**
```python
"agent_1_memory"        # ✓
"production-env"        # ✓
"customer_123"          # ✓
"test.namespace.v2"     # ✓
```

**Invalid Namespaces:**
```python
"has spaces"            # ✗ Contains space
"has/slash"             # ✗ Contains /
"../parent"             # ✗ Path traversal
""                      # ✗ Empty
"   "                   # ✗ Whitespace only
"a" * 129               # ✗ Too long
```

**Error Response:**
```json
{
  "detail": "Namespace can only contain alphanumeric characters, hyphens, underscores, and dots",
  "error_code": "INVALID_NAMESPACE"
}
```

### 5.5 Default Values Contract

**Guarantee:** Default values are applied consistently when optional parameters are omitted:

| Parameter | Default Value | Context |
|-----------|---------------|---------|
| `model` | `BAAI/bge-small-en-v1.5` | Embedding generation |
| `namespace` | `"default"` | Vector storage/search |
| `top_k` | `10` | Search operations |
| `similarity_threshold` | `0.0` | Search operations |
| `upsert` | `false` | Embed-and-store |
| `include_metadata` | `true` | Search responses |
| `include_embeddings` | `false` | Search responses |

**Code Reference:** Schema definitions in `/backend/app/schemas/`

---

## §6: Namespace & Scoping Semantics

### 6.1 Namespace Isolation Guarantee

**Guarantee:** Namespaces provide **COMPLETE ISOLATION** for vector storage and retrieval.

**Isolation Rules:**
1. Vectors stored in namespace A are **INVISIBLE** to namespace B
2. Search operations in namespace A will **NEVER** return vectors from namespace B
3. Same `vector_id` can exist in different namespaces without conflict
4. Default namespace (`"default"`) is isolated from all named namespaces

**Code Reference:** `/backend/app/services/vector_store_service.py:208-275`

**Example:**
```python
# Store vector in namespace "agent_1"
store_vector(text="Agent 1 memory", namespace="agent_1")

# Search in namespace "agent_2"
results = search_vectors(query="Agent 1 memory", namespace="agent_2")

# GUARANTEED: results will be EMPTY
assert len(results) == 0  # Namespace isolation enforced
```

**Why This Matters:** Multi-agent systems require guaranteed isolation to prevent memory contamination between agents. Compliance scenarios require strict data segregation.

### 6.2 Default Namespace Behavior

**Guarantee:** When `namespace` parameter is omitted or `null`, the `"default"` namespace is used.

**Equivalence:**
```python
# These are IDENTICAL
store_vector(text="test")
store_vector(text="test", namespace="default")
store_vector(text="test", namespace=None)
```

**Code Reference:** `/backend/app/services/vector_store_service.py:54-67`

### 6.3 Namespace Scoping in Search

**Guarantee:** Search operations are **STRICTLY SCOPED** to the specified namespace.

**Search Behavior:**
- `namespace` parameter in search request determines which namespace is searched
- Results ONLY include vectors from that namespace
- Vectors from other namespaces are never returned
- Empty results if namespace doesn't exist (not an error)

**Example:**
```python
# Store in multiple namespaces
store_vector(text="Compliance check", namespace="compliance_agent")
store_vector(text="Risk assessment", namespace="risk_agent")

# Search in specific namespace
results = search_vectors(query="check", namespace="compliance_agent")

# GUARANTEED: Only "Compliance check" is returned
# "Risk assessment" is INVISIBLE to this search
assert len(results) == 1
assert results[0]["namespace"] == "compliance_agent"
```

**Code Reference:** `/backend/app/services/vector_store_service.py:262-276`

### 6.4 Namespace in Response

**Guarantee:** All vector operation responses include `namespace` field confirming the namespace used.

**Example:**
```json
{
  "vector_id": "vec_abc123",
  "namespace": "agent_1_memory",  // GUARANTEED: Always present
  "dimensions": 384,
  ...
}
```

### 6.5 Namespace Best Practices

**Recommended Patterns:**
- Agent isolation: `agent_{agent_id}_memory`
- Environment separation: `prod`, `staging`, `dev`
- Tenant separation: `customer_{customer_id}`
- Feature testing: `feature_{feature_name}`

**Anti-Patterns:**
- Using user input directly as namespace (security risk)
- Creating thousands of namespaces (performance impact)
- Using namespaces for fine-grained filtering (use metadata instead)

---

## §7: Embedding & Vector Operations Contract

### 7.1 Embedding Determinism Guarantee

**Guarantee:** Embedding generation is **DETERMINISTIC** for the same model and input.

**What This Means:**
- Same `text` + same `model` → same `embedding` (every time)
- Embedding values are stable and reproducible
- No random seed or non-deterministic operations
- Replay guarantees for compliance and debugging

**Code Reference:** `/backend/app/services/embedding_service.py`

**Example:**
```python
# Generate embedding twice
result1 = generate_embedding(text="test", model="BAAI/bge-small-en-v1.5")
result2 = generate_embedding(text="test", model="BAAI/bge-small-en-v1.5")

# GUARANTEED: Embeddings are identical
assert result1["embedding"] == result2["embedding"]
```

**Why This Matters:** Regulatory compliance requires reproducible results. Debugging requires deterministic behavior. Agent workflows require predictable outputs.

### 7.2 Vector Upsert Semantics

**Guarantee:** Vector upsert behavior is deterministic based on `vector_id` and `upsert` flag.

**Behavior Matrix:**

| Scenario | `vector_id` | `upsert` | Result |
|----------|-------------|----------|--------|
| New vector, no ID | Not provided | `false` | ID auto-generated, vector created |
| New vector, with ID | Provided, doesn't exist | `false` | Vector created with provided ID |
| Update vector | Provided, exists | `true` | Vector updated, preserves `created_at` |
| Duplicate without upsert | Provided, exists | `false` | Error: Vector ID already exists |
| New with upsert | Provided, doesn't exist | `true` | Vector created (upsert allows create) |

**Code Reference:** `/backend/app/services/vector_store_service.py:102-206`

**Example - Create:**
```python
result = upsert_vector(
    vector_embedding=[...],
    dimensions=384,
    document="test",
    vector_id="vec_123",
    upsert=False
)
assert result["created"] == True
```

**Example - Update:**
```python
result = upsert_vector(
    vector_embedding=[...],
    dimensions=384,
    document="updated test",
    vector_id="vec_123",
    upsert=True  # Must be True to update existing
)
assert result["created"] == False  # False = updated
```

### 7.3 Metadata Storage Guarantee

**Guarantee:** Metadata is stored as-is and returned exactly as provided.

**Metadata Rules:**
- Must be valid JSON object (dictionary)
- No maximum size limit (within reasonable bounds)
- All JSON types supported: string, number, boolean, array, object, null
- Nested objects and arrays supported
- Metadata is OPTIONAL (can be omitted or null)

**Code Reference:** `/backend/app/services/vector_store_service.py:167-177`

**Example:**
```python
# Store with complex metadata
metadata = {
    "agent_id": "did:ethr:0xabc123",
    "task": "compliance_check",
    "passed": True,
    "risk_score": 0.15,
    "tags": ["fintech", "compliance", "automated"],
    "context": {
        "transaction_id": "tx_789",
        "amount": 10000.50
    }
}

result = store_vector(..., metadata=metadata)

# GUARANTEED: Metadata returned exactly as stored
assert result["metadata"] == metadata
```

### 7.4 Search Ranking Guarantee

**Guarantee:** Search results are ALWAYS sorted by similarity score in descending order.

**Ranking Rules:**
1. Results sorted by `similarity` score (highest first)
2. Ties resolved by storage order (oldest first)
3. `top_k` limit applied AFTER sorting
4. `similarity_threshold` filter applied BEFORE sorting

**Code Reference:** `/backend/app/services/vector_store_service.py:323-325`

**Example:**
```python
results = search_vectors(query="test", top_k=5)

# GUARANTEED: Results are sorted by similarity descending
for i in range(len(results) - 1):
    assert results[i]["similarity"] >= results[i+1]["similarity"]
```

### 7.5 Top-K Guarantee

**Guarantee:** `top_k` parameter limits results to exactly K or fewer vectors.

**Behavior:**
- `top_k` range: 1-100 (validated)
- Returns UP TO `top_k` results (may be fewer if not enough vectors match)
- Applied AFTER similarity threshold filter
- Default: 10 if not specified

**Code Reference:** `/backend/app/schemas/embeddings.py:385-395`

**Example:**
```python
# Request top 5 results
results = search_vectors(query="test", top_k=5)

# GUARANTEED: Never more than 5 results
assert len(results) <= 5
```

### 7.6 Similarity Threshold Guarantee

**Guarantee:** `similarity_threshold` parameter filters results by minimum similarity score.

**Behavior:**
- Range: 0.0-1.0 (validated)
- Only returns vectors with `similarity >= similarity_threshold`
- Applied BEFORE `top_k` limit
- Default: 0.0 (no filtering)

**Code Reference:** `/backend/app/services/vector_store_service.py:303-320`

**Example:**
```python
# Only return highly similar results
results = search_vectors(query="test", similarity_threshold=0.8)

# GUARANTEED: All results have similarity >= 0.8
for result in results:
    assert result["similarity"] >= 0.8
```

### 7.7 Metadata Filtering Guarantee

**Guarantee:** Metadata filters are applied AFTER similarity search to refine results.

**Supported Operators:**

| Operator | Syntax | Example | Meaning |
|----------|--------|---------|---------|
| Equals | `{"field": value}` | `{"status": "active"}` | Exact match |
| In list | `{"field": {"$in": [...]}}` | `{"category": {"$in": ["A", "B"]}}` | Value in list |
| Contains | `{"field": {"$contains": value}}` | `{"tags": {"$contains": "urgent"}}` | Array contains value |
| Greater than | `{"field": {"$gt": value}}` | `{"score": {"$gt": 0.8}}` | Numeric > |
| Greater or equal | `{"field": {"$gte": value}}` | `{"score": {"$gte": 0.8}}` | Numeric >= |
| Less than | `{"field": {"$lt": value}}` | `{"risk": {"$lt": 0.5}}` | Numeric < |
| Less or equal | `{"field": {"$lte": value}}` | `{"risk": {"$lte": 0.5}}` | Numeric <= |
| Exists | `{"field": {"$exists": true}}` | `{"optional_field": {"$exists": true}}` | Field present |
| Not equals | `{"field": {"$not_equals": value}}` | `{"status": {"$not_equals": "archived"}}` | Not equal |

**Code Reference:** `/backend/app/services/metadata_filter.py`

**Example:**
```python
results = search_vectors(
    query="compliance",
    metadata_filter={
        "agent_id": "compliance_agent",
        "risk_score": {"$lte": 0.5},
        "tags": {"$contains": "fintech"}
    }
)

# GUARANTEED: All results match ALL filter criteria
```

### 7.8 Conditional Field Inclusion Guarantee

**Guarantee:** Response fields can be toggled to optimize response size.

**Toggleable Fields:**

| Parameter | Default | Controls | Use Case |
|-----------|---------|----------|----------|
| `include_metadata` | `true` | Metadata in results | Set false when metadata not needed |
| `include_embeddings` | `false` | Embedding vectors | Set true only for re-ranking or analysis |

**Code Reference:** `/backend/app/schemas/embeddings.py:409-423`

**Example:**
```python
# Minimal response (no metadata, no embeddings)
results = search_vectors(
    query="test",
    include_metadata=False,
    include_embeddings=False
)

# GUARANTEED: metadata and embedding fields are absent
for result in results:
    assert "metadata" not in result
    assert "embedding" not in result
```

**Why This Matters:** Including embeddings increases response size by 1000x (384-1536 floats per result). This toggle enables bandwidth optimization.

---

## §8: Database Operations Guarantees

### 8.1 Endpoint Prefix Requirement

**Guarantee:** All database operations require `/database/` prefix in URL path.

**Affected Operations:**
- Vector operations: `/v1/public/{project_id}/database/vectors/*`
- Embedding storage: `/v1/public/{project_id}/database/embeddings/*`
- Event operations: `/v1/public/{project_id}/database/events/*`
- Agent memory: `/v1/public/{project_id}/database/agent_memory/*`
- Compliance events: `/v1/public/{project_id}/database/compliance_events/*`

**Code Reference:** Route definitions in `/backend/app/api/`

**Example:**
```bash
# CORRECT
POST /v1/public/proj_123/database/vectors/upsert

# INCORRECT - Returns 404
POST /v1/public/proj_123/vectors/upsert
```

**Why This Matters:** Separates data plane from control plane. Makes API structure predictable. Enables future routing optimizations.

### 8.2 Project ID Validation

**Guarantee:** All database operations validate `project_id` from URL path.

**Validation Rules:**
- Project must exist
- User must have access to project
- Returns 404 `PROJECT_NOT_FOUND` if invalid

**Code Reference:** `/backend/app/core/errors.py:78-95`

### 8.3 Data Persistence Guarantee

**Guarantee:** All stored data is durable within the scope of the current MVP.

**Current Scope:** In-memory storage (MVP demo)
**Future Scope:** Persistent database (production)

**What This Means:**
- Data persists for the lifetime of the API server process
- Server restart clears data (MVP limitation)
- Production version will use durable storage

**Code Reference:** `/backend/app/services/vector_store_service.py:49-51`

---

## §9: Versioning & Breaking Changes Policy

### 9.1 API Versioning Scheme

**Guarantee:** ZeroDB uses **URL-based versioning** with semantic versioning semantics.

**Current Version:** `v1` (all endpoints under `/v1/public/`)

**Version Format:** `/v{major}/` where major version is an integer

**Example Versions:**
- `/v1/public/projects` (current)
- `/v2/public/projects` (future, if breaking changes needed)

### 9.2 What Constitutes a Breaking Change

**Breaking Changes** (require major version bump):
- Removing a required field from request
- Removing a field from response
- Changing field type (string → number)
- Changing field semantics (ID format change)
- Changing error codes for existing errors
- Removing an endpoint
- Changing default values
- Changing authentication requirements

**Non-Breaking Changes** (allowed in v1):
- Adding new optional request fields
- Adding new fields to response
- Adding new endpoints
- Adding new error codes (for new scenarios)
- Improving error messages (keeping same error code)
- Performance improvements
- Bug fixes

### 9.3 Backward Compatibility Promise

**Guarantee:** Within v1, all changes are backward compatible.

**What This Means:**
- Code written against v1 today will continue to work
- New fields may appear in responses (clients should ignore unknown fields)
- Error codes for existing scenarios will not change
- Default values will not change

**Example - Safe Evolution:**
```json
// Current response
{
  "vector_id": "vec_123",
  "dimensions": 384
}

// Future response (backward compatible)
{
  "vector_id": "vec_123",
  "dimensions": 384,
  "storage_tier": "standard"  // New field - old clients ignore it
}
```

### 9.4 Deprecation Policy

**Guarantee:** Deprecated features will be supported for AT LEAST 12 months after deprecation notice.

**Deprecation Process:**
1. Feature marked as deprecated in documentation
2. Response headers include `X-Deprecated-Endpoint: true`
3. Minimum 12-month support period
4. Removal only in next major version (v2)

**Example:**
```http
HTTP/1.1 200 OK
X-Deprecated-Endpoint: true
X-Deprecation-Date: 2026-06-01
X-Sunset-Date: 2027-06-01
X-Replacement-Endpoint: /v2/public/embeddings/generate
```

### 9.5 Version Transition Period

**Guarantee:** When v2 is released, v1 will be supported for AT LEAST 12 months.

**Transition Plan:**
- v2 released alongside v1 (parallel operation)
- v1 marked as deprecated
- 12-month transition period
- v1 sunset after transition period

---

## §10: Performance & Rate Limiting Expectations

### 10.1 Processing Time Observability

**Guarantee:** All operations return `processing_time_ms` for observability.

**Measurement Scope:**
- Includes: Request parsing, validation, business logic, response serialization
- Excludes: Network latency, client-side processing

**Code Reference:** All endpoint implementations track processing time

### 10.2 Rate Limiting (Future)

**Current State:** No rate limiting in MVP

**Future Guarantee:** When rate limiting is implemented:
- Limits will be documented per tier
- Rate limit headers will be included in responses
- 429 status code for exceeded limits
- Error code: `RATE_LIMIT_EXCEEDED`

**Example Future Headers:**
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1641820800
```

### 10.3 Quota Management

**Guarantee:** Project limits are enforced based on user tier.

**Current Limits:**

| Tier | Max Projects |
|------|-------------|
| `free` | 5 |
| `pro` | 50 |
| `enterprise` | Unlimited |

**Code Reference:** `/backend/app/core/config.py`

**Enforcement:**
- Project creation returns 429 `PROJECT_LIMIT_EXCEEDED` when limit reached
- Error response includes current count and limit

**Example:**
```json
{
  "detail": "Project limit exceeded for tier 'free'. Current projects: 5/5.",
  "error_code": "PROJECT_LIMIT_EXCEEDED"
}
```

### 10.4 Performance Expectations

**Guarantee:** Target performance metrics for common operations:

| Operation | Target P95 | Target P99 |
|-----------|-----------|-----------|
| Embedding generation | < 100ms | < 200ms |
| Vector search | < 50ms | < 100ms |
| Vector upsert | < 20ms | < 50ms |
| List projects | < 10ms | < 20ms |

**Note:** These are targets, not guarantees. Actual performance depends on deployment environment.

---

## §11: Agent & Compliance Guarantees

### 11.1 Agent Identity Contract

**Guarantee:** Agent identities are based on Decentralized Identifiers (DIDs).

**DID Format:** `did:ethr:0x...` or `did:key:z6Mk...`

**Requirements:**
- Agent DID must be unique within a project
- Duplicate DID creation returns 409 `DUPLICATE_AGENT_DID`
- DID is immutable after creation

**Code Reference:** `/backend/app/core/errors.py:222-241`

**Example:**
```python
# Create agent with DID
create_agent(
    did="did:ethr:0xabc123",
    name="ComplianceAgent",
    project_id="proj_123"
)

# Attempt duplicate - FAILS
create_agent(
    did="did:ethr:0xabc123",  # Already exists
    name="AnotherAgent",
    project_id="proj_123"
)
# Returns: 409 DUPLICATE_AGENT_DID
```

### 11.2 Agent Memory Isolation

**Guarantee:** Agent memory is scoped by namespace and agent_id.

**Best Practice:** Use namespace pattern `agent_{agent_id}_memory`

**Example:**
```python
# Agent 1's memory (isolated)
store_memory(
    text="Compliance check passed",
    namespace="agent_compliance_123_memory",
    metadata={"agent_id": "compliance_123"}
)

# Agent 2's memory (isolated)
store_memory(
    text="Risk assessment completed",
    namespace="agent_risk_456_memory",
    metadata={"agent_id": "risk_456"}
)
```

### 11.3 Compliance Event Auditability

**Guarantee:** Compliance events are stored in append-only table for audit trail.

**Event Fields:**
- `event_id`: Unique identifier
- `agent_id`: Agent that triggered event (optional)
- `event_type`: Type of compliance event
- `timestamp`: ISO8601 timestamp
- `event_data`: Event payload (JSON)
- `created_at`: Immutable creation timestamp

**Code Reference:** `/backend/app/models/event.py`

### 11.4 Workflow Replayability

**Guarantee:** All operations include sufficient metadata for workflow replay.

**Replay Requirements:**
- Deterministic embedding generation (same input → same output)
- Immutable audit trail (append-only tables)
- Timestamp tracking (ISO8601 format)
- Event ordering (creation order preserved)

**Why This Matters:** Regulatory compliance requires ability to replay agent decisions and prove correct behavior.

---

## §12: Append-Only & Non-Repudiation Contract

### 12.1 Immutable Tables

**Guarantee:** The following tables are **APPEND-ONLY** (create and read only, no update or delete).

**Protected Tables:**

| Table | Purpose | Why Immutable |
|-------|---------|---------------|
| `agents` | Agent registration | Agent identity is forensically significant |
| `agent_memory` | Agent recall data | Learning history must be reproducible |
| `compliance_events` | Regulatory audit trail | Compliance events are legal records |
| `x402_requests` | Payment transactions | Financial transactions require non-repudiation |

**Code Reference:** `/backend/app/core/errors.py:243-290`

### 12.2 Blocked Operations

**Guarantee:** Update and delete operations on append-only tables return 403 `IMMUTABLE_RECORD`.

**Blocked HTTP Methods:**
- `PUT` (full update)
- `PATCH` (partial update)
- `DELETE` (deletion)

**Allowed HTTP Methods:**
- `GET` (read)
- `POST` (create)

**Example:**
```bash
# ALLOWED - Create agent
POST /v1/public/{project_id}/database/agents

# ALLOWED - Read agent
GET /v1/public/{project_id}/database/agents/{agent_id}

# BLOCKED - Update agent (returns 403)
PUT /v1/public/{project_id}/database/agents/{agent_id}

# BLOCKED - Delete agent (returns 403)
DELETE /v1/public/{project_id}/database/agents/{agent_id}
```

**Error Response:**
```json
{
  "detail": "Cannot update records in 'agents' table. This table is append-only for audit trail integrity. Per PRD Section 10: Agent records are immutable for non-repudiation.",
  "error_code": "IMMUTABLE_RECORD"
}
```

### 12.3 Workarounds for Updates

**Guarantee:** Since records cannot be updated, use these patterns:

**Pattern 1: Superseding Records**
```python
# Original record
create_record({
    "id": "config_v1",
    "setting": "value_old"
})

# Superseding record (marks previous as superseded)
create_record({
    "id": "config_v2",
    "setting": "value_new",
    "supersedes": "config_v1"
})
```

**Pattern 2: Status Events**
```python
# Status change event instead of updating status field
create_event({
    "event_type": "status_change",
    "entity_id": "agent_123",
    "previous_status": "active",
    "new_status": "suspended",
    "reason": "Manual suspension by admin"
})
```

**Pattern 3: Correction Records**
```python
# Correction record for data errors
create_event({
    "event_type": "correction",
    "corrects": "event_789",
    "reason": "Data entry error",
    "corrected_values": {
        "amount": 100.00
    }
})
```

### 12.4 Non-Repudiation Guarantee

**Guarantee:** Immutable tables ensure non-repudiation:

- Records cannot be altered after creation
- Deletion is impossible (cannot destroy evidence)
- Audit trail is tamper-evident
- All changes require new records (full history preserved)

**Why This Matters:**
- Financial regulations require tamper-proof audit trails
- Agent decision-making must be forensically reconstructable
- Compliance investigations require complete, unalterable history

### 12.5 Response Metadata

**Guarantee:** Responses from append-only tables include immutability indicators:

```json
{
  "id": "agent_123",
  "did": "did:key:z6Mk...",
  "name": "ComplianceAgent",
  "metadata": {
    "immutable": true,
    "append_only": true,
    "prd_reference": "PRD Section 10 (Non-repudiation)"
  }
}
```

**Fields:**
- `immutable`: Always `true` for protected tables
- `append_only`: Always `true` for protected tables
- `prd_reference`: Reference to specification

**Code Reference:** Documentation in `/docs/api/APPEND_ONLY_GUARANTEE.md`

---

## Contract Enforcement & Validation

### How This Contract Is Enforced

**1. Automated Testing**
- 100+ test cases verify contract compliance
- Tests are run on every code change
- Contract violations break the build

**Test Coverage:**
- Authentication & authorization: 15+ tests
- Error handling: 20+ tests
- Dimension validation: 10+ tests
- Namespace isolation: 8+ tests
- Metadata filtering: 6+ tests
- Timestamp validation: 5+ tests
- Append-only enforcement: 4+ tests

**Test Locations:**
- `/backend/app/tests/test_*.py`
- `/tests/test_*.py`

**2. Schema Validation**
- Pydantic schemas enforce request/response structure
- Type checking prevents invalid data
- Validation errors return 422 with clear messages

**Schema Locations:**
- `/backend/app/schemas/*.py`

**3. Middleware Enforcement**
- Authentication middleware enforces auth requirements
- Immutability middleware blocks updates to append-only tables
- Error handling middleware ensures consistent error format

**Middleware Locations:**
- `/backend/app/middleware/*.py`

**4. Code Reviews**
- All changes reviewed for contract compliance
- Contract violations rejected in PR review
- Breaking changes require explicit approval and versioning

### Contract Violation Response

**If the API violates this contract:**

1. **Report:** File a GitHub issue with `contract-violation` label
2. **Priority:** Contract violations are P0 bugs
3. **Timeline:** Fix within 24-48 hours
4. **Communication:** Users notified via status page and API changelog
5. **Compensation:** For paid tiers, service credits for material violations

### Contract Updates

**How This Contract Can Change:**

1. **Additions:** New guarantees can be added (never removed)
2. **Clarifications:** Ambiguous language can be clarified
3. **Examples:** More examples can be added
4. **Breaking Changes:** Require new major version (v2, v3, etc.)

**Update Process:**
1. Proposed changes documented in GitHub issue
2. Community feedback period (minimum 30 days)
3. Approval by maintainers
4. Update published with version number
5. Notification to all registered users

---

## Summary of Key Invariants

| Category | Key Invariant | Enforcement |
|----------|---------------|-------------|
| **Authentication** | All `/v1/public/*` endpoints require X-API-Key or JWT | Middleware |
| **Error Format** | All errors return `{detail, error_code}` | Error handlers |
| **Dimensions** | Only {384, 768, 1024, 1536} supported | Schema validation |
| **Default Model** | `BAAI/bge-small-en-v1.5` when model omitted | Service layer |
| **Namespace Isolation** | Vectors in namespace A invisible to namespace B | Storage layer |
| **Determinism** | Same text+model → same embedding | Embedding service |
| **Timestamps** | ISO8601 format required | Validation |
| **Top-K** | Results limited to top_k or fewer | Search logic |
| **Append-Only** | agents, agent_memory, compliance_events, x402_requests | Middleware |
| **Error Codes** | Stable, documented, never change in v1 | Error definitions |
| **Sorting** | Search results sorted by similarity descending | Search logic |
| **Versioning** | Breaking changes require new major version | API design |

---

## Contact & Support

**Questions about this contract?**
- GitHub Issues: https://github.com/ainative/zerodb/issues
- Documentation: https://docs.ainative.studio/
- Email: support@ainative.studio

**Report contract violations:**
- Label: `contract-violation`
- Priority: P0 (highest)
- SLA: Response within 24 hours

---

**This DX Contract is a living document. Version 1.0.0 published 2026-01-11.**

**© 2026 AINative. All guarantees subject to this contract.**
