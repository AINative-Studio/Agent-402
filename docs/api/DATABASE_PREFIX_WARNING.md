# Critical: /database/ Prefix Requirement

**Last Updated:** 2026-01-10
**Applies To:** Vector Operations API (Epic 6)
**Severity:** High - Mandatory for all vector/database operations

---

## Overview

All ZeroDB vector and database operations **REQUIRE** the `/database/` prefix in the endpoint path. This is a mandatory routing requirement enforced by the API gateway and cannot be omitted.

---

## The Critical Rule

```
ALL vector operations MUST include /database/ in the path
```

**This applies to:**
- Vector upsert operations
- Vector search operations
- Vector retrieval operations
- Vector deletion operations
- Table operations (NoSQL)
- File storage operations

---

## Correct vs Incorrect Endpoint Paths

### Vector Operations

**CORRECT Paths (Required):**
```bash
# ✅ Vector upsert - CORRECT
POST https://api.ainative.studio/v1/public/database/vectors/upsert

# ✅ Vector search - CORRECT
POST https://api.ainative.studio/v1/public/database/vectors/search

# ✅ Get vector by ID - CORRECT
GET https://api.ainative.studio/v1/public/database/vectors/{vector_id}

# ✅ Delete vector - CORRECT
DELETE https://api.ainative.studio/v1/public/database/vectors/{vector_id}

# ✅ List vectors - CORRECT
GET https://api.ainative.studio/v1/public/database/vectors
```

**INCORRECT Paths (Will Fail):**
```bash
# ❌ Missing /database/ - WILL RETURN 404
POST https://api.ainative.studio/v1/public/vectors/upsert

# ❌ Missing /database/ - WILL RETURN 404
POST https://api.ainative.studio/v1/public/vectors/search

# ❌ Wrong order - WILL RETURN 404
POST https://api.ainative.studio/v1/database/public/vectors/upsert

# ❌ Typo in prefix - WILL RETURN 404
POST https://api.ainative.studio/v1/public/databases/vectors/upsert
```

---

## Table Operations (NoSQL)

**CORRECT Paths:**
```bash
# ✅ Create table - CORRECT
POST https://api.ainative.studio/v1/public/database/tables

# ✅ Insert rows - CORRECT
POST https://api.ainative.studio/v1/public/database/tables/{table_id}/rows

# ✅ Query rows - CORRECT
POST https://api.ainative.studio/v1/public/database/tables/{table_id}/query

# ✅ List tables - CORRECT
GET https://api.ainative.studio/v1/public/database/tables
```

**INCORRECT Paths:**
```bash
# ❌ Missing /database/ - WILL RETURN 404
POST https://api.ainative.studio/v1/public/tables

# ❌ Missing /database/ - WILL RETURN 404
POST https://api.ainative.studio/v1/public/tables/{table_id}/rows
```

---

## File Storage Operations

**CORRECT Paths:**
```bash
# ✅ Upload file - CORRECT
POST https://api.ainative.studio/v1/public/database/files/upload

# ✅ Download file - CORRECT
GET https://api.ainative.studio/v1/public/database/files/{file_id}

# ✅ List files - CORRECT
GET https://api.ainative.studio/v1/public/database/files
```

**INCORRECT Paths:**
```bash
# ❌ Missing /database/ - WILL RETURN 404
POST https://api.ainative.studio/v1/public/files/upload

# ❌ Missing /database/ - WILL RETURN 404
GET https://api.ainative.studio/v1/public/files/{file_id}
```

---

## What Operations DO NOT Require /database/?

The following operations work directly under `/v1/public/` without the `/database/` prefix:

**Projects API:**
```bash
# ✅ No /database/ needed for projects
GET  https://api.ainative.studio/v1/public/projects
POST https://api.ainative.studio/v1/public/projects
GET  https://api.ainative.studio/v1/public/projects/{project_id}
```

**Embeddings API:**
```bash
# ✅ No /database/ needed for embeddings generation
POST https://api.ainative.studio/v1/public/{project_id}/embeddings/generate
GET  https://api.ainative.studio/v1/public/embeddings/models
```

