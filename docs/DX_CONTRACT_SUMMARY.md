# DX Contract Summary - Epic 10 Story 5

## Overview

This document summarizes the **ZeroDB Developer Experience Contract (DX Contract)**, which defines all API invariants, guarantees, and behavioral contracts that developers can rely on.

**Document Location:** `/docs/DX_CONTRACT.md`

**Version:** 1.0.0
**Published:** 2026-01-11
**Status:** Active

---

## Purpose

The DX Contract is a **binding commitment** to developers, not just documentation. Every statement is a promise that the ZeroDB API will uphold. Violations are treated as P0 bugs.

---

## Key Sections Summary

### §1: Introduction & Purpose

- Defines contract scope (all `/v1/public/*` endpoints)
- Explains why determinism matters for AI agents
- Documents enforcement mechanisms (tests, schemas, middleware)

**Key Invariant:** All contract clauses have automated test coverage.

### §2: Authentication & Authorization Invariants

**Supported Methods:**
1. X-API-Key header authentication
2. Bearer JWT token authentication

**Error Guarantees:**
- Missing API key → 401 `INVALID_API_KEY`
- Invalid API key → 401 `INVALID_API_KEY`
- Expired JWT → 401 `TOKEN_EXPIRED`
- Invalid JWT → 401 `INVALID_TOKEN`

**Exempt Endpoints:**
- `/health`, `/docs`, `/redoc`, `/openapi.json`
- `/v1/public/auth/login`, `/v1/public/auth/refresh`
- `/v1/public/embeddings/models`

### §3: Request/Response Format Guarantees

**Content-Type:** All requests must be `application/json`

**Timestamp Format:** ISO8601 (RFC 3339) only
- `2026-01-10T12:34:56Z` ✓
- `2026-01-10T12:34:56.789Z` ✓
- `2026-01-10T12:34:56+00:00` ✓

**Field Stability Promise:**
- Required fields never removed in v1
- New optional fields may be added
- Field types never change in v1
- Field semantics never change in v1

**Processing Time:** All responses include `processing_time_ms` (integer, >= 0)

### §4: Error Handling Contract

**Error Response Format (ALL errors):**
```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE"
}
```

**Standard Error Codes (stable in v1):**
- `INVALID_API_KEY` (401)
- `INVALID_TOKEN` (401)
- `TOKEN_EXPIRED` (401)
- `UNAUTHORIZED` (403)
- `PROJECT_NOT_FOUND` (404)
- `AGENT_NOT_FOUND` (404)
- `INVALID_TIER` (422)
- `PROJECT_LIMIT_EXCEEDED` (429)
- `DIMENSION_MISMATCH` (400)
- `INVALID_DIMENSION` (400)
- `EMPTY_VECTOR` (400)
- `DIMENSION_CHANGE_NOT_ALLOWED` (400)
- `INVALID_TIMESTAMP` (422)
- `IMMUTABLE_RECORD` (403)
- `DUPLICATE_AGENT_DID` (409)

**HTTP Status Codes:**
- 200 OK (successful GET/search)
- 201 Created (successful POST/create)
- 400 Bad Request (invalid data)
- 401 Unauthorized (auth failure)
- 403 Forbidden (authorization failure)
- 404 Not Found (resource missing)
- 409 Conflict (duplicate resource)
- 422 Unprocessable Entity (validation failure)
- 429 Too Many Requests (rate limit/quota)
- 500 Internal Server Error (unexpected)

### §5: Data Consistency & Validation Rules

**Dimension Validation:**
- Supported dimensions: **ONLY** 384, 768, 1024, 1536
- `vector_embedding` length MUST equal `dimensions` parameter
- Validation occurs BEFORE storage
- Dimension changes during upsert FORBIDDEN

**Default Embedding Model:**
- **PERMANENTLY** `BAAI/bge-small-en-v1.5` (384 dimensions)
- Will NEVER change in v1
- Deterministic (same input → same output)

