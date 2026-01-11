# Similarity Threshold Guide

**Implementation:** Issue #25 - Epic 5, Story 5
**Status:** ✅ Implemented and Tested
**API Version:** v1/public

## Overview

The `similarity_threshold` parameter allows you to filter search results based on minimum similarity scores, ensuring only high-quality matches are returned. This feature is essential for:

- **Quality Control:** Filter out low-relevance results
- **Performance:** Reduce result processing by excluding poor matches
- **Precision:** Focus on semantically relevant documents
- **Cost Optimization:** Process only meaningful results

## Quick Start

### Basic Usage

```python
import requests

# Search with similarity threshold
response = requests.post(
    "https://api.ainative.studio/v1/public/{project_id}/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "compliance check results",
        "similarity_threshold": 0.7,  # Only return results >= 70% similar
        "top_k": 10
    }
)

results = response.json()
print(f"Found {results['total_results']} results above 0.7 threshold")
```

## Parameter Specification

### `similarity_threshold`

- **Type:** `float`
- **Range:** `0.0` to `1.0` (inclusive)
- **Default:** `0.0` (returns all results)
- **Description:** Minimum similarity score required for results
- **Validation:** Enforced at schema level

### Valid Values

| Threshold | Interpretation | Use Case |
|-----------|----------------|----------|
| `0.0` | No filtering (default) | Exploratory search, return everything |
| `0.3-0.5` | Low similarity | Broad semantic search, find related topics |
| `0.6-0.7` | Moderate similarity | General search, filter unrelated content |
| `0.8-0.9` | High similarity | Precise search, find very similar content |
| `1.0` | Perfect match only | Exact duplicate detection |

## Behavior Guarantees

### 1. Threshold Filtering

**Guarantee:** Only results with `similarity >= threshold` are returned.

```python
# All returned results meet the threshold
response = requests.post(url, json={
    "query": "agent workflow",
    "similarity_threshold": 0.75
})

for result in response.json()["results"]:
    assert result["similarity"] >= 0.75  # Always true
```

### 2. Interaction with top_k

**Guarantee:** Threshold is applied BEFORE top_k limiting.

**Execution Order:**
1. Calculate similarity scores for all vectors
2. **Filter by threshold** (keep only scores >= threshold)
3. Sort by similarity (descending)
4. Apply top_k limit

```python
# Example: 100 vectors total, 30 pass threshold, top_k=10
response = requests.post(url, json={
    "query": "compliance check",
    "similarity_threshold": 0.7,  # Filters to 30 vectors
    "top_k": 10                    # Returns top 10 of those 30
})

# Result: 10 highest-scoring vectors that passed 0.7 threshold
```

### 3. Empty Results

**Guarantee:** Returns empty results array when no vectors meet threshold.

```python
# No error when threshold is too high
response = requests.post(url, json={
    "query": "unrelated query",
    "similarity_threshold": 0.95  # Very strict
})

data = response.json()
assert data["total_results"] == 0  # May be 0, not an error
assert data["results"] == []       # Empty array, valid response
assert response.status_code == 200 # Still 200 OK
```

### 4. Validation Errors

**Guarantee:** Invalid threshold values return HTTP 422 with clear error.

```python
# Threshold > 1.0
response = requests.post(url, json={
    "query": "test",
    "similarity_threshold": 1.5  # Invalid
})

assert response.status_code == 422
assert "detail" in response.json()

# Negative threshold
response = requests.post(url, json={
    "query": "test",
    "similarity_threshold": -0.1  # Invalid
})

assert response.status_code == 422
```

## Real-World Examples

### Example 1: Agent Memory Recall (High Precision)

```python
# Retrieve only highly relevant agent memories
response = requests.post(
    f"https://api.ainative.studio/v1/public/{project_id}/embeddings/search",
    headers={"X-API-Key": api_key},
    json={
        "query": "previous compliance decisions for fintech transactions",
        "namespace": "agent_memory",
        "similarity_threshold": 0.8,  # High precision
        "top_k": 5,
        "metadata_filter": {
            "agent_id": "compliance_agent",
            "type": "decision"
        }
    }
)

# Only very similar past decisions are returned
for result in response.json()["results"]:
    print(f"Decision: {result['text']} (similarity: {result['similarity']:.2f})")
```

### Example 2: Document Discovery (Broad Search)

