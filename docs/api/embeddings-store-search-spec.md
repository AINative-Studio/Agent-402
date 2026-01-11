# Embeddings Store & Search API Specification

**Version:** v1.0
**Last Updated:** 2026-01-10
**Implementation:** Epic 4 (Embed & Store), Epic 5 (Semantic Search)
**Base URL:** `https://api.ainative.studio/v1/public`

---

## ⚠️ IMPORTANT: Vector Operations Require /database/ Prefix

**For direct vector operations** (not embeddings endpoints), you MUST include the `/database/` prefix:

```
✅ CORRECT:   /v1/public/database/vectors/upsert
❌ INCORRECT: /v1/public/vectors/upsert  (will return 404)
```

**This document covers embeddings endpoints** which do NOT require `/database/`:
- `/v1/public/{project_id}/embeddings/embed-and-store` ✅
- `/v1/public/{project_id}/embeddings/search` ✅

**For vector operations** (Epic 6), see:
- [DATABASE_PREFIX_WARNING.md](/docs/api/DATABASE_PREFIX_WARNING.md) - Complete guide
- [Vector Operations API](/docs/api/vector-operations-spec.md) - API specification

---

## ⚠️ CRITICAL: Model Consistency Requirement

**BEFORE YOU START:** You MUST use the **SAME model** for both storing and searching documents.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Store with Model X → Search with Model X              │
│                                                         │
│  Using different models will cause:                     │
│  • DIMENSION_MISMATCH errors                            │
│  • Poor search quality                                  │
│  • No results found                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**📖 READ THIS FIRST:** [Model Consistency Guide](/docs/api/MODEL_CONSISTENCY_GUIDE.md)

This guide contains critical information about:
- Why model consistency matters
- What happens when you mix models
- Troubleshooting model mismatch errors
- Best practices and migration guides

---

## Overview

The Embeddings Store & Search API allows you to:
1. **Store documents** with automatic embedding generation
2. **Search documents** using semantic similarity
3. **Organize documents** using namespaces
4. **Update documents** using upsert behavior

This is the foundation for agent memory, semantic search, and document retrieval.

---

## Authentication

All endpoints require authentication via the `X-API-Key` header.

**IMPORTANT:** API keys must only be used in server-side environments. See [SECURITY.md](/SECURITY.md) for details.

```bash
curl -X POST "https://api.ainative.studio/v1/public/{project_id}/embeddings/embed-and-store" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json"
```

---

## Endpoint 1: Embed and Store

Store documents with automatic embedding generation.

### Endpoint

```
POST /v1/public/{project_id}/embeddings/embed-and-store
```

### ⚠️ Model Consistency Warning

**REMEMBER THE MODEL YOU USE HERE!** You must use the same model when searching this namespace.

**Best Practice:**
```python
# Define model as constant
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Use for all operations in this namespace
store_response = embed_and_store(model=EMBEDDING_MODEL, ...)
search_response = search(model=EMBEDDING_MODEL, ...)
```

### Request Body

