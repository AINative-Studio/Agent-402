# Critical Requirements Reference

**Version:** 1.0
**Last Updated:** 2026-01-11
**Status:** Authoritative
**Scope:** All ZeroDB API endpoints and agent workflows

---

## Purpose

This document catalogs all **critical requirements** that MUST be enforced consistently across the ZeroDB Agent Finance platform. These requirements are derived from:

- **Product Requirements Document (PRD)** - `/prd.md`
- **DX Contract** - `/DX-Contract.md`
- **API Specifications** - `/docs/api/*.md`

Critical requirements represent **hard invariants** that:
1. Are guaranteed not to change without explicit versioning
2. Must be enforced at the code level
3. Must be validated through automated tests
4. Must be clearly documented for developers

---

## Table of Contents

1. [Authentication Requirements](#1-authentication-requirements)
2. [Error Response Format](#2-error-response-format)
3. [Endpoint Prefixing](#3-endpoint-prefixing)
4. [Embedding & Vector Dimensions](#4-embedding--vector-dimensions)
5. [Model Consistency](#5-model-consistency)
6. [Namespace Scoping](#6-namespace-scoping)
7. [Project Status Field](#7-project-status-field)
8. [Append-Only Enforcement](#8-append-only-enforcement)
9. [Timestamp Validation](#9-timestamp-validation)
10. [API Stability Guarantees](#10-api-stability-guarantees)

---

## 1. Authentication Requirements

### 1.1 X-API-Key Header (Mandatory)

**Requirement:**
All `/v1/public/*` endpoints MUST require authentication via the `X-API-Key` header.

**Source:**
- **DX Contract §2:** Authentication
- **PRD §10:** Signed requests + auditability
- **Epic 2, Story 1:** X-API-Key authentication

**Enforcement:**
- **File:** `/backend/app/middleware/api_key_auth.py`
- **Class:** `APIKeyAuthMiddleware`
- **Lines:** 34-225

**Error Response:**
```json
{
  "detail": "Missing X-API-Key header",
  "error_code": "INVALID_API_KEY"
}
```
- **HTTP Status:** 401 Unauthorized
- **Error Code:** `INVALID_API_KEY`

**Test Coverage:**
- **File:** `/backend/app/tests/test_api_key_auth.py`
- **Test:** `test_public_endpoint_requires_api_key`
- **File:** `/backend/app/tests/test_api_key_middleware.py`

**Examples:**

✅ **CORRECT:**
```bash
curl -X GET "https://api.ainative.studio/v1/public/projects" \
  -H "X-API-Key: zerodb_sk_abc123xyz456"
```

❌ **INCORRECT:**
```bash
curl -X GET "https://api.ainative.studio/v1/public/projects"
# Returns: 401 INVALID_API_KEY
```

**Server-Side Only:**
API keys MUST NEVER be used in client-side code. See `/docs/api/API_KEY_SECURITY.md` for details.

---

### 1.2 Invalid API Key Handling

**Requirement:**
All invalid API key scenarios MUST return the same error code for security.

**Scenarios:**
1. Missing `X-API-Key` header
2. Empty API key value
3. Invalid/unknown API key
4. Malformed API key

**Error Response (All Scenarios):**
```json
{
  "detail": "<specific message>",
  "error_code": "INVALID_API_KEY"
}
```

**Enforcement:**
- **File:** `/backend/app/middleware/api_key_auth.py`
- **Method:** `_authenticate_request`
- **Lines:** 130-225

**Test Coverage:**
- **File:** `/backend/app/tests/test_invalid_api_keys.py`
- **File:** `/backend/app/tests/test_invalid_api_key.py`

---

## 2. Error Response Format

### 2.1 Deterministic Error Shape

**Requirement:**
ALL error responses MUST include both `detail` and `error_code` fields.

**Source:**
- **DX Contract §7:** Error Semantics
- **Epic 2, Story 3:** All errors include detail field

**Mandatory Format:**
```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE"
}
```

**Enforcement:**
- **File:** `/backend/app/core/errors.py`
- **Function:** `format_error_response`
- **Lines:** 324-348
- **File:** `/backend/app/schemas/errors.py`
- **Class:** `ErrorResponse`
- **Lines:** 19-50

**Error Code Catalog:**
- **File:** `/backend/app/schemas/errors.py`
- **Class:** `ErrorCodes`
- **Lines:** 116-164

**Test Coverage:**
- **File:** `/backend/app/tests/test_error_detail.py`
- **File:** `/backend/app/tests/test_error_detail_field.py`

**Guarantees:**
1. `detail` field is NEVER null or empty
2. `error_code` field is NEVER null or empty
3. Error codes are stable and documented
4. HTTP status codes are deterministic per error type

---

### 2.2 Validation Errors (HTTP 422)

**Requirement:**
All validation errors MUST return HTTP 422 (Unprocessable Entity).

**Source:**
- **DX Contract §7:** Validation errors use HTTP 422

**Standard Validation Error Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Enforcement:**
- FastAPI automatic validation
- Pydantic schema validation
- Custom validators in `/backend/app/core/dimension_validator.py`

**Examples:**

❌ **Invalid Request:**
```json
{
  "name": ""  // Empty name (validation error)
}
```

**Response (HTTP 422):**
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

---

## 3. Endpoint Prefixing

### 3.1 /database/ Prefix (Mandatory)

**Requirement:**
ALL vector and database operations MUST include `/database/` in the endpoint path.

**Source:**
- **DX Contract §4:** Endpoint Prefixing
- **Epic 6:** Vector Operations API

**Operations Requiring /database/ Prefix:**
- Vector operations: `/v1/public/database/vectors/*`
- Table operations: `/v1/public/database/tables/*`
- File operations: `/v1/public/database/files/*`
- Event operations: `/v1/public/database/events/*`

**Operations NOT Requiring /database/:**
- Projects API: `/v1/public/projects`
- Embeddings generation: `/v1/public/{project_id}/embeddings/generate`
- Embed and store: `/v1/public/{project_id}/embeddings/embed-and-store`
- Semantic search: `/v1/public/{project_id}/embeddings/search`

**Documentation:**
- **File:** `/docs/api/DATABASE_PREFIX_WARNING.md`
- **Comprehensive guide with examples in all major languages**

**Error Response (Missing Prefix):**
```json
{
  "detail": "Not Found"
}
```
- **HTTP Status:** 404 Not Found
- **Reason:** Routing error - endpoint does not exist without prefix

**Examples:**

✅ **CORRECT:**
```bash
POST https://api.ainative.studio/v1/public/database/vectors/upsert
POST https://api.ainative.studio/v1/public/database/tables
GET  https://api.ainative.studio/v1/public/database/vectors/{vector_id}
```

❌ **INCORRECT (Returns 404):**
```bash
POST https://api.ainative.studio/v1/public/vectors/upsert
POST https://api.ainative.studio/v1/public/tables
```

**Enforcement:**
- API gateway routing configuration
- FastAPI route definitions
- **Cannot be bypassed** - this is a routing requirement

**Test Coverage:**
- Integration tests verify correct endpoint paths
- Smoke tests validate routing behavior

---

## 4. Embedding & Vector Dimensions

### 4.1 Default Embedding Model

**Requirement:**
When `model` parameter is omitted, the default model MUST be `BAAI/bge-small-en-v1.5` with **384 dimensions**.

**Source:**
- **DX Contract §3:** Embeddings & Vectors
- **Epic 3:** Embeddings Generate API

**Default Behavior:**
```python
# Request (model omitted)
{
  "texts": ["sample text"]
}

# Guaranteed to use:
# - Model: BAAI/bge-small-en-v1.5
# - Dimensions: 384
```

**Enforcement:**
- **File:** `/backend/app/services/embedding_service.py`
- **Default model constant**

**Test Coverage:**
- **File:** `/backend/app/tests/test_embeddings_default_model.py`

---

### 4.2 Dimension Validation

**Requirement:**
Vector dimension mismatches MUST return HTTP 400 with `DIMENSION_MISMATCH` error code.

**Source:**
- **DX Contract §3:** Dimension mismatches always return DIMENSION_MISMATCH error
- **Issue #28:** Dimension validation

**Supported Dimensions:**
- **384** (BAAI/bge-small-en-v1.5, default)
- **768** (BAAI/bge-base-en-v1.5)
- **1024** (BAAI/bge-large-en-v1.5)
- **1536** (OpenAI text-embedding-ada-002)

**Enforcement:**
- **File:** `/backend/app/core/dimension_validator.py`
- **Constant:** `SUPPORTED_DIMENSIONS` (line 19)
- **Function:** `validate_vector_dimensions` (lines 67-138)

**Error Response:**
```json
{
  "detail": "Vector dimension mismatch: declared dimensions=384, but vector_embedding has 768 elements. Array length must match dimensions parameter exactly.",
  "error_code": "DIMENSION_MISMATCH"
}
```
- **HTTP Status:** 400 Bad Request
- **Error Code:** `DIMENSION_MISMATCH`

**Test Coverage:**
- **File:** `/backend/app/tests/test_dimension_mismatch.py`
- **File:** `/backend/app/tests/test_issue_28_dimension_validation.py`

**Examples:**

❌ **INCORRECT (Dimension Mismatch):**
```json
{
  "vector_embedding": [0.1, 0.2, ...],  // 768 values
  "dimensions": 384,  // Claims 384 but has 768
  "document": "Test"
}
```

**Response (HTTP 400):**
```json
{
  "detail": "Vector dimension mismatch: declared dimensions=384, but vector_embedding has 768 elements.",
  "error_code": "DIMENSION_MISMATCH"
}
```

---

## 5. Model Consistency

### 5.1 Same Model for Store and Search

**Requirement:**
The SAME embedding model MUST be used for both storing vectors and searching within a namespace.

**Source:**
- **DX Contract §3:** Model Consistency Requirement (CRITICAL)
- **Model Consistency Guide:** `/docs/api/MODEL_CONSISTENCY_GUIDE.md`

**Why This Matters:**
Mixing models within the same namespace causes:
- Poor search results (semantic drift)
- Low similarity scores
- Unpredictable behavior

**Best Practices:**
1. Define model as a configuration constant
2. Use separate namespaces for different models
3. Document which model each namespace uses

**Example:**

✅ **CORRECT:**
```python
MODEL = "BAAI/bge-small-en-v1.5"
NAMESPACE = "agent_memory"

# Store
embed_and_store(text="...", model=MODEL, namespace=NAMESPACE)

# Search (use same model)
search(query="...", model=MODEL, namespace=NAMESPACE)
```

❌ **INCORRECT:**
```python
# Store with model A
embed_and_store(text="...", model="BAAI/bge-small-en-v1.5", namespace="docs")

# Search with model B (different model = poor results)
search(query="...", model="BAAI/bge-base-en-v1.5", namespace="docs")
```

**Documentation:**
- **File:** `/docs/api/MODEL_CONSISTENCY_GUIDE.md`
- **File:** `/docs/api/MODEL_CONSISTENCY_QUICK_REFERENCE.md`

**Enforcement:**
- Not enforced programmatically (by design)
- Documented as critical developer responsibility
- Model stored with each vector for transparency

---

## 6. Namespace Scoping

### 6.1 Namespace Isolation

**Requirement:**
Vectors stored in namespace A MUST be completely invisible to namespace B.

**Source:**
- **DX Contract §3:** Namespace guarantees
- **PRD §6:** Agent-scoped memory
- **Issue #17:** Namespace implementation
- **Issue #23:** Namespace search scoping

**Guarantees:**
1. **Storage Isolation:** Vectors in namespace A cannot be accessed from namespace B
2. **Search Isolation:** Searching namespace A never returns vectors from namespace B
3. **No Cross-Contamination:** Even with identical vector IDs, namespaces remain isolated
4. **Default Namespace:** When omitted, defaults to `"default"` namespace

**Enforcement:**
- Database-level isolation
- Query filters applied at storage layer
- **File:** `/backend/app/services/vector_store_service.py`

**Test Coverage:**
- **File:** `/backend/app/tests/test_namespace_isolation.py`
- **File:** `/backend/app/tests/test_search_namespace_scoping.py`

**Documentation:**
- **File:** `/docs/api/NAMESPACE_USAGE.md`
- **File:** `/docs/NAMESPACE_SEARCH_SCOPING.md`

**Examples:**

✅ **Isolation Verified:**
```python
# Store in namespace A
store(text="Alpha secret", namespace="team_alpha")

# Store in namespace B
store(text="Beta secret", namespace="team_beta")

# Search namespace A
results_a = search(query="secret", namespace="team_alpha", top_k=100)
# Returns ONLY "Alpha secret" - Beta is invisible

# Search namespace B
results_b = search(query="secret", namespace="team_beta", top_k=100)
# Returns ONLY "Beta secret" - Alpha is invisible
```

---

### 6.2 Namespace Validation

**Requirement:**
Namespace names MUST follow strict validation rules for security.

**Validation Rules:**
1. **Allowed Characters:** Alphanumeric, hyphens (`-`), underscores (`_`), dots (`.`)
2. **Maximum Length:** 128 characters
3. **Cannot be Empty:** Empty strings or whitespace rejected
4. **Case Sensitive:** `"MySpace"` ≠ `"myspace"`

**Invalid Namespaces (Return HTTP 422):**
- `"has spaces"` - No spaces allowed
- `"has/slash"` - No slashes
- `"../traversal"` - No path traversal
- `"has@symbol"` - No special chars
- `""` - No empty strings
- `"a" * 129` - Too long

**Error Response:**
```json
{
  "detail": "Namespace can only contain alphanumeric characters, hyphens, underscores, and dots",
  "error_code": "INVALID_NAMESPACE"
}
```
- **HTTP Status:** 422 Unprocessable Entity
- **Error Code:** `INVALID_NAMESPACE`

**Test Coverage:**
- **File:** `/backend/app/tests/test_namespace_validation.py`

---

## 7. Project Status Field

### 7.1 Status Field Always Present

**Requirement:**
The `status` field MUST appear in ALL project responses and MUST NEVER be null or omitted.

**Source:**
- **DX Contract §6:** Projects API
- **API Spec:** `/docs/api/api-spec.md` (lines 374-391)
- **Epic 1, Story 5:** Project status field guarantee

**Guaranteed Behavior:**
1. **Presence:** `status` field MUST appear in ALL project responses
2. **Creation Default:** New projects MUST have `status: "ACTIVE"`
3. **Non-null:** Status MUST NEVER be null or undefined
4. **Type Safety:** Status MUST be a string enum value

**Valid Status Values:**
- `"ACTIVE"` - Project is operational (default for new projects)
- `"SUSPENDED"` - Project is temporarily disabled
- `"DELETED"` - Project is marked for deletion

**Enforcement:**
- **File:** `/backend/app/schemas/project.py`
- **File:** `/backend/app/api/projects.py`
- **Default status set on creation**

**Test Coverage:**
- **File:** `/backend/app/tests/test_projects_api.py`
- **Test:** `test_list_projects_status_values` (line 121)
- **Test:** Status field validation in create/list/get operations

**Examples:**

✅ **Guaranteed Response:**
```json
{
  "id": "proj_abc123",
  "name": "My Project",
  "status": "ACTIVE",  // Always present, never null
  "tier": "free",
  "created_at": "2026-01-11T10:00:00Z"
}
```

**Applies To:**
- `POST /v1/public/projects` (create)
- `GET /v1/public/projects` (list - all items)
- `GET /v1/public/projects/{id}` (get details)

---

## 8. Append-Only Enforcement

### 8.1 Immutable Agent Records

**Requirement:**
Agent-related tables MUST enforce append-only semantics. UPDATE and DELETE operations are FORBIDDEN.

**Source:**
- **PRD §10:** Non-repudiation
- **DX Contract §9:** Agent-Native Guarantees
- **Epic 12, Issue 6:** Append-only enforcement

**Protected Tables (Append-Only):**
1. **`agents`** - Agent registration and configuration
2. **`agent_memory`** - Agent recall and learning data
3. **`compliance_events`** - Regulatory audit trail
4. **`x402_requests`** - Payment protocol transactions

**Enforcement:**
- **File:** `/backend/app/middleware/immutable.py`
- **Constant:** `IMMUTABLE_TABLES` (line 37)
- **Class:** `ImmutableRecordError` (lines 51-93)
- **Decorator:** `@immutable_table` (lines 96-178)
- **Middleware:** `ImmutableMiddleware` (routes-level enforcement)

**Error Response (Attempted Update/Delete):**
```json
{
  "detail": "Cannot update records in 'agents' table. This table is append-only for audit trail integrity. Per PRD Section 10: Agent records are immutable for non-repudiation.",
  "error_code": "IMMUTABLE_RECORD"
}
```
- **HTTP Status:** 403 Forbidden
- **Error Code:** `IMMUTABLE_RECORD`

**Test Coverage:**
- **File:** `/backend/app/tests/test_immutable_middleware.py`

**Why This Matters:**
- **Audit Trails:** Regulatory compliance requires immutable records
- **Non-repudiation:** Agent actions cannot be retroactively altered
- **Forensic Analysis:** Historical data remains intact for investigation
- **Payment Integrity:** X402 transactions cannot be modified

**Allowed Operations:**
- ✅ **CREATE (INSERT)** - Append new records
- ✅ **READ (SELECT)** - Query existing records
- ❌ **UPDATE** - Forbidden (returns 403)
- ❌ **DELETE** - Forbidden (returns 403)

**Documentation:**
- **File:** `/docs/api/APPEND_ONLY_GUARANTEE.md`

---

## 9. Timestamp Validation

### 9.1 ISO 8601 Format Required

**Requirement:**
All timestamp fields MUST use ISO 8601 format (RFC 3339). Invalid timestamps return HTTP 422 with `INVALID_TIMESTAMP` error code.

**Source:**
- **GitHub Issue #39:** Invalid timestamps return clear errors
- **Epic 8, Story 3:** Timestamp validation

**Valid Formats:**
```
2026-01-10T12:34:56Z
2026-01-10T12:34:56.789Z
2026-01-10T12:34:56+00:00
2026-01-10T12:34:56-05:00
```

**Enforcement:**
- **File:** `/backend/app/core/timestamp_validator.py`
- **Error Class:** `InvalidTimestampError` in `/backend/app/core/errors.py` (lines 292-322)

**Error Response:**
```json
{
  "detail": "Invalid timestamp format. Expected ISO8601 format (RFC 3339). Valid examples: '2026-01-10T12:34:56Z', '2026-01-10T12:34:56.789Z'",
  "error_code": "INVALID_TIMESTAMP"
}
```
- **HTTP Status:** 422 Unprocessable Entity
- **Error Code:** `INVALID_TIMESTAMP`

**Test Coverage:**
- **File:** `/backend/app/tests/test_timestamp_validation.py`
- **File:** `/backend/app/tests/test_timestamp_validation_api.py`

---

## 10. API Stability Guarantees

### 10.1 Versioned Breaking Changes

**Requirement:**
Breaking changes to API request/response shapes MUST require a new API version (e.g., `/v2/`).

**Source:**
- **DX Contract §1:** API Stability

**What's Guaranteed:**
1. **Request Shapes:** Required fields and validation rules remain stable
2. **Response Shapes:** Field names, types, and meanings remain stable
3. **Error Codes:** Error codes and HTTP status codes remain stable

**What Can Change (Additive):**
- New optional fields
- New endpoints
- New error codes (for new scenarios)

**Enforcement:**
- API versioning in endpoint paths (`/v1/public/`)
- Documented DX Contract commitment
- Smoke tests validate backward compatibility

---

## Enforcement Summary

### How Critical Requirements Are Enforced

| Requirement | Enforcement Mechanism | File Location | Test Coverage |
|-------------|----------------------|---------------|---------------|
| X-API-Key Authentication | Middleware | `app/middleware/api_key_auth.py` | `test_api_key_auth.py` |
| Error Response Format | Error handler + schemas | `app/core/errors.py` | `test_error_detail.py` |
| /database/ Prefix | Routing configuration | FastAPI routes | Integration tests |
| Dimension Validation | Validator utility | `app/core/dimension_validator.py` | `test_dimension_mismatch.py` |
| Model Consistency | Documentation (dev responsibility) | N/A (documented pattern) | Best practice guide |
| Namespace Isolation | Database query filters | `app/services/vector_store_service.py` | `test_namespace_isolation.py` |
| Project Status Field | Schema enforcement | `app/schemas/project.py` | `test_projects_api.py` |
| Append-Only Records | Middleware + decorator | `app/middleware/immutable.py` | `test_immutable_middleware.py` |
| Timestamp Validation | Validator utility | `app/core/timestamp_validator.py` | `test_timestamp_validation.py` |
| API Stability | Versioning + DX Contract | `/v1/` path prefix | Smoke tests |

---

## Testing Requirements

### Mandatory Test Coverage for Critical Requirements

Every critical requirement MUST have:

1. **Unit Tests**
   - Test the enforcement mechanism in isolation
   - Test edge cases and boundary conditions
   - Test error handling and error messages

2. **Integration Tests**
   - Test the requirement end-to-end via API
   - Test interaction with other requirements
   - Test with realistic data and scenarios

3. **Smoke Tests**
   - Verify requirement in production-like environment
   - Detect regressions in deployed code

**Test Organization:**
```
/backend/app/tests/
  ├── test_api_key_auth.py           # Auth requirement tests
  ├── test_dimension_mismatch.py     # Dimension validation tests
  ├── test_error_detail.py           # Error format tests
  ├── test_namespace_isolation.py    # Namespace scoping tests
  ├── test_projects_api.py           # Project status tests
  ├── test_immutable_middleware.py   # Append-only tests
  └── test_timestamp_validation.py   # Timestamp tests
```

---

## Developer Checklist

When implementing new features, verify compliance with critical requirements:

### Authentication
- [ ] Endpoint requires `X-API-Key` header
- [ ] Returns 401 `INVALID_API_KEY` when auth fails
- [ ] Exempt paths documented if needed

### Error Handling
- [ ] All errors return `{ detail, error_code }`
- [ ] Error codes follow `UPPER_SNAKE_CASE` convention
- [ ] HTTP status codes are appropriate
- [ ] Validation errors use HTTP 422

### Endpoints
- [ ] Database operations include `/database/` prefix
- [ ] Endpoint paths documented correctly
- [ ] Examples show correct paths

### Vectors & Embeddings
- [ ] Default model is `BAAI/bge-small-en-v1.5` (384 dims)
- [ ] Dimension validation enforced
- [ ] Model consistency documented for namespace
- [ ] Dimension mismatch returns `DIMENSION_MISMATCH`

### Namespaces
- [ ] Namespace isolation enforced in storage
- [ ] Namespace validation applied
- [ ] Default namespace behavior correct
- [ ] Namespace documented in API examples

### Data Integrity
- [ ] Project responses include `status` field
- [ ] Append-only tables reject updates/deletes
- [ ] Timestamps use ISO 8601 format
- [ ] Immutable records protected

### Testing
- [ ] Unit tests cover enforcement logic
- [ ] Integration tests verify end-to-end behavior
- [ ] Error scenarios tested
- [ ] Edge cases covered

---

## Documentation References

### Primary Sources
- **PRD:** `/prd.md` - Product requirements and business logic
- **DX Contract:** `/DX-Contract.md` - Developer guarantees and invariants
- **API Spec:** `/docs/api/api-spec.md` - Complete API documentation

### Requirement-Specific Guides
- **Authentication:** `/docs/api/API_KEY_SECURITY.md`
- **Database Prefix:** `/docs/api/DATABASE_PREFIX_WARNING.md`
- **Model Consistency:** `/docs/api/MODEL_CONSISTENCY_GUIDE.md`
- **Namespaces:** `/docs/api/NAMESPACE_USAGE.md`
- **Append-Only:** `/docs/api/APPEND_ONLY_GUARANTEE.md`

### Quick References
- **Quickstart:** `/docs/quick-reference/QUICKSTART.md`
- **API Key Checklist:** `/docs/quick-reference/API_KEY_SAFETY_CHECKLIST.md`
- **Vector Upsert:** `/docs/quick-reference/VECTOR_UPSERT_QUICK_START.md`

---

## Compliance Verification

To verify compliance with critical requirements:

### 1. Run Test Suite
```bash
cd backend
pytest app/tests/ -v --cov=app --cov-report=term-missing
```

### 2. Check Coverage
Ensure critical enforcement files have ≥90% coverage:
- `app/middleware/api_key_auth.py`
- `app/core/errors.py`
- `app/core/dimension_validator.py`
- `app/middleware/immutable.py`

### 3. Smoke Test Production
```bash
./smoke_test.sh
```

### 4. Review Documentation
Ensure all critical requirements are documented in:
- API specifications
- Error catalogs
- Example code
- Integration guides

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-11 | Initial release - Epic 10 Story 4 deliverable |

---

## Feedback & Updates

Critical requirements changes require:
1. **PRD Update** - Change business requirement
2. **DX Contract Update** - Update developer guarantee
3. **Code Changes** - Implement enforcement
4. **Test Updates** - Verify new behavior
5. **Documentation Updates** - Update all references
6. **Version Bump** - If breaking change, create `/v2/` API

**This document is authoritative.** Any discrepancies between code behavior and documented requirements should be treated as bugs.

---

**End of Critical Requirements Reference**