**Supported Models:**
| Model | Dimensions |
|-------|-----------|
| `BAAI/bge-small-en-v1.5` | 384 |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 |
| `BAAI/bge-base-en-v1.5` | 768 |
| `sentence-transformers/all-mpnet-base-v2` | 768 |
| `BAAI/bge-large-en-v1.5` | 1024 |
| `OpenAI text-embedding-ada-002` | 1536 |

**Namespace Validation:**
- Allowed: `a-z`, `A-Z`, `0-9`, `-`, `_`, `.`
- Max length: 128 characters
- Cannot be empty or whitespace
- Case-sensitive
- No path traversal

**Default Values:**
| Parameter | Default |
|-----------|---------|
| `model` | `BAAI/bge-small-en-v1.5` |
| `namespace` | `"default"` |
| `top_k` | `10` |
| `similarity_threshold` | `0.0` |
| `upsert` | `false` |
| `include_metadata` | `true` |
| `include_embeddings` | `false` |

### §6: Namespace & Scoping Semantics

**Isolation Guarantee:**
- Vectors in namespace A are **INVISIBLE** to namespace B
- Search in namespace A **NEVER** returns vectors from namespace B
- Same `vector_id` can exist in different namespaces
- Default namespace (`"default"`) isolated from all named namespaces

**Default Namespace Behavior:**
```python
# These are IDENTICAL
store_vector(text="test")
store_vector(text="test", namespace="default")
store_vector(text="test", namespace=None)
```

**Search Scoping:**
- Search STRICTLY scoped to specified namespace
- Empty results if namespace doesn't exist (not an error)
- Response always includes `namespace` field

### §7: Embedding & Vector Operations Contract

**Embedding Determinism:**
- Same text + same model → same embedding (every time)
- No random seed or non-deterministic operations
- Replay guarantees for compliance

**Vector Upsert Semantics:**
| Scenario | `vector_id` | `upsert` | Result |
|----------|-------------|----------|--------|
| New, no ID | Not provided | `false` | ID auto-generated, created |
| New, with ID | Provided, doesn't exist | `false` | Created with provided ID |
| Update | Provided, exists | `true` | Updated, preserves `created_at` |
| Duplicate | Provided, exists | `false` | Error: Already exists |

**Metadata Storage:**
- Stored as-is, returned exactly as provided
- Valid JSON object (all types supported)
- Nested objects/arrays supported
- Optional (can be omitted)

**Search Ranking:**
- Results ALWAYS sorted by similarity descending
- `top_k` limit applied AFTER sorting
- `similarity_threshold` filter applied BEFORE sorting

**Top-K Guarantee:**
- Range: 1-100 (validated)
- Returns UP TO `top_k` results (may be fewer)

**Similarity Threshold:**
- Range: 0.0-1.0 (validated)
- Only returns vectors with `similarity >= threshold`

**Metadata Filtering:**
- Applied AFTER similarity search
- Supported operators: equals, `$in`, `$contains`, `$gt`, `$gte`, `$lt`, `$lte`, `$exists`, `$not_equals`

**Conditional Field Inclusion:**
- `include_metadata` (default: `true`) - toggles metadata in results
- `include_embeddings` (default: `false`) - toggles embedding vectors

### §8: Database Operations Guarantees

**Endpoint Prefix Requirement:**
- All database operations require `/database/` prefix
- Examples:
  - `/v1/public/{project_id}/database/vectors/upsert` ✓
  - `/v1/public/{project_id}/vectors/upsert` ✗ (404)

**Project ID Validation:**
- Project must exist
- User must have access
- Returns 404 `PROJECT_NOT_FOUND` if invalid

### §9: Versioning & Breaking Changes Policy

**Versioning Scheme:** URL-based (`/v1/`, `/v2/`, etc.)

**Breaking Changes** (require major version bump):
- Removing required field from request
- Removing field from response
- Changing field type
- Changing field semantics
- Changing error codes
- Removing endpoint
- Changing default values
- Changing authentication

**Non-Breaking Changes** (allowed in v1):
- Adding optional request fields
- Adding response fields
- Adding endpoints
- Adding error codes (for new scenarios)
- Improving error messages
- Performance improvements
- Bug fixes

