# Metadata Filtering Guide (Issue #24)

## Overview

The metadata filtering feature allows you to refine vector search results by filtering on metadata fields. Filters are applied **AFTER** similarity search to ensure you get the most relevant results that also match your criteria.

## Supported Filter Operations

### 1. Simple Equality (Default)

Match exact values:

```json
{
  "metadata_filter": {
    "agent_id": "agent_1",
    "source": "memory",
    "status": "active"
  }
}
```

**Behavior**: All conditions must match (AND logic).

### 2. In List (`$in`)

Match if value is in a list:

```json
{
  "metadata_filter": {
    "agent_id": {"$in": ["agent_1", "agent_2", "agent_3"]},
    "status": {"$in": ["active", "completed"]}
  }
}
```

**Use Cases**:
- Multi-agent queries
- Multiple status values
- Tag matching

### 3. Contains (`$contains`)

Match if string contains substring:

```json
{
  "metadata_filter": {
    "status": {"$contains": "pend"},  // Matches "pending", "suspended"
    "description": {"$contains": "compliance"}
  }
}
```

**Use Cases**:
- Partial text matching
- Flexible string searches
- Category filtering

### 4. Numeric Comparisons

#### Greater Than or Equal (`$gte`)

```json
{
  "metadata_filter": {
    "score": {"$gte": 0.8},
    "confidence": {"$gte": 0.9}
  }
}
```

#### Greater Than (`$gt`)

```json
{
  "metadata_filter": {
    "score": {"$gt": 0.75}
  }
}
```

#### Less Than or Equal (`$lte`)

```json
{
  "metadata_filter": {
    "risk_score": {"$lte": 0.3},
    "age_days": {"$lte": 30}
  }
}
```

#### Less Than (`$lt`)

```json
{
  "metadata_filter": {
    "priority": {"$lt": 5}
  }
}
```

**Use Cases**:
- Threshold filtering
- Score-based filtering
- Time-based filtering

### 5. Field Existence (`$exists`)

Check if a field exists or doesn't exist:

```json
{
  "metadata_filter": {
    "audit_log": {"$exists": True},
    "optional_field": {"$exists": False}
  }
}
```

**Use Cases**:
- Finding records with optional fields populated
- Detecting missing data
- Schema validation

### 6. Not Equals (`$not_equals`)

Match values that don't equal a specific value:

```json
{
  "metadata_filter": {
    "status": {"$not_equals": "deleted"},
    "agent_id": {"$not_equals": "system"}
  }
}
```

**Use Cases**:
- Exclusion filters
- Negative matching

## Complete API Examples

### Example 1: Compliance Query

Search for high-confidence compliance checks from specific agents:

```python
import requests

response = requests.post(
    "https://api.ainative.studio/v1/public/proj_abc123/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "compliance check results",
        "top_k": 10,
        "similarity_threshold": 0.7,
        "metadata_filter": {
            "agent_id": {"$in": ["compliance_agent_1", "compliance_agent_2"]},
            "confidence": {"$gte": 0.8},
            "status": "completed",
            "audit_trail": {"$exists": True}
        }
    }
)

results = response.json()
```

### Example 2: Risk Assessment

Find recent high-risk assessments:

```python
response = requests.post(
    "https://api.ainative.studio/v1/public/proj_abc123/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "financial risk assessment",
        "top_k": 20,
        "metadata_filter": {
            "risk_level": {"$in": ["high", "critical"]},
            "age_days": {"$lte": 7},
            "reviewed": True
        }
    }
)
```

### Example 3: Agent Memory Retrieval

Retrieve specific agent memories with quality threshold:

```python
response = requests.post(
    "https://api.ainative.studio/v1/public/proj_abc123/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "fintech transaction analysis",
        "namespace": "agent_memory",
        "top_k": 5,
        "metadata_filter": {
            "agent_id": "agent_xyz",
            "source": "decision",
            "quality_score": {"$gte": 0.85},
            "tags": {"$in": ["fintech", "transaction", "analysis"]}
        }
    }
)
```

## Filter Execution Flow

1. **Similarity Search**: First, vectors are searched by semantic similarity to the query
2. **Top-K Selection**: The top K most similar vectors are selected based on `top_k` parameter
3. **Metadata Filtering**: Metadata filters are applied to refine the top-K results
4. **Final Results**: Only vectors matching both similarity AND metadata criteria are returned

This ensures you get the most semantically relevant results that also match your metadata requirements.

## Performance Considerations

### Best Practices

1. **Use similarity threshold first**: Set `similarity_threshold` to reduce candidates before metadata filtering
2. **Combine filters effectively**: Use multiple filters to narrow results progressively
3. **Index frequently filtered fields**: Consider metadata structure for common query patterns
4. **Limit metadata size**: Keep metadata focused and concise

### Efficient Query Patterns

```python
# Good: Narrow by similarity first, then refine with metadata
{
    "query": "compliance",
    "similarity_threshold": 0.7,  # Reduces candidates
    "top_k": 10,
    "metadata_filter": {"agent_id": "agent_1"}
}

# Less efficient: Large top_k with complex metadata filters
{
    "query": "compliance",
    "top_k": 1000,  # Many candidates to filter
    "metadata_filter": {
        "field1": {"$gte": 0.5},
        "field2": {"$in": [...]},
        "field3": {"$contains": "..."}
    }
}
```

## Filter Validation

All metadata filters are validated before execution:

### Valid Filters

```python
# Simple equality
{"agent_id": "agent_1"}  ✓

# Operators with $ prefix
{"score": {"$gte": 0.8}}  ✓

# Multiple conditions
{"agent_id": "agent_1", "score": {"$gte": 0.8}}  ✓
```