```json
{
  "documents": [
    {
      "id": "doc-001",
      "text": "Compliance check passed for transaction TX-123",
      "metadata": {
        "agent_id": "compliance_agent",
        "transaction_id": "TX-123",
        "timestamp": "2026-01-10T12:00:00Z"
      }
    },
    {
      "id": "doc-002",
      "text": "Risk score: low for customer ABC-456",
      "metadata": {
        "agent_id": "risk_agent",
        "customer_id": "ABC-456",
        "risk_level": "low"
      }
    }
  ],
  "model": "BAAI/bge-small-en-v1.5",
  "namespace": "compliance_events",
  "upsert": true
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `documents` | array | **Yes** | Array of documents to embed and store |
| `documents[].id` | string | **Yes** | Unique document identifier within namespace |
| `documents[].text` | string | **Yes** | Document text content (non-empty) |
| `documents[].metadata` | object | No | Optional metadata for filtering and context |
| `model` | string | No | Embedding model to use (defaults to `BAAI/bge-small-en-v1.5`) |
| `namespace` | string | No | Namespace for document organization (defaults to `default`) |
| `upsert` | boolean | No | If true, updates existing documents with same ID (defaults to `false`) |

### ⚠️ Important Field Notes

**documents[].id:**
- Must be unique within the namespace
- If `upsert: false` and ID exists → error
- If `upsert: true` and ID exists → document is updated

**model:**
- **CRITICAL:** Write down the model you use here
- You MUST use this same model when searching
- If omitted, defaults to `BAAI/bge-small-en-v1.5` (384 dimensions)
- See [supported models](/docs/api/embeddings-api-spec.md#supported-models)

**namespace:**
- Isolates documents into separate spaces
- Different agents can use different namespaces
- **Best Practice:** Use one namespace per model
- Example namespaces: `agent_memory`, `compliance_events`, `customer_data`

### Success Response (200 OK)

```json
{
  "stored_count": 2,
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "namespace": "compliance_events",
  "documents": [
    {
      "id": "doc-001",
      "status": "created",
      "vector_length": 384
    },
    {
      "id": "doc-002",
      "status": "updated",
      "vector_length": 384
    }
  ],
  "processing_time_ms": 123.45
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `stored_count` | integer | Number of documents successfully stored |
| `model` | string | Model actually used (includes default if omitted) |
| `dimensions` | integer | Vector dimensions (validates consistency) |
| `namespace` | string | Namespace where documents were stored |
| `documents` | array | Per-document status information |
| `documents[].status` | string | `created` (new) or `updated` (upserted) |
| `processing_time_ms` | float | Total processing time in milliseconds |

### Error Responses

```json
// 400 Bad Request - Duplicate ID without upsert
{
  "detail": "Document with ID 'doc-001' already exists in namespace 'compliance_events'. Set upsert=true to update.",
  "error_code": "DUPLICATE_DOCUMENT_ID"
}

// 401 Unauthorized - Invalid API key
{
  "detail": "Invalid API key",
  "error_code": "INVALID_API_KEY"
}

// 404 Not Found - Project not found
{
  "detail": "Project not found",
  "error_code": "PROJECT_NOT_FOUND"
}

// 422 Unprocessable Entity - Validation error
{
  "detail": [
    {
      "loc": ["body", "documents"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

// 422 - Unsupported model
{
  "detail": "Model 'invalid-model' is not supported. Use GET /embeddings/models to see supported models.",
  "error_code": "MODEL_NOT_FOUND"
}
```

### Example: Basic Store

```bash
curl -X POST "https://api.ainative.studio/v1/public/proj_123/embeddings/embed-and-store" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "memo-001",
        "text": "Agent completed compliance check successfully",
        "metadata": {"agent": "compliance_agent", "status": "passed"}
      }
    ],
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "agent_memory"
  }'
```

### Example: Upsert (Update Existing)

```bash
curl -X POST "https://api.ainative.studio/v1/public/proj_123/embeddings/embed-and-store" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "memo-001",
        "text": "Agent completed compliance check successfully - UPDATED",
        "metadata": {"agent": "compliance_agent", "status": "passed", "updated": true}
      }
    ],
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "agent_memory",
    "upsert": true
  }'
```

### Python Example

```python
import requests

BASE_URL = "https://api.ainative.studio"
API_KEY = "your_api_key"
PROJECT_ID = "proj_123"

# ✅ BEST PRACTICE: Define model as constant
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
NAMESPACE = "agent_memory"

def store_agent_memory(agent_id: str, memory_text: str, metadata: dict):
    """Store agent memory with consistent model usage."""
    response = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "documents": [
                {
                    "id": f"{agent_id}-{metadata.get('timestamp', 'unknown')}",
                    "text": memory_text,
                    "metadata": {
                        "agent_id": agent_id,
                        **metadata
                    }
                }
            ],
            "model": EMBEDDING_MODEL,  # ← Remember this model!
            "namespace": NAMESPACE,
            "upsert": True
        }
    )
    response.raise_for_status()
    return response.json()

# Store some memories
store_agent_memory(
    agent_id="compliance_agent",
    memory_text="Completed KYC check for customer ABC-123",
    metadata={"customer_id": "ABC-123", "check_type": "KYC"}
)
```

---

## Endpoint 2: Semantic Search

Search documents using semantic similarity.

### Endpoint

```
POST /v1/public/{project_id}/embeddings/search
```

### ⚠️ Model Consistency Warning

**USE THE SAME MODEL AS embed-and-store!**

If you stored documents with `BAAI/bge-small-en-v1.5`, you MUST search with `BAAI/bge-small-en-v1.5`.

**Using a different model will cause:**
- `DIMENSION_MISMATCH` errors if dimensions don't match
- Poor search results if dimensions match but model is different
- No results found even though documents exist

**If you get poor results or errors:** Check that the model parameter matches the model used in embed-and-store for this namespace.

### Request Body

```json
{
  "query": "find compliance results for transaction",
  "model": "BAAI/bge-small-en-v1.5",
  "namespace": "compliance_events",
  "top_k": 5,
  "similarity_threshold": 0.7,
  "filter": {
    "metadata.agent_id": "compliance_agent",
    "metadata.risk_level": "low"
  },
  "include_metadata": true,
  "include_embeddings": false
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | **Yes** | Search query text (semantic search) |
| `model` | string | No | **MUST match model used in embed-and-store** (defaults to `BAAI/bge-small-en-v1.5`) |
| `namespace` | string | No | Namespace to search (defaults to `default`) |
| `top_k` | integer | No | Maximum number of results to return (defaults to 10, max 100) |
| `similarity_threshold` | float | No | Minimum similarity score 0.0-1.0 (defaults to 0.0) |
| `filter` | object | No | Metadata filters (key-value matching) |
| `include_metadata` | boolean | No | Include document metadata in results (defaults to `true`) |
| `include_embeddings` | boolean | No | Include vector embeddings in results (defaults to `false`) |

### ⚠️ Important Field Notes

**model:**
- **CRITICAL:** Must be the SAME model used in embed-and-store
- If you're getting poor results, this is the first thing to check
- If omitted, uses default (`BAAI/bge-small-en-v1.5`)
- **Pro Tip:** Always specify explicitly to avoid confusion

**namespace:**
- Must match the namespace used in embed-and-store
- Documents are isolated by namespace
- Searching wrong namespace returns no results

**similarity_threshold:**
- Range: 0.0 to 1.0 (higher = more similar)
- 0.0 = return all results (sorted by similarity)
- 0.7 = good default for quality results
- 0.9 = very high similarity required

**filter:**
- Filters on document metadata
- Supports exact matching only (no regex)
- Example: `{"metadata.agent_id": "compliance_agent"}`

### Success Response (200 OK)

```json
{
  "results": [
    {
      "id": "doc-001",
      "text": "Compliance check passed for transaction TX-123",
      "similarity": 0.92,
      "metadata": {
        "agent_id": "compliance_agent",
        "transaction_id": "TX-123",
        "timestamp": "2026-01-10T12:00:00Z"
      }
    },
    {
      "id": "doc-003",
      "text": "Transaction TX-456 flagged for review",
      "similarity": 0.78,
      "metadata": {
        "agent_id": "compliance_agent",
        "transaction_id": "TX-456",
        "status": "review"
      }
    }
  ],
  "total_results": 2,
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "namespace": "compliance_events",
  "processing_time_ms": 45.67
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | Array of matching documents (sorted by similarity) |
| `results[].id` | string | Document identifier |
| `results[].text` | string | Document text content |
| `results[].similarity` | float | Similarity score (0.0 to 1.0, higher is better) |
| `results[].metadata` | object | Document metadata (if `include_metadata: true`) |
| `results[].embedding` | array | Vector embedding (if `include_embeddings: true`) |
| `total_results` | integer | Number of results returned |
| `model` | string | Model actually used for search |
| `dimensions` | integer | Vector dimensions used |
| `namespace` | string | Namespace searched |
| `processing_time_ms` | float | Processing time in milliseconds |

### Error Responses

```json
// 400 Bad Request - Dimension mismatch
{
  "detail": "Vector dimension mismatch. Namespace 'compliance_events' contains 768-dim vectors, but query is 384-dim. Check that search model matches the model used in embed-and-store.",
  "error_code": "DIMENSION_MISMATCH"
}

// 401 Unauthorized - Invalid API key
{
  "detail": "Invalid API key",
  "error_code": "INVALID_API_KEY"
}

// 404 Not Found - Project not found
{
  "detail": "Project not found",
  "error_code": "PROJECT_NOT_FOUND"
}

// 404 Not Found - Namespace not found
{
  "detail": "Namespace 'invalid_namespace' not found in project",
  "error_code": "NAMESPACE_NOT_FOUND"
}

// 422 Unprocessable Entity - Validation error
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

// 422 - Unsupported model
{
  "detail": "Model 'invalid-model' is not supported. Use GET /embeddings/models to see supported models.",
  "error_code": "MODEL_NOT_FOUND"
}
```

### Example: Basic Search

```bash
curl -X POST "https://api.ainative.studio/v1/public/proj_123/embeddings/search" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compliance check results",
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "agent_memory",
    "top_k": 5,
    "similarity_threshold": 0.7
  }'
```

### Example: Search with Metadata Filter

```bash
curl -X POST "https://api.ainative.studio/v1/public/proj_123/embeddings/search" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "find agent decisions",
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "agent_memory",
    "top_k": 10,
    "filter": {
      "metadata.agent_id": "compliance_agent",
      "metadata.status": "passed"
    }
  }'
```

### Python Example

```python
import requests

BASE_URL = "https://api.ainative.studio"
API_KEY = "your_api_key"
PROJECT_ID = "proj_123"

# ✅ BEST PRACTICE: Use same model as store
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
NAMESPACE = "agent_memory"

def search_agent_memory(query: str, agent_id: str = None, top_k: int = 5):
    """Search agent memory using semantic similarity."""
    payload = {
        "query": query,
        "model": EMBEDDING_MODEL,  # ← SAME model as embed-and-store
        "namespace": NAMESPACE,
        "top_k": top_k,
        "similarity_threshold": 0.7,
        "include_metadata": True
    }

    # Add agent filter if specified
    if agent_id:
        payload["filter"] = {"metadata.agent_id": agent_id}

    response = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json=payload
    )
    response.raise_for_status()
    return response.json()

# Search for compliance-related memories
results = search_agent_memory(
    query="compliance check for customer ABC-123",
    agent_id="compliance_agent",
    top_k=5
)

for result in results["results"]:
    print(f"ID: {result['id']}")
    print(f"Similarity: {result['similarity']:.2f}")
    print(f"Text: {result['text']}")
    print(f"Metadata: {result['metadata']}")
    print("---")
```

---

## Complete Workflow Example

This example shows the complete store → search workflow with proper model consistency.

### Step 1: Define Configuration

```python
# config.py
"""
Agent Memory Configuration

⚠️ CRITICAL: Do NOT change EMBEDDING_MODEL without re-embedding all documents.
Changing the model will break semantic search.

Last updated: 2026-01-10
"""

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384
AGENT_MEMORY_NAMESPACE = "agent_memory"
COMPLIANCE_NAMESPACE = "compliance_events"

BASE_URL = "https://api.ainative.studio"
PROJECT_ID = "proj_123"
```

### Step 2: Store Documents

```python
# store_memory.py
import requests
from config import EMBEDDING_MODEL, AGENT_MEMORY_NAMESPACE, BASE_URL, PROJECT_ID

def store_agent_decision(agent_id: str, decision_text: str, context: dict):
    """Store agent decision in memory."""
    response = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
        headers={"X-API-Key": os.getenv("ZERODB_API_KEY")},
        json={
            "documents": [
                {
                    "id": f"{agent_id}-{context['task_id']}",
                    "text": decision_text,
                    "metadata": {
                        "agent_id": agent_id,
                        **context
                    }
                }
            ],
            "model": EMBEDDING_MODEL,  # ← Defined in config
            "namespace": AGENT_MEMORY_NAMESPACE,
            "upsert": True
        }
    )
    response.raise_for_status()
    return response.json()

# Store some decisions
store_agent_decision(
    agent_id="compliance_agent",
    decision_text="KYC check passed for customer ABC-123. Risk score: low.",
    context={"task_id": "task-001", "customer_id": "ABC-123"}
)

store_agent_decision(
    agent_id="transaction_agent",
    decision_text="Transaction TX-789 approved. Amount: $1000.",
    context={"task_id": "task-002", "transaction_id": "TX-789"}
)
```

### Step 3: Search Documents

```python
# search_memory.py
import requests
from config import EMBEDDING_MODEL, AGENT_MEMORY_NAMESPACE, BASE_URL, PROJECT_ID

def recall_agent_memories(query: str, agent_id: str = None):
    """Recall relevant agent memories."""
    payload = {
        "query": query,
        "model": EMBEDDING_MODEL,  # ← SAME model as store
        "namespace": AGENT_MEMORY_NAMESPACE,
        "top_k": 5,
        "similarity_threshold": 0.7
    }

    if agent_id:
        payload["filter"] = {"metadata.agent_id": agent_id}

    response = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
        headers={"X-API-Key": os.getenv("ZERODB_API_KEY")},
        json=payload
    )
    response.raise_for_status()
    return response.json()

# Recall compliance-related memories
results = recall_agent_memories(
    query="customer ABC-123 compliance check",
    agent_id="compliance_agent"
)

print(f"Found {results['total_results']} relevant memories:")
for result in results["results"]:
    print(f"\nSimilarity: {result['similarity']:.2%}")
    print(f"Text: {result['text']}")
    print(f"Agent: {result['metadata']['agent_id']}")
```

### Step 4: Validate Consistency

```python
# test_consistency.py
import pytest
from config import EMBEDDING_MODEL, AGENT_MEMORY_NAMESPACE

def test_model_consistency():
    """Ensure store and search use the same model."""
    from store_memory import EMBEDDING_MODEL as store_model
    from search_memory import EMBEDDING_MODEL as search_model

    assert store_model == search_model, \
        f"Model mismatch! Store: {store_model}, Search: {search_model}"

def test_namespace_consistency():
    """Ensure store and search use the same namespace."""
    from store_memory import AGENT_MEMORY_NAMESPACE as store_ns
    from search_memory import AGENT_MEMORY_NAMESPACE as search_ns

    assert store_ns == search_ns, \
        f"Namespace mismatch! Store: {store_ns}, Search: {search_ns}"
```

---

## Namespaces: Organization Best Practices

### What are Namespaces?

Namespaces isolate documents into separate vector spaces. Documents in one namespace are completely separate from documents in another namespace.

### When to Use Separate Namespaces

1. **Different Models:**
   ```python
   # Fast model for general memory
   store(model="BAAI/bge-small-en-v1.5", namespace="general_384")

   # High-quality model for compliance
   store(model="sentence-transformers/all-mpnet-base-v2", namespace="compliance_768")
   ```

2. **Different Agents:**
   ```python
   # Separate namespace per agent
   store(namespace="compliance_agent_memory")
   store(namespace="transaction_agent_memory")
   store(namespace="analyst_agent_memory")
   ```

3. **Different Data Types:**
   ```python
   # Separate by purpose
   store(namespace="agent_decisions")
   store(namespace="compliance_events")
   store(namespace="transaction_logs")
   ```

### Namespace Naming Conventions

```python
# ✅ Good namespace names
"agent_memory"
"compliance_events"
"customer_documents_384"
"high_quality_search_768"

# ❌ Avoid these
"test"  # Too vague
"data"  # Not descriptive
"ns1"   # Not meaningful
```

---

## Troubleshooting

### Problem: DIMENSION_MISMATCH Error

**Error:**
```json
{
  "detail": "Vector dimension mismatch. Expected 384, got 768",
  "error_code": "DIMENSION_MISMATCH"
}
```

**Cause:** Search model has different dimensions than stored vectors.

**Solution:**
1. Check what model was used to store documents in this namespace
2. Use the SAME model for search
3. If you need a different model, use a different namespace

**Example Fix:**
```python
# ❌ This caused the error
store(model="BAAI/bge-small-en-v1.5", ...)     # 384 dims
search(model="sentence-transformers/all-mpnet-base-v2", ...)  # 768 dims

# ✅ Fix: Use same model
search(model="BAAI/bge-small-en-v1.5", ...)    # 384 dims
```

### Problem: No Results Found

**Symptom:** Search returns empty results even though documents exist.

**Possible Causes:**

1. **Wrong namespace:**
   ```python
   # ❌ Stored in namespace A, searching namespace B
   store(namespace="agent_memory", ...)
   search(namespace="compliance_events", ...)  # Wrong namespace!

   # ✅ Fix: Search same namespace
   search(namespace="agent_memory", ...)
   ```

2. **Different models (semantic drift):**
   ```python
   # ❌ Different models, even with same dimensions
   store(model="BAAI/bge-small-en-v1.5", ...)
   search(model="sentence-transformers/all-MiniLM-L6-v2", ...)  # Different encoding

   # ✅ Fix: Use same model
   search(model="BAAI/bge-small-en-v1.5", ...)
   ```

3. **Similarity threshold too high:**
   ```python
   # ❌ Threshold too high
   search(similarity_threshold=0.95, ...)  # Very strict

   # ✅ Fix: Lower threshold
   search(similarity_threshold=0.7, ...)  # More lenient
   ```

### Problem: Poor Search Quality

**Symptom:** Search returns results but they're not relevant.

**Causes and Solutions:**

1. **Model mismatch:** Use the SAME model as store
2. **Query too vague:** Make query more specific
3. **Metadata filter too restrictive:** Relax filters
4. **Low top_k:** Increase `top_k` to see more results

---

## Rate Limits and Quotas

| Tier | Store Operations/min | Search Operations/min | Max Documents/namespace |
|------|---------------------|----------------------|-------------------------|
| Free | 10 | 20 | 1,000 |
| Starter | 100 | 200 | 10,000 |
| Pro | 1,000 | 2,000 | 100,000 |
| Enterprise | Custom | Custom | Custom |

---

## Related Documentation

- **[Model Consistency Guide](/docs/api/MODEL_CONSISTENCY_GUIDE.md)** - MUST READ before implementation
- [Embeddings API Spec](/docs/api/embeddings-api-spec.md) - Model details and generate endpoint
- [DX Contract Section 3](/DX-Contract.md) - Embeddings guarantees
- [Security Guidelines](/SECURITY.md) - API key security
- [PRD Section 6](/prd.md) - ZeroDB integration requirements

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-10 | Initial specification (Epic 4, Epic 5, Issue #20) |

---

**Remember: Store with Model X → Search with Model X** 🎯
