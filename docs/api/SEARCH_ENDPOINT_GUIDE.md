# Embeddings Search Endpoint - Quick Reference Guide

**Endpoint:** `POST /v1/public/{project_id}/embeddings/search`
**Implementation:** Issue #21 (Epic 5, Story 1 - 2 points)
**Last Updated:** 2026-01-11

---

## Overview

The embeddings search endpoint enables semantic similarity search over stored vectors. It accepts a query text, generates an embedding, and returns matching documents ordered by similarity score (highest first).

**Key Features:**
- ✅ Query text to embedding generation
- ✅ Similarity search against stored vectors
- ✅ Results ordered by similarity (highest first)
- ✅ Namespace scoping for multi-agent isolation
- ✅ Similarity threshold filtering
- ✅ Metadata filtering
- ✅ Top-k result limiting
- ✅ Optional embedding inclusion for debugging

---

## Environment Setup

```bash
# Set environment variables first
export API_KEY="your_api_key_here"
export PROJECT_ID="proj_123"
export BASE_URL="https://api.ainative.studio"
```

## Quick Start

### Basic Search

```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/embeddings/search" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compliance check results for transaction"
  }'
```

### Python Example

```python
import requests
import os

# Use environment variables
API_KEY = os.getenv('API_KEY', 'your_api_key_here')
PROJECT_ID = os.getenv('PROJECT_ID', 'proj_123')
BASE_URL = os.getenv('BASE_URL', 'https://api.ainative.studio')

response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    json={"query": "compliance check results"}
)

results = response.json()
for result in results["results"]:
    print(f"Similarity: {result['similarity']:.2f} - {result['text']}")
```

---

## Request Specification

### Endpoint

