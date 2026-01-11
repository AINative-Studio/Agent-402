# top_k Parameter Usage Guide

**Issue #22: Limiting Search Results**

The `top_k` parameter allows developers to limit the number of results returned from the `/embeddings/search` endpoint, ensuring only the most similar vectors are retrieved.

---

## Quick Reference

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `top_k` | integer | 10 | 1-100 | Maximum number of results to return |

---

## Behavior

### Core Functionality

1. **Result Limiting**: Returns at most `top_k` most similar vectors
2. **Similarity Ordering**: Results are always sorted by similarity score (descending)
3. **Automatic Handling**: If fewer vectors exist than `top_k`, all available vectors are returned
4. **Deterministic**: Same query with same `top_k` produces identical results

### Default Value

When `top_k` is omitted, the default value of **10** is used:

```python
# These are equivalent
search_request = {"query": "agent workflow"}
search_request = {"query": "agent workflow", "top_k": 10}
```

---

## Examples

### Basic Usage

```python
import requests

API_KEY = "your_api_key"
PROJECT_ID = "proj_abc123"

# Search with top_k=5
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "agent compliance check",
        "top_k": 5
    }
)

results = response.json()
print(f"Returned {len(results['results'])} results")  # At most 5
```

### Finding the Single Best Match

```python
# Get only the most similar vector
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "specific compliance rule",
        "top_k": 1
    }
)

best_match = response.json()["results"][0]
print(f"Best match: {best_match['text']}")
print(f"Similarity: {best_match['similarity']}")
```

### Retrieving Many Results

```python
# Get up to 50 results
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "agent memory",
        "top_k": 50
    }
)

results = response.json()
print(f"Retrieved {results['total_results']} results")
```

### Combining with Similarity Threshold

```python
# Get top 10 results with minimum similarity of 0.7
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "payment processing",
        "top_k": 10,
        "similarity_threshold": 0.7
    }
)

# May return fewer than 10 if not enough vectors meet the threshold
results = response.json()
print(f"Found {results['total_results']} high-quality matches")
```

### Combining with Metadata Filter

```python
# Get top 5 results from a specific agent
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "task completion",
        "top_k": 5,
        "metadata_filter": {
            "agent_id": "agent_001"
        }
    }
)

# Returns at most 5 results, all from agent_001
results = response.json()
```

### Namespace-Scoped Search with top_k

```python
# Get top 3 results from a specific namespace
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "compliance workflow",
        "namespace": "agent_1_memory",
        "top_k": 3
    }
)

# Returns at most 3 results from agent_1_memory namespace only
results = response.json()
```

---

## Edge Cases

### Case 1: top_k Greater Than Available Vectors

When requesting more results than exist:

```python
# Database has only 5 vectors, but we request 100
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "agent workflow",
        "top_k": 100
    }
)

results = response.json()
# Returns only 5 results (all available vectors)
assert len(results["results"]) == 5
```

### Case 2: Zero Matching Vectors

When no vectors match the query:

```python
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "nonexistent content",
        "top_k": 10
    }
)

results = response.json()
# Returns empty results
assert len(results["results"]) == 0
assert results["total_results"] == 0
```

### Case 3: Invalid top_k Values

```python
# top_k = 0 (invalid)
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={"query": "test", "top_k": 0}
)
# Returns 422 Validation Error

# top_k = 101 (exceeds maximum)
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={"query": "test", "top_k": 101}
)
# Returns 422 Validation Error
```

---

## Response Structure

The response includes `total_results` which reflects the actual number of results returned (limited by `top_k`):

```json
{
  "results": [
    {
      "vector_id": "vec_abc123",
      "namespace": "default",
      "text": "Autonomous agent compliance workflow",
      "similarity": 0.95,
      "model": "BAAI/bge-small-en-v1.5",
      "dimensions": 384,
      "metadata": {"agent_id": "agent_001"},
      "created_at": "2026-01-11T10:30:00Z"
    },
    {
      "vector_id": "vec_def456",
      "namespace": "default",
      "text": "Agent workflow system",
      "similarity": 0.87,
      "model": "BAAI/bge-small-en-v1.5",
      "dimensions": 384,
      "metadata": {"agent_id": "agent_002"},
      "created_at": "2026-01-11T10:31:00Z"
    }
  ],
  "query": "agent compliance workflow",
  "namespace": "default",
  "model": "BAAI/bge-small-en-v1.5",
  "total_results": 2,
  "processing_time_ms": 15
}
```

