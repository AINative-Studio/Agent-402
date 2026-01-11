"""
Embed-and-store API schemas for Issue #16.

Epic 4 Story 1: As a developer, I can embed and store documents via embed-and-store endpoint.

Per PRD §6 (Agent memory foundation):
- Accept documents (text) and automatically generate embeddings
- Store both the document text and embedding vector in ZeroDB
- Support optional metadata and namespace parameters
- Return confirmation with vector IDs and document count

DX Contract Guarantee:
- When model is omitted, BAAI/bge-small-en-v1.5 (384-dim) is used
- Namespace defaults to 'default' when omitted
- Returns deterministic vector IDs for stored documents
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    is_model_supported,
    get_supported_models
)


class EmbedAndStoreRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/embeddings/embed-and-store.

    Epic 4 Story 1 (Issue #16): Embed and store documents with metadata.

    Per PRD §6 (Agent memory foundation):
    - Accept documents (text) and automatically generate embeddings
    - Support optional metadata for document classification
    - Support optional namespace for logical separation

    DX Contract Guarantee:
    - When model is omitted, BAAI/bge-small-en-v1.5 (384-dim) is used
    - Namespace defaults to 'default' when omitted
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
        description="Logical namespace for organizing vectors. Defaults to 'default'"
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
        """Ensure namespace is valid."""
        if v is None:
            return "default"

        # Clean and validate namespace
        cleaned = v.strip()
        if not cleaned:
            return "default"

        # Namespace should only contain alphanumeric, underscore, and hyphen
        if not all(c.isalnum() or c in ('_', '-') for c in cleaned):
            raise ValueError("Namespace can only contain alphanumeric characters, underscores, and hyphens")

        return cleaned

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
                "namespace": "agent_memory"
            }
        }


class VectorStorageResult(BaseModel):
    """
    Result of storing a single vector.

    Contains the vector ID and document metadata.
    """
    vector_id: str = Field(..., description="Unique identifier for the stored vector")
    document: str = Field(..., description="Original document text")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Associated metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "vector_id": "vec_abc123xyz456",
                "document": "Autonomous fintech agent executing compliance check",
                "metadata": {"source": "agent_memory", "agent_id": "compliance_agent"}
            }
        }


class EmbedAndStoreResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/embeddings/embed-and-store.

    Epic 4 Story 1 (Issue #16): Return confirmation with vector IDs and count.
    Epic 4 Story 4 (Issue #19): Response includes vectors_stored, model, dimensions.

    Per PRD §6:
    - Return vector IDs for all stored documents
    - Include document count for verification (vectors_stored per Issue #19)
    - Include model and dimensions for transparency (Issue #19)
    - Include processing time for observability
    """
    vector_ids: List[str] = Field(
        ...,
        description="List of vector IDs for stored documents"
    )
    vectors_stored: int = Field(
        ...,
        description="Number of vectors successfully stored (Issue #19 - required field)",
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
    namespace: str = Field(
        ...,
        description="Namespace where vectors were stored"
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

    class Config:
        json_schema_extra = {
            "example": {
                "vector_ids": ["vec_abc123", "vec_xyz789"],
                "vectors_stored": 2,
                "model": "BAAI/bge-small-en-v1.5",
                "dimensions": 384,
                "namespace": "agent_memory",
                "results": [
                    {
                        "vector_id": "vec_abc123",
                        "document": "Autonomous fintech agent executing compliance check",
                        "metadata": {"source": "agent_memory", "agent_id": "compliance_agent"}
                    },
                    {
                        "vector_id": "vec_xyz789",
                        "document": "Transaction risk assessment completed",
                        "metadata": {"source": "agent_memory", "agent_id": "risk_agent"}
                    }
                ],
                "processing_time_ms": 125
            }
        }