```
POST /v1/public/{project_id}/embeddings/search
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Your ZeroDB project identifier |

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | **Yes** | Your API key for authentication |
| `Content-Type` | **Yes** | Must be `application/json` |

### Request Body

```json
{
  "query": "find compliance results for customer ABC-123",
  "model": "BAAI/bge-small-en-v1.5",
  "namespace": "agent_memory",
  "top_k": 5,
  "similarity_threshold": 0.7,
  "metadata_filter": {
    "agent_id": "compliance_agent",
    "status": "completed"
  },
  "include_embeddings": false
}
```

### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | **Yes** | - | Query text for semantic search (non-empty) |
| `model` | string | No | `BAAI/bge-small-en-v1.5` | Embedding model (must match stored vectors) |
| `namespace` | string | No | `default` | Namespace to search within |
| `top_k` | integer | No | 10 | Maximum results to return (1-100) |
| `similarity_threshold` | float | No | 0.0 | Minimum similarity score (0.0-1.0) |
| `metadata_filter` | object | No | `null` | Filter results by metadata key-value pairs |
| `include_embeddings` | boolean | No | `false` | Include embedding vectors in response |

#### Field Details

**query** (required)
- Must be non-empty string
- Whitespace-only strings are rejected
- Supports any text length
- Used to generate query embedding for similarity search

**model** (optional)
- **CRITICAL:** Must match the model used to store vectors
- If vectors stored with `BAAI/bge-small-en-v1.5`, search must use same model
- Using different model causes poor results or dimension mismatch errors
- Defaults to `BAAI/bge-small-en-v1.5` (384 dimensions)
- See [Supported Models](#supported-models) section

**namespace** (optional)
- Scopes search to specific namespace only
- Vectors in other namespaces are never returned
- Use for agent isolation, environment separation, or model organization
- Defaults to `default` namespace
- **Best Practice:** Use one namespace per model

**top_k** (optional)
- Controls maximum number of results returned
- Range: 1 to 100
- Results are top K most similar vectors
- Sorted by similarity descending (highest first)
- Default: 10

**similarity_threshold** (optional)
- Filters results by minimum similarity score
- Range: 0.0 (no filtering) to 1.0 (exact match)
- Only results with `similarity >= threshold` are returned
- Useful for quality control
- Default: 0.0 (return all results)
- Recommended: 0.7 for production use

**metadata_filter** (optional)
- Filters results by exact metadata key-value matching
- All filter conditions must match (AND logic)
- Example: `{"agent_id": "agent_001", "task": "compliance"}`
- Only returns vectors where metadata contains all specified key-value pairs
- Applied before similarity ranking
- Default: `null` (no filtering)

**include_embeddings** (optional)
- Controls whether embedding vectors are included in response
- Set to `true` for debugging or vector analysis
- Significantly increases response size
- Default: `false` (embeddings not included)

---

## Response Specification

### Success Response (200 OK)

```json
{
  "results": [
    {
      "vector_id": "vec_abc123",
      "namespace": "agent_memory",
      "text": "Compliance check passed for customer ABC-123",
      "similarity": 0.92,
      "model": "BAAI/bge-small-en-v1.5",
      "dimensions": 384,
      "metadata": {
        "agent_id": "compliance_agent",
        "customer_id": "ABC-123",
        "status": "completed"
      },
      "created_at": "2026-01-10T12:30:00.000Z"
    },
    {
      "vector_id": "vec_def456",
      "namespace": "agent_memory",
      "text": "Customer ABC-123 risk assessment complete",
      "similarity": 0.85,
      "model": "BAAI/bge-small-en-v1.5",
      "dimensions": 384,
      "metadata": {
        "agent_id": "risk_agent",
        "customer_id": "ABC-123"
      },
      "created_at": "2026-01-10T12:25:00.000Z"
    }
  ],
  "query": "find compliance results for customer ABC-123",
  "namespace": "agent_memory",
  "model": "BAAI/bge-small-en-v1.5",
  "total_results": 2,
  "processing_time_ms": 15
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | Array of matching vectors (sorted by similarity, descending) |
| `query` | string | Original query text |
| `namespace` | string | Namespace that was searched |
| `model` | string | Model used for query embedding |
| `total_results` | integer | Number of results returned |
| `processing_time_ms` | integer | Processing time in milliseconds |

### Result Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `vector_id` | string | Unique identifier of the matched vector |
| `namespace` | string | Namespace where vector was found |
| `text` | string | Original text content of the vector |
| `similarity` | float | Similarity score (0.0-1.0, higher is better) |
| `model` | string | Model used to generate this vector |
| `dimensions` | integer | Vector dimensionality |
| `metadata` | object | Vector metadata (empty object if no metadata) |
| `embedding` | array\<float\> | Vector embedding (only if `include_embeddings: true`) |
| `created_at` | string | ISO 8601 timestamp when vector was created |

---

## Error Responses

### 401 Unauthorized - Missing or Invalid API Key

```json
{
  "detail": "Authentication required. Provide X-API-Key or Authorization Bearer token.",
  "error_code": "UNAUTHORIZED"
}
```

**Cause:** No `X-API-Key` header provided or API key is invalid

**Solution:** Add valid `X-API-Key` header to request

### 422 Unprocessable Entity - Validation Error

**Empty Query:**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "query"],
      "msg": "Value error, Query cannot be empty or whitespace"
    }
  ]
}
```

**Invalid top_k:**
```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "top_k"],
      "msg": "Input should be greater than or equal to 1"
    }
  ]
}
```

**Invalid similarity_threshold:**
```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["body", "similarity_threshold"],
      "msg": "Input should be less than or equal to 1.0"
    }
  ]
}
```

**Cause:** Request validation failed

**Solutions:**
- Ensure `query` is non-empty string
- Ensure `top_k` is between 1 and 100
- Ensure `similarity_threshold` is between 0.0 and 1.0

### 404 Not Found - Unsupported Model

```json
{
  "detail": "Model 'invalid-model' is not supported. Supported models: BAAI/bge-small-en-v1.5, ...",
  "error_code": "MODEL_NOT_FOUND"
}
```

**Cause:** Specified model is not in supported models list

**Solution:** Use one of the supported models (see [Supported Models](#supported-models))

---

## Usage Examples

### Example 1: Basic Search

```python
import requests

BASE_URL = "https://api.ainative.studio"
PROJECT_ID = "proj_123"
API_KEY = "your_api_key"

response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "compliance check results"
    }
)

data = response.json()
print(f"Found {data['total_results']} results:")
for result in data["results"]:
    print(f"- {result['text']} (similarity: {result['similarity']:.2%})")
```

### Example 2: Search with Namespace and Threshold

```python
response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "transaction approval decision",
        "namespace": "agent_decisions",
        "top_k": 3,
        "similarity_threshold": 0.8  # Only high-quality matches
    }
)

