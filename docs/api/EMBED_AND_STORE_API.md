# Issue #16: Embed and Store API Documentation

## Overview

The `POST /v1/public/{project_id}/embeddings/embed-and-store` endpoint enables developers to embed multiple documents and store them in ZeroDB vector storage in a single API call.

**Epic:** Epic 4 Story 1 (2 points)
**PRD Reference:** §6 (Agent memory foundation)
**DX Contract:** Compliant with §3 (Embeddings & Vectors)

---

## Endpoint

### POST /v1/public/{project_id}/embeddings/embed-and-store

Generate embedding vectors for multiple documents and store them in ZeroDB.

#### Authentication
- **Required:** Yes
- **Method:** X-API-Key header
- **Format:** `X-API-Key: your_api_key_here`

#### URL Parameters
- `project_id` (string, required): Project identifier

#### Request Body

```json
{
  "documents": ["string"],
  "model": "string (optional)",
  "metadata": [{"key": "value"}] (optional),
  "namespace": "string (optional)"
}
```

**Fields:**

- `documents` (array of strings, required)
  - List of text documents to embed and store
  - Minimum: 1 document
  - Each document must be non-empty (no whitespace-only)
  - Example: `["Autonomous fintech agent executing compliance check", "Transaction risk assessment completed"]`

- `model` (string, optional)
  - Embedding model to use
  - Default: `BAAI/bge-small-en-v1.5` (384 dimensions)
  - Supported models:
    - `BAAI/bge-small-en-v1.5`: 384 dimensions (default)
    - `sentence-transformers/all-MiniLM-L6-v2`: 384 dimensions
    - `sentence-transformers/all-mpnet-base-v2`: 768 dimensions
    - See `GET /embeddings/models` for full list

- `metadata` (array of objects, optional)
  - Metadata for each document
  - If provided, length must match documents length
  - Each entry is a key-value object
  - Example: `[{"source": "agent_memory", "agent_id": "compliance_agent"}]`

- `namespace` (string, optional)
  - Logical namespace for organizing vectors
  - Default: `"default"`
  - Must contain only alphanumeric characters, underscores, and hyphens
  - Used for logical separation of vector collections
  - Example: `"agent_memory"`, `"compliance_logs"`, `"user_documents"`

#### Response (200 OK)

```json
{
  "vector_ids": ["string"],
  "stored_count": 2,
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "namespace": "default",
  "results": [
    {
      "vector_id": "vec_abc123xyz456",
      "document": "Autonomous fintech agent executing compliance check",
      "metadata": {"source": "agent_memory", "agent_id": "compliance_agent"}
    }
  ],
  "processing_time_ms": 125
}
```

**Response Fields:**

- `vector_ids` (array of strings): Unique identifiers for all stored vectors
- `stored_count` (integer): Number of documents successfully stored
- `model` (string): Model used for embedding generation
- `dimensions` (integer): Dimensionality of the embedding vectors
- `namespace` (string): Namespace where vectors were stored
- `results` (array): Detailed results for each document
  - `vector_id` (string): Unique vector identifier
  - `document` (string): Original document text
  - `metadata` (object, nullable): Associated metadata
- `processing_time_ms` (integer): Total processing time in milliseconds

#### Error Responses

##### 401 Unauthorized
Missing or invalid API key.

```json
{
  "detail": "Invalid or missing API key",
  "error_code": "UNAUTHORIZED"
}
```

##### 404 Not Found
Model not found or not supported.

```json
{
  "detail": "Model 'unsupported-model' not found. Supported models: ...",
  "error_code": "MODEL_NOT_FOUND"
}
```

##### 422 Unprocessable Entity
Validation errors (empty documents, metadata mismatch, invalid namespace, etc.)

```json
{
  "detail": [
    {
      "loc": ["body", "documents", 0],
      "msg": "Document at index 0 cannot be empty or whitespace",
      "type": "value_error"
    }
  ]
}
```

Common validation errors:
- Empty documents list
- Whitespace-only documents
- Metadata length doesn't match documents length
- Invalid namespace characters
- Unsupported model

