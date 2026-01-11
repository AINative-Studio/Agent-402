# Error Codes Reference

**Version:** v1.0
**Last Updated:** 2026-01-11
**Epic:** 9 (Developer Experience)
**Issue:** #45 - Top 10 Common Errors Documentation

---

## Overview

This document provides a comprehensive reference for the top 10 most common errors in the Agent-402 API. Each error includes the error code, HTTP status, when it occurs, example responses, and how to fix it.

**DX Contract Compliance:** All errors return the standard format:
```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE"
}
```

---

## Table of Contents

1. [INVALID_API_KEY (401)](#1-invalid_api_key-401)
2. [VALIDATION_ERROR (422)](#2-validation_error-422)
3. [MODEL_NOT_FOUND (404)](#3-model_not_found-404)
4. [PROJECT_NOT_FOUND (404)](#4-project_not_found-404)
5. [DIMENSION_MISMATCH (422)](#5-dimension_mismatch-422)
6. [INVALID_NAMESPACE (422)](#6-invalid_namespace-422)
7. [INVALID_METADATA_FILTER (422)](#7-invalid_metadata_filter-422)
8. [PATH_NOT_FOUND (404)](#8-path_not_found-404)
9. [PROJECT_LIMIT_EXCEEDED (429)](#9-project_limit_exceeded-429)
10. [INVALID_TIER (422)](#10-invalid_tier-422)

---

## 1. INVALID_API_KEY (401)

### When it occurs

This error is returned when the `X-API-Key` header is missing, empty, malformed, expired, or not recognized by the system.

**Scenarios:**
- Missing `X-API-Key` header entirely
- Empty or whitespace-only API key
- Malformed API key (too short, invalid characters)
- Expired API key
- API key not found in system

### Example Response

```json
{
  "detail": "Invalid or missing API key",
  "error_code": "INVALID_API_KEY"
}
```

### How to fix

1. **Verify the header is present:**
   ```bash
   # Correct
   curl -X POST "${BASE_URL}/v1/public/projects" \
     -H "X-API-Key: your_api_key_here" \
     -H "Content-Type: application/json"

   # Incorrect - missing header
   curl -X POST "${BASE_URL}/v1/public/projects" \
     -H "Content-Type: application/json"
   ```

2. **Check for typos in header name:**
   ```bash
   # Correct
   -H "X-API-Key: your_api_key"

   # Common mistakes
   -H "X-Api-Key: your_api_key"    # Wrong case
   -H "API-Key: your_api_key"      # Wrong name
   -H "Authorization: your_api_key" # Wrong header
   ```

3. **Ensure key is not expired:**
   - Contact your administrator to verify key status
   - Generate a new API key if needed

4. **Verify key format:**
   - API keys should not contain leading/trailing whitespace
   - Check for copy-paste issues with hidden characters

---

## 2. VALIDATION_ERROR (422)

### When it occurs

This error is returned when the request body fails Pydantic validation. This includes missing required fields, invalid field types, values outside allowed ranges, or constraint violations.

**Scenarios:**
- Missing required fields (e.g., `name` in project creation)
- Invalid field types (e.g., string instead of number)
- Values outside allowed ranges (e.g., negative `top_k`)
- Pattern violations (e.g., invalid email format)

### Example Response

```json
{
  "detail": "Validation error on field 'name': field required",
  "error_code": "VALIDATION_ERROR",
  "validation_errors": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### How to fix

1. **Check required fields:**
   ```python
   # Correct - includes required 'name' field
   {
       "name": "My Project",
       "tier": "free"
   }

   # Incorrect - missing required 'name'
   {
       "tier": "free"
   }
   ```

2. **Verify field types:**
   ```python
   # Correct - top_k is integer
   {
       "query": "search text",
       "top_k": 10
   }

   # Incorrect - top_k is string
   {
       "query": "search text",
       "top_k": "10"
   }
   ```

3. **Check value constraints:**
   ```python
   # Correct - top_k in valid range (1-100)
   {"top_k": 10}

   # Incorrect - top_k too large
   {"top_k": 500}
   ```

4. **Review the `validation_errors` array** for specific field locations and messages.

---

## 3. MODEL_NOT_FOUND (404)

### When it occurs

This error is returned when the specified embedding model is not supported by the API.

**Scenarios:**
- Typo in model name
- Using unsupported model
- Missing vendor prefix (e.g., `BAAI/`)
- Extra whitespace in model name

### Example Response

```json
{
  "detail": "Model 'BAAI/bge-small-v1.5' is not supported. Supported models: BAAI/bge-small-en-v1.5, BAAI/bge-base-en-v1.5, BAAI/bge-large-en-v1.5, sentence-transformers/all-mpnet-base-v2",
  "error_code": "MODEL_NOT_FOUND"
}
```

### How to fix

1. **Use exact model names:**
   ```python
   # Correct
   "model": "BAAI/bge-small-en-v1.5"

   # Common mistakes
   "model": "BAAI/bge-small-v1.5"      # Missing 'en'
   "model": "bge-small-en-v1.5"        # Missing 'BAAI/'
   "model": "BAAI/bge-small-en-v1.5 "  # Trailing space
   ```

2. **Supported models:**
   | Model | Dimensions |
   |-------|------------|
   | `BAAI/bge-small-en-v1.5` | 384 |
   | `BAAI/bge-base-en-v1.5` | 768 |
   | `BAAI/bge-large-en-v1.5` | 1024 |
   | `sentence-transformers/all-mpnet-base-v2` | 768 |

3. **Define model as constant to avoid typos:**
   ```python
   EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

   # Use constant in all API calls
   requests.post(url, json={"model": EMBEDDING_MODEL, ...})
   ```

---

## 4. PROJECT_NOT_FOUND (404)

### When it occurs

This error is returned when the specified project ID does not exist or the user does not have access to it.

**Scenarios:**
- Project ID is incorrect or typo
- Project was deleted
- User lacks access to the project
- Using wrong environment (dev vs prod)

### Example Response

```json
{
  "detail": "Project not found: proj_nonexistent_123",
  "error_code": "PROJECT_NOT_FOUND"
}
```

### How to fix

1. **Verify project ID:**
   ```bash
   # List your projects to get correct ID
   curl -X GET "${BASE_URL}/v1/public/projects" \
     -H "X-API-Key: ${API_KEY}"
   ```

2. **Check for typos:**
   ```python
   # Correct
   project_id = "proj_abc123def456"

   # Common mistakes
   project_id = "proj_abc123def45"   # Missing character
   project_id = "proj-abc123def456"  # Wrong separator
   ```

3. **Verify environment:**
   - Ensure you're using the correct API base URL
   - Projects created in dev are not available in prod

4. **Check project access:**
   - Verify your API key has access to the project
   - Contact administrator if access was revoked

---

## 5. DIMENSION_MISMATCH (422)

### When it occurs

This error is returned when the vector dimensions don't match what was expected. This typically happens when searching with a different embedding model than was used for storage.

**Scenarios:**
- Storing with Model A (384 dims), searching with Model B (768 dims)
- Omitting model in search (uses default 384) when stored with 768-dim model
- Changing models mid-project without re-embedding

### Example Response

```json
{
  "detail": "Vector dimension mismatch. Expected 384, got 768. Ensure you use the same embedding model for storage and search.",
  "error_code": "DIMENSION_MISMATCH"
}
```

### How to fix

1. **Use the same model for store and search:**
   ```python
   MODEL = "BAAI/bge-small-en-v1.5"  # 384 dimensions

   # Store
   requests.post(f"{BASE_URL}/embeddings/embed-and-store", json={
       "model": MODEL,
       "documents": [...]
   })

   # Search - MUST use same model
   requests.post(f"{BASE_URL}/embeddings/search", json={
       "model": MODEL,
       "query": "search text"
   })
   ```

2. **Always specify model explicitly:**
   ```python
   # Good - explicit model
   {"model": "BAAI/bge-small-en-v1.5", "query": "..."}

   # Bad - relies on default
   {"query": "..."}  # May not match stored vectors
   ```

3. **Model dimension reference:**
   | Model | Dimensions |
   |-------|------------|
   | `BAAI/bge-small-en-v1.5` | 384 |
   | `BAAI/bge-base-en-v1.5` | 768 |
   | `BAAI/bge-large-en-v1.5` | 1024 |
   | `sentence-transformers/all-mpnet-base-v2` | 768 |

4. **If you must change models:** Re-embed all existing documents with the new model.

---

## 6. INVALID_NAMESPACE (422)

### When it occurs

This error is returned when the namespace format violates validation rules.

**Validation rules:**
- Valid characters: `a-z`, `A-Z`, `0-9`, `_`, `-`
- Maximum length: 64 characters
- Cannot start with `_` or `-`
- Cannot be empty (use `null` or omit for default)

### Example Response

```json
{
  "detail": "Invalid namespace format. Namespace can only contain alphanumeric characters, underscores, and hyphens. Max length: 64. Cannot start with underscore or hyphen.",
  "error_code": "INVALID_NAMESPACE"
}
```

### How to fix

1. **Use valid characters:**
   ```python
   # Valid namespaces
   "agent_memory"
   "production-env"
   "customer123"
   "AgentMemoryV2"

   # Invalid namespaces
   "has spaces"      # Spaces not allowed
   "has/slash"       # Slashes not allowed
   "../parent"       # Path traversal not allowed
   "_starts_wrong"   # Cannot start with underscore
   "-starts-wrong"   # Cannot start with hyphen
   ```

2. **Check length:**
   ```python
   # Valid - under 64 characters
   namespace = "my_agent_memory"

   # Invalid - over 64 characters
   namespace = "a" * 65
   ```

3. **Use default namespace when appropriate:**
   ```python
   # To use default namespace, omit the field or set to None
   {"text": "...", "namespace": None}  # Uses "default"
   {"text": "..."}                     # Uses "default"
   ```

---

## 7. INVALID_METADATA_FILTER (422)

### When it occurs

This error is returned when the metadata filter format is invalid or uses unsupported operators.

**Supported operators:**
- `$eq` - Equals (default)
- `$ne` - Not equals
- `$gt`, `$gte`, `$lt`, `$lte` - Numeric comparisons
- `$in`, `$nin` - Value in/not in array
- `$exists` - Field exists
- `$contains` - String contains substring

### Example Response

```json
{
  "detail": "Invalid metadata filter format. Unsupported operator '$like'. Supported: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $exists, $contains",
  "error_code": "INVALID_METADATA_FILTER"
}
```

### How to fix

1. **Use correct operator syntax:**
   ```python
   # Correct
   {
       "metadata_filter": {
           "score": {"$gte": 0.8},
           "status": {"$in": ["active", "pending"]}
       }
   }

   # Incorrect - missing $ prefix
   {
       "metadata_filter": {
           "score": {"gte": 0.8}
       }
   }
   ```

2. **Verify operator types:**
   ```python
   # Correct - $in requires array
   {"status": {"$in": ["active", "pending"]}}

   # Incorrect - $in with non-array
   {"status": {"$in": "active"}}

   # Correct - $gt requires number
   {"score": {"$gt": 0.8}}

   # Incorrect - $gt with string
   {"score": {"$gt": "high"}}
   ```

3. **Filter must be a dictionary:**
   ```python
   # Correct
   {"metadata_filter": {"field": "value"}}

   # Incorrect - filter is not a dict
   {"metadata_filter": "field=value"}
   {"metadata_filter": ["field", "value"]}
   ```

---

## 8. PATH_NOT_FOUND (404)

### When it occurs

This error is returned when the requested API endpoint does not exist.

**Scenarios:**
- Typo in endpoint URL
- Missing required path segments
- Using wrong HTTP method for endpoint
- Hitting deprecated endpoints

### Example Response

```json
{
  "detail": "Path '/v1/public/invalid_endpoint' not found. Check the API documentation for valid endpoints.",
  "error_code": "PATH_NOT_FOUND"
}
```

### How to fix

1. **Check endpoint path:**
   ```bash
   # Correct paths
   /v1/public/projects
   /v1/public/{project_id}/embeddings/search
   /v1/public/database/vectors/upsert

   # Common mistakes
   /v1/projects                    # Missing 'public'
   /v1/public/project              # Wrong pluralization
   /v1/public/embeddings/search    # Missing project_id
   ```

2. **Verify database prefix for vector operations:**
   ```bash
   # Vector operations need /database/ prefix
   /v1/public/database/vectors/upsert    # Correct
   /v1/public/vectors/upsert             # Incorrect

   # Embeddings operations do NOT need /database/
   /v1/public/{project_id}/embeddings/search  # Correct
   ```

3. **Check HTTP method:**
   ```bash
   # Correct method for each endpoint
   POST /v1/public/projects                       # Create project
   GET  /v1/public/projects                       # List projects
   POST /v1/public/{project_id}/embeddings/search # Search

   # Wrong method
   GET  /v1/public/projects                       # Correct
   POST /v1/public/projects                       # For creation only
   ```

4. **Reference API documentation:**
   - Check `/docs` or `/redoc` for interactive API reference
   - Review `docs/api/api-spec.md` for complete endpoint list

---

## 9. PROJECT_LIMIT_EXCEEDED (429)

### When it occurs

This error is returned when you attempt to create more projects than your tier allows.

**Tier limits:**
| Tier | Max Projects |
|------|-------------|
| free | 3 |
| starter | 10 |
| professional | 50 |
| enterprise | Unlimited |

### Example Response

```json
{
  "detail": "Project limit exceeded for tier 'free'. Current projects: 3/3.",
  "error_code": "PROJECT_LIMIT_EXCEEDED"
}
```

### How to fix

1. **Delete unused projects:**
   ```bash
   # List current projects
   curl -X GET "${BASE_URL}/v1/public/projects" \
     -H "X-API-Key: ${API_KEY}"

   # Delete unused project
   curl -X DELETE "${BASE_URL}/v1/public/projects/{project_id}" \
     -H "X-API-Key: ${API_KEY}"
   ```

2. **Upgrade your tier:**
   ```bash
   # Contact support to upgrade tier
   # Or use API if self-service available
   curl -X PATCH "${BASE_URL}/v1/public/account/tier" \
     -H "X-API-Key: ${API_KEY}" \
     -H "Content-Type: application/json" \
     -d '{"tier": "starter"}'
   ```

3. **Check current usage:**
   ```bash
   curl -X GET "${BASE_URL}/v1/public/account/usage" \
     -H "X-API-Key: ${API_KEY}"
   ```

---

## 10. INVALID_TIER (422)

### When it occurs

This error is returned when an invalid tier value is specified during project creation or tier update.

**Valid tiers:** `free`, `starter`, `professional`, `enterprise`

### Example Response

```json
{
  "detail": "Invalid tier 'premium'. Valid tiers are: free, starter, professional, enterprise.",
  "error_code": "INVALID_TIER"
}
```

### How to fix

1. **Use valid tier values:**
   ```python
   # Correct - valid tier names
   {"name": "My Project", "tier": "free"}
   {"name": "My Project", "tier": "starter"}
   {"name": "My Project", "tier": "professional"}
   {"name": "My Project", "tier": "enterprise"}

   # Incorrect - invalid tier names
   {"name": "My Project", "tier": "premium"}
   {"name": "My Project", "tier": "Free"}      # Case-sensitive
   {"name": "My Project", "tier": "STARTER"}   # Case-sensitive
   ```

2. **Tiers are case-sensitive:**
   ```python
   # Correct - lowercase
   "tier": "free"

   # Incorrect - wrong case
   "tier": "Free"
   "tier": "FREE"
   ```

3. **Define tier as constant:**
   ```python
   class Tiers:
       FREE = "free"
       STARTER = "starter"
       PROFESSIONAL = "professional"
       ENTERPRISE = "enterprise"

   # Use constant in API calls
   requests.post(url, json={
       "name": "My Project",
       "tier": Tiers.FREE
   })
   ```

---

## Quick Reference Table

| Error Code | HTTP | Common Cause | Quick Fix |
|------------|------|--------------|-----------|
| `INVALID_API_KEY` | 401 | Missing/invalid API key | Add `X-API-Key` header |
| `VALIDATION_ERROR` | 422 | Invalid request body | Check required fields and types |
| `MODEL_NOT_FOUND` | 404 | Invalid model name | Use exact supported model name |
| `PROJECT_NOT_FOUND` | 404 | Wrong project ID | Verify project exists |
| `DIMENSION_MISMATCH` | 422 | Different models for store/search | Use same model consistently |
| `INVALID_NAMESPACE` | 422 | Invalid namespace chars | Use alphanumeric, `_`, `-` only |
| `INVALID_METADATA_FILTER` | 422 | Bad filter syntax | Check operator format |
| `PATH_NOT_FOUND` | 404 | Wrong endpoint URL | Verify endpoint path |
| `PROJECT_LIMIT_EXCEEDED` | 429 | Too many projects | Delete projects or upgrade |
| `INVALID_TIER` | 422 | Invalid tier value | Use: free, starter, professional, enterprise |

---

## Related Documentation

- [Quick Troubleshooting Guide](/docs/quick-reference/COMMON_ERRORS_FIXES.md)
- [API Specification](/docs/api/api-spec.md)
- [Model Consistency Guide](/docs/api/MODEL_CONSISTENCY_GUIDE.md)
- [Namespace Usage Guide](/docs/api/NAMESPACE_USAGE.md)
- [Metadata Filter Reference](/docs/quick-reference/METADATA_FILTER_QUICK_REF.md)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-11 | Initial documentation (Issue #45) |
