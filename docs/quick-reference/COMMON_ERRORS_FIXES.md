# Common Errors Quick Fixes

**Version:** v1.0 | **Issue:** #45 | **Epic:** 9

Quick troubleshooting guide for the top 10 most common API errors.

---

## Error Quick Reference

| # | Error Code | HTTP | 30-Second Fix |
|---|------------|------|---------------|
| 1 | `INVALID_API_KEY` | 401 | Add `-H "X-API-Key: your_key"` header |
| 2 | `VALIDATION_ERROR` | 422 | Check required fields and data types |
| 3 | `MODEL_NOT_FOUND` | 404 | Use `BAAI/bge-small-en-v1.5` (exact name) |
| 4 | `PROJECT_NOT_FOUND` | 404 | Verify project ID with `GET /projects` |
| 5 | `DIMENSION_MISMATCH` | 422 | Use SAME model for store AND search |
| 6 | `INVALID_NAMESPACE` | 422 | Use only `a-z`, `A-Z`, `0-9`, `_`, `-` |
| 7 | `INVALID_METADATA_FILTER` | 422 | Use `$` prefix: `{"$gte": 0.8}` |
| 8 | `PATH_NOT_FOUND` | 404 | Check endpoint path and HTTP method |
| 9 | `PROJECT_LIMIT_EXCEEDED` | 429 | Delete projects or upgrade tier |
| 10 | `INVALID_TIER` | 422 | Use: `free`, `starter`, `professional`, `enterprise` |

---

## 1. INVALID_API_KEY (401)

**Problem:** Missing or invalid API key

**Quick Fix:**
```bash
# Add this header to all requests
-H "X-API-Key: your_api_key_here"
```

**Full Request Example:**
```bash
curl -X POST "${BASE_URL}/v1/public/projects" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "tier": "free"}'
```

**Checklist:**
- [ ] Header present: `X-API-Key` (not `Api-Key` or `Authorization`)
- [ ] No trailing whitespace in key
- [ ] Key not expired

---

## 2. VALIDATION_ERROR (422)

**Problem:** Invalid request body

**Quick Fix:** Check the `validation_errors` array in the response.

**Example Error Response:**
```json
{
  "detail": "Validation error on field 'name': field required",
  "error_code": "VALIDATION_ERROR",
  "validation_errors": [
    {"loc": ["body", "name"], "msg": "field required", "type": "value_error.missing"}
  ]
}
```

**Common Fixes:**

```python
# Missing required field
# Bad:
{"tier": "free"}
# Good:
{"name": "My Project", "tier": "free"}

# Wrong type
# Bad:
{"top_k": "10"}  # String
# Good:
{"top_k": 10}    # Integer

# Value out of range
# Bad:
{"top_k": 500}   # Max is 100
# Good:
{"top_k": 100}
```

---

## 3. MODEL_NOT_FOUND (404)

**Problem:** Invalid embedding model name

**Quick Fix:** Use exact model names:

```python
# Supported models (copy-paste safe)
"BAAI/bge-small-en-v1.5"              # 384 dims (default)
"BAAI/bge-base-en-v1.5"               # 768 dims
"BAAI/bge-large-en-v1.5"              # 1024 dims
"sentence-transformers/all-mpnet-base-v2"  # 768 dims
```

**Common Typos:**
```python
# WRONG                          # RIGHT
"BAAI/bge-small-v1.5"            "BAAI/bge-small-en-v1.5"  # Missing 'en'
"bge-small-en-v1.5"              "BAAI/bge-small-en-v1.5"  # Missing prefix
"BAAI/bge-small-en-v1.5 "        "BAAI/bge-small-en-v1.5"  # Trailing space
```

**Best Practice:**
```python
# Define as constant
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Use everywhere
requests.post(url, json={"model": EMBEDDING_MODEL, ...})
```

---

## 4. PROJECT_NOT_FOUND (404)

**Problem:** Invalid or inaccessible project ID

**Quick Fix:** List your projects first:

```bash
# Get list of your projects
curl -X GET "${BASE_URL}/v1/public/projects" \
  -H "X-API-Key: ${API_KEY}"
```

**Checklist:**
- [ ] Project ID copied correctly (no missing characters)
- [ ] Using correct environment (dev vs prod)
- [ ] API key has access to project

---

## 5. DIMENSION_MISMATCH (422)

**Problem:** Different models for store vs search

**The Golden Rule:**
```
SAME namespace + SAME model = Working search
```

**Quick Fix:**
```python
# Define model ONCE
MODEL = "BAAI/bge-small-en-v1.5"

# Use SAME model for BOTH operations
# Store:
requests.post(".../embed-and-store", json={"model": MODEL, ...})

# Search:
requests.post(".../search", json={"model": MODEL, ...})
```

**Model Dimensions:**
| Model | Dimensions |
|-------|------------|
| `BAAI/bge-small-en-v1.5` | 384 |
| `BAAI/bge-base-en-v1.5` | 768 |
| `BAAI/bge-large-en-v1.5` | 1024 |
| `sentence-transformers/all-mpnet-base-v2` | 768 |

---

## 6. INVALID_NAMESPACE (422)

**Problem:** Namespace contains invalid characters