---

## Examples

### Environment Setup

```bash
# Set environment variables
export API_KEY="your_api_key_here"
export PROJECT_ID="proj_abc123"
export BASE_URL="https://api.ainative.studio"
```

### Example 1: Basic Usage (Single Document)

**Request:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/embeddings/embed-and-store" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": ["Autonomous fintech agent executing compliance check"]
  }'
```

**Response:**
```json
{
  "vector_ids": ["vec_a1b2c3d4e5f6"],
  "stored_count": 1,
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "namespace": "default",
  "results": [
    {
      "vector_id": "vec_a1b2c3d4e5f6",
      "document": "Autonomous fintech agent executing compliance check",
      "metadata": null
    }
  ],
  "processing_time_ms": 52
}
```

### Example 2: Batch Documents with Metadata

**Request:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/embeddings/embed-and-store" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      "Autonomous fintech agent executing compliance check",
      "Transaction risk assessment completed successfully",
      "Portfolio rebalancing recommendation generated"
    ],
    "metadata": [
      {"source": "agent_memory", "agent_id": "compliance_agent", "type": "decision"},
      {"source": "agent_memory", "agent_id": "risk_agent", "type": "assessment"},
      {"source": "agent_memory", "agent_id": "portfolio_agent", "type": "recommendation"}
    ],
    "namespace": "agent_memory"
  }'
```

**Response:**
```json
{
  "vector_ids": ["vec_a1b2c3", "vec_d4e5f6", "vec_g7h8i9"],
  "stored_count": 3,
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "namespace": "agent_memory",
  "results": [
    {
      "vector_id": "vec_a1b2c3",
      "document": "Autonomous fintech agent executing compliance check",
      "metadata": {"source": "agent_memory", "agent_id": "compliance_agent", "type": "decision"}
    },
    {
      "vector_id": "vec_d4e5f6",
      "document": "Transaction risk assessment completed successfully",
      "metadata": {"source": "agent_memory", "agent_id": "risk_agent", "type": "assessment"}
    },
    {
      "vector_id": "vec_g7h8i9",
      "document": "Portfolio rebalancing recommendation generated",
      "metadata": {"source": "agent_memory", "agent_id": "portfolio_agent", "type": "recommendation"}
    }
  ],
  "processing_time_ms": 125
}
```

### Example 3: Custom Model

**Request:**
```bash
curl -X POST "$BASE_URL/v1/public/$PROJECT_ID/embeddings/embed-and-store" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": ["High-quality embedding test"],
    "model": "sentence-transformers/all-mpnet-base-v2"
  }'
```

**Response:**
```json
{
  "vector_ids": ["vec_j1k2l3"],
  "stored_count": 1,
  "model": "sentence-transformers/all-mpnet-base-v2",
  "dimensions": 768,
  "namespace": "default",
  "results": [
    {
      "vector_id": "vec_j1k2l3",
      "document": "High-quality embedding test",
      "metadata": null
    }
  ],
  "processing_time_ms": 68
}
```

### Example 4: Python Client

```python
import requests
import os

# Use standard environment variables
API_KEY = os.getenv('API_KEY', 'your_api_key_here')
PROJECT_ID = os.getenv('PROJECT_ID', 'proj_abc123')
BASE_URL = os.getenv('BASE_URL', 'https://api.ainative.studio')

def embed_and_store_documents(documents, metadata=None, namespace="default", model=None):
    """
    Embed and store multiple documents in ZeroDB.

    Args:
        documents: List of text documents
        metadata: Optional list of metadata dicts
        namespace: Logical namespace for organization
        model: Optional embedding model

    Returns:
        Response data with vector IDs and results
    """
    url = f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    payload = {"documents": documents}
    if metadata:
        payload["metadata"] = metadata
    if namespace:
        payload["namespace"] = namespace
    if model:
        payload["model"] = model

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()

# Usage
documents = [
    "Autonomous fintech agent executing compliance check",
    "Transaction risk assessment completed successfully"
]

metadata = [
    {"source": "agent_memory", "agent_id": "compliance_agent"},
    {"source": "agent_memory", "agent_id": "risk_agent"}
]

result = embed_and_store_documents(
    documents=documents,
    metadata=metadata,
    namespace="agent_memory"
)

print(f"Stored {result['stored_count']} documents")
print(f"Vector IDs: {result['vector_ids']}")
```