```python
# Find related documents with moderate threshold
response = requests.post(
    f"https://api.ainative.studio/v1/public/{project_id}/embeddings/search",
    headers={"X-API-Key": api_key},
    json={
        "query": "risk assessment methodologies",
        "namespace": "knowledge_base",
        "similarity_threshold": 0.5,  # Broader search
        "top_k": 20
    }
)

# Returns diverse related content
print(f"Found {response.json()['total_results']} related documents")
```

### Example 3: Duplicate Detection

```python
# Find exact or near-exact duplicates
response = requests.post(
    f"https://api.ainative.studio/v1/public/{project_id}/embeddings/search",
    headers={"X-API-Key": api_key},
    json={
        "query": document_text,
        "namespace": "documents",
        "similarity_threshold": 0.95,  # Near-perfect match
        "top_k": 10
    }
)

duplicates = response.json()["results"]
if duplicates:
    print(f"Warning: {len(duplicates)} potential duplicates found")
```

### Example 4: Quality-Controlled RAG

```python
# RAG with quality threshold
def get_context_for_rag(query: str, min_quality: float = 0.7) -> list:
    """
    Retrieve context for RAG with minimum quality guarantee.

    Args:
        query: User question
        min_quality: Minimum similarity threshold (0.0-1.0)

    Returns:
        List of high-quality context documents
    """
    response = requests.post(
        f"https://api.ainative.studio/v1/public/{project_id}/embeddings/search",
        headers={"X-API-Key": api_key},
        json={
            "query": query,
            "namespace": "knowledge_base",
            "similarity_threshold": min_quality,
            "top_k": 5
        }
    )

    results = response.json()["results"]

    # Only use results if they meet quality threshold
    if not results:
        print("Warning: No high-quality context found")
        return []

    return [r["text"] for r in results]


# Usage in RAG pipeline
context = get_context_for_rag("What are the compliance requirements?", min_quality=0.75)
if context:
    # Feed to LLM with confidence
    prompt = f"Context:\n{'\n'.join(context)}\n\nQuestion: ..."
```

## Best Practices

### 1. Choose Appropriate Thresholds

```python
# Use case-specific thresholds
THRESHOLDS = {
    "exact_match": 0.95,        # Duplicate detection
    "high_precision": 0.8,      # Critical decisions
    "standard": 0.7,            # General search
    "exploratory": 0.5,         # Broad discovery
    "all": 0.0                  # No filtering
}

# Agent decision retrieval (high stakes)
response = search(query, threshold=THRESHOLDS["high_precision"])

# Knowledge discovery (exploratory)
response = search(query, threshold=THRESHOLDS["exploratory"])
```

### 2. Handle Empty Results Gracefully

```python
def search_with_fallback(query: str, threshold: float) -> list:
    """Search with automatic fallback if no results."""
    response = requests.post(url, json={
        "query": query,
        "similarity_threshold": threshold,
        "top_k": 10
    })

    results = response.json()["results"]

    # Fallback to lower threshold if no results
    if not results and threshold > 0.5:
        print(f"No results at {threshold}, trying lower threshold...")
        return search_with_fallback(query, threshold - 0.1)

    return results
```

### 3. Combine with Other Filters

```python
# Threshold + namespace + metadata filtering
response = requests.post(url, json={
    "query": "compliance violations",
    "similarity_threshold": 0.75,        # Quality filter
    "namespace": "audit_logs",            # Scope filter
    "metadata_filter": {                  # Metadata filter
        "severity": "high",
        "status": "open"
    },
    "top_k": 20                          # Count limit
})

# All filters applied in sequence:
# 1. Namespace scoping
# 2. Metadata filtering
# 3. Threshold filtering
# 4. Sorting by similarity
# 5. Top K limiting
```

### 4. Monitor Threshold Effectiveness

```python
# Test different thresholds to find optimal value
def find_optimal_threshold(query: str, expected_results: int) -> float:
    """Find threshold that returns expected number of results."""
    for threshold in [0.9, 0.8, 0.7, 0.6, 0.5]:
        response = requests.post(url, json={
            "query": query,
            "similarity_threshold": threshold,
            "top_k": 100
        })

        count = response.json()["total_results"]
        print(f"Threshold {threshold}: {count} results")

        if count >= expected_results:
            return threshold

    return 0.0  # Use no threshold as fallback


# Usage
optimal = find_optimal_threshold("compliance requirements", expected_results=10)
print(f"Optimal threshold: {optimal}")
```

## Performance Considerations

### 1. Threshold Reduces Processing

Higher thresholds reduce the number of results, improving:
- Response time (less data to serialize)
- Bandwidth (smaller payloads)
- Client-side processing (fewer results to handle)