**Valid Characters:**
```
a-z  A-Z  0-9  _  -
```

**Examples:**
```python
# VALID
"agent_memory"
"production-env"
"customer123"

# INVALID
"has spaces"      # No spaces
"has/slash"       # No slashes
"_starts_wrong"   # No leading underscore
"../traversal"    # No path traversal
```

**Max Length:** 64 characters

---

## 7. INVALID_METADATA_FILTER (422)

**Problem:** Invalid filter syntax

**Quick Fix:** Use `$` prefix for operators:

```python
# CORRECT syntax
{
    "metadata_filter": {
        "score": {"$gte": 0.8},           # Greater or equal
        "status": {"$in": ["a", "b"]},    # In list
        "active": True                     # Exact match
    }
}

# WRONG - missing $ prefix
{
    "metadata_filter": {
        "score": {"gte": 0.8}              # Missing $
    }
}
```

**Supported Operators:**
| Operator | Example | Description |
|----------|---------|-------------|
| `$eq` | `{"field": {"$eq": "value"}}` | Equals |
| `$ne` | `{"field": {"$ne": "value"}}` | Not equals |
| `$gt` | `{"score": {"$gt": 0.5}}` | Greater than |
| `$gte` | `{"score": {"$gte": 0.5}}` | Greater or equal |
| `$lt` | `{"score": {"$lt": 0.5}}` | Less than |
| `$lte` | `{"score": {"$lte": 0.5}}` | Less or equal |
| `$in` | `{"status": {"$in": ["a","b"]}}` | In list |
| `$nin` | `{"status": {"$nin": ["x"]}}` | Not in list |
| `$exists` | `{"field": {"$exists": true}}` | Field exists |
| `$contains` | `{"text": {"$contains": "word"}}` | Contains substring |

---

## 8. PATH_NOT_FOUND (404)

**Problem:** Endpoint doesn't exist

**Quick Fix:** Check the URL structure:

```bash
# Correct endpoint patterns
GET  /v1/public/projects
POST /v1/public/projects
POST /v1/public/{project_id}/embeddings/search
POST /v1/public/database/vectors/upsert
```

**Common Mistakes:**
```bash
# WRONG                              # RIGHT
/v1/projects                         /v1/public/projects
/v1/public/embeddings/search         /v1/public/{project_id}/embeddings/search
/v1/public/vectors/upsert            /v1/public/database/vectors/upsert
```

**Vector vs Embeddings:**
- Embeddings: `/v1/public/{project_id}/embeddings/...`
- Vectors: `/v1/public/database/vectors/...` (needs `/database/`)

---

## 9. PROJECT_LIMIT_EXCEEDED (429)

**Problem:** Too many projects for your tier

**Tier Limits:**
| Tier | Max Projects |
|------|-------------|
| free | 3 |
| starter | 10 |
| professional | 50 |
| enterprise | Unlimited |

**Quick Fix Options:**

1. **Delete unused projects:**
   ```bash
   curl -X DELETE "${BASE_URL}/v1/public/projects/{project_id}" \
     -H "X-API-Key: ${API_KEY}"
   ```

2. **Upgrade tier** (contact support or use account API)

---

## 10. INVALID_TIER (422)

**Problem:** Invalid tier value

**Valid Tiers (case-sensitive):**
```python
"free"          # 3 projects
"starter"       # 10 projects
"professional"  # 50 projects
"enterprise"    # Unlimited
```

**Quick Fix:**
```python
# WRONG - wrong case
{"tier": "Free"}
{"tier": "STARTER"}

# RIGHT - lowercase only
{"tier": "free"}
{"tier": "starter"}
```

---

## Debugging Checklist

When you hit an error, check these in order:

1. [ ] **API Key present?** Add `-H "X-API-Key: your_key"`
2. [ ] **Correct endpoint?** Check URL path and HTTP method
3. [ ] **Required fields?** Check `validation_errors` in response
4. [ ] **Correct types?** Numbers vs strings, arrays vs objects
5. [ ] **Same model?** Store and search must use identical model
6. [ ] **Valid namespace?** Only `a-z`, `A-Z`, `0-9`, `_`, `-`
7. [ ] **Project exists?** List projects to verify ID

---

## Copy-Paste Templates

### Basic Request with Auth
```bash
curl -X POST "${BASE_URL}/v1/public/projects" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "tier": "free"}'
```

### Embed and Store
```bash
curl -X POST "${BASE_URL}/v1/public/${PROJECT_ID}/embeddings/embed-and-store" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your text here",
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "default"
  }'
```

### Search (Same Model!)
```bash
curl -X POST "${BASE_URL}/v1/public/${PROJECT_ID}/embeddings/search" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Your search query",
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "default",
    "top_k": 10
  }'
```

---

## Need More Help?

- **Full Error Reference:** [/docs/api/ERROR_CODES_REFERENCE.md](/docs/api/ERROR_CODES_REFERENCE.md)
- **API Specification:** [/docs/api/api-spec.md](/docs/api/api-spec.md)
- **Model Guide:** [/docs/api/MODEL_CONSISTENCY_GUIDE.md](/docs/api/MODEL_CONSISTENCY_GUIDE.md)
- **Interactive Docs:** `${BASE_URL}/docs` (Swagger UI)