data = response.json()
for result in data["results"]:
    print(f"Similarity: {result['similarity']:.2%}")
    print(f"Text: {result['text']}")
    print(f"Metadata: {result['metadata']}")
    print("---")
```

### Example 3: Search with Metadata Filter

```python
response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "customer risk assessment",
        "namespace": "agent_memory",
        "metadata_filter": {
            "agent_id": "risk_agent",
            "status": "completed"
        },
        "top_k": 10
    }
)

# Results will only include vectors where:
# - metadata.agent_id == "risk_agent" AND
# - metadata.status == "completed"
```

### Example 4: Agent Memory Recall

```python
def recall_agent_memory(query: str, agent_id: str, namespace: str = "agent_memory"):
    """Recall relevant agent memories using semantic search."""
    response = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
        headers={"X-API-Key": API_KEY},
        json={
            "query": query,
            "namespace": namespace,
            "metadata_filter": {"agent_id": agent_id},
            "top_k": 5,
            "similarity_threshold": 0.7
        }
    )
    return response.json()

# Recall compliance agent's memories about customer ABC-123
memories = recall_agent_memory(
    query="customer ABC-123 compliance check",
    agent_id="compliance_agent"
)

for memory in memories["results"]:
    print(f"Recalled: {memory['text']}")
    print(f"Confidence: {memory['similarity']:.2%}")
```

### Example 5: Multi-Agent Search

```python
def search_across_agents(query: str, agent_ids: list):
    """Search across multiple agent namespaces."""
    all_results = []

    for agent_id in agent_ids:
        response = requests.post(
            f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": API_KEY},
            json={
                "query": query,
                "namespace": f"{agent_id}_memory",
                "top_k": 3
            }
        )
        results = response.json()
        all_results.extend(results["results"])

    # Sort combined results by similarity
    all_results.sort(key=lambda x: x["similarity"], reverse=True)
    return all_results[:10]  # Top 10 across all agents

# Search memories from compliance and risk agents
results = search_across_agents(
    query="customer ABC-123 assessment",
    agent_ids=["compliance_agent", "risk_agent", "transaction_agent"]
)
```

---

## Supported Models

| Model | Dimensions | Description |
|-------|-----------|-------------|
| `BAAI/bge-small-en-v1.5` | 384 | Default - lightweight, fast, good quality |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Fast semantic similarity |
| `sentence-transformers/all-MiniLM-L12-v2` | 384 | Balanced performance |
| `sentence-transformers/all-mpnet-base-v2` | 768 | High quality, larger vectors |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 | Multi-lingual support (50+ languages) |
| `sentence-transformers/all-distilroberta-v1` | 768 | RoBERTa-based, high quality |
| `sentence-transformers/msmarco-distilbert-base-v4` | 768 | Optimized for search/retrieval |

**⚠️ CRITICAL:** The model used for search **MUST** match the model used to store vectors in that namespace.

---

## Best Practices

### 1. Model Consistency

Always use the same model for storing and searching within a namespace:

```python
# ✅ GOOD - Define model as constant
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
NAMESPACE = "agent_memory"

# Store with defined model
store_response = embed_and_store(
    text="...",
    model=EMBEDDING_MODEL,
    namespace=NAMESPACE
)

# Search with same model
search_response = search(
    query="...",
    model=EMBEDDING_MODEL,
    namespace=NAMESPACE
)
```

### 2. Use Namespaces for Isolation

```python
# ✅ GOOD - Separate namespaces per agent
compliance_results = search(
    query="risk assessment",
    namespace="compliance_agent_memory"
)

transaction_results = search(
    query="risk assessment",
    namespace="transaction_agent_memory"
)

# Results are completely isolated
```

### 3. Set Appropriate Similarity Thresholds

```python
# Quality thresholds for different use cases
THRESHOLDS = {
    "high_precision": 0.9,  # Very strict, few results
    "production": 0.7,      # Good balance
    "exploratory": 0.5,     # More permissive
    "all_results": 0.0      # No filtering
}

# Use appropriate threshold for use case
results = search(
    query="...",
    similarity_threshold=THRESHOLDS["production"]
)
```

### 4. Use Metadata Filters Effectively

```python
# ✅ GOOD - Combine semantic search with filters
results = search(
    query="transaction approval",
    metadata_filter={
        "status": "pending",
        "amount_range": "high",
        "requires_review": True
    }
)

