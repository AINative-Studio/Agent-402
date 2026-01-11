# Namespace Scoping in Search (Issue #23)

## Overview

The `/v1/public/{project_id}/embeddings/search` endpoint supports namespace scoping to enable complete isolation between different agents, environments, or tenants. This document describes how to use namespace parameters in search operations.

## Key Features

- **Namespace Parameter**: Optional `namespace` field in search requests
- **Default Namespace**: When omitted, searches in the `"default"` namespace
- **Complete Isolation**: Vectors in namespace A NEVER appear in namespace B searches
- **Namespace Validation**: Same validation rules as storage operations

## API Reference

### Search Endpoint

```
POST /v1/public/{project_id}/embeddings/search
```

### Request Schema

```json
{
  "query": "your search query",
  "namespace": "optional_namespace",  // Optional, defaults to "default"
  "model": "BAAI/bge-small-en-v1.5",  // Optional, defaults to default model
  "top_k": 10,                         // Optional, max results (1-100)
  "similarity_threshold": 0.0,         // Optional, min similarity (0.0-1.0)
  "metadata_filter": {},               // Optional, filter by metadata
  "include_embeddings": false          // Optional, include vectors in response
}
```

### Response Schema

```json
{
  "results": [
    {
      "vector_id": "vec_abc123",
      "namespace": "team_alpha",       // Confirms searched namespace
      "text": "Original document text",
      "similarity": 0.92,
      "model": "BAAI/bge-small-en-v1.5",
      "dimensions": 384,
      "metadata": {},
      "created_at": "2026-01-11T10:00:00.000Z"
    }
  ],
  "query": "your search query",
  "namespace": "team_alpha",           // Confirms searched namespace
  "model": "BAAI/bge-small-en-v1.5",
  "total_results": 1,
  "processing_time_ms": 15
}
```

## Usage Examples

### Example 1: Search in a Specific Namespace

Search for vectors in the `"agent_1_memory"` namespace:

```python
import requests

response = requests.post(
    "https://api.example.com/v1/public/proj_abc/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "compliance check results",
        "namespace": "agent_1_memory",
        "top_k": 5
    }
)

data = response.json()
print(f"Searched namespace: {data['namespace']}")
print(f"Results found: {data['total_results']}")
for result in data['results']:
    assert result['namespace'] == "agent_1_memory"  // Guaranteed isolation
```

### Example 2: Search in Default Namespace

When namespace parameter is omitted, searches in the `"default"` namespace:

```python
response = requests.post(
    "https://api.example.com/v1/public/proj_abc/embeddings/search",
    headers={"X-API-Key": "your_api_key"},
    json={
        "query": "general documentation",
        "top_k": 10
    }
)

data = response.json()
assert data['namespace'] == "default"
```

### Example 3: Multi-Agent Isolation

Use namespaces to isolate memories between different agents:

```python
# Agent 1 searches its own memory
agent1_search = requests.post(
    f"{base_url}/embeddings/search",
    headers=headers,
    json={
        "query": "previous compliance decisions",
        "namespace": "compliance_agent",
        "metadata_filter": {"agent_id": "agent_1"}
    }
)

# Agent 2 searches its own memory
agent2_search = requests.post(
    f"{base_url}/embeddings/search",
    headers=headers,
    json={
        "query": "risk assessments",
        "namespace": "risk_agent",
        "metadata_filter": {"agent_id": "agent_2"}
    }
)

# Results are completely isolated
assert agent1_search.json()['namespace'] == "compliance_agent"
assert agent2_search.json()['namespace'] == "risk_agent"
# No cross-contamination possible
```

### Example 4: Environment Separation

Use namespaces to separate development, staging, and production data:

```python
# Search production vectors
prod_results = requests.post(
    f"{base_url}/embeddings/search",
    headers=headers,
    json={
        "query": "production configuration",
        "namespace": "production",
        "top_k": 10
    }
)

# Search staging vectors
staging_results = requests.post(
    f"{base_url}/embeddings/search",
    headers=headers,
    json={
        "query": "staging setup",
        "namespace": "staging",
        "top_k": 10
    }
)

# Each environment is completely isolated
assert prod_results.json()['namespace'] == "production"
assert staging_results.json()['namespace'] == "staging"
```

## Namespace Validation Rules

Namespaces must follow these rules (same as storage):

- **Allowed Characters**: Alphanumeric, hyphens (`-`), underscores (`_`), and dots (`.`)
- **Maximum Length**: 128 characters
- **Cannot be Empty**: Empty strings or whitespace-only strings are rejected
- **Case Sensitive**: `"MySpace"` and `"myspace"` are different namespaces

### Valid Namespaces

```python
valid_namespaces = [
    "simple",
    "with-hyphens",
    "with_underscores",
    "with.dots",
    "mixed-chars_123.test",
    "production-v2",
    "agent_memory_2025"
]
```

### Invalid Namespaces (Return HTTP 422)

```python
invalid_namespaces = [
    "has spaces",       # No spaces allowed
    "has/slash",        # No slashes
    "../traversal",     # No path traversal
    "has@symbol",       # No special chars
    "",                 # No empty strings
    "a" * 129           # Too long (>128 chars)
]
```

## Isolation Guarantees

### Complete Isolation

The namespace parameter provides **complete isolation** at the database level:

1. **Storage Isolation**: Vectors stored in namespace A cannot be accessed from namespace B
2. **Search Isolation**: Searching namespace A never returns vectors from namespace B
3. **No Cross-Contamination**: Even with identical vector IDs, namespaces remain isolated
4. **Default Namespace Isolation**: The `"default"` namespace is isolated from all named namespaces

### Isolation Example

```python
# Store vectors in different namespaces
requests.post(f"{base_url}/embeddings/embed-and-store", json={
    "text": "Alpha team secret project",
    "namespace": "team_alpha"
})

requests.post(f"{base_url}/embeddings/embed-and-store", json={
    "text": "Beta team secret project",
    "namespace": "team_beta"
})

# Search in team_alpha
alpha_search = requests.post(f"{base_url}/embeddings/search", json={
    "query": "secret project",
    "namespace": "team_alpha",
    "top_k": 100  # Even with high limit
})

alpha_results = alpha_search.json()
# Will ONLY return alpha team vector
assert alpha_results['total_results'] == 1
assert alpha_results['results'][0]['namespace'] == "team_alpha"
# Beta team vector is completely invisible
```

## Metadata Filtering Within Namespace

Metadata filters are scoped **within** the specified namespace:

```python
# Store vectors with metadata in "logs" namespace
requests.post(f"{base_url}/embeddings/embed-and-store", json={
    "text": "Error: Database connection failed",
    "namespace": "logs",
    "metadata": {"severity": "error", "service": "api"}
})

requests.post(f"{base_url}/embeddings/embed-and-store", json={
    "text": "Info: Request processed successfully",
    "namespace": "logs",
    "metadata": {"severity": "info", "service": "api"}
})

# Search with namespace + metadata filter
search_response = requests.post(f"{base_url}/embeddings/search", json={
    "query": "database",
    "namespace": "logs",
    "metadata_filter": {"severity": "error"},
    "top_k": 10
})

results = search_response.json()
# Only returns error logs from "logs" namespace
assert results['namespace'] == "logs"
for result in results['results']:
    assert result['metadata']['severity'] == "error"
```

## Best Practices

### 1. Consistent Namespace Strategy

Choose a namespace strategy and stick with it:

```python
# Agent-based namespaces
namespace = f"agent_{agent_id}_memory"

# Environment-based namespaces
namespace = f"{environment}_data"  # production_data, staging_data

# Tenant-based namespaces (multi-tenancy)
namespace = f"tenant_{tenant_id}"

# Feature-based namespaces
namespace = f"{feature}_vectors"  # search_vectors, recommendation_vectors
```

### 2. Use Same Namespace for Store and Search

Always use the same namespace when storing and searching:

```python
NAMESPACE = "compliance_agent"

# Store
requests.post(f"{base_url}/embeddings/embed-and-store", json={
    "text": "Compliance document",
    "namespace": NAMESPACE
})

# Search
requests.post(f"{base_url}/embeddings/search", json={
    "query": "compliance",
    "namespace": NAMESPACE  # Use same namespace
})
```

### 3. Document Namespace Usage

Document your namespace strategy for team members:

```python
# Namespace schema:
# - production: Production environment vectors
# - staging: Staging environment vectors
# - agent_<id>: Per-agent memory isolation
# - default: Shared/global vectors

def get_agent_namespace(agent_id: str) -> str:
    """Get namespace for agent's isolated memory."""
    return f"agent_{agent_id}"
```

### 4. Validate Namespace Before Use

Use the namespace validation rules to prevent errors:

```python
import re

def is_valid_namespace(namespace: str) -> bool:
    """Validate namespace format."""
    if not namespace or len(namespace) > 128:
        return False
    return bool(re.match(r'^[a-zA-Z0-9._-]+$', namespace))

# Use validation
namespace = "my-custom-namespace"
if is_valid_namespace(namespace):
    requests.post(f"{base_url}/embeddings/search", json={
        "query": "test",
        "namespace": namespace
    })
```

## Error Handling

### Invalid Namespace Format (HTTP 422)

```python
response = requests.post(f"{base_url}/embeddings/search", json={
    "query": "test",
    "namespace": "invalid/namespace"  # Contains invalid character '/'
})

# Returns HTTP 422
assert response.status_code == 422
error = response.json()
assert "detail" in error
assert "Namespace can only contain" in error["detail"]
```

### Empty Namespace Returns Empty Results

```python
response = requests.post(f"{base_url}/embeddings/search", json={
    "query": "test",
    "namespace": "nonexistent_namespace"  # No vectors in this namespace
})

# Returns HTTP 200 with empty results
assert response.status_code == 200
data = response.json()
assert data['total_results'] == 0
assert data['results'] == []
assert data['namespace'] == "nonexistent_namespace"
```

## References

- **PRD §6**: Agent-scoped memory and isolation
- **Epic 5 Story 3**: Namespace scoping in search
- **Issue #17**: Namespace implementation in storage
- **Issue #23**: Namespace parameter in search endpoint
- **DX Contract**: Deterministic namespace behavior

## See Also

- [Namespace Validation](./NAMESPACE_VALIDATION.md)
- [Agent Memory Isolation](./AGENT_MEMORY_ISOLATION.md)
- [Search API Reference](./SEARCH_API.md)