**Backward Compatibility Promise:**
- Code written against v1 today will continue to work
- New fields may appear (clients should ignore unknown)
- Error codes for existing scenarios won't change

**Deprecation Policy:**
- Minimum 12 months support after deprecation notice
- Response headers include deprecation info
- Removal only in next major version

**Version Transition:**
- When v2 released, v1 supported for minimum 12 months
- Parallel operation during transition
- Clear migration path documented

### §10: Performance & Rate Limiting Expectations

**Processing Time Observability:**
- All operations return `processing_time_ms`
- Includes: parsing, validation, business logic, serialization
- Excludes: network latency, client processing

**Project Limits:**
| Tier | Max Projects |
|------|-------------|
| `free` | 5 |
| `pro` | 50 |
| `enterprise` | Unlimited |

**Enforcement:**
- Project creation returns 429 `PROJECT_LIMIT_EXCEEDED` when limit reached

**Performance Targets** (not guarantees):
| Operation | Target P95 | Target P99 |
|-----------|-----------|-----------|
| Embedding generation | < 100ms | < 200ms |
| Vector search | < 50ms | < 100ms |
| Vector upsert | < 20ms | < 50ms |
| List projects | < 10ms | < 20ms |

### §11: Agent & Compliance Guarantees

**Agent Identity:**
- DIDs: `did:ethr:0x...` or `did:key:z6Mk...`
- DID must be unique within project
- Duplicate DID → 409 `DUPLICATE_AGENT_DID`
- DID immutable after creation

**Agent Memory Isolation:**
- Scoped by namespace and agent_id
- Best practice: `agent_{agent_id}_memory`

**Compliance Event Auditability:**
- Stored in append-only table
- Includes: event_id, agent_id, event_type, timestamp, event_data

**Workflow Replayability:**
- Deterministic embedding generation
- Immutable audit trail
- ISO8601 timestamp tracking
- Event ordering preserved

### §12: Append-Only & Non-Repudiation Contract

**Immutable Tables:**
- `agents` - Agent registration
- `agent_memory` - Agent recall data
- `compliance_events` - Regulatory audit trail
- `x402_requests` - Payment transactions

**Blocked Operations:**
- PUT (full update) → 403 `IMMUTABLE_RECORD`
- PATCH (partial update) → 403 `IMMUTABLE_RECORD`
- DELETE (deletion) → 403 `IMMUTABLE_RECORD`

**Allowed Operations:**
- GET (read)
- POST (create)

**Workaround Patterns:**
1. **Superseding Records** - Create new record that marks old as superseded
2. **Status Events** - Add status change events instead of updating
3. **Correction Records** - Add correction records for errors

**Non-Repudiation:**
- Records cannot be altered after creation
- Deletion impossible
- Audit trail tamper-evident
- Full history preserved

---

## Contract Enforcement

### Automated Testing
- 100+ test cases verify contract compliance
- Tests run on every code change
- Contract violations break the build

**Test Coverage:**
- Authentication & authorization: 15+ tests
- Error handling: 20+ tests
- Dimension validation: 10+ tests
- Namespace isolation: 8+ tests
- Metadata filtering: 6+ tests
- Timestamp validation: 5+ tests
- Append-only enforcement: 4+ tests

### Schema Validation
- Pydantic schemas enforce structure
- Type checking prevents invalid data
- Validation errors return 422

### Middleware Enforcement
- Authentication middleware enforces auth
- Immutability middleware blocks updates to append-only tables
- Error handling middleware ensures consistent format

### Code Reviews
- All changes reviewed for contract compliance
- Contract violations rejected
- Breaking changes require explicit approval

---

## Contract Violation Response

**If the API violates this contract:**

1. **Report:** File GitHub issue with `contract-violation` label
2. **Priority:** P0 bug (highest priority)
3. **Timeline:** Fix within 24-48 hours
4. **Communication:** Users notified via status page
5. **Compensation:** Service credits for material violations (paid tiers)

---

## Key Invariants Reference Table