**Note**: `total_results` will never exceed `top_k`.

---

## Validation Rules

The `top_k` parameter is validated as follows:

| Rule | Description | Error Code |
|------|-------------|------------|
| Minimum | Must be at least 1 | 422 Validation Error |
| Maximum | Cannot exceed 100 | 422 Validation Error |
| Type | Must be an integer | 422 Validation Error |

---

## Performance Considerations

### Optimal Values

- **Single best match**: `top_k=1`
- **Quick overview**: `top_k=5` to `top_k=10` (default)
- **Comprehensive review**: `top_k=20` to `top_k=50`
- **Maximum retrieval**: `top_k=100` (use sparingly)

### Performance Tips

1. **Use the smallest top_k needed** for your use case
2. **Combine with similarity_threshold** to filter out low-quality matches
3. **Use metadata_filter** to pre-filter before applying top_k
4. **Consider pagination** if you need more than 100 results (use multiple queries with different filters)

---

## Use Cases

### Agent Memory Retrieval

```python
# Retrieve top 3 most relevant memories for an agent decision
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "previous compliance decisions",
        "namespace": "agent_memory",
        "top_k": 3,
        "metadata_filter": {"agent_id": "compliance_agent"}
    }
)
```

### Document Retrieval for RAG

```python
# Retrieve top 5 documents for context augmentation
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "financial regulations for startups",
        "top_k": 5,
        "similarity_threshold": 0.75
    }
)

# Use results as context for LLM
contexts = [r["text"] for r in response.json()["results"]]
```

### Deduplication Check

```python
# Check if similar content already exists
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": new_document_text,
        "top_k": 1,
        "similarity_threshold": 0.95
    }
)

results = response.json()
if results["total_results"] > 0 and results["results"][0]["similarity"] > 0.95:
    print("Similar document already exists!")
```

---

## DX Contract Guarantees

Per [DX-Contract.md](../../DX-Contract.md):

1. **Default value (10) is guaranteed** and will not change without versioning
2. **Range (1-100) is guaranteed** and will not change without versioning
3. **Similarity ordering (descending) is guaranteed** and deterministic
4. **Behavior is stable** across API versions

---

## Related Parameters

- **similarity_threshold**: Filters results before applying top_k limit
- **metadata_filter**: Pre-filters vectors before similarity search
- **namespace**: Scopes search to specific namespace before applying top_k
- **include_embeddings**: Controls whether embedding vectors are included in response

---

## Troubleshooting

### Problem: Getting fewer results than top_k

**Possible causes**:
1. Fewer vectors exist in the database/namespace
2. `similarity_threshold` is filtering out results
3. `metadata_filter` is excluding vectors

**Solution**:
```python
# Check without filters first
response = requests.post(
    f"https://api.ainative.studio/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "your query",
        "top_k": 100,
        "similarity_threshold": 0.0  # Accept all similarities
    }
)
print(f"Total vectors available: {len(response.json()['results'])}")
```

### Problem: Validation error on top_k

**Cause**: Invalid value provided

**Solution**: Ensure `top_k` is between 1 and 100:
```python
# Valid values
top_k_values = [1, 5, 10, 20, 50, 100]

# Invalid values (will cause 422 error)
invalid_values = [0, -1, 101, 200]
```

---

## References

- **Issue #22**: [As a developer, I can limit results via top_k](https://github.com/your-org/zerodb/issues/22)
- **PRD §10**: Predictable replay requirements
- **Epic 5, Story 2**: Limit results with top_k parameter (2 points)
- **DX Contract**: Parameter standards and guarantees
