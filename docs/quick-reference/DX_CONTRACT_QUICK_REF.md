# DX Contract Quick Reference

**For the complete contract, see:** `/docs/DX_CONTRACT.md`

---

## Authentication (§2)

```bash
# X-API-Key (preferred for server-to-server)
curl -H "X-API-Key: zerodb_sk_your_key" https://api.ainative.studio/v1/public/projects

# JWT Bearer Token (preferred for user-facing apps)
curl -H "Authorization: Bearer eyJhbG..." https://api.ainative.studio/v1/public/projects
```

**Auth Error Codes:**
- Missing/invalid API key → `INVALID_API_KEY` (401)
- Invalid JWT → `INVALID_TOKEN` (401)
- Expired JWT → `TOKEN_EXPIRED` (401)

---

## Error Response Format (§4)

**ALL errors return:**
```json
{
  "detail": "Human-readable message",
  "error_code": "MACHINE_READABLE_CODE"
}
```

**Common Error Codes:**
| Code | Status | Meaning |
|------|--------|---------|
| `INVALID_API_KEY` | 401 | Auth failed |
| `DIMENSION_MISMATCH` | 400 | Vector length ≠ dimensions |
| `INVALID_TIMESTAMP` | 422 | Not ISO8601 |
| `IMMUTABLE_RECORD` | 403 | Update to append-only table |
| `PROJECT_LIMIT_EXCEEDED` | 429 | Quota exceeded |

---

## Dimensions (§5)

**ONLY supported:** `384`, `768`, `1024`, `1536`

```python
# CORRECT
{
  "vector_embedding": [0.1, 0.2, ...],  # 384 elements
  "dimensions": 384
}

# WRONG - Returns DIMENSION_MISMATCH
{
  "vector_embedding": [0.1, 0.2, ...],  # 512 elements
  "dimensions": 384
}
```

---

## Default Embedding Model (§5)

**Default:** `BAAI/bge-small-en-v1.5` (384 dimensions)

**Will NEVER change in v1**

```python
# These are IDENTICAL
{"text": "test"}
{"text": "test", "model": "BAAI/bge-small-en-v1.5"}
```

---

## Namespaces (§6)

**Isolation:** Vectors in namespace A are INVISIBLE to namespace B

```python
# Store in namespace A
store_vector(text="test", namespace="agent_1")

# Search in namespace B
results = search_vectors(query="test", namespace="agent_2")

# GUARANTEED: results = [] (empty)
```

**Default namespace:**
```python
# These are IDENTICAL
store_vector(text="test")
store_vector(text="test", namespace="default")
store_vector(text="test", namespace=None)
```

**Valid namespace characters:** `a-z A-Z 0-9 - _ .` (max 128 chars)

---

## Timestamps (§3)

**ONLY ISO8601 (RFC 3339):**

```python
# VALID
"2026-01-10T12:34:56Z"
"2026-01-10T12:34:56.789Z"
"2026-01-10T12:34:56+00:00"

# INVALID - Returns INVALID_TIMESTAMP
"2026-01-10"           # Missing time
"2026-01-10 12:34:56"  # Space instead of T
"1641820496"           # Unix timestamp
```

---

## Search Guarantees (§7)

**Ranking:** Results ALWAYS sorted by similarity (descending)

**Top-K:** Returns UP TO `top_k` results (1-100, default 10)

**Similarity Threshold:** Only returns vectors with `similarity >= threshold` (0.0-1.0, default 0.0)

**Metadata Filtering:** Applied AFTER similarity search

```python
results = search_vectors(
    query="test",
    top_k=5,                    # Max 5 results
    similarity_threshold=0.8,   # Only >= 0.8 similarity
    metadata_filter={           # Refine results
        "agent_id": "agent_1",
        "score": {"$gte": 0.9}
    }
)
```

---

## Upsert Behavior (§7)