### Invalid Filters

```python
# Not a dictionary
"agent_id=agent_1"  ✗

# Operator without $ prefix
{"score": {"gte": 0.8}}  ✗

# Unsupported operator
{"field": {"$regex": "pattern"}}  ✗

# Wrong value type for operator
{"score": {"$gte": "not_a_number"}}  ✗
```

## Error Handling

### Common Errors

#### 1. Invalid Filter Format

```json
{
  "detail": "metadata_filter must be a dictionary",
  "error_code": "VALIDATION_ERROR"
}
```

**Solution**: Ensure filter is a JSON object/dictionary.

#### 2. Unsupported Operator

```json
{
  "detail": "Unsupported operator: $regex. Supported operators: $eq, $in, $contains, ...",
  "error_code": "VALIDATION_ERROR"
}
```

**Solution**: Use only supported operators listed in this guide.

#### 3. Type Mismatch

```json
{
  "detail": "Operator '$gte' requires a numeric value, got: <class 'str'>",
  "error_code": "VALIDATION_ERROR"
}
```

**Solution**: Ensure value types match operator requirements.

## No-Match Cases

When no vectors match your metadata filter, the API returns an empty results list:

```json
{
  "results": [],
  "query": "compliance",
  "namespace": "default",
  "model": "BAAI/bge-small-en-v1.5",
  "total_results": 0,
  "processing_time_ms": 15
}
```

This is a valid response indicating:
- The similarity search found results
- But none matched the metadata criteria
- Consider relaxing your metadata filters or checking your data

## Combining with Other Features

### With Namespace Isolation (Issue #17)

```python
{
    "query": "compliance",
    "namespace": "prod_agent_1",  # Namespace isolation
    "metadata_filter": {
        "environment": "production",
        "agent_id": "agent_1"
    }
}
```

### With Similarity Threshold (Issue #22)

```python
{
    "query": "compliance",
    "similarity_threshold": 0.75,  # Semantic relevance
    "metadata_filter": {
        "confidence": {"$gte": 0.8}  # Metadata quality
    }
}
```

### With Field Optimization (Issue #26)

```python
{
    "query": "compliance",
    "metadata_filter": {"agent_id": "agent_1"},
    "include_metadata": True,  # Include metadata in results
    "include_embeddings": False  # Reduce response size
}
```

## Use Case Examples

### 1. Compliance & Audit

```python
# Find all passed compliance checks from the last week
{
    "query": "compliance audit",
    "metadata_filter": {
        "check_type": "compliance",
        "status": "passed",
        "age_days": {"$lte": 7},
        "audit_trail": {"$exists": True}
    }
}
```

### 2. Multi-Agent Systems

```python
# Search across specific agents for high-quality decisions
{
    "query": "transaction decision",
    "metadata_filter": {
        "agent_id": {"$in": ["agent_1", "agent_2", "agent_3"]},
        "decision_type": "transaction",
        "confidence": {"$gte": 0.9}
    }
}
```

### 3. Time-Based Filtering

```python
# Recent memories with high relevance
{
    "query": "customer interaction",
    "metadata_filter": {
        "age_hours": {"$lte": 24},
        "relevance_score": {"$gte": 0.8},
        "archived": {"$not_equals": True}
    }
}
```

### 4. Tag-Based Organization

```python
# Find vectors with specific tags
{
    "query": "fintech analysis",
    "metadata_filter": {
        "tags": {"$in": ["fintech", "compliance", "risk"]},
        "category": "analysis"
    }
}
```

## Best Practices Summary

1. ✓ **Use simple equality for exact matches** - Fastest and most straightforward
2. ✓ **Set similarity threshold** - Reduce candidates before metadata filtering
3. ✓ **Combine operators logically** - All conditions must match (AND logic)
4. ✓ **Structure metadata consistently** - Same fields across similar vectors
5. ✓ **Validate filters early** - API validates on submission
6. ✓ **Handle empty results** - Check `total_results` field
7. ✓ **Test with your data** - Verify filters match your metadata structure

## Technical Details

### Filter Application Order

1. Namespace isolation (if specified)
2. User ID filtering (if specified)
3. Cosine similarity calculation
4. Similarity threshold filtering
5. Top-K selection
6. **Metadata filtering** ← Applied here
7. Results returned

### Supported Operators Reference

| Operator | Type | Description | Example |
|----------|------|-------------|---------|
| (none) | Any | Exact equality | `{"field": "value"}` |
| `$eq` | Any | Explicit equality | `{"field": {"$eq": "value"}}` |
| `$not_equals` | Any | Not equal | `{"field": {"$not_equals": "value"}}` |
| `$in` | List | Value in list | `{"field": {"$in": ["a", "b"]}}` |
| `$contains` | String | Substring match | `{"field": {"$contains": "sub"}}` |
| `$gt` | Number | Greater than | `{"field": {"$gt": 5}}` |
| `$gte` | Number | Greater or equal | `{"field": {"$gte": 5}}` |
| `$lt` | Number | Less than | `{"field": {"$lt": 5}}` |
| `$lte` | Number | Less or equal | `{"field": {"$lte": 5}}` |
| `$exists` | Boolean | Field exists | `{"field": {"$exists": True}}` |

## References

- **Issue #24**: Metadata filtering implementation
- **PRD §6**: Compliance & audit requirements
- **Epic 5, Story 4**: Filter search results by metadata (2 points)
- **DX Contract**: Filtering standards and guarantees

## Support

For issues or questions:
1. Check metadata structure matches your filter
2. Validate filter format with examples above
3. Test with simple filters first
4. Review API error messages for validation details
