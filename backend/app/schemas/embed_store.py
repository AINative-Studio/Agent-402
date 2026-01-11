"""
Embed-and-store API schemas for Epic 4, Issue #16.

As a developer, I can embed and store documents via embed-and-store endpoint.

Per PRD Section 6 (Agent memory foundation):
- Accept texts (array of strings) and automatically generate embeddings
- Store both the text and embedding vector in ZeroDB
- Support optional model, namespace, metadata, and upsert parameters
- Return confirmation with vectors_stored count, model, dimensions, and vector_ids

DX Contract Guarantee:
- When model is omitted, BAAI/bge-small-en-v1.5 (384-dim) is used
- Namespace defaults to 'default' when omitted
- Returns deterministic vector IDs for stored texts
- Error responses follow { detail, error_code } format
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    is_model_supported,
    get_supported_models
)


class EmbedStoreRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/embeddings/embed-and-store.

    Epic 4 Story 1 (Issue #16): Embed and store documents via embed-and-store.

    Per PRD Section 6 (Agent memory foundation):
    - Accept texts (array of strings) and automatically generate embeddings
    - Store each embedding as a vector with the original text as document
    - Support optional metadata for document classification
    - Support optional namespace for logical separation
    - Support optional upsert for update vs create behavior

    DX Contract Guarantee:
    - When model is omitted, BAAI/bge-small-en-v1.5 (384-dim) is used
    - Namespace defaults to 'default' when omitted
    - Upsert defaults to false for safe create-only behavior
    """
    texts: List[str] = Field(
        ...,
        min_items=1,
        description="Array of text strings to embed and store (required, non-empty)"
    )
    model: Optional[str] = Field(
        default=None,
        description=(
            f"Embedding model to use. Defaults to '{DEFAULT_EMBEDDING_MODEL}' (384 dimensions) "
            f"when omitted. Supported models: BAAI/bge-small-en-v1.5, BAAI/bge-base-en-v1.5, "
            f"BAAI/bge-large-en-v1.5"
        )
    )
    namespace: Optional[str] = Field(
        default=None,
        description=(
            "Logical namespace for organizing vectors. Defaults to 'default'. "
            "Vectors in different namespaces are completely isolated."
        )
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional metadata to attach to all vectors. Common fields: agent_id, task_id, "
            "source, timestamp, tags. Metadata is queryable and filterable in search operations."
        )
    )
    upsert: Optional[bool] = Field(
        default=False,
        description=(
            "Upsert behavior: When true, updates existing vectors if IDs match. "
            "When false (default), creates new vectors with auto-generated IDs. "
            "For idempotent operations, set upsert=true."
        )
    )

    @validator('texts')
    def texts_not_empty(cls, v):
        """Ensure all texts are not just whitespace."""
        if not v:
            raise ValueError("Texts array cannot be empty")

        cleaned_texts = []
        for idx, text in enumerate(v):
            if not text or not text.strip():
                raise ValueError(f"Text at index {idx} cannot be empty or whitespace")
            cleaned_texts.append(text.strip())

        return cleaned_texts

    @validator('model')
    def validate_model(cls, v):
        """
        Validate that the specified model is supported.

        Per Issue #16: Default model is BAAI/bge-small-en-v1.5 (384 dims).
        """
        if v is None:
            return DEFAULT_EMBEDDING_MODEL

        if not is_model_supported(v):
            supported = ", ".join(get_supported_models().keys())
            raise ValueError(
                f"Model '{v}' is not supported. "
                f"Supported models: {supported}"
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

        # Namespace should only contain alphanumeric, underscore, hyphen, and dot
        if not all(c.isalnum() or c in ('_', '-', '.') for c in cleaned):
            raise ValueError(
                "Namespace can only contain alphanumeric characters, "
                "underscores, hyphens, and dots"
            )

        # Limit namespace length
        if len(cleaned) > 128:
            raise ValueError("Namespace cannot exceed 128 characters")

        return cleaned

    class Config:
        json_schema_extra = {
            "example": {
                "texts": [
                    "Autonomous fintech agent executing compliance check",
                    "Transaction risk assessment completed successfully"
                ],
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "agent_memory",
                "metadata": {
                    "agent_id": "compliance_agent",
                    "source": "agent_memory",
                    "task_type": "compliance_check"
                },
                "upsert": False
            }
        }


class EmbedStoreResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/embeddings/embed-and-store.

    Epic 4 Story 1 (Issue #16): Return confirmation with vector IDs and count.

    Per Issue #16 Requirements:
    - vectors_stored: Number of vectors successfully stored (count)
    - model: Model used for embedding generation
    - dimensions: Dimensionality of the embedding vectors
    - vector_ids: Array of vector IDs for all stored texts

    Per PRD Section 6:
    - Return vector IDs for all stored documents
    - Include count for verification
    - Include model and dimensions for transparency
    """
    vectors_stored: int = Field(
        ...,
        description="Number of vectors successfully stored",
        ge=0
    )
    model: str = Field(
        ...,
        description="Model used for embedding generation"
    )
    dimensions: int = Field(
        ...,
        description="Dimensionality of the embedding vectors"
    )
    vector_ids: List[str] = Field(
        ...,
        description="Array of vector IDs for all stored texts"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vectors_stored": 2,
                "model": "BAAI/bge-small-en-v1.5",
                "dimensions": 384,
                "vector_ids": ["vec_abc123def456", "vec_xyz789ghi012"]
            }
        }
