# Model Consistency for Embed and Store Operations

**Version:** v1.0
**Last Updated:** 2026-01-11
**Related:** Epic 4, Issue #20
**PRD Reference:** Section 10 (Determinism)

---

## Overview

This document provides comprehensive guidance on maintaining model consistency when using the embed-and-store and semantic search APIs. Failing to use the same model for both operations is one of the most common causes of search failures.

> **WARNING:** Using different embedding models for store and search operations will cause search failures, dimension mismatch errors, or semantically incorrect results. Always use the SAME model for both operations.

---

## The Fundamental Rule

```
+------------------------------------------------------------------+
|                                                                  |
|   SAME MODEL must be used for BOTH store AND search operations   |
|                                                                  |
|   embed-and-store(model="X") --> search(model="X")               |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Supported Models and Dimensions

The following embedding models are supported. Each model produces vectors of a specific dimension that MUST match between store and search operations.

### Model Dimension Reference Table

| Model Name | Dimensions | Performance | Use Case |
|------------|------------|-------------|----------|
| **BAAI/bge-small-en-v1.5** | 384 | Fast | General purpose, DEFAULT model |
| sentence-transformers/all-MiniLM-L6-v2 | 384 | Fast | Lightweight, efficient |
| sentence-transformers/all-MiniLM-L12-v2 | 384 | Medium | Balanced speed/quality |
| sentence-transformers/all-mpnet-base-v2 | 768 | Slower | High quality results |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | Medium | Multi-language support |
| sentence-transformers/all-distilroberta-v1 | 768 | Slower | Robust encoding |
| sentence-transformers/msmarco-distilbert-base-v4 | 768 | Slower | Search-optimized |

### Dimension Groups

**384-dimension models:**
- BAAI/bge-small-en-v1.5 (DEFAULT)
- sentence-transformers/all-MiniLM-L6-v2
- sentence-transformers/all-MiniLM-L12-v2
- paraphrase-multilingual-MiniLM-L12-v2

**768-dimension models:**
- sentence-transformers/all-mpnet-base-v2
- sentence-transformers/all-distilroberta-v1
- sentence-transformers/msmarco-distilbert-base-v4

---

## Critical Warning: Mixing Models Causes Failures

> **DANGER ZONE**
>
> Mixing embedding models between store and search operations will result in:
>
> 1. **DIMENSION_MISMATCH errors** - When models have different output dimensions (e.g., 384 vs 768)
> 2. **Poor search quality** - When models have same dimensions but different semantic encoding
> 3. **No results found** - Documents exist but cannot be matched due to incompatible embeddings
> 4. **Unpredictable behavior** - Results that seem random or irrelevant

### What Happens When You Mix Models

| Store Model | Search Model | Result |
|-------------|--------------|--------|
| BAAI/bge-small-en-v1.5 (384) | BAAI/bge-small-en-v1.5 (384) | SUCCESS |
| BAAI/bge-small-en-v1.5 (384) | all-mpnet-base-v2 (768) | DIMENSION_MISMATCH ERROR |
| BAAI/bge-small-en-v1.5 (384) | all-MiniLM-L6-v2 (384) | POOR RESULTS (semantic drift) |
| all-mpnet-base-v2 (768) | all-mpnet-base-v2 (768) | SUCCESS |
| all-mpnet-base-v2 (768) | all-distilroberta-v1 (768) | POOR RESULTS (semantic drift) |

---

## Best Practices

### 1. Always Specify Model Explicitly

Do not rely on defaults in production. Always explicitly specify the model parameter.

```python
# config.py - Define model as constant
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384
NAMESPACE = "agent_memory"
```

```python
# store.py - Use constant for store
from config import EMBEDDING_MODEL, NAMESPACE

response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
    headers={"X-API-Key": API_KEY},
    json={
        "documents": [{"id": "doc1", "text": "..."}],
        "model": EMBEDDING_MODEL,  # Explicit model
        "namespace": NAMESPACE
    }
)
```

```python
# search.py - Use SAME constant for search
from config import EMBEDDING_MODEL, NAMESPACE