---

## DX Contract Guarantees

Per DX Contract §3 (Embeddings & Vectors):

1. **Default Model:** When `model` is omitted, `BAAI/bge-small-en-v1.5` (384 dimensions) is used
2. **Default Namespace:** When `namespace` is omitted, `"default"` is used
3. **Deterministic Behavior:** Same input always produces same output
4. **Model Consistency:** The same model must be used for store and search operations
5. **Error Format:** All errors return `{ detail, error_code }` format
6. **Dimension Validation:** Embeddings always match the model's expected dimensions

---

## Best Practices

### 1. Batch Processing
- Process multiple documents in a single request for better performance
- Recommended batch size: 10-100 documents per request
- Use pagination for larger datasets

### 2. Metadata Usage
- Include metadata for document classification and filtering
- Common metadata fields:
  - `source`: Where the document came from
  - `agent_id`: Which agent created/owns the document
  - `type`: Document type (decision, assessment, log, etc.)
  - `timestamp`: When the document was created
  - `version`: Document version if applicable

### 3. Namespace Organization
- Use namespaces to logically separate different types of data
- Examples:
  - `agent_memory`: Agent decision history
  - `compliance_logs`: Compliance check results
  - `risk_assessments`: Risk analysis documents
  - `user_documents`: User-uploaded content

### 4. Model Selection
- Use default model (`BAAI/bge-small-en-v1.5`) for most use cases
- Use higher-dimension models for better quality when needed
- Ensure consistency: use the same model for embedding and searching

### 5. Error Handling
```python
try:
    result = embed_and_store_documents(documents, metadata, namespace)
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 422:
        print(f"Validation error: {e.response.json()}")
    elif e.response.status_code == 401:
        print("Authentication error: Check your API key")
    else:
        print(f"Error: {e}")
```

### 6. Agent Memory Pattern
For autonomous agents, use this pattern:
```python
def store_agent_decision(agent_id, decision_text, confidence, context):
    """Store agent decision in memory."""
    metadata = {
        "source": "agent_memory",
        "agent_id": agent_id,
        "type": "decision",
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
        **context
    }

    result = embed_and_store_documents(
        documents=[decision_text],
        metadata=[metadata],
        namespace="agent_memory"
    )

    return result["vector_ids"][0]
```

---

## Testing

Comprehensive tests are available in `/Users/aideveloper/Agent-402/backend/app/tests/test_embed_and_store.py`

Test coverage includes:
- Basic functionality (single and batch documents)
- Metadata support
- Namespace support
- Custom model support
- Input validation
- Error handling
- DX Contract compliance
- Integration with vector storage

To run tests:
```bash
cd /Users/aideveloper/Agent-402/backend
python3 -m pytest app/tests/test_embed_and_store.py -v
```

---

## Implementation Files

- **Schemas:** `/Users/aideveloper/Agent-402/backend/app/schemas/embeddings_store.py`
- **Endpoint:** `/Users/aideveloper/Agent-402/backend/app/api/embeddings_issue16.py`
- **Service:** `/Users/aideveloper/Agent-402/backend/app/services/embedding_service.py`
- **ZeroDB Integration:** `/Users/aideveloper/Agent-402/backend/app/services/zerodb_vector_service.py`
- **Tests:** `/Users/aideveloper/Agent-402/backend/app/tests/test_embed_and_store.py`

---

## Related Endpoints

- `POST /v1/public/{project_id}/embeddings/generate` - Generate embeddings without storage
- `POST /v1/public/{project_id}/embeddings/search` - Search stored vectors (Issue #17)
- `GET /embeddings/models` - List supported embedding models

---

## Support

For issues or questions:
- Review test cases for usage examples
- Check DX Contract for guaranteed behaviors
- Consult datamodel.md for ZeroDB integration patterns
