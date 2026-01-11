# Issue #26: Performance Guide - Toggle Metadata and Embeddings

## Overview

Issue #26 implements two parameters to control what fields are included in search results:
- `include_metadata` (boolean, default: `true`)
- `include_embeddings` (boolean, default: `false`)

These parameters allow you to optimize response size and network transfer based on your use case.

---

## Default Behavior

**Optimized for common use cases:**
- `include_metadata=true` - Metadata is included (useful for filtering, context, auditing)
- `include_embeddings=false` - Embeddings are excluded (reduces response size significantly)

```json
{
  "query": "search query",
  "namespace": "default",
  "top_k": 10
  // include_metadata defaults to true
  // include_embeddings defaults to false
}
```

**Response includes:**
- vector_id
- namespace
- text (original document)
- similarity score
- model
- dimensions
- **metadata** ✓ (included by default)
- embedding ✗ (excluded by default)
- created_at

---

## Performance Characteristics

### Response Size Comparison

For a single 384-dimensional vector result:

| Configuration | Approx. Size | Use Case |
|--------------|-------------|----------|
| `include_metadata=false, include_embeddings=false` | ~500 bytes | Minimal payload - just text and scores |
| `include_metadata=true, include_embeddings=false` | ~800 bytes | **DEFAULT** - includes context/filters |
| `include_metadata=false, include_embeddings=true` | ~3.5 KB | Embeddings for processing, no metadata |
| `include_metadata=true, include_embeddings=true` | ~3.8 KB | Complete data - largest payload |

**Key Insight:** Embeddings are large (384+ floats), so including them increases response size by 400-700% per result.

### Network Transfer Impact

For `top_k=10` results:

| Configuration | Approx. Total Size | Network Impact |
|--------------|-------------------|----------------|
| Both false | ~5 KB | Minimal bandwidth |
| Default (metadata only) | ~8 KB | Optimal for most cases |
| Embeddings only | ~35 KB | 7x larger than default |
| Both true | ~38 KB | 4.75x larger than default |

**Recommendation:** Only include embeddings when necessary for downstream processing.

---

## Use Cases

### 1. Standard Search (Default)
**Include metadata, exclude embeddings**

```json
{
  "query": "compliance check results",
  "namespace": "agent_memory",
  "top_k": 5,
  "include_metadata": true,
  "include_embeddings": false
}
```

**When to use:**
- Displaying search results to users
- Filtering by metadata fields
- Audit trails and compliance tracking
- Most agent memory recall scenarios

**Response size:** ~800 bytes per result

---

### 2. Minimal Payload
**Exclude both metadata and embeddings**

```json
{
  "query": "quick lookup",
  "namespace": "default",
  "top_k": 100,
  "include_metadata": false,
  "include_embeddings": false
}
```

**When to use:**
- High-volume searches with many results
- Mobile/low-bandwidth environments
- When you only need text and similarity scores
- Preview/autocomplete scenarios

**Response size:** ~500 bytes per result

---

### 3. Embedding Processing
**Include embeddings, optionally include metadata**

```json
{
  "query": "vector analysis",
  "namespace": "vectors",
  "top_k": 10,
  "include_metadata": false,
  "include_embeddings": true
}
```

**When to use:**
- Re-ranking search results
- Computing custom similarity metrics
- Clustering or dimensionality reduction
- Training downstream models
- Debugging embedding quality

**Response size:** ~3.5 KB per result (without metadata), ~3.8 KB (with metadata)

**WARNING:** Including embeddings significantly increases response size and network transfer time.

---

### 4. Complete Data Export
**Include both metadata and embeddings**

```json
{
  "query": "export all data",
  "namespace": "archive",
  "top_k": 100,
  "include_metadata": true,
  "include_embeddings": true
}
```

**When to use:**
- Data migration/backup
- Full vector database exports
- Debugging/troubleshooting
- Vector quality analysis with metadata context

**Response size:** ~3.8 KB per result

**WARNING:** This produces the largest possible response. Use sparingly and only when necessary.

---

## Performance Best Practices

### 1. Use Defaults for Most Cases
The default configuration (`include_metadata=true, include_embeddings=false`) is optimized for 90% of use cases.

### 2. Exclude Embeddings Unless Needed
Embeddings are large and rarely needed in search results. Only include them when:
- You need to perform custom similarity calculations
- You're exporting data for offline processing
- You're debugging embedding quality

