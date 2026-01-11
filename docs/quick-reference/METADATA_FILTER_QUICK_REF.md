# Metadata Filtering Quick Reference

## Basic Usage

```python
import requests

response = requests.post(
    "https://api.ainative.studio/v1/public/{project_id}/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "your search query",
        "metadata_filter": {
            # Your filters here
        }
    }
)
```

## Filter Operations Cheat Sheet

| Operation | Syntax | Example | Use Case |
|-----------|--------|---------|----------|
| **Equals** | `{"field": "value"}` | `{"agent_id": "agent_1"}` | Exact match |
| **In List** | `{"field": {"$in": [...]}}` | `{"status": {"$in": ["active", "pending"]}}` | Multiple values |
| **Contains** | `{"field": {"$contains": "..."}}` | `{"text": {"$contains": "compliance"}}` | Partial match |
| **Greater Than** | `{"field": {"$gt": N}}` | `{"score": {"$gt": 0.8}}` | Threshold |
| **Greater or Equal** | `{"field": {"$gte": N}}` | `{"confidence": {"$gte": 0.75}}` | Min value |
| **Less Than** | `{"field": {"$lt": N}}` | `{"risk": {"$lt": 0.3}}` | Max value |
| **Less or Equal** | `{"field": {"$lte": N}}` | `{"age_days": {"$lte": 7}}` | Time window |
| **Exists** | `{"field": {"$exists": true}}` | `{"audit_log": {"$exists": true}}` | Field present |
| **Not Equals** | `{"field": {"$not_equals": "..."}}` | `{"status": {"$not_equals": "deleted"}}` | Exclusion |

## Common Patterns

### Compliance Query
```python
{
    "query": "compliance check",
    "metadata_filter": {
        "agent_id": {"$in": ["compliance_agent_1", "compliance_agent_2"]},
        "confidence": {"$gte": 0.8},
        "audit_trail": {"$exists": True}
    }
}
```

### High-Quality Recent Results
```python
{
    "query": "transaction analysis",
    "metadata_filter": {
        "quality_score": {"$gte": 0.85},
        "age_days": {"$lte": 7},
        "status": "completed"
    }
}
```

### Multi-Agent Search
```python
{
    "query": "risk assessment",
    "metadata_filter": {
        "agent_id": {"$in": ["agent_1", "agent_2", "agent_3"]},
        "reviewed": True
    }
}
```

### Tag-Based Filtering
```python
{
    "query": "fintech analysis",
    "metadata_filter": {
        "category": "fintech",
        "tags": {"$in": ["compliance", "audit", "risk"]}
    }
}
```

## Tips

- ✓ Filters use AND logic (all must match)
- ✓ Applied AFTER similarity search
- ✓ Operators need `$` prefix
- ✓ Empty filter `{}` returns all results
- ✓ `None` filter same as no filter
- ✓ Validation happens before search

## Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| "must be a dictionary" | Wrong type | Use JSON object |
| "Unsupported operator" | Invalid operator | Check spelling, add `$` |
| "requires a list value" | Wrong type for `$in` | Use array `[...]` |
| "requires a numeric value" | Wrong type for comparison | Use number |

## Full Documentation

See `/backend/METADATA_FILTERING_GUIDE.md` for complete details.