# First filters by metadata, then ranks by similarity
```

### 5. Handle Empty Results Gracefully

```python
response = search(query="rare event")
results = response["results"]

if not results:
    print("No matching results found")
    # Try with lower threshold or different query
    retry_response = search(
        query="rare event",
        similarity_threshold=0.5  # Lower threshold
    )
else:
    for result in results:
        process_result(result)
```

---

## Troubleshooting

### Problem: No Results Returned

**Symptoms:**
- `total_results: 0`
- Empty `results` array

**Possible Causes:**

1. **Wrong namespace:**
   ```python
   # ❌ Stored in 'agent_memory', searching 'default'
   search(query="...", namespace="default")  # Wrong!

   # ✅ Fix
   search(query="...", namespace="agent_memory")
   ```

2. **Similarity threshold too high:**
   ```python
   # ❌ Too strict
   search(query="...", similarity_threshold=0.95)

   # ✅ Fix
   search(query="...", similarity_threshold=0.7)
   ```

3. **No vectors in namespace:**
   - Verify vectors were stored successfully
   - Check namespace spelling matches exactly

### Problem: Poor Quality Results

**Symptoms:**
- Results returned but not relevant
- Low similarity scores

**Possible Causes:**

1. **Model mismatch:**
   ```python
   # ❌ Stored with model A, searching with model B
   embed_and_store(model="BAAI/bge-small-en-v1.5", ...)
   search(model="sentence-transformers/all-mpnet-base-v2", ...)

   # ✅ Fix - use same model
   search(model="BAAI/bge-small-en-v1.5", ...)
   ```

2. **Query too vague:**
   ```python
   # ❌ Too general
   search(query="transaction")

   # ✅ More specific
   search(query="high-value transaction approval for customer ABC-123")
   ```

3. **Metadata filter too restrictive:**
   - Remove or relax metadata filters
   - Check filter values match stored metadata

### Problem: Dimension Mismatch Error

**Error:**
```json
{
  "detail": "Vector dimension mismatch. Expected 384, got 768",
  "error_code": "DIMENSION_MISMATCH"
}
```

**Cause:** Search model has different dimensions than stored vectors

**Solution:** Use model with matching dimensions:
```python
# Check what model/dimensions were used to store
# Then use same model for search
search(model="BAAI/bge-small-en-v1.5")  # 384 dims
```

---

## Performance Considerations

### Response Times

Typical response times (depends on dataset size):

| Vectors in Namespace | Avg Response Time |
|---------------------|-------------------|
| < 1,000 | 10-50ms |
| 1,000 - 10,000 | 50-200ms |
| 10,000 - 100,000 | 200-500ms |
| > 100,000 | 500ms+ |

### Optimizations

1. **Use appropriate top_k:**
   ```python
   # Don't request more results than needed
   search(top_k=5)  # Faster than top_k=100
   ```

2. **Apply metadata filters:**
   ```python
   # Pre-filter with metadata before similarity search
   search(
       query="...",
       metadata_filter={"status": "active"}  # Reduces search space
   )
   ```

3. **Use similarity threshold:**
   ```python
   # Stop early when similarity drops
   search(similarity_threshold=0.7)
   ```

---

## Related Documentation

- **[Embeddings Store & Search API](/docs/api/embeddings-store-search-spec.md)** - Complete API specification
- **[Model Consistency Guide](/docs/api/MODEL_CONSISTENCY_GUIDE.md)** - Critical model usage patterns
- **[Embed and Store API](/docs/api/EMBED_AND_STORE_API.md)** - Storing vectors
- **[Namespace Usage Guide](/docs/api/NAMESPACE_USAGE.md)** - Namespace best practices
- **[DX Contract](/DX-Contract.md)** - API stability guarantees
- **[PRD Section 6](/prd.md)** - Agent recall requirements

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-11 | Initial documentation for Issue #21 (Epic 5, Story 1) |

---

**Summary:** The search endpoint accepts query text, generates an embedding, and returns similar vectors ordered by similarity score. Use namespace scoping for agent isolation, metadata filters for precision, and consistent models for reliable results.