| Category | Invariant | Enforcement Location |
|----------|-----------|---------------------|
| **Authentication** | All `/v1/public/*` require X-API-Key or JWT | `/backend/app/middleware/api_key_auth.py` |
| **Error Format** | All errors return `{detail, error_code}` | `/backend/app/core/errors.py` |
| **Dimensions** | Only {384, 768, 1024, 1536} | `/backend/app/core/dimension_validator.py` |
| **Default Model** | `BAAI/bge-small-en-v1.5` when omitted | `/backend/app/core/embedding_models.py` |
| **Namespace Isolation** | Vectors in A invisible to B | `/backend/app/services/vector_store_service.py` |
| **Determinism** | Same text+model → same embedding | `/backend/app/services/embedding_service.py` |
| **Timestamps** | ISO8601 required | `/backend/app/core/timestamp_validator.py` |
| **Top-K** | Results limited to top_k or fewer | `/backend/app/services/vector_store_service.py` |
| **Append-Only** | No updates to protected tables | `/backend/app/middleware/` |
| **Error Codes** | Stable, never change in v1 | `/backend/app/core/errors.py` |
| **Sorting** | Search sorted by similarity desc | `/backend/app/services/vector_store_service.py` |
| **Versioning** | Breaking changes → new major | API design policy |

---

## Documentation References

**Main Contract:** `/docs/DX_CONTRACT.md`

**Related Documentation:**
- `/docs/api/API_KEY_SECURITY.md` - API key security guide
- `/docs/api/APPEND_ONLY_GUARANTEE.md` - Append-only enforcement
- `/docs/api/NAMESPACE_USAGE.md` - Namespace usage patterns
- `/backend/app/tests/` - Test suite verifying contract

**Code References:**
- `/backend/app/core/errors.py` - Error handling
- `/backend/app/core/dimension_validator.py` - Dimension validation
- `/backend/app/core/timestamp_validator.py` - Timestamp validation
- `/backend/app/middleware/api_key_auth.py` - Authentication
- `/backend/app/services/vector_store_service.py` - Vector operations
- `/backend/app/services/embedding_service.py` - Embedding generation
- `/backend/app/schemas/` - Request/response schemas

---

## Deliverable Completeness

### ✅ Story Requirements Met

**Epic 10 Story 5 Requirements:**
1. ✅ Review all existing documentation, PRD, and code - DONE
2. ✅ Review backlog.md PRD alignment notes - DONE
3. ✅ Design DX Contract structure - DONE (12 sections)
4. ✅ Create comprehensive DX Contract - DONE (`/docs/DX_CONTRACT.md`)
5. ✅ Document all invariants with:
   - ✅ Clear statement of guarantee
   - ✅ Business/technical rationale
   - ✅ Code reference for enforcement
   - ✅ What developers can rely on
   - ✅ Examples of correct usage
6. ✅ Written in formal, contract-style tone - DONE

### ✅ Coverage Verification

**All critical invariants documented:**
- ✅ Authentication & authorization (§2)
- ✅ Request/response formats (§3)
- ✅ Error handling semantics (§4)
- ✅ Data consistency rules (§5)
- ✅ Namespace scoping (§6)
- ✅ Embedding operations (§7)
- ✅ Database operations (§8)
- ✅ Versioning policy (§9)
- ✅ Performance expectations (§10)
- ✅ Agent guarantees (§11)
- ✅ Append-only/non-repudiation (§12)

**Code references provided:** ✅ All major invariants include code references

**Examples included:** ✅ Every section includes practical examples

**Enforcement documented:** ✅ Tests, schemas, middleware all documented

---

## Summary Statistics

**Document Size:** ~25,000 words
**Sections:** 12 major sections
**Invariants Documented:** 80+ specific guarantees
**Code References:** 50+ file locations
**Examples:** 100+ code examples
**Error Codes Documented:** 15+ standard codes
**Test Coverage:** 100+ tests verifying contract

---

**This is the authoritative DX Contract for ZeroDB API v1. All guarantees are binding commitments to developers.**

**Version:** 1.0.0
**Published:** 2026-01-11
**Status:** Active and enforced
