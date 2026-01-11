"""
Embed-and-store API schemas for Issue #16, Issue #17, Issue #18, and Issue #19.

Epic 4 Story 1: As a developer, I can embed and store documents via embed-and-store endpoint.
Epic 4 Story 2 (Issue #17): As a developer, namespace scopes retrieval correctly.
Epic 4 Story 3 (Issue #18): As a developer, upsert: true updates existing IDs without duplication.
Epic 4 Story 4 (Issue #19): Response includes vectors_stored, model, dimensions, vector_ids.

Per PRD Section 6 (Agent memory foundation):
- Accept documents (text) and automatically generate embeddings
- Store both the document text and embedding vector in ZeroDB
- Support optional metadata and namespace parameters
- Return confirmation with vector IDs and document count

Per PRD Section 9 (Demo proof):
- Response must include comprehensive metadata for observability
- success, vectors_stored, model, dimensions are required fields
- Optional include_details parameter for per-vector status

Per PRD Section 10 (Replayability):
- When upsert=true and vector_id exists: UPDATE the existing vector
- When upsert=false and vector_id exists: Return error VECTOR_ALREADY_EXISTS
- When upsert=true and vector_id doesn't exist: INSERT as new vector
- Track and return which vectors were inserted vs updated in response
- Ensure idempotent behavior for replay scenarios

DX Contract Guarantee:
- When model is omitted, BAAI/bge-small-en-v1.5 (384-dim) is used
- Namespace defaults to 'default' when omitted
- Returns deterministic vector IDs for stored documents
- Response format is consistent with DX Contract Section 7

Issue #17 Namespace Rules:
- Valid characters: a-z, A-Z, 0-9, underscore, hyphen
- Max length: 64 characters
- Cannot start with underscore or hyphen
- Cannot be empty if provided
- INVALID_NAMESPACE (422) for invalid format
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    is_model_supported,
    get_supported_models
)
from app.core.namespace_validator import (
    validate_namespace as _validate_namespace_func,
    NamespaceValidationError,
    DEFAULT_NAMESPACE
)


class EmbedAndStoreRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/embeddings/embed-and-store.

    Epic 4 Story 1 (Issue #16): Embed and store documents with metadata.
    Epic 4 Story 2 (Issue #17): Namespace scopes retrieval correctly.
    Epic 4 Story 3 (Issue #18): Support upsert parameter for vector updates.

    Per PRD Section 6 (Agent memory foundation):
    - Accept documents (text) and automatically generate embeddings
    - Support optional metadata for document classification
    - Support optional namespace for logical separation

    Per PRD Section 10 (Replayability - Issue #18):
    - When upsert=true and vector_id exists: UPDATE the existing vector
    - When upsert=false and vector_id exists: Return error VECTOR_ALREADY_EXISTS
    - When upsert=true and vector_id doesn't exist: INSERT as new vector
    - Track and return which vectors were inserted vs updated in response
    - Ensure idempotent behavior for replay scenarios

    DX Contract Guarantee:
    - When model is omitted, BAAI/bge-small-en-v1.5 (384-dim) is used
    - Namespace defaults to 'default' when omitted

    Issue #17 Namespace Rules:
    - Valid characters: a-z, A-Z, 0-9, underscore, hyphen
    - Max length: 64 characters
    - Cannot start with underscore or hyphen
    - Cannot be empty if provided
    """
    documents: List[str] = Field(
        ...,
        min_items=1,
        description="List of text documents to embed and store (required, non-empty)"
    )
    model: Optional[str] = Field(
        default=None,
        description=f"Embedding model to use. Defaults to '{DEFAULT_EMBEDDING_MODEL}' (384 dimensions) when omitted"
    )
    metadata: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional metadata for each document. If provided, must match documents length."
    )
    namespace: Optional[str] = Field(
        default="default",
        description=(
            "Logical namespace for organizing vectors (Issue #17). "
            "Defaults to 'default'. Valid: alphanumeric, underscore, hyphen. "
            "Max 64 chars. Cannot start with underscore or hyphen."
        )
    )
    upsert: bool = Field(
        default=False,
        description=(
            "Upsert behavior (Issue #18, PRD Section 10 Replayability): "
            "When true, updates existing vector if vector_id exists (idempotent). "
            "When false (default), creates new vector or returns 409 VECTOR_ALREADY_EXISTS "
            "if vector_id already exists. Enables replay scenarios."
        )
    )
    vector_ids: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional list of custom vector IDs (Issue #18). "
            "If provided, must match documents length. "
            "When upsert=true and ID exists, vector is updated. "
            "When upsert=false and ID exists, returns VECTOR_ALREADY_EXISTS error. "
            "If not provided, IDs are auto-generated."
        )
    )
    include_details: bool = Field(
        default=False,
        description=(
            "Include per-vector status details in response (Issue #19). "
            "When true, response includes 'details' array with vector_id, text_preview, "
            "and status (inserted/updated) for each vector. Useful for debugging and observability."
        )
    )

    @validator('documents')
    def documents_not_empty(cls, v):
        """Ensure all documents are not just whitespace."""
        if not v:
            raise ValueError("Documents list cannot be empty")

        cleaned_docs = []
        for idx, doc in enumerate(v):
            if not doc or not doc.strip():
                raise ValueError(f"Document at index {idx} cannot be empty or whitespace")
            cleaned_docs.append(doc.strip())

        return cleaned_docs

    @validator('model')
    def validate_model(cls, v):
        """Validate that the specified model is supported."""
        if v is None:
            return DEFAULT_EMBEDDING_MODEL

        if not is_model_supported(v):
            supported = ", ".join(get_supported_models().keys())
            raise ValueError(
                f"Model '{v}' is not supported. "
                f"Supported models: {supported}"
            )

        return v

    @validator('metadata')
    def validate_metadata(cls, v, values):
        """Ensure metadata length matches documents length if provided."""
        if v is not None and 'documents' in values:
            if len(v) != len(values['documents']):
                raise ValueError(
                    f"Metadata length ({len(v)}) must match documents length ({len(values['documents'])})"
                )
        return v

    @validator('namespace')
    def validate_namespace(cls, v):
        """
        Validate namespace per Issue #17 requirements.

        Rules:
        - Valid characters: a-z, A-Z, 0-9, underscore, hyphen
        - Max length: 64 characters
        - Cannot start with underscore or hyphen
        - Cannot be empty if provided
        - Defaults to 'default' when None or empty
        """
        try:
            return _validate_namespace_func(v)
        except NamespaceValidationError as e:
            raise ValueError(e.message)

    @validator('vector_ids')
    def validate_vector_ids(cls, v, values):
        """
        Validate vector_ids length matches documents length if provided.

        Issue #18: Custom vector IDs for upsert operations.
        - If vector_ids is provided, length must match documents length
        - Each vector_id should be a non-empty string
        """
        if v is not None and 'documents' in values:
            if len(v) != len(values['documents']):
                raise ValueError(
                    f"vector_ids length ({len(v)}) must match documents length ({len(values['documents'])})"
                )
            # Validate each vector_id is non-empty
            for idx, vid in enumerate(v):
                if not vid or not vid.strip():
                    raise ValueError(f"vector_id at index {idx} cannot be empty or whitespace")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "documents": [
                    "Autonomous fintech agent executing compliance check",
                    "Transaction risk assessment completed successfully"
                ],
                "model": "BAAI/bge-small-en-v1.5",
                "metadata": [
                    {"source": "agent_memory", "agent_id": "compliance_agent", "type": "decision"},
                    {"source": "agent_memory", "agent_id": "risk_agent", "type": "assessment"}
                ],
                "namespace": "agent_memory",
                "upsert": True,
                "vector_ids": ["vec_compliance_001", "vec_risk_001"],
                "include_details": True
            }
        }


