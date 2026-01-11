# Embeddings API Specification

**Version:** v1
**Last Updated:** 2026-01-10
**Implementation:** GitHub Issue #13
**Base URL:** `https://api.ainative.studio/v1/public`

---

## Overview

The Embeddings API provides vector embedding generation for text data with support for multiple embedding models. This API is designed for:

- Agent memory storage (PRD §6)
- Semantic search capabilities
- Document embedding and retrieval
- Multi-model support with dimension validation (Issue #13)

---

## ⚠️ CRITICAL: Model Consistency Requirement

**YOU MUST USE THE SAME MODEL FOR STORE AND SEARCH OPERATIONS**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  IF you store with Model X, you MUST search with Model X │
│                                                         │
│  Failure to do so results in:                          │
│  • Poor search quality                                  │
│  • Incorrect or no results                              │
│  • DIMENSION_MISMATCH errors                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**See the comprehensive [Model Consistency Guide](/docs/api/MODEL_CONSISTENCY_GUIDE.md) for:**
- Why model consistency matters
- What happens when models don't match
- Troubleshooting guide for model mismatch issues
- Best practices for model selection and usage

**Quick Rule:** Define your model once as a constant and use it everywhere.

```python
# ✅ CORRECT PATTERN
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Use for storing
store(model=EMBEDDING_MODEL, ...)

# Use for searching
search(model=EMBEDDING_MODEL, ...)
```

---

## Authentication

All embedding endpoints require authentication via the `X-API-Key` header.

**IMPORTANT:** API keys must only be used in server-side environments. See [SECURITY.md](/SECURITY.md) for details.

```bash
curl -X POST "https://api.ainative.studio/v1/public/embeddings/generate" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json"
```

---

## Supported Models

Issue #13 implements multi-model support with the following embedding models:

| Model | Dimensions | Description | Use Case |
|-------|------------|-------------|----------|
| **BAAI/bge-small-en-v1.5** | 384 | Lightweight, fast, good quality (default) | General purpose, agent memory |
| sentence-transformers/all-MiniLM-L6-v2 | 384 | Fast and efficient | Semantic similarity |
| sentence-transformers/all-MiniLM-L12-v2 | 384 | Balanced performance | General purpose |
| sentence-transformers/all-mpnet-base-v2 | 768 | High-quality embeddings | Advanced search |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | 384 | Multi-lingual support | 50+ languages |
| sentence-transformers/all-distilroberta-v1 | 768 | RoBERTa-based | High quality |
| sentence-transformers/msmarco-distilbert-base-v4 | 768 | Optimized for search | Semantic retrieval |

### Default Model (DX Contract §3)

**Model:** `BAAI/bge-small-en-v1.5`
**Dimensions:** 384
**Guarantee:** This default will not change without a version bump

When the `model` parameter is omitted, the API automatically uses the default model. This behavior is guaranteed per DX Contract §3.

---

## Endpoints

### 1. Generate Embeddings

Generate vector embeddings from text using a specified model.

**Endpoint:** `POST /v1/public/embeddings/generate`

**Authentication:** Required (`X-API-Key` header)

**Request Body:**

```json
{
  "text": "string (required, non-empty)",
  "model": "string (optional, defaults to BAAI/bge-small-en-v1.5)"
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Text to generate embeddings from (non-empty, no whitespace-only) |
| `model` | string | No | Embedding model to use (see Supported Models table) |

**Success Response (200 OK):**

```json
{
  "embedding": [0.123, -0.456, 0.789, "..."],
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "text": "Autonomous fintech agent executing compliance check",
  "processing_time_ms": 45.67
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `embedding` | array[float] | Generated embedding vector (length = dimensions) |
| `model` | string | Model actually used (includes default if omitted) |
| `dimensions` | integer | Dimensionality of the embedding vector |
| `text` | string | Original input text (for verification) |
| `processing_time_ms` | float | Processing time in milliseconds |

**Error Responses:**

```json
// 401 Unauthorized - Invalid API key
{
  "detail": "Invalid API key",
  "error_code": "INVALID_API_KEY"
}

// 422 Unprocessable Entity - Validation error
{
  "detail": [
    {
      "loc": ["body", "text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

// 422 - Unsupported model
{
  "detail": [
    {
      "loc": ["body", "model"],
      "msg": "Model 'invalid-model' is not supported. Supported models: ...",
      "type": "value_error"
    }
  ]
}
```

**Example Request with Default Model:**

```bash
curl -X POST "https://api.ainative.studio/v1/public/embeddings/generate" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Agent memory: Compliance check passed for transaction TX-123"
  }'
```

**Example Request with Specific Model:**

```bash
curl -X POST "https://api.ainative.studio/v1/public/embeddings/generate" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "High-quality semantic search query",
    "model": "sentence-transformers/all-mpnet-base-v2"
  }'
```

**Python Example:**

```python
import requests

# Using default model (384 dimensions)
response = requests.post(
    "https://api.ainative.studio/v1/public/embeddings/generate",
    headers={"X-API-Key": "your_api_key"},
    json={"text": "Compliance check for TX-123"}
)

data = response.json()
print(f"Model: {data['model']}")
print(f"Dimensions: {data['dimensions']}")
print(f"Vector length: {len(data['embedding'])}")
# Output: Model: BAAI/bge-small-en-v1.5, Dimensions: 384, Vector length: 384

# Using specific model (768 dimensions)
response = requests.post(
    "https://api.ainative.studio/v1/public/embeddings/generate",
    headers={"X-API-Key": "your_api_key"},
    json={
        "text": "High-quality search query",
        "model": "sentence-transformers/all-mpnet-base-v2"
    }
)

data = response.json()
print(f"Dimensions: {data['dimensions']}")
# Output: Dimensions: 768
```

---

### 2. List Supported Models

Get information about all supported embedding models.

**Endpoint:** `GET /v1/public/embeddings/models`

**Authentication:** Required (`X-API-Key` header)

**Success Response (200 OK):**

```json
{
  "models": {
    "BAAI/bge-small-en-v1.5": {
      "dimensions": 384,
      "description": "Lightweight English model with good quality/speed trade-off (default)",
      "languages": ["en"],
      "max_seq_length": 512
    },
    "sentence-transformers/all-mpnet-base-v2": {
      "dimensions": 768,
      "description": "High-quality embeddings with larger dimension",
      "languages": ["en"],
      "max_seq_length": 384
    }
    // ... other models
  },
  "default_model": "BAAI/bge-small-en-v1.5",
  "total_models": 7
}
```

**Example Request:**

```bash
curl -X GET "https://api.ainative.studio/v1/public/embeddings/models" \
  -H "X-API-Key: your_api_key_here"
```

---

## DX Contract Guarantees (Issue #13)

### Model Behavior Guarantees

1. **Default Model Stability:** The default model (`BAAI/bge-small-en-v1.5`, 384 dimensions) will not change without a version bump

2. **Dimension Consistency:** Each model always returns the same number of dimensions:
   - Same model + multiple requests → same dimensions
   - Dimensions match model specification exactly

3. **Model Validation:** Unsupported models return clear validation errors listing all supported models

4. **Response Format:** All responses include:
   - `model` field indicating which model was used
   - `dimensions` field matching the model's specification
   - `embedding` array with length == dimensions

### Backward Compatibility

- Omitting the `model` parameter continues to work (uses default)
- Response format remains stable across updates
- Error codes and messages are consistent

---

## Model Selection Guidelines

### When to Use Each Model

**384-Dimension Models (Faster, Smaller)**
- Best for: Agent memory, general-purpose embeddings, limited storage
- Models: BAAI/bge-small-en-v1.5, all-MiniLM variants

**768-Dimension Models (Higher Quality)**
- Best for: Advanced search, high-precision retrieval, quality-critical applications
- Models: all-mpnet-base-v2, all-distilroberta-v1, msmarco-distilbert-base-v4

**Multi-lingual Models**
- Best for: Non-English text, multi-language applications
- Models: paraphrase-multilingual-MiniLM-L12-v2

### Important Considerations

1. **⚠️ CRITICAL - Model Consistency Requirement:**

   **YOU MUST USE THE SAME MODEL FOR STORING AND SEARCHING**

   ```python
   # ✅ CORRECT - Same model throughout
   CHOSEN_MODEL = "BAAI/bge-small-en-v1.5"

   # Store documents
   embed_response = generate_embedding(text="doc", model=CHOSEN_MODEL)
   store_response = embed_and_store(documents=[...], model=CHOSEN_MODEL)

   # Search documents - MUST use same model
   search_response = search(query="query", model=CHOSEN_MODEL)

   # ❌ INCORRECT - Different models will break search
   store_response = embed_and_store(documents=[...], model="BAAI/bge-small-en-v1.5")
   search_response = search(query="query", model="sentence-transformers/all-mpnet-base-v2")
   # Result: DIMENSION_MISMATCH error or poor results
   ```

   **What happens when models don't match:**
   - **Dimension mismatch:** `DIMENSION_MISMATCH` error (e.g., 384 vs 768 dims)
   - **Semantic drift:** Poor search results, low similarity scores
   - **No results found:** Documents exist but search can't find them

   **📖 Read the [Model Consistency Guide](/docs/api/MODEL_CONSISTENCY_GUIDE.md) for complete details, troubleshooting, and best practices.**

2. **Storage Impact:** Higher dimensions = more storage required
   - 384 dims: ~1.5 KB per vector
   - 768 dims: ~3 KB per vector

3. **Performance:** Lower dimensions = faster similarity calculations

4. **Best Practice:** Define model as a configuration constant
   ```python
   # config.py
   EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

   # Use everywhere - ensures consistency
   from config import EMBEDDING_MODEL
   ```

---

## Testing Requirements (Issue #13)

Per the implementation requirements, all integrations MUST validate:

1. Default model returns 384 dimensions when model omitted
2. Each supported model returns correct dimensions
3. Unsupported models return validation errors
4. Response format includes all required fields
5. Same model produces consistent dimensions across requests

**Example Test:**

```python
import pytest

def test_default_model_dimensions():
    """Test that default model returns 384 dimensions."""
    response = client.post(
        "/v1/public/embeddings/generate",
        headers={"X-API-Key": api_key},
        json={"text": "test"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "BAAI/bge-small-en-v1.5"
    assert data["dimensions"] == 384
    assert len(data["embedding"]) == 384

def test_all_models_work():
    """Test each supported model."""
    models = {
        "BAAI/bge-small-en-v1.5": 384,
        "sentence-transformers/all-mpnet-base-v2": 768,
        # ... etc
    }

    for model, expected_dims in models.items():
        response = client.post(
            "/v1/public/embeddings/generate",
            headers={"X-API-Key": api_key},
            json={"text": "test", "model": model}
        )

        assert response.status_code == 200
        assert response.json()["dimensions"] == expected_dims
```

---

## Integration with Agent Workflows

When CrewAI agents or autonomous systems use embeddings:

1. **Agent Memory:** Store agent decisions and observations
   ```python
   embedding_response = generate_embedding(
       text="Compliance check passed for TX-123",
       model="BAAI/bge-small-en-v1.5"  # Or omit for default
   )
   ```

2. **Semantic Search:** Retrieve relevant historical context
   ```python
   # Use same model for consistency
   search(query="compliance TX-", model="BAAI/bge-small-en-v1.5")
   ```

3. **Event Logging:** Log embedding generation events
   ```python
   create_event({
       "event_type": "embedding_generated",
       "data": {
           "model": response["model"],
           "dimensions": response["dimensions"],
           "processing_time_ms": response["processing_time_ms"]
       }
   })
   ```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-10 | Initial specification with multi-model support (Issue #13) |

---

## Related Documentation

- [ZeroDB Developer Guide](/datamodel.md)
- [DX Contract](/DX-Contract.md)
- [PRD Section 6: ZeroDB Integration](/prd.md)
- [PRD Section 12: Extensibility](/prd.md)
- [Backlog Epic 3: Embeddings API](/backlog.md)
- [Security Guidelines](/SECURITY.md)
