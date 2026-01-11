# Namespace Support for Embed-and-Store API

**Issue #17: As a developer, namespace scopes retrieval correctly**
**PRD Reference:** Section 6 (Agent-scoped memory)

This document describes how namespaces work in the embed-and-store API for vector isolation and agent-scoped memory.

## Table of Contents

- [Overview](#overview)
- [Namespace Rules](#namespace-rules)
- [API Usage](#api-usage)
- [Namespace Isolation](#namespace-isolation)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Overview

Namespaces provide complete isolation for vector storage and retrieval in the Agent-402 API. When you store vectors in one namespace, they are completely invisible to other namespaces. This enables:

- **Multi-agent systems**: Each agent can have its own isolated memory
- **Multi-tenant applications**: Customer data is completely separated
- **Environment isolation**: Development, staging, and production data are isolated
- **Feature isolation**: Test new features without affecting production

### Key Guarantees

1. **Complete Isolation**: Vectors in namespace A never appear in namespace B
2. **Scoped Retrieval**: Search operations only return vectors from the specified namespace
3. **Default Namespace**: When omitted, namespace defaults to "default"
4. **Validation**: Namespace names are validated per Issue #17 rules

## Namespace Rules

Per Issue #17, namespace validation follows these rules:

### Valid Characters

- Lowercase letters: `a-z`
- Uppercase letters: `A-Z`
- Numbers: `0-9`
- Underscore: `_`
- Hyphen: `-`

### Constraints

| Rule | Constraint |
|------|------------|
| Max length | 64 characters |
| Start character | Must start with alphanumeric (a-z, A-Z, 0-9) |
| Cannot start with | Underscore (`_`) or hyphen (`-`) |
| Empty handling | Empty/null defaults to "default" |

### Valid Namespace Examples

```
agent_memory
compliance-agent-v1
MyNamespace123
prod
dev
staging
customer_12345
agent-1-memory
```

### Invalid Namespace Examples

```
_private           # Cannot start with underscore
-invalid           # Cannot start with hyphen
has spaces         # No spaces allowed
has/slash          # No slashes allowed
../parent          # No path traversal
has.dot            # Dots NOT allowed per Issue #17
a_very_long_namespace_that_exceeds_sixty_four_characters_limit_here  # Too long
```

## API Usage

### Embed and Store with Namespace

**POST** `/v1/public/{project_id}/embeddings/embed-and-store`

```json
{
  "text": "Compliance check passed for transaction TX-123",
  "namespace": "compliance_agent_memory",
  "model": "BAAI/bge-small-en-v1.5",
  "metadata": {
    "agent_id": "compliance_agent",
    "task": "compliance_check"
  }
}
```

**Response:**

```json
{
  "vectors_stored": 1,
  "vector_id": "vec_abc123",
  "namespace": "compliance_agent_memory",
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "text": "Compliance check passed for transaction TX-123",
  "created": true,
  "processing_time_ms": 45,
  "stored_at": "2026-01-11T12:00:00.000Z"
}
```

### Search with Namespace Scoping

**POST** `/v1/public/{project_id}/embeddings/search`

```json
{
  "query": "compliance check results",
  "namespace": "compliance_agent_memory",
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

**Response:**

```json
{
  "results": [
    {
      "vector_id": "vec_abc123",
      "namespace": "compliance_agent_memory",
      "text": "Compliance check passed for transaction TX-123",
      "similarity": 0.92,
      "model": "BAAI/bge-small-en-v1.5",
      "dimensions": 384,
      "metadata": {
        "agent_id": "compliance_agent",
        "task": "compliance_check"
      },
      "created_at": "2026-01-11T12:00:00.000Z"
    }
  ],
  "query": "compliance check results",
  "namespace": "compliance_agent_memory",
  "model": "BAAI/bge-small-en-v1.5",
  "total_results": 1,
  "processing_time_ms": 12
}
```

### Using Default Namespace

When namespace is omitted or null, "default" is used:

```json
{
  "text": "General purpose vector"
}
```

This is equivalent to:

```json
{
  "text": "General purpose vector",
  "namespace": "default"
}
```

## Namespace Isolation

### Isolation Guarantees

1. **Storage Isolation**: Vectors stored in namespace A are only accessible in namespace A
2. **Search Isolation**: Search in namespace B never returns vectors from namespace A
3. **ID Independence**: The same vector_id can exist in different namespaces

### Example: Multi-Agent Memory Isolation

```python
import requests

BASE_URL = "https://api.example.com/v1/public"
PROJECT_ID = "proj_abc123"
API_KEY = "your_api_key"

headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Agent 1 stores its memory
agent1_response = requests.post(
    f"{BASE_URL}/{PROJECT_ID}/embeddings/embed-and-store",
    headers=headers,
    json={
        "text": "Risk assessment: Transaction approved",
        "namespace": "risk_agent_memory",
        "metadata": {"agent_id": "risk_agent"}
    }
)

# Agent 2 stores its memory
agent2_response = requests.post(
    f"{BASE_URL}/{PROJECT_ID}/embeddings/embed-and-store",
    headers=headers,
    json={
        "text": "Compliance check completed",
        "namespace": "compliance_agent_memory",
        "metadata": {"agent_id": "compliance_agent"}
    }
)

# Agent 1 searches its memory (only sees its own vectors)
search_response = requests.post(
    f"{BASE_URL}/{PROJECT_ID}/embeddings/search",
    headers=headers,
    json={
        "query": "transaction assessment",
        "namespace": "risk_agent_memory",
        "top_k": 10
    }
)
# Returns ONLY vectors from risk_agent_memory namespace
```

## Error Handling

### INVALID_NAMESPACE Error

When an invalid namespace is provided, the API returns:

**HTTP Status:** 422 Unprocessable Entity

**Response:**

```json
{
  "detail": "Namespace cannot start with underscore",
  "error_code": "INVALID_NAMESPACE"
}
```

### Common Validation Errors

| Invalid Input | Error Message |
|---------------|---------------|
| `_private` | "Namespace cannot start with underscore" |
| `-invalid` | "Namespace cannot start with hyphen" |
| `has spaces` | "Namespace can only contain alphanumeric characters, underscores, and hyphens" |
| `a` * 65 | "Namespace cannot exceed 64 characters. Received 65 characters." |

### Error Response Format

All errors follow the DX Contract format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "INVALID_NAMESPACE"
}
```

## Best Practices

### 1. Use Descriptive Namespace Names

```python
# Good - Clear and descriptive
"compliance_agent_memory"
"risk_agent_v2_memory"
"customer_12345_data"

# Avoid - Unclear
"ns1"
"temp"
"test"
```

### 2. Use Consistent Naming Conventions

Choose a naming convention and stick to it:

```python
# Snake case (recommended)
"agent_compliance_memory"
"agent_risk_memory"
"agent_approval_memory"

# Kebab case (also valid)
"agent-compliance-memory"
"agent-risk-memory"
"agent-approval-memory"
```

### 3. Separate Environments

```python
# Development
namespace = f"dev_{agent_id}_memory"

# Staging
namespace = f"staging_{agent_id}_memory"

# Production
namespace = f"prod_{agent_id}_memory"
```

### 4. Validate User Input

Never use user-provided input directly as namespace without validation:

```python
from app.core.namespace_validator import validate_namespace, NamespaceValidationError

def get_user_namespace(user_input: str) -> str:
    """Validate and return namespace, or use default."""
    try:
        return validate_namespace(user_input)
    except NamespaceValidationError:
        # Log the invalid input and use default
        logger.warning(f"Invalid namespace input: {user_input}")
        return "default"
```

### 5. Document Agent Namespaces

Keep track of which namespaces are used by which agents:

```python
AGENT_NAMESPACES = {
    "compliance_agent": "agent_compliance_memory",
    "risk_agent": "agent_risk_memory",
    "approval_agent": "agent_approval_memory",
    "shared": "shared_knowledge"
}
```

## Implementation Details

### Files Modified for Issue #17

1. **`backend/app/core/namespace_validator.py`** - Centralized namespace validation
2. **`backend/app/schemas/embeddings_store.py`** - Schema with namespace validation
3. **`backend/app/schemas/embeddings.py`** - Schema with namespace validation
4. **`backend/app/services/vector_store_service.py`** - Namespace-scoped storage
5. **`backend/app/core/errors.py`** - InvalidNamespaceError class

### Validation Flow

```
Request with namespace
        |
        v
+------------------+
| Schema Validator |
+------------------+
        |
        v
+------------------+
| namespace_       |
| validator.py     |
+------------------+
        |
   Valid?
  /      \
Yes       No
 |         |
 v         v
Store   Return
Vector  INVALID_NAMESPACE
        (422)
```

## Related Documentation

- [NAMESPACE_USAGE.md](./NAMESPACE_USAGE.md) - General namespace usage guide
- [EMBED_AND_STORE_API.md](./EMBED_AND_STORE_API.md) - Full embed-and-store API reference
- [DX-Contract.md](../../DX-Contract.md) - Developer experience guarantees
- [PRD Section 6](../../prd.md) - Agent-scoped memory requirements