class VectorStorageResult(BaseModel):
    """
    Result of storing a single vector.

    Contains the vector ID, document metadata, and whether it was inserted or updated.

    Issue #18: Track whether each vector was inserted (new) or updated (existing).
    """
    vector_id: str = Field(..., description="Unique identifier for the stored vector")
    document: str = Field(..., description="Original document text")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Associated metadata")
    created: bool = Field(
        default=True,
        description="True if vector was inserted (new), False if updated (existing). Issue #18."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vector_id": "vec_abc123xyz456",
                "document": "Autonomous fintech agent executing compliance check",
                "metadata": {"source": "agent_memory", "agent_id": "compliance_agent"},
                "created": True
            }
        }


class VectorDetail(BaseModel):
    """
    Per-vector status detail for Issue #18 and #19.

    Provides detailed information about each vector operation including:
    - vector_id: The ID of the stored vector
    - text_preview: Truncated preview of the document text
    - status: Whether the vector was 'inserted' (new) or 'updated' (existing)

    Only included in response when include_details=true in the request.
    """
    vector_id: str = Field(
        ...,
        description="Unique identifier for the stored vector"
    )
    text_preview: str = Field(
        ...,
        description="Truncated preview of the document text (first 50 characters with ellipsis if longer)"
    )
    status: Literal["inserted", "updated"] = Field(
        ...,
        description="Vector operation status: 'inserted' for new vectors, 'updated' for existing vectors"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vector_id": "vec_abc123xyz456",
                "text_preview": "Autonomous fintech agent executing compliance...",
                "status": "inserted"
            }
        }


class EmbedAndStoreResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/embeddings/embed-and-store.

    Epic 4 Story 1 (Issue #16): Return confirmation with vector IDs and count.
    Epic 4 Story 2 (Issue #17): Return namespace for confirmation.
    Epic 4 Story 3 (Issue #18): Track and return which vectors were inserted vs updated.
    Epic 4 Story 4 (Issue #19): Response includes vectors_stored, model, dimensions.

    Per PRD Section 6:
    - Return vector IDs for all stored documents
    - Include document count for verification (vectors_stored per Issue #19)
    - Include model and dimensions for transparency (Issue #19)
    - Include processing time for observability

    Per PRD Section 10 (Replayability - Issue #18):
    - Track vectors_inserted (new vectors created)
    - Track vectors_updated (existing vectors updated via upsert)
    - Ensure idempotent behavior for replay scenarios
    """
    vectors_stored: int = Field(
        ...,
        description="Total number of vectors successfully stored (Issue #19 - required field)",
        ge=0
    )
    vectors_inserted: int = Field(
        ...,
        description="Number of new vectors inserted (Issue #18 - required field)",
        ge=0
    )
    vectors_updated: int = Field(
        ...,
        description="Number of existing vectors updated via upsert (Issue #18 - required field)",
        ge=0
    )
    model: str = Field(
        ...,
        description="Model used for embedding generation (Issue #19 - required field)"
    )
    dimensions: int = Field(
        ...,
        description="Dimensionality of the embedding vectors (Issue #19 - required field)"
    )
    vector_ids: List[str] = Field(
        ...,
        description="List of vector IDs for stored documents"
    )
    namespace: str = Field(
        ...,
        description="Namespace where vectors were stored (Issue #17 - confirms isolation)"
    )
    results: List[VectorStorageResult] = Field(
        ...,
        description="Detailed results for each stored document"
    )
    processing_time_ms: int = Field(
        ...,
        description="Total processing time in milliseconds (Issue #19 - included when available)",
        ge=0
    )
    details: Optional[List[VectorDetail]] = Field(
        default=None,
        description=(
            "Per-vector status details (Issue #18/#19 - optional). "
            "Only included when include_details=true in the request. "
            "Contains vector_id, text_preview, and status (inserted/updated) for each vector."
        )
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vectors_stored": 3,
                "vectors_inserted": 2,
                "vectors_updated": 1,
                "model": "BAAI/bge-small-en-v1.5",
                "dimensions": 384,
                "vector_ids": ["vec_abc123", "vec_xyz789", "vec_def456"],
                "namespace": "agent_memory",
                "results": [
                    {
                        "vector_id": "vec_abc123",
                        "document": "Autonomous fintech agent executing compliance check",
                        "metadata": {"source": "agent_memory", "agent_id": "compliance_agent"},
                        "created": True
                    },
                    {
                        "vector_id": "vec_xyz789",
                        "document": "Transaction risk assessment completed",
                        "metadata": {"source": "agent_memory", "agent_id": "risk_agent"},
                        "created": True
                    },
                    {
                        "vector_id": "vec_def456",
                        "document": "Updated compliance policy document",
                        "metadata": {"source": "agent_memory", "agent_id": "policy_agent"},
                        "created": False
                    }
                ],
                "processing_time_ms": 125
            }
        }
