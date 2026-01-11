# Model Consistency Guide

**Version:** v1.0
**Last Updated:** 2026-01-10
**Related:** Epic 4, Story 5 (Issue #20)
**PRD Reference:** Section 10 (Determinism)

---

## Overview

**CRITICAL REQUIREMENT:** You MUST use the **SAME embedding model** for both storing documents and searching them. Using different models will result in poor search quality, incorrect results, or complete search failures.

This guide explains:
- Why model consistency matters
- What happens when models don't match
- How to ensure correct usage
- Troubleshooting model mismatch issues

---

## Why Model Consistency Matters

### The Math Behind Embeddings

Embedding models transform text into high-dimensional vectors. Each model:
1. Uses different training data
2. Produces vectors in different dimensional spaces
3. Encodes semantic meaning differently

**Example:**
```
Text: "compliance check passed"

Model A (384 dims): [0.123, -0.456, 0.789, ...]  ← Space A
Model B (768 dims): [0.891, 0.234, -0.567, ...]  ← Space B
```

These vectors exist in **completely different mathematical spaces**. Comparing them is like comparing meters to pounds.

### What Breaks When Models Don't Match

| Issue | Cause | Impact |
|-------|-------|--------|
| **Dimension Mismatch Error** | Store: 384 dims, Search: 768 dims | `DIMENSION_MISMATCH` error, search fails |
| **Poor Search Results** | Store: Model A, Search: Model A but re-initialized | Inconsistent results, low similarity scores |
| **Semantic Drift** | Store: English model, Search: Multilingual model | Relevant documents not found |
| **Complete Search Failure** | Different model families | No relevant results returned |

---

## The Golden Rule

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  IF you store with Model X, you MUST search with Model X │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Correct Pattern

```python
# ✅ CORRECT: Same model for store and search
CHOSEN_MODEL = "BAAI/bge-small-en-v1.5"  # 384 dimensions

# Store documents
store_response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
    headers={"X-API-Key": API_KEY},
    json={
        "documents": [
            {"id": "doc1", "text": "Compliance check passed for TX-123"},
            {"id": "doc2", "text": "Risk score: low for customer ABC"}
        ],
        "model": CHOSEN_MODEL,  # ← Using Model X
        "namespace": "compliance_events"
    }
)

# Search documents
search_response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "find compliance results",
        "model": CHOSEN_MODEL,  # ← Using SAME Model X
        "namespace": "compliance_events",
        "top_k": 5
    }
)
```

### Incorrect Pattern

```python
# ❌ INCORRECT: Different models for store and search
# Store with small model
store_response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
    headers={"X-API-Key": API_KEY},
    json={
        "documents": [...],
        "model": "BAAI/bge-small-en-v1.5",  # ← 384 dimensions
        "namespace": "compliance_events"
    }
)

# Search with large model
search_response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "find compliance results",
        "model": "sentence-transformers/all-mpnet-base-v2",  # ❌ 768 dimensions - WRONG!
        "namespace": "compliance_events"
    }
)

# Result: DIMENSION_MISMATCH error or poor results
```

---

## Common Mistake Patterns

### Mistake 1: Omitting Model in Search

```python
# Store with explicit model
store_response = requests.post(..., json={
    "model": "sentence-transformers/all-mpnet-base-v2",  # 768 dims
    "documents": [...]
})

# ❌ Search omits model (uses default 384 dims)
search_response = requests.post(..., json={
    "query": "find documents",
    # model parameter omitted - defaults to BAAI/bge-small-en-v1.5 (384 dims)
})

# Result: DIMENSION_MISMATCH error (768 vs 384)
```

**Fix:**
```python
# ✅ Explicitly specify same model in search
search_response = requests.post(..., json={
    "query": "find documents",
    "model": "sentence-transformers/all-mpnet-base-v2"  # Match store model
})
```

### Mistake 2: Changing Models Mid-Project

```python
# Week 1: Store with default model
store_response_week1 = requests.post(..., json={
    # model omitted - uses BAAI/bge-small-en-v1.5
    "documents": [{"id": "old-doc", "text": "old data"}]
})

# Week 2: Decide to use better model
store_response_week2 = requests.post(..., json={
    "model": "sentence-transformers/all-mpnet-base-v2",  # Different model!
    "documents": [{"id": "new-doc", "text": "new data"}]
})

# ❌ Now you have mixed models in same namespace
# Search will only work well for documents matching search model
```

**Fix:**
```python
# Option 1: Use namespaces to separate model spaces
store_week1 = requests.post(..., json={
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "old_data_384",  # ← Model-specific namespace
    "documents": [...]
})

store_week2 = requests.post(..., json={
    "model": "sentence-transformers/all-mpnet-base-v2",
    "namespace": "new_data_768",  # ← Different namespace for different model
    "documents": [...]
})

# Option 2: Re-embed all old documents with new model
# Then search new namespace
```

### Mistake 3: Model Name Typos

```python
# Store with correct model name
store_response = requests.post(..., json={
    "model": "BAAI/bge-small-en-v1.5",
    "documents": [...]
})

# ❌ Search with typo in model name
search_response = requests.post(..., json={
    "model": "BAAI/bge-small-en-v1.5 ",  # Extra space!
    "query": "find documents"
})

# Result: MODEL_NOT_FOUND error or uses default model
```

**Fix:**
```python
# Define model as constant to avoid typos
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

store_response = requests.post(..., json={"model": EMBEDDING_MODEL, ...})
search_response = requests.post(..., json={"model": EMBEDDING_MODEL, ...})
```

---

## Best Practices

### 1. Define Model as Configuration Constant

```python
# config.py
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384

# store.py
from config import EMBEDDING_MODEL

def store_documents(docs):
    return requests.post(..., json={
        "model": EMBEDDING_MODEL,
        "documents": docs
    })

# search.py
from config import EMBEDDING_MODEL

def search_documents(query):
    return requests.post(..., json={
        "model": EMBEDDING_MODEL,
        "query": query
    })
```

### 2. Use Namespace Per Model

```python
# When you must use multiple models, use separate namespaces
MODELS = {
    "fast": {
        "model": "BAAI/bge-small-en-v1.5",
        "namespace": "embeddings_384",
        "dimensions": 384
    },
    "quality": {
        "model": "sentence-transformers/all-mpnet-base-v2",
        "namespace": "embeddings_768",
        "dimensions": 768
    }
}

# Store with model A in namespace A
store_response = requests.post(..., json={
    "model": MODELS["fast"]["model"],
    "namespace": MODELS["fast"]["namespace"],
    "documents": [...]
})

# Search same namespace with same model
search_response = requests.post(..., json={
    "model": MODELS["fast"]["model"],
    "namespace": MODELS["fast"]["namespace"],
    "query": "..."
})
```

### 3. Document Model Selection in Code

```python
"""
Agent Memory Module

EMBEDDING MODEL: BAAI/bge-small-en-v1.5 (384 dimensions)
NAMESPACE: agent_memory

⚠️ WARNING: Do NOT change the model without re-embedding ALL documents.
Changing models will break semantic search.

Last reviewed: 2026-01-10
"""

AGENT_MEMORY_MODEL = "BAAI/bge-small-en-v1.5"
AGENT_MEMORY_NAMESPACE = "agent_memory"
```

### 4. Validate Model Consistency in Tests

```python
import pytest

def test_model_consistency():
    """Ensure store and search use same model."""
    from config import EMBEDDING_MODEL
    from store import store_documents
    from search import search_documents

    # This test fails if models don't match
    store_model = EMBEDDING_MODEL
    search_model = EMBEDDING_MODEL

    assert store_model == search_model, \
        f"Model mismatch! Store: {store_model}, Search: {search_model}"

def test_namespace_model_mapping():
    """Document which model each namespace uses."""
    NAMESPACE_MODELS = {
        "agent_memory": "BAAI/bge-small-en-v1.5",
        "compliance_events": "BAAI/bge-small-en-v1.5",
        "high_quality_search": "sentence-transformers/all-mpnet-base-v2"
    }

    # Enforce model usage per namespace
    for namespace, expected_model in NAMESPACE_MODELS.items():
        # Your validation logic here
        pass
```

---

## Troubleshooting Model Mismatches

### Error: DIMENSION_MISMATCH

**Symptom:**
```json
{
  "detail": "Vector dimension mismatch. Expected 384, got 768",
  "error_code": "DIMENSION_MISMATCH"
}
```

**Cause:** Search query embedding has different dimensions than stored vectors.

**Diagnosis:**
1. Check what model was used to store documents
2. Check what model is being used to search
3. Compare dimensions

**Solutions:**

```python
# Solution 1: Use correct model for search
# If stored with 384-dim model, search with 384-dim model
search_response = requests.post(..., json={
    "model": "BAAI/bge-small-en-v1.5",  # 384 dims - matches storage
    "query": "..."
})

# Solution 2: Re-embed documents with search model
# If you want to use 768-dim model for search:
# 1. Fetch all documents
# 2. Re-embed with new model
# 3. Store in new namespace or update existing

# Solution 3: Use separate namespaces per model
# Store 384-dim vectors in namespace_384
# Store 768-dim vectors in namespace_768
# Search appropriate namespace
```

### Error: No Results Found (Semantic Drift)

**Symptom:**
- Search completes without error
- Returns empty results or very low similarity scores
- Documents definitely exist in namespace

**Cause:** Different models encode semantics differently, even with same dimensions.

**Example:**
```python
# Stored with Model A
store_response = requests.post(..., json={
    "model": "BAAI/bge-small-en-v1.5",
    "documents": [{"text": "compliance check passed"}]
})

# Search with Model B (even if same dimensions)
search_response = requests.post(..., json={
    "model": "sentence-transformers/all-MiniLM-L6-v2",  # Different model, same 384 dims
    "query": "compliance"
})
# Result: Poor results despite same dimensions
```

**Diagnosis:**
1. Verify model name matches exactly between store and search
2. Check for typos or extra spaces in model names
3. Confirm model didn't change between operations

**Solution:**
```python
# Use exact same model name
MODEL = "BAAI/bge-small-en-v1.5"

# Store
requests.post(..., json={"model": MODEL, ...})

# Search
requests.post(..., json={"model": MODEL, ...})
```

### Error: MODEL_NOT_FOUND

**Symptom:**
```json
{
  "detail": "Model 'BAAI/bge-small-v1.5' is not supported",
  "error_code": "MODEL_NOT_FOUND"
}
```

**Cause:** Model name typo or unsupported model.

**Solution:**
1. List supported models:
   ```bash
   curl -X GET "${BASE_URL}/v1/public/embeddings/models" \
     -H "X-API-Key: ${API_KEY}"
   ```

2. Use exact model name from supported list:
   ```python
   # ✅ Correct
   "model": "BAAI/bge-small-en-v1.5"

   # ❌ Common typos
   "model": "BAAI/bge-small-v1.5"      # Missing 'en'
   "model": "bge-small-en-v1.5"        # Missing 'BAAI/'
   "model": "BAAI/bge-small-en-v1.5 "  # Extra space
   ```

---

## Default Model Behavior

### When Model is Omitted

Per DX Contract Section 3:

```python
# If model is omitted, API uses default: BAAI/bge-small-en-v1.5 (384 dims)
response = requests.post(..., json={
    # "model" parameter omitted
    "documents": [...]
})

# This is EQUIVALENT to:
response = requests.post(..., json={
    "model": "BAAI/bge-small-en-v1.5",
    "documents": [...]
})
```

**Recommendation:** Always specify model explicitly to avoid confusion.

```python
# ✅ BETTER: Explicit model specification
response = requests.post(..., json={
    "model": "BAAI/bge-small-en-v1.5",  # Explicit, clear intent
    "documents": [...]
})
```

---

## Migration Guide: Changing Models

If you need to change models for a namespace:

### Step 1: Audit Current State

```python
# Document current model and namespace
CURRENT_STATE = {
    "namespace": "agent_memory",
    "model": "BAAI/bge-small-en-v1.5",
    "dimensions": 384,
    "document_count": 1500
}
```

### Step 2: Choose Migration Strategy

**Option A: Create New Namespace (Recommended)**
```python
# Store new documents in new namespace with new model
NEW_NAMESPACE = "agent_memory_v2"
NEW_MODEL = "sentence-transformers/all-mpnet-base-v2"

# Old data stays in old namespace
# New data goes to new namespace
# Update search logic to query new namespace
```

**Option B: Re-embed All Documents**
```python
# 1. Fetch all documents from old namespace
old_docs = fetch_all_documents(namespace="agent_memory")

# 2. Re-embed with new model
for doc in old_docs:
    store_response = requests.post(..., json={
        "model": NEW_MODEL,
        "namespace": "agent_memory",  # Same namespace
        "documents": [{"id": doc["id"], "text": doc["text"]}],
        "upsert": True  # Update existing
    })

# 3. Update all search calls to use new model
```

### Step 3: Update Configuration

```python
# config.py - Before
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# config.py - After
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

# Add comment documenting change
"""
Model changed from BAAI/bge-small-en-v1.5 to all-mpnet-base-v2
Date: 2026-01-10
Reason: Better search quality needed
Migration: Re-embedded all documents in agent_memory namespace
"""
```

### Step 4: Verify Migration

```python
# Test search quality after migration
def verify_migration():
    # Store test document
    test_doc = {"id": "test-1", "text": "compliance check passed"}
    store_response = requests.post(..., json={
        "model": NEW_MODEL,
        "documents": [test_doc]
    })

    # Search for it
    search_response = requests.post(..., json={
        "model": NEW_MODEL,
        "query": "compliance"
    })

    # Verify found
    assert len(search_response.json()["results"]) > 0
    assert search_response.json()["results"][0]["id"] == "test-1"
```

---

## API Endpoint Documentation

### embed-and-store Endpoint

**⚠️ MODEL CONSISTENCY WARNING:**
The model you specify here MUST be used for all future searches in this namespace.

```bash
POST /v1/public/{project_id}/embeddings/embed-and-store

Request Body:
{
  "documents": [...],
  "model": "BAAI/bge-small-en-v1.5",  # ← Remember this model!
  "namespace": "my_namespace"
}
```

**Remember:** Write down the model you use. You'll need it for search.

### search Endpoint

**⚠️ MODEL CONSISTENCY WARNING:**
Use the SAME model that was used in embed-and-store for this namespace.

```bash
POST /v1/public/{project_id}/embeddings/search

Request Body:
{
  "query": "...",
  "model": "BAAI/bge-small-en-v1.5",  # ← MUST match embed-and-store model
  "namespace": "my_namespace"
}
```

**If you get DIMENSION_MISMATCH or poor results:** Check that this model matches the model used in embed-and-store.

---

## Summary: Quick Reference

| ✅ DO | ❌ DON'T |
|-------|----------|
| Use same model for store and search | Use different models for same namespace |
| Define model as configuration constant | Hard-code model strings everywhere |
| Document model choice in code | Change models without re-embedding |
| Use namespaces to separate model spaces | Mix models in same namespace |
| Specify model explicitly | Rely on defaults without documenting |
| Test model consistency | Assume all models are interchangeable |

---

## Related Documentation

- [DX Contract Section 3: Embeddings & Vectors](/DX-Contract.md)
- [Embeddings API Specification](/docs/api/embeddings-api-spec.md)
- [PRD Section 10: Determinism](/prd.md)
- [ZeroDB Developer Guide](/datamodel.md)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-10 | Initial guide created (Issue #20) |

---

**Remember: Same namespace → Same model → Successful search** 🎯