```python
# High threshold = faster response
response = requests.post(url, json={
    "query": "specific question",
    "similarity_threshold": 0.8,  # Returns fewer results
    "top_k": 5
})

# Low threshold = more comprehensive but slower
response = requests.post(url, json={
    "query": "broad topic",
    "similarity_threshold": 0.3,  # Returns many results
    "top_k": 50
})
```

### 2. Early Filtering

Threshold filtering happens during search, not after:
- Database filters results immediately
- No wasted computation on low-quality matches
- Optimal for large vector stores

## Testing Recommendations

```python
import pytest

def test_threshold_filters_results(api_client):
    """Test that threshold correctly filters results."""
    # Search with low threshold
    response_low = api_client.post("/embeddings/search", json={
        "query": "test query",
        "similarity_threshold": 0.0,
        "top_k": 100
    })

    # Search with high threshold
    response_high = api_client.post("/embeddings/search", json={
        "query": "test query",
        "similarity_threshold": 0.8,
        "top_k": 100
    })

    results_low = response_low.json()["results"]
    results_high = response_high.json()["results"]

    # High threshold returns fewer or equal results
    assert len(results_high) <= len(results_low)

    # All high-threshold results meet threshold
    for result in results_high:
        assert result["similarity"] >= 0.8


def test_threshold_validation(api_client):
    """Test that invalid thresholds are rejected."""
    # Threshold > 1.0
    response = api_client.post("/embeddings/search", json={
        "query": "test",
        "similarity_threshold": 1.5
    })
    assert response.status_code == 422

    # Negative threshold
    response = api_client.post("/embeddings/search", json={
        "query": "test",
        "similarity_threshold": -0.1
    })
    assert response.status_code == 422


def test_empty_results_handled(api_client):
    """Test that no-match cases return valid empty response."""
    response = api_client.post("/embeddings/search", json={
        "query": "completely unrelated query xyz abc",
        "similarity_threshold": 0.99
    })

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total_results" in data
    assert data["total_results"] >= 0
```

## Troubleshooting

### Problem: No results returned

**Solution:** Lower the threshold or check if data exists

```python
# Debug: Check what similarities exist
response = requests.post(url, json={
    "query": query,
    "similarity_threshold": 0.0,  # No filtering
    "top_k": 10
})

results = response.json()["results"]
if results:
    similarities = [r["similarity"] for r in results]
    print(f"Top similarities: {similarities}")
    print(f"Consider threshold <= {min(similarities)}")
else:
    print("No vectors in namespace")
```

### Problem: Too many results

**Solution:** Increase threshold or reduce top_k

```python
# Increase threshold to get fewer, higher-quality results
response = requests.post(url, json={
    "query": query,
    "similarity_threshold": 0.85,  # Stricter
    "top_k": 5                     # Fewer results
})
```

### Problem: Threshold validation error

**Solution:** Ensure threshold is between 0.0 and 1.0

```python
# Validate before sending
def validate_threshold(threshold: float) -> float:
    """Ensure threshold is in valid range."""
    if threshold < 0.0:
        return 0.0
    if threshold > 1.0:
        return 1.0
    return threshold


threshold = validate_threshold(user_input)
```

## API Reference

### Request Schema

```json
{
  "query": "string (required)",
  "model": "string (optional, default: BAAI/bge-small-en-v1.5)",
  "namespace": "string (optional, default: 'default')",
  "top_k": "integer (optional, 1-100, default: 10)",
  "similarity_threshold": "float (optional, 0.0-1.0, default: 0.0)",
  "metadata_filter": "object (optional)",
  "include_embeddings": "boolean (optional, default: false)"
}
```

### Response Schema

```json
{
  "results": [
    {
      "vector_id": "string",
      "namespace": "string",
      "text": "string",
      "similarity": "float (0.0-1.0)",
      "model": "string",
      "dimensions": "integer",
      "metadata": "object",
      "embedding": "array[float] | null",
      "created_at": "string (ISO8601)"
    }
  ],
  "query": "string",
  "namespace": "string",
  "model": "string",
  "total_results": "integer",
  "processing_time_ms": "integer"
}
```

## References

- **PRD:** Section 10 (Explainability)
- **Epic:** Epic 5 (Semantic Search)
- **Story:** Story 5 (Similarity Threshold)
- **Issue:** #25
- **DX Contract:** Section 10 (Deterministic Behavior)
- **Tests:** `/backend/app/tests/test_similarity_threshold.py`

## Support

For issues or questions:
1. Check test cases for usage examples
2. Review API specification
3. Consult DX Contract for guarantees
4. Check troubleshooting section above