| `vector_id` | `upsert` | Result |
|-------------|----------|--------|
| Not provided | `false` | Create with auto-ID |
| Provided, new | `false` | Create with provided ID |
| Provided, exists | `true` | Update existing |
| Provided, exists | `false` | ERROR: Already exists |

```python
# Create
upsert_vector(..., vector_id="vec_123", upsert=False)
# Returns: created=True

# Update
upsert_vector(..., vector_id="vec_123", upsert=True)
# Returns: created=False
```

---

## Append-Only Tables (§12)

**Immutable tables:**
- `agents`
- `agent_memory`
- `compliance_events`
- `x402_requests`

**Blocked operations:**
- PUT → 403 `IMMUTABLE_RECORD`
- PATCH → 403 `IMMUTABLE_RECORD`
- DELETE → 403 `IMMUTABLE_RECORD`

**Allowed operations:**
- GET ✓
- POST ✓

---

## Endpoint Prefix (§8)

**Database operations require `/database/` prefix:**

```bash
# CORRECT
POST /v1/public/proj_123/database/vectors/upsert

# WRONG - Returns 404
POST /v1/public/proj_123/vectors/upsert
```

---

## Default Values (§5)

| Parameter | Default |
|-----------|---------|
| `model` | `BAAI/bge-small-en-v1.5` |
| `namespace` | `"default"` |
| `top_k` | `10` |
| `similarity_threshold` | `0.0` |
| `upsert` | `false` |
| `include_metadata` | `true` |
| `include_embeddings` | `false` |

---

## Metadata Filtering (§7)

**Supported operators:**

| Operator | Syntax | Example |
|----------|--------|---------|
| Equals | `{"field": value}` | `{"status": "active"}` |
| In | `{"field": {"$in": [...]}}` | `{"category": {"$in": ["A", "B"]}}` |
| Contains | `{"field": {"$contains": val}}` | `{"tags": {"$contains": "urgent"}}` |
| Greater than | `{"field": {"$gt": val}}` | `{"score": {"$gt": 0.8}}` |
| Greater or equal | `{"field": {"$gte": val}}` | `{"score": {"$gte": 0.8}}` |
| Less than | `{"field": {"$lt": val}}` | `{"risk": {"$lt": 0.5}}` |
| Less or equal | `{"field": {"$lte": val}}` | `{"risk": {"$lte": 0.5}}` |
| Exists | `{"field": {"$exists": true}}` | `{"field": {"$exists": true}}` |
| Not equals | `{"field": {"$not_equals": val}}` | `{"status": {"$not_equals": "archived"}}` |

---

## Versioning (§9)

**Breaking changes require new major version (v2, v3, etc.)**

**Non-breaking changes allowed in v1:**
- Adding optional request fields ✓
- Adding response fields ✓
- Adding endpoints ✓
- Improving error messages ✓
- Performance improvements ✓

**Deprecation policy:**
- Minimum 12 months support after deprecation
- Version transition: v1 supported for 12 months after v2 release

---

## Project Limits (§10)

| Tier | Max Projects |
|------|-------------|
| `free` | 5 |
| `pro` | 50 |
| `enterprise` | Unlimited |

**Exceeded limit:** 429 `PROJECT_LIMIT_EXCEEDED`

---

## Performance Targets (§10)

**Not guaranteed, but target P95:**

| Operation | Target |
|-----------|--------|
| Embedding generation | < 100ms |
| Vector search | < 50ms |
| Vector upsert | < 20ms |
| List projects | < 10ms |

**All responses include:** `processing_time_ms` (integer, >= 0)

---

## Contract Violations

**Report:** GitHub issue with `contract-violation` label

**Priority:** P0 (highest)

**SLA:** Fix within 24-48 hours

---

## Full Documentation

**Complete DX Contract:** `/docs/DX_CONTRACT.md`
**Summary:** `/docs/DX_CONTRACT_SUMMARY.md`
**This Quick Ref:** `/docs/quick-reference/DX_CONTRACT_QUICK_REF.md`

---

**Version 1.0.0 | Published 2026-01-11 | © 2026 AINative**