response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "find documents",
        "model": EMBEDDING_MODEL,  # Same model as store
        "namespace": NAMESPACE
    }
)
```

### 2. Use Namespace-Per-Model Strategy

When you need to use multiple models, create separate namespaces for each model.

```python
MODEL_CONFIGS = {
    "fast": {
        "model": "BAAI/bge-small-en-v1.5",
        "namespace": "agent_memory_384",
        "dimensions": 384
    },
    "quality": {
        "model": "sentence-transformers/all-mpnet-base-v2",
        "namespace": "agent_memory_768",
        "dimensions": 768
    }
}

# Store with fast model
config = MODEL_CONFIGS["fast"]
store_documents(model=config["model"], namespace=config["namespace"])

# Search with same configuration
search_documents(model=config["model"], namespace=config["namespace"])
```

### 3. Document Your Model Choice

Add comments documenting which model is used for each namespace.

```python
"""
Agent Memory Configuration

NAMESPACE: agent_memory
MODEL: BAAI/bge-small-en-v1.5
DIMENSIONS: 384

IMPORTANT: Do NOT change the model without re-embedding ALL documents.
Changing models will break semantic search.

Last reviewed: 2026-01-11
"""
```

### 4. Validate Consistency in Tests

```python
import pytest

def test_model_consistency():
    """Ensure store and search use the same model."""
    from config import EMBEDDING_MODEL

    # These should be imported from the same config
    store_model = EMBEDDING_MODEL
    search_model = EMBEDDING_MODEL

    assert store_model == search_model, \
        f"Model mismatch! Store: {store_model}, Search: {search_model}"
```

---

## Code Examples

### Correct Usage Pattern (curl)

**Step 1: Store documents with explicit model**

```bash
# Store documents
curl -X POST "https://api.ainative.studio/v1/public/${PROJECT_ID}/embeddings/embed-and-store" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"id": "doc1", "text": "Compliance check passed for TX-123"},
      {"id": "doc2", "text": "Risk assessment completed for customer ABC"}
    ],
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "compliance_events"
  }'
```

**Step 2: Search with SAME model**

```bash
# Search with same model
curl -X POST "https://api.ainative.studio/v1/public/${PROJECT_ID}/embeddings/search" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "find compliance results",
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "compliance_events",
    "top_k": 5
  }'
```

### Correct Usage Pattern (Python)

```python
import requests
import os

# Configuration - single source of truth for model
class EmbeddingConfig:
    MODEL = "BAAI/bge-small-en-v1.5"
    DIMENSIONS = 384
    NAMESPACE = "agent_memory"

    BASE_URL = "https://api.ainative.studio"
    PROJECT_ID = os.getenv("PROJECT_ID")
    API_KEY = os.getenv("API_KEY")

def store_documents(documents: list[dict]) -> dict:
    """Store documents with configured model."""
    response = requests.post(
        f"{EmbeddingConfig.BASE_URL}/v1/public/{EmbeddingConfig.PROJECT_ID}/embeddings/embed-and-store",
        headers={
            "X-API-Key": EmbeddingConfig.API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "documents": documents,
            "model": EmbeddingConfig.MODEL,  # Use config
            "namespace": EmbeddingConfig.NAMESPACE
        }
    )
    response.raise_for_status()
    return response.json()

def search_documents(query: str, top_k: int = 5) -> dict:
    """Search documents with SAME configured model."""
    response = requests.post(
        f"{EmbeddingConfig.BASE_URL}/v1/public/{EmbeddingConfig.PROJECT_ID}/embeddings/search",
        headers={
            "X-API-Key": EmbeddingConfig.API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": query,
            "model": EmbeddingConfig.MODEL,  # Same config
            "namespace": EmbeddingConfig.NAMESPACE,
            "top_k": top_k
        }
    )
    response.raise_for_status()
    return response.json()