**Embeddings Store & Search API:**
```bash
# ✅ No /database/ needed for embed-and-store
POST https://api.ainative.studio/v1/public/{project_id}/embeddings/embed-and-store
POST https://api.ainative.studio/v1/public/{project_id}/embeddings/search
```

---

## Error Response for Missing /database/

When you omit `/database/` from a path that requires it, you will receive:

**HTTP 404 Not Found**
```json
{
  "detail": "Not Found"
}
```

**This is a routing error**, not a business logic error. The endpoint literally does not exist without the `/database/` prefix.

---

## Why This Prefix Exists

The `/database/` prefix serves multiple purposes:

1. **API Gateway Routing:** Separates database operations from other API services
2. **Access Control:** Different rate limits and permissions for database operations
3. **Service Isolation:** Database operations route to specialized backend services
4. **Clarity:** Makes it explicit that you're performing data operations
5. **Future Compatibility:** Allows for multiple database backends in the future

**Per DX Contract §4:** This behavior is permanent and guaranteed not to change without a version bump.

---

## Common Mistakes

### Mistake 1: Copy-pasting from projects/embeddings API
```python
# ❌ WRONG - Using pattern from projects API
response = requests.post(
    "https://api.ainative.studio/v1/public/vectors/upsert",  # Missing /database/
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

### Mistake 2: Assuming consistency across all endpoints
```python
# ✅ Projects API - No /database/ needed
projects = requests.get("https://api.ainative.studio/v1/public/projects")

# ❌ WRONG - Assuming same pattern for vectors
vectors = requests.get("https://api.ainative.studio/v1/public/vectors")  # 404!

# ✅ CORRECT - Vectors require /database/
vectors = requests.get("https://api.ainative.studio/v1/public/database/vectors")
```

### Mistake 3: Incorrect environment variable configuration
```bash
# ❌ WRONG - Base URL doesn't include /database/
ZERODB_BASE_URL="https://api.ainative.studio/v1/public"

# Code that will fail:
curl "$ZERODB_BASE_URL/vectors/upsert"  # Results in: /v1/public/vectors/upsert (404)

# ✅ CORRECT - Include /database/ in your code, not base URL
ZERODB_BASE_URL="https://api.ainative.studio/v1/public"

# Then in code:
curl "$ZERODB_BASE_URL/database/vectors/upsert"  # Results in: /v1/public/database/vectors/upsert ✅
```

### Mistake 4: Wrong prefix order
```bash
# ❌ WRONG - /database/ before /public/
https://api.ainative.studio/v1/database/public/vectors/upsert

# ✅ CORRECT - /database/ after /public/
https://api.ainative.studio/v1/public/database/vectors/upsert
```

---

## Quick Reference Checklist

Before making a vector/database operation, verify:

- [ ] Path includes `/v1/public/database/` (in that exact order)
- [ ] `/database/` comes AFTER `/v1/public/`
- [ ] No typos in "database" (not "databases" or "db")
- [ ] Using the correct operation path after `/database/`

**Mental Model:**
```
/v1/public/database/{operation}/{resource}
           ^^^^^^^^^ ALWAYS INCLUDE THIS FOR DATABASE OPERATIONS
```

---

## Language-Specific Examples

### Python (requests)
```python
import requests

BASE_URL = "https://api.ainative.studio/v1/public"
API_KEY = "your_api_key"

# ✅ CORRECT - Vector upsert
response = requests.post(
    f"{BASE_URL}/database/vectors/upsert",  # Note: /database/ prefix
    headers={"X-API-Key": API_KEY},
    json={
        "vectors": [{
            "id": "vec-001",
            "values": [0.1, 0.2, 0.3],
            "metadata": {"source": "test"}
        }]
    }
)
```

### JavaScript (fetch)
```javascript
const BASE_URL = "https://api.ainative.studio/v1/public";
const API_KEY = "your_api_key";

