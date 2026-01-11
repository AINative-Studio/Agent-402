# Namespace Usage Guide

**Issue #17: Namespace scopes retrieval correctly**

This guide explains how to use namespaces to isolate vector storage and retrieval in the Agent-402 API.

## Table of Contents

- [Overview](#overview)
- [What are Namespaces?](#what-are-namespaces)
- [When to Use Namespaces](#when-to-use-namespaces)
- [Namespace Rules](#namespace-rules)
- [API Examples](#api-examples)
- [Multi-Agent Systems](#multi-agent-systems)
- [Best Practices](#best-practices)

## Overview

Namespaces provide complete isolation for vector storage and retrieval. Vectors stored in one namespace are completely invisible to other namespaces, enabling secure multi-tenant and multi-agent systems.

### Key Features

- **Complete Isolation**: Vectors in different namespaces never cross-contaminate
- **Default Namespace**: When omitted, namespace defaults to "default"
- **Case-Sensitive**: "MyNamespace" and "mynamespace" are different namespaces
- **Validation**: Namespace names are validated for security

## What are Namespaces?

A namespace is a logical container for vectors within a project. Think of it like a folder that keeps related vectors together and isolated from others.

### Namespace Guarantees (Per PRD §6)

1. **Isolation**: Vectors stored in namespace A cannot appear in namespace B
2. **Scoping**: Search operations only return vectors from the specified namespace
3. **Independence**: Same vector_id can exist in different namespaces
4. **Default**: When namespace is omitted, "default" namespace is used

## When to Use Namespaces

### Use Case 1: Multi-Agent Systems

Isolate memory for different autonomous agents:

```python
# Agent 1's memory
response = requests.post(
    f"{BASE_URL}/{PROJECT_ID}/embeddings/embed-and-store",
    headers={"X-API-Key": API_KEY},
    json={
        "text": "Compliance check passed for transaction TX-123",
        "namespace": "compliance_agent_memory",
        "metadata": {"agent_id": "compliance_agent", "task": "compliance"}
    }
)

# Agent 2's memory
response = requests.post(
    f"{BASE_URL}/{PROJECT_ID}/embeddings/embed-and-store",
    headers={"X-API-Key": API_KEY},
    json={
        "text": "Risk assessment completed for customer C-456",
        "namespace": "risk_agent_memory",
        "metadata": {"agent_id": "risk_agent", "task": "risk_assessment"}
    }
)
```

### Use Case 2: Environment Isolation

Separate development, staging, and production data:

```python
# Development environment
requests.post(url, json={
    "text": "Test vector for development",
    "namespace": "dev"
})

# Production environment
requests.post(url, json={
    "text": "Production vector",
    "namespace": "prod"
})
```

### Use Case 3: Multi-Tenant Applications

Isolate data for different customers:

```python
# Customer A's data
requests.post(url, json={
    "text": "Customer A's sensitive data",
    "namespace": f"customer_{customer_a_id}"
})

# Customer B's data (completely isolated from A)
requests.post(url, json={
    "text": "Customer B's sensitive data",
    "namespace": f"customer_{customer_b_id}"
})
```

### Use Case 4: Feature Isolation

Test new features without affecting production:

```python
# Experimental feature
requests.post(url, json={
    "text": "Experimental feature data",
    "namespace": "feature_experiment"
})

# Production feature
requests.post(url, json={
    "text": "Production feature data",
    "namespace": "feature_production"
})
```

## Namespace Rules

### Valid Namespace Characters

Namespaces can contain:
- Alphanumeric characters: `a-z`, `A-Z`, `0-9`
- Hyphens: `-`
- Underscores: `_`
- Dots: `.`

### Invalid Namespace Characters

The following characters are **NOT** allowed:
- Spaces: ` `
- Special characters: `/ \ @ # $ % * ! ? [ ] { } ( ) < > | ; : ' "`
- Path traversal: `..`, `./`, `/`

### Validation Rules

1. **Length**: Maximum 128 characters
2. **Empty**: Cannot be empty or whitespace-only
3. **Type**: Must be a string (or `null` for default)
4. **Security**: Path traversal attempts are blocked

### Examples

**Valid Namespaces**:
```python
"agent_1_memory"        # Valid
"production-env"        # Valid
"customer_123"          # Valid
"test.namespace.v2"     # Valid
"MixedCase123"          # Valid
```

**Invalid Namespaces**:
```python
"has spaces"            # Invalid (contains space)
"has/slash"             # Invalid (contains /)
"../parent"             # Invalid (path traversal)
""                      # Invalid (empty)
"   "                   # Invalid (whitespace only)
"a" * 129               # Invalid (too long)
```

## API Examples

### Store Vector in Namespace

**Request**:
```bash
curl -X POST "${BASE_URL}/${PROJECT_ID}/embeddings/embed-and-store" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Autonomous agent compliance check result",
    "namespace": "agent_1_memory",
    "metadata": {
      "agent_id": "compliance_agent",
      "timestamp": "2026-01-10T12:00:00Z"
    }
  }'
```

**Response**:
```json
{
  "vectors_stored": 1,
  "vector_id": "vec_abc123",
  "namespace": "agent_1_memory",
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "text": "Autonomous agent compliance check result",
  "created": true,
  "processing_time_ms": 45,
  "stored_at": "2026-01-10T12:00:00.000Z"
}
```

### Search Within Namespace

**Request**:
```bash
curl -X POST "${BASE_URL}/${PROJECT_ID}/embeddings/search" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compliance check results",
    "namespace": "agent_1_memory",
    "top_k": 5,
    "similarity_threshold": 0.7
  }'
```

**Response**:
```json
{
  "results": [
    {
      "vector_id": "vec_abc123",
      "namespace": "agent_1_memory",
      "text": "Autonomous agent compliance check result",
      "similarity": 0.92,
      "model": "BAAI/bge-small-en-v1.5",
      "dimensions": 384,
      "metadata": {
        "agent_id": "compliance_agent",
        "timestamp": "2026-01-10T12:00:00Z"
      },
      "created_at": "2026-01-10T12:00:00.000Z"
    }
  ],
  "query": "compliance check results",
  "namespace": "agent_1_memory",
  "model": "BAAI/bge-small-en-v1.5",
  "total_results": 1,
  "processing_time_ms": 12
}
```

### Use Default Namespace

When `namespace` is omitted or set to `null`, the "default" namespace is used:

**Request**:
```json
{
  "text": "General purpose vector",
  // namespace omitted - will use "default"
}
```

**Equivalent to**:
```json
{
  "text": "General purpose vector",
  "namespace": "default"
}
```

## Multi-Agent Systems

### Agent Memory Isolation

Each agent should have its own namespace:

```python
# Agent configuration
agents = {
    "compliance_agent": {
        "namespace": "agent_compliance_memory",
        "role": "compliance_check"
    },
    "risk_agent": {
        "namespace": "agent_risk_memory",
        "role": "risk_assessment"
    },
    "approval_agent": {
        "namespace": "agent_approval_memory",
        "role": "final_approval"
    }
}

# Store agent decision
def store_agent_memory(agent_name, text, metadata):
    agent_config = agents[agent_name]

    response = requests.post(
        f"{BASE_URL}/{PROJECT_ID}/embeddings/embed-and-store",
        headers={"X-API-Key": API_KEY},
        json={
            "text": text,
            "namespace": agent_config["namespace"],
            "metadata": {
                **metadata,
                "agent_name": agent_name,
                "agent_role": agent_config["role"]
            }
        }
    )
    return response.json()

# Search agent memory
def search_agent_memory(agent_name, query):
    agent_config = agents[agent_name]

    response = requests.post(
        f"{BASE_URL}/{PROJECT_ID}/embeddings/search",
        headers={"X-API-Key": API_KEY},
        json={
            "query": query,
            "namespace": agent_config["namespace"],
            "top_k": 10
        }
    )
    return response.json()
```

### Cross-Agent Communication

Agents can store shared knowledge in a common namespace:

```python
# Shared knowledge namespace for all agents
SHARED_NAMESPACE = "shared_knowledge"

# Agent 1 stores shared insight
store_agent_memory("compliance_agent",
    "New regulation XYZ requires additional checks",
    {"type": "shared_knowledge", "priority": "high"}
)

# Agent 2 can access shared knowledge (not agent 1's private memory)
results = search_agent_memory("risk_agent", "regulation requirements")
```

## Best Practices

### 1. Naming Conventions

Use descriptive, hierarchical namespace names:

```python
# Good
"agent_compliance_memory"
"customer_123_prod"
"feature_v2_experimental"

# Avoid
"ns1"
"temp"
"test"
```

### 2. Namespace Lifecycle

Clean up unused namespaces periodically:

```python
# List all namespaces
namespaces = list_namespaces(project_id)

# Check stats for each namespace
for namespace in namespaces:
    stats = get_namespace_stats(project_id, namespace)

    if stats["vector_count"] == 0:
        # Consider removing empty namespace
        pass
```

### 3. Security Considerations

- **Never** use user-provided input directly as namespace without validation
- Sanitize namespace names to prevent injection attacks
- Use project-level access control in addition to namespaces
- Audit namespace access patterns

```python
# Bad - Direct user input
namespace = request.get("namespace")  # DANGEROUS!

# Good - Validated and sanitized
namespace = validate_namespace(request.get("namespace"))
```

### 4. Performance Tips

- Use consistent namespace names to leverage caching
- Don't create too many namespaces (100s is fine, 1000s may impact performance)
- Use metadata filters for fine-grained filtering within a namespace
- Monitor namespace sizes using stats endpoint

### 5. Testing Isolation

Always test namespace isolation:

```python
# Test: Vectors in namespace A don't appear in namespace B
def test_namespace_isolation():
    # Store in namespace A
    store_vector(text="A vector", namespace="ns_a")

    # Search in namespace B
    results = search_vectors(query="A vector", namespace="ns_b")

    # Should return empty
    assert len(results) == 0
```

## Error Handling

### Invalid Namespace Error

**Request**:
```json
{
  "text": "Test",
  "namespace": "invalid/namespace"
}
```

**Response** (422 Unprocessable Entity):
```json
{
  "detail": "Namespace can only contain alphanumeric characters, hyphens, underscores, and dots",
  "error_code": "INVALID_NAMESPACE"
}
```

### Empty Namespace Error

**Request**:
```json
{
  "text": "Test",
  "namespace": ""
}
```

**Response** (422 Unprocessable Entity):
```json
{
  "detail": "Namespace cannot be empty or whitespace",
  "error_code": "INVALID_NAMESPACE"
}
```

## Summary

Namespaces provide powerful isolation for multi-agent, multi-tenant, and multi-environment systems. By following the validation rules and best practices in this guide, you can build secure, scalable applications with complete data isolation.

### Key Takeaways

1. Namespaces provide **complete isolation** between vector collections
2. Use **descriptive names** following validation rules
3. Default namespace ("default") is used when namespace is omitted
4. Namespace isolation is **enforced at the storage layer**
5. Test namespace isolation to ensure correct behavior

### Related Documentation

- [API Reference](../api-spec.md)
- [DX Contract](../../DX-Contract.md)
- [PRD](../../PRD.md)
- [Test Examples](../app/tests/test_namespace_isolation.py)