# Usage
documents = [
    {"id": "doc1", "text": "Agent completed compliance check"},
    {"id": "doc2", "text": "Transaction approved after risk assessment"}
]

# Store
result = store_documents(documents)
print(f"Stored {result['stored_count']} documents")

# Search
results = search_documents("compliance check status")
for item in results["results"]:
    print(f"  - {item['text']} (similarity: {item['similarity']:.2f})")
```

### Incorrect Usage Pattern (Avoid This)

```python
# DO NOT DO THIS - mixing models

# Store with default model (384 dims)
requests.post(..., json={
    "documents": [...],
    # model omitted - uses BAAI/bge-small-en-v1.5 (384)
})

# Search with different model (768 dims) - THIS WILL FAIL
requests.post(..., json={
    "query": "find documents",
    "model": "sentence-transformers/all-mpnet-base-v2"  # WRONG!
})

# Result: DIMENSION_MISMATCH error
```

---

## Troubleshooting

### Error: DIMENSION_MISMATCH

**Symptom:**
```json
{
  "detail": "Vector dimension mismatch. Expected 384, got 768",
  "error_code": "DIMENSION_MISMATCH"
}
```

**Cause:** The search query was embedded with a model that produces different dimensions than the stored vectors.

**Solution:**
1. Identify the model used during embed-and-store
2. Use the exact same model for search
3. If you need a different model, create a new namespace

### Error: Poor Search Results or No Results

**Symptom:**
- Search returns empty results
- Results have very low similarity scores
- Results are semantically incorrect

**Cause:** Using different models with the same dimensions (semantic drift).

**Solution:**
1. Verify the model name is exactly the same (check for typos)
2. Verify the namespace is correct
3. Use a configuration constant to ensure consistency

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
1. Check for typos in model name
2. Use the exact model name from the supported models table
3. List available models: `GET /v1/public/embeddings/models`

---

## Migration: Changing Models

If you need to change models for existing data:

### Option 1: Create New Namespace (Recommended)

```python
# Old namespace stays with old model
OLD_CONFIG = {"model": "BAAI/bge-small-en-v1.5", "namespace": "data_v1"}

# New namespace for new model
NEW_CONFIG = {"model": "sentence-transformers/all-mpnet-base-v2", "namespace": "data_v2"}

# All new data goes to new namespace
store_documents(model=NEW_CONFIG["model"], namespace=NEW_CONFIG["namespace"])
search_documents(model=NEW_CONFIG["model"], namespace=NEW_CONFIG["namespace"])
```

### Option 2: Re-embed All Documents

```python
# 1. Export all documents from old namespace
old_documents = export_all_documents(namespace="data_v1")

# 2. Re-embed with new model
for doc in old_documents:
    store_document(
        id=doc["id"],
        text=doc["text"],
        model="sentence-transformers/all-mpnet-base-v2",
        namespace="data_v1",  # Same namespace
        upsert=True  # Update existing
    )

# 3. Update configuration
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
```

---

## Summary Checklist

Before implementing embed-and-store with search:

- [ ] Choose a single embedding model for your namespace
- [ ] Define model as a configuration constant
- [ ] Use the same constant for both store and search operations
- [ ] Document your model choice in code comments
- [ ] Add tests to verify model consistency
- [ ] Use namespace-per-model strategy if multiple models needed

---

## Related Documentation

- [Model Consistency Guide](/docs/api/MODEL_CONSISTENCY_GUIDE.md) - General model consistency principles
- [Quick Reference Guide](/docs/quick-reference/EMBED_STORE_MODEL_GUIDE.md) - Quick lookup card
- [Embed and Store API](/docs/api/EMBED_AND_STORE_API.md) - Full API documentation
- [Embeddings Store Search Spec](/docs/api/embeddings-store-search-spec.md) - Complete API specification

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-11 | Initial documentation (Epic 4, Issue #20) |

---

Built by AINative Dev Team