### 3. Consider Pagination
When using `include_embeddings=true`, limit `top_k` to avoid massive responses:
- Good: `top_k=10` with embeddings → ~38 KB
- Bad: `top_k=100` with embeddings → ~380 KB

### 4. Network Transfer Time

Approximate transfer times on different connections (for `top_k=10`):

| Configuration | Fast (100 Mbps) | Medium (10 Mbps) | Slow (1 Mbps) |
|--------------|-----------------|------------------|---------------|
| Both false | <1ms | ~5ms | ~40ms |
| Default | ~1ms | ~6ms | ~64ms |
| Embeddings only | ~3ms | ~28ms | ~280ms |
| Both true | ~3ms | ~30ms | ~304ms |

**Impact on mobile:** Including embeddings can significantly impact mobile users on 3G/4G connections.

---

## API Examples

### Example 1: Fast Search (Exclude Both)
```python
import requests

response = requests.post(
    "https://api.ainative.studio/v1/public/{project_id}/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "fast search query",
        "namespace": "default",
        "top_k": 50,
        "include_metadata": False,
        "include_embeddings": False
    }
)

# Small response, fast transfer
results = response.json()["results"]
for result in results:
    print(f"{result['text']}: {result['similarity']}")
```

### Example 2: Standard Search (Default)
```python
response = requests.post(
    "https://api.ainative.studio/v1/public/{project_id}/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "compliance check",
        "namespace": "agent_memory",
        "top_k": 10,
        # Defaults: include_metadata=true, include_embeddings=false
    }
)

results = response.json()["results"]
for result in results:
    print(f"{result['text']} (agent: {result['metadata']['agent_id']})")
```

### Example 3: Advanced Processing (Include Embeddings)
```python
response = requests.post(
    "https://api.ainative.studio/v1/public/{project_id}/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "vector processing",
        "namespace": "vectors",
        "top_k": 10,
        "include_metadata": True,
        "include_embeddings": True
    }
)

results = response.json()["results"]
for result in results:
    # Custom re-ranking using embeddings
    embedding = result["embedding"]
    custom_score = compute_custom_similarity(query_embedding, embedding)
    print(f"{result['text']}: custom_score={custom_score}")
```

---

## Monitoring Response Sizes

You can monitor response sizes in your application:

```python
response = requests.post(...)

# Check response size
response_size_kb = len(response.content) / 1024
print(f"Response size: {response_size_kb:.2f} KB")

# Log if response is unexpectedly large
if response_size_kb > 100:
    logger.warning(f"Large response detected: {response_size_kb:.2f} KB")
```

---

## Migration Guide

### From Previous Versions

If you're upgrading from a version without Issue #26:

1. **No changes required** - defaults are backward compatible
2. Metadata is included by default (same as before)
3. Embeddings are excluded by default (same as before)
4. You can now explicitly control these fields

### Opt-In to Smaller Responses

To reduce bandwidth usage:

```python
# Before (implicit defaults)
search_request = {
    "query": "search",
    "namespace": "default"
}

# After (explicit optimization)
search_request = {
    "query": "search",
    "namespace": "default",
    "include_metadata": False,  # NEW: Reduce response size
    "include_embeddings": False
}
```

---

## Troubleshooting

### Issue: Response is too large

**Solution:** Exclude embeddings and/or metadata:
```json
{
  "query": "...",
  "include_metadata": false,
  "include_embeddings": false
}
```

### Issue: Missing metadata in results

**Cause:** `include_metadata=false` was set

**Solution:** Set `include_metadata=true` or omit it (defaults to true)

### Issue: Need embeddings for processing

**Solution:** Set `include_embeddings=true`
```json
{
  "query": "...",
  "include_embeddings": true
}
```

**Note:** Be aware of increased response size and transfer time.

---

## Summary

| Parameter | Default | Impact | When to Change |
|-----------|---------|--------|---------------|
| `include_metadata` | `true` | +60% size | Set to `false` for minimal payloads |
| `include_embeddings` | `false` | +400% size | Set to `true` only when embeddings needed |

**Key Takeaway:** The defaults are optimized for most use cases. Only change them when you have a specific need for smaller responses or require embeddings for processing.

---

## References

- **Issue #26:** Toggle metadata and embeddings in results
- **PRD §9:** Demo visibility and response optimization
- **Epic 5, Story 6:** Response field control (1 point)
- **DX Contract:** Response format standards and backward compatibility
