"""
Embeddings API schemas for request/response validation.
Implements Epic 3 (Embeddings: Generate) per backlog.md and PRD §6.
GitHub Issue #13: Multi-model support with dimension validation.

Per DX Contract (Issue #12 & #13):
- Default model: BAAI/bge-small-en-v1.5 (384 dimensions)
- Model parameter is optional - defaults when omitted
- Behavior must be deterministic and consistent
- Response must indicate which model was used
- Support multiple models with correct dimensions
- Include processing_time_ms for observability
- Return { detail, error_code } for errors
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    is_model_supported,
    get_model_dimensions,
    get_supported_models,
    EMBEDDING_MODEL_SPECS
)

# Export for backward compatibility with embedding_service.py
DEFAULT_EMBEDDING_DIMENSIONS = 384
SUPPORTED_MODELS = EMBEDDING_MODEL_SPECS


class EmbeddingGenerateRequest(BaseModel):
    """
    Request schema for POST /v1/public/embeddings/generate.

    Epic 3 Story 1: Generate embeddings via POST /embeddings/generate.
    Epic 3 Story 2 (Issue #12): Default to 384-dim embeddings when model is omitted.
    Epic 3 Story 3: Support multiple models with correct dimensions.

    DX Contract Guarantee:
    - When model is omitted, BAAI/bge-small-en-v1.5 (384-dim) is used
    - This default will not change without a version bump
    """
    text: str = Field(
        ...,
        min_length=1,
        description="Text to generate embeddings from (required, non-empty)"
    )
    model: Optional[str] = Field(
        default=None,
        description=f"Embedding model to use. Defaults to '{DEFAULT_EMBEDDING_MODEL}' (384 dimensions) when omitted"
    )

    @validator('text')
    def text_not_empty(cls, v):
        """Ensure text is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace")
        return v.strip()

    @validator('model')
    def validate_model(cls, v):
        """
        Validate that the specified model is supported.
        Issue #13: Validate model parameter against supported models list.
        Epic 3 Story 4: Unsupported models return MODEL_NOT_FOUND.
        """
        if v is None:
            # Use default model (DX Contract §3)
            return DEFAULT_EMBEDDING_MODEL

        if not is_model_supported(v):
            supported = ", ".join(get_supported_models().keys())
            raise ValueError(
                f"Model '{v}' is not supported. "
                f"Supported models: {supported}"
            )

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Autonomous fintech agent executing compliance check",
                "model": "BAAI/bge-small-en-v1.5"
            }
        }


class EmbeddingGenerateResponse(BaseModel):
    """
    Response schema for POST /v1/public/embeddings/generate.

    Epic 3 Story 3: Return embedding vector with metadata.
    Epic 3 Story 5 (Issue #12): Include processing_time_ms for demo observability.

    Technical Details (Issue #12):
    - Response MUST indicate which model was used (for determinism)
    - When model is omitted in request, response shows DEFAULT_EMBEDDING_MODEL
    """
    embedding: List[float] = Field(
        ...,
        description="Generated embedding vector"
    )
    model: str = Field(
        ...,
        description="Model used for generation (indicates actual model used, including default)"
    )
    dimensions: int = Field(
        ...,
        description="Dimensionality of the embedding vector"
    )
    text: str = Field(
        ...,
        description="Original input text (returned for verification)"
    )
    processing_time_ms: int = Field(
        ...,
        description="Processing time in milliseconds (integer)",
        ge=0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "embedding": [0.123, -0.456, 0.789, "..."],
                "model": "BAAI/bge-small-en-v1.5",
                "dimensions": 384,
                "text": "Autonomous fintech agent executing compliance check",
                "processing_time_ms": 46
            }
        }


class ModelInfo(BaseModel):
    """
    Information about a supported embedding model.

    Issue #12: Documents available models and their dimensions.
    """
    name: str = Field(..., description="Model identifier")
    dimensions: int = Field(..., description="Embedding dimensionality")
    description: str = Field(..., description="Model description")
    is_default: bool = Field(default=False, description="Whether this is the default model")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "BAAI/bge-small-en-v1.5",
                "dimensions": 384,
                "description": "Default embedding model - Fast and efficient (384 dimensions)",
                "is_default": True
            }
        }


class SupportedModelsResponse(BaseModel):
    """
    Response schema for listing supported embedding models.
    Issue #13: Return all supported models with their specifications.
    """
    models: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Dictionary of supported models and their specifications"
    )

    default_model: str = Field(
        ...,
        description="Default model used when none is specified",
        example=DEFAULT_EMBEDDING_MODEL
    )

    total_models: int = Field(
        ...,
        description="Total number of supported models"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "models": {
                    "BAAI/bge-small-en-v1.5": {
                        "dimensions": 384,
                        "description": "Lightweight English model (default)",
                        "languages": ["en"],
                        "max_seq_length": 512
                    },
                    "sentence-transformers/all-mpnet-base-v2": {
                        "dimensions": 768,
                        "description": "High-quality embeddings",
                        "languages": ["en"],
                        "max_seq_length": 384
                    }
                },
                "default_model": "BAAI/bge-small-en-v1.5",
                "total_models": 7
            }
        }


class EmbedAndStoreRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/embeddings/embed-and-store.

    Epic 4 Story 2 (Issue #17): Namespace scopes retrieval correctly.
    Epic 4 Story 3 (Issue #18): Implement upsert parameter for vector updates.

    DX Contract Guarantee (PRD §10):
    - When upsert=true: Update existing vector if ID exists (idempotent)
    - When upsert=false: Create new vector or error if ID exists
    - Prevents duplicate vectors with same ID when upsert=false
    - Namespace isolates vectors (Issue #17)
    """
    text: str = Field(
        ...,
        min_length=1,
        description="Text to generate embeddings from and store"
    )
    model: Optional[str] = Field(
        default=None,
        description=f"Embedding model to use. Defaults to '{DEFAULT_EMBEDDING_MODEL}' (384 dimensions)"
    )
    namespace: Optional[str] = Field(
        default=None,
        description=(
            "Namespace for vector isolation (Issue #17). "
            "Defaults to 'default'. Vectors in different namespaces are completely isolated. "
            "Use namespaces to separate agent memories, environments, or tenants."
        )
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata to store with the vector"
    )
    vector_id: Optional[str] = Field(
        default=None,
        description="Optional vector ID. If not provided, auto-generated. Required for upsert=true updates"
    )
    upsert: bool = Field(
        default=False,
        description=(
            "Upsert behavior (Issue #18): "
            "When true, updates existing vector if vector_id exists (idempotent). "
            "When false, creates new vector or errors if vector_id already exists"
        )
    )

    @validator('text')
    def text_not_empty(cls, v):
        """Ensure text is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace")
        return v.strip()

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

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Autonomous fintech agent executing compliance check",
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "agent_1_memory",
                "metadata": {
                    "source": "agent_memory",
                    "agent_id": "compliance_agent"
                },
                "vector_id": "vec_abc123",
                "upsert": True
            }
        }


class EmbedAndStoreResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/embeddings/embed-and-store.

    Epic 4 Story 2 (Issue #17): Return namespace for confirmation.
    Epic 4 Story 3 (Issue #18): Confirm vector storage with upsert status.
    Epic 4 Story 4 (Issue #19): Response includes vectors_stored, model, dimensions.

    Technical Details:
    - Issue #17: Returns namespace for isolation confirmation
    - Issue #18: Returns whether vector was created or updated
    - Issue #19: MUST include vectors_stored count, model, dimensions
    - Confirms idempotency for upsert operations
    - Provides vector_id for future reference
    - Per PRD §9: Demo proof requires observable metadata
    """
    vectors_stored: int = Field(
        ...,
        description="Number of vectors successfully stored (Issue #19 - required field)",
        ge=0
    )
    vector_id: str = Field(
        ...,
        description="Unique identifier for the stored vector"
    )
    namespace: str = Field(
        ...,
        description="Namespace where vector was stored (Issue #17 - confirms isolation)"
    )
    model: str = Field(
        ...,
        description="Model used for embedding generation (Issue #19 - required field)"
    )
    dimensions: int = Field(
        ...,
        description="Dimensionality of the embedding vector (Issue #19 - required field)"
    )
    text: str = Field(
        ...,
        description="Original input text"
    )
    created: bool = Field(
        ...,
        description="True if new vector was created, False if existing vector was updated"
    )
    processing_time_ms: int = Field(
        ...,
        description="Processing time in milliseconds (Issue #19 - included when available)",
        ge=0
    )
    stored_at: str = Field(
        ...,
        description="ISO timestamp when vector was stored"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vectors_stored": 1,
                "vector_id": "vec_abc123",
                "namespace": "agent_1_memory",
                "model": "BAAI/bge-small-en-v1.5",
                "dimensions": 384,
                "text": "Autonomous fintech agent executing compliance check",
                "created": False,
                "processing_time_ms": 52,
                "stored_at": "2026-01-10T12:34:56.789Z"
            }
        }


class EmbeddingSearchRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/embeddings/search.

    Epic 5 Story 1: Search via /embeddings/search.
    Epic 5 Story 3 (Issue #17): Scope search by namespace.

    DX Contract Guarantee (PRD §10):
    - Namespace isolation is strictly enforced
    - Default namespace is used when namespace parameter is omitted
    - Vectors in other namespaces are never returned
    """
    query: str = Field(
        ...,
        min_length=1,
        description="Query text to search for similar vectors"
    )
    model: Optional[str] = Field(
        default=None,
        description=f"Embedding model to use. Defaults to '{DEFAULT_EMBEDDING_MODEL}' (384 dimensions). Must match stored vectors model"
    )
    namespace: Optional[str] = Field(
        default=None,
        description=(
            "Namespace to search within (Issue #17). "
            "Defaults to 'default'. Only searches vectors in this namespace. "
            "Vectors from other namespaces are never returned."
        )
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description=(
            "Maximum number of results to return (1-100). "
            "Issue #22: Limits the search results to the top K most similar vectors. "
            "Results are ordered by similarity score (descending). "
            "If fewer vectors exist than top_k, all available vectors are returned."
        )
    )
    similarity_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0.0-1.0). Only return results above this threshold"
    )
    metadata_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional metadata filters to apply to search results (Issue #24). "
            "Supports: equals, $in, $contains, $gt, $gte, $lt, $lte, $exists, $not_equals. "
            "Applied AFTER similarity search to refine results."
        )
    )
    include_metadata: bool = Field(
        default=True,
        description=(
            "Whether to include metadata in response (Issue #26). "
            "Default: true. Set to false to reduce response size when metadata is not needed."
        )
    )
    include_embeddings: bool = Field(
        default=False,
        description=(
            "Whether to include embedding vectors in response (Issue #26). "
            "Default: false. Set to true when embeddings are needed for further processing. "
            "WARNING: Including embeddings significantly increases response size."
        )
    )

    @validator('query')
    def query_not_empty(cls, v):
        """Ensure query is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace")
        return v.strip()

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

    @validator('namespace')
    def validate_namespace(cls, v):
        """
        Validate namespace format (Issue #23).

        Same validation rules as storage:
        - Alphanumeric characters, hyphens, underscores, and dots only
        - Max 128 characters
        - No path traversal attempts
        """
        if v is None:
            return None  # Will default to "default" in service layer

        # Check for invalid characters
        if not all(c.isalnum() or c in ['-', '_', '.'] for c in v):
            raise ValueError(
                "Namespace can only contain alphanumeric characters, hyphens, underscores, and dots"
            )

        # Check length
        if len(v) > 128:
            raise ValueError("Namespace cannot exceed 128 characters")

        # Check not empty after stripping
        if not v.strip():
            raise ValueError("Namespace cannot be empty or whitespace")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "compliance check results",
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "agent_1_memory",
                "top_k": 5,
                "similarity_threshold": 0.7,
                "metadata_filter": {
                    "agent_id": "compliance_agent",
                    "score": {"$gte": 0.8},
                    "status": {"$in": ["active", "completed"]}
                },
                "include_metadata": True,
                "include_embeddings": False
            }
        }


class SearchResult(BaseModel):
    """
    Individual search result with similarity score.

    Issue #26 - Conditional field inclusion:
    - metadata: Optional, only included if include_metadata=true
    - embedding: Optional, only included if include_embeddings=true
    """
    vector_id: str = Field(..., description="Unique identifier of the matched vector")
    namespace: str = Field(..., description="Namespace where vector was found (Issue #17)")
    text: str = Field(..., description="Original text of the matched vector")
    similarity: float = Field(..., description="Similarity score (0.0-1.0)", ge=0.0, le=1.0)
    model: str = Field(..., description="Model used to generate this vector")
    dimensions: int = Field(..., description="Dimensionality of the vector")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Vector metadata (only if include_metadata=true in request, Issue #26)"
    )
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Embedding vector (only if include_embeddings=true in request, Issue #26)"
    )
    created_at: str = Field(..., description="ISO timestamp when vector was created")


class EmbeddingSearchResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/embeddings/search.

    Epic 5 Story 1-6: Search memory with filters and thresholds.
    Issue #17: Confirms namespace isolation in results.
    """
    results: List[SearchResult] = Field(
        ...,
        description="List of similar vectors, sorted by similarity (descending)"
    )
    query: str = Field(
        ...,
        description="Original search query"
    )
    namespace: str = Field(
        ...,
        description="Namespace that was searched (Issue #17 - confirms scope)"
    )
    model: str = Field(
        ...,
        description="Model used for query embedding"
    )
    total_results: int = Field(
        ...,
        description="Number of results returned",
        ge=0
    )
    processing_time_ms: int = Field(
        ...,
        description="Processing time in milliseconds",
        ge=0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "vector_id": "vec_abc123",
                        "namespace": "agent_1_memory",
                        "text": "Agent compliance check passed",
                        "similarity": 0.92,
                        "model": "BAAI/bge-small-en-v1.5",
                        "dimensions": 384,
                        "metadata": {
                            "agent_id": "compliance_agent",
                            "task": "compliance_check"
                        },
                        "created_at": "2026-01-10T12:30:00.000Z"
                    }
                ],
                "query": "compliance check results",
                "namespace": "agent_1_memory",
                "model": "BAAI/bge-small-en-v1.5",
                "total_results": 1,
                "processing_time_ms": 15
            }
        }