// ✅ CORRECT - Vector search
const response = await fetch(
  `${BASE_URL}/database/vectors/search`,  // Note: /database/ prefix
  {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      vector: [0.1, 0.2, 0.3],
      top_k: 10
    })
  }
);
```

### cURL
```bash
# ✅ CORRECT - Create table
curl -X POST "https://api.ainative.studio/v1/public/database/tables" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "customers",
    "schema": {
      "fields": {
        "id": "string",
        "name": "string"
      }
    }
  }'
```

### Go
```go
package main

import (
    "bytes"
    "net/http"
)

const (
    BaseURL = "https://api.ainative.studio/v1/public"
    APIKey  = "your_api_key"
)

func upsertVector() error {
    // ✅ CORRECT - Include /database/ prefix
    url := BaseURL + "/database/vectors/upsert"

    payload := []byte(`{"vectors": [...]}`)
    req, err := http.NewRequest("POST", url, bytes.NewBuffer(payload))
    if err != nil {
        return err
    }

    req.Header.Set("X-API-Key", APIKey)
    req.Header.Set("Content-Type", "application/json")

    client := &http.Client{}
    resp, err := client.Do(req)
    defer resp.Body.Close()

    return err
}
```

---

## Troubleshooting Guide

### Getting 404 on vector operations?

**Step 1:** Check your URL structure
```bash
# Print your full URL before making the request
echo $FULL_URL

# Expected format:
# https://api.ainative.studio/v1/public/database/vectors/...
#                                       ^^^^^^^^^ Must include this
```

**Step 2:** Verify the exact path
```python
# Add debug logging
url = f"{BASE_URL}/database/vectors/upsert"
print(f"Request URL: {url}")  # Should print: .../v1/public/database/vectors/upsert
response = requests.post(url, ...)
```

**Step 3:** Check for common typos
- "databases" instead of "database" ❌
- "db" instead of "database" ❌
- "/database" instead of "/database/" ❌
- Wrong order: "/database/public/" ❌

**Step 4:** Compare against working examples
```bash
# Copy this EXACT URL and test it works:
curl -X GET "https://api.ainative.studio/v1/public/database/vectors" \
  -H "X-API-Key: your_api_key"

# If this works but yours doesn't, compare the URLs character-by-character
```

---

## Testing Your Implementation

Use this test checklist to verify your code:

```python
import requests

BASE_URL = "https://api.ainative.studio/v1/public"
API_KEY = "your_api_key"

def test_database_prefix():
    """Test that /database/ prefix is correctly included."""

    # ✅ This should succeed
    correct_url = f"{BASE_URL}/database/vectors"
    response = requests.get(
        correct_url,
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code != 404, \
        f"Expected success, got 404. Check URL: {correct_url}"

    # ❌ This should fail with 404
    incorrect_url = f"{BASE_URL}/vectors"
    response = requests.get(
        incorrect_url,
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 404, \
        f"Expected 404 for missing /database/, got {response.status_code}"

    print("✅ All prefix tests passed!")

if __name__ == "__main__":
    test_database_prefix()
```

---

## Documentation References

- **DX Contract §4:** Endpoint Prefixing - `/database/` requirement is guaranteed
- **Epic 6:** Vector Operations API specification
- **API Spec:** Complete endpoint documentation with correct paths
- **Quick Start Guide:** Copy-paste ready examples with correct prefixes

---

## Summary: One Rule to Remember

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ALL vector and database operations require:           │
│                                                         │
│  /v1/public/database/{operation}                       │
│             ^^^^^^^^^ MANDATORY PREFIX                  │
│                                                         │
│  Missing /database/ → 404 Not Found                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**When in doubt:** Add `/database/` to the path. It's required for all database operations.

---

**Questions or Issues?**

If you're still getting 404 errors after following this guide:
1. Check the exact URL you're using (print/log it)
2. Compare against the "Correct Paths" examples above
3. Verify no typos in "database"
4. Ensure correct order: `/v1/public/database/` not `/v1/database/public/`

This is a routing requirement that **cannot be bypassed**. Per the DX Contract, this behavior is permanent.
