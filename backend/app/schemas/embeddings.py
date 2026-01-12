"""
Embeddings API schemas for request/response validation.
Implements Epic 3 (Embeddings: Generate) per backlog.md and PRD Section 6.
GitHub Issue #13: Multi-model support with dimension validation.
GitHub Issue #17: Namespace scopes retrieval correctly.

Per DX Contract (Issue #12 & #13):
- Default model: BAAI/bge-small-en-v1.5 (384 dimensions)
- Model parameter is optional - defaults when omitted
- Behavior must be deterministic and consistent
- Response must indicate which model was used
- Support multiple models with correct dimensions
- Include processing_time_ms for observability
- Return { detail, error_code } for errors

Issue #17 Namespace Rules:
- Valid characters: a-z, A-Z, 0-9, underscore, hyphen
- Max length: 64 characters
- Cannot start with underscore or hyphen
- Cannot be empty if provided
- INVALID_NAMESPACE (422) for invalid format
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
from app.core.namespace_validator import (
    validate_namespace as _validate_namespace_func,
    NamespaceValidationError,
    DEFAULT_NAMESPACE
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
            # Use default model (DX Contract Section 3)
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

    DX Contract Guarantee (PRD Section 10):
    - When upsert=true: Update existing vector if ID exists (idempotent)
    - When upsert=false: Create new vector or error if ID exists
    - Prevents duplicate vectors with same ID when upsert=false
    - Namespace isolates vectors (Issue #17)

    Issue #17 Namespace Rules:
    - Valid characters: a-z, A-Z, 0-9, underscore, hyphen
    - Max length: 64 characters
    - Cannot start with underscore or hyphen
    - Cannot be empty if provided
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
            "Use namespaces to separate agent memories, environments, or tenants. "
            "Valid: alphanumeric, underscore, hyphen. Max 64 chars. Cannot start with _ or -."
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
    - Per PRD Section 9: Demo proof requires observable metadata
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
    Epic 5 Story 2 (Issue #22): Limit results via top_k parameter.
    Epic 5 Story 3 (Issue #23): Scope search by namespace.

    DX Contract Guarantee (PRD Section 10):
    - Namespace isolation is strictly enforced
    - Default namespace ("default") is used when namespace parameter is omitted
    - Vectors in other namespaces are never returned
    - If namespace doesn't exist, returns empty results (not an error)
    - top_k limits results for predictable replay (1-100, default: 10)

    Issue #22 top_k Requirements:
    - Default value: 10 if not specified
    - Minimum value: 1
    - Maximum value: 100
    - Returns 422 VALIDATION_ERROR if out of range
    - Results sorted by similarity score (highest first)
    - If fewer matches exist than top_k, all matches are returned

    Issue #23 Namespace Rules (per centralized validator from Epic 4):
    - Valid characters: a-z, A-Z, 0-9, underscore, hyphen
    - Max length: 64 characters
    - Cannot start with underscore or hyphen
    - Cannot be empty if provided
    - INVALID_NAMESPACE (422) for invalid format
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
            "Namespace to search within (Issue #23). "
            "Defaults to 'default'. Only searches vectors in this namespace. "
            "Vectors from other namespaces are never returned. "
            "If namespace doesn't exist, returns empty results (not an error). "
            "Valid: alphanumeric, underscore, hyphen. Max 64 chars. Cannot start with _ or -."
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
            "Optional metadata filters using MongoDB-style operators (Issue #24). "
            "Filters are applied AFTER similarity search to refine results. "
            "Supported operators: $eq (equals, default), $ne (not equals), "
            "$gt, $gte, $lt, $lte (numeric comparisons), "
            "$in (value in array), $nin (value not in array), "
            "$exists (field exists/doesn't exist), $contains (string contains). "
            "Simple equality: {'agent_id': 'agent_1'}. "
            "With operators: {'score': {'$gte': 0.8}, 'status': {'$in': ['active', 'pending']}}. "
            "Invalid filters return 422 INVALID_METADATA_FILTER."
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

    @validator('namespace', always=True)
    def validate_namespace(cls, v):
        """
        Validate namespace format per Issue #23.

        Uses centralized namespace validator from Epic 4 (namespace_validator.py)
        to ensure consistent validation across all API endpoints.

        Note: always=True ensures this validator runs even when namespace is None,
        allowing the centralized validator to apply the default "default" namespace.

        Rules (per Issue #17/23):
        - Valid characters: a-z, A-Z, 0-9, underscore, hyphen
        - Max length: 64 characters
        - Cannot start with underscore or hyphen
        - Cannot be empty if provided
        - Defaults to 'default' when None

        Returns:
            Validated namespace (or DEFAULT_NAMESPACE if None)

        Raises:
            ValueError: If namespace format is invalid (triggers INVALID_NAMESPACE error)
        """
        try:
            return _validate_namespace_func(v)
        except NamespaceValidationError as e:
            raise ValueError(e.message)

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

    Issue #21 - Search endpoint response fields:
    - id: Unique identifier of the matched vector
    - score: Similarity score (0.0-1.0)
    - document: Original text of the matched vector
    - metadata: Optional, only included if include_metadata=true (Issue #26)
    - embedding: Optional, only included if include_embeddings=true (Issue #26)
    """
    id: str = Field(..., description="Unique identifier of the matched vector")
    score: float = Field(..., description="Similarity score (0.0-1.0)", ge=0.0, le=1.0)
    document: str = Field(..., description="Original text of the matched vector")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Vector metadata (only if include_metadata=true in request, Issue #26)"
    )
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Embedding vector (only if include_embeddings=true in request, Issue #26)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "vec_abc123",
                "score": 0.92,
                "document": "Agent compliance check passed",
                "metadata": {
                    "agent_id": "compliance_agent",
                    "task": "compliance_check"
                }
            }
        }


class EmbeddingSearchResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/embeddings/search.

    Issue #21 - Search endpoint response:
    - results: Array of search results with id, score, document, metadata, embedding
    - model: Model used for query embedding
    - namespace: Namespace searched
    - processing_time_ms: Time taken in milliseconds

    Issue #22 - top_k result limiting:
    - Results are limited to top_k most similar vectors
    - Sorted by similarity score (highest first)
    - If fewer matches exist than top_k, all matches are returned

    Epic 5 Story 1-6: Search memory with filters and thresholds.
    Issue #17: Confirms namespace isolation in results.
    """
    results: List[SearchResult] = Field(
        ...,
        description="List of similar vectors, sorted by similarity score (descending)"
    )
    model: str = Field(
        ...,
        description="Model used for query embedding"
    )
    namespace: str = Field(
        ...,
        description="Namespace that was searched (Issue #17 - confirms scope)"
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
                        "id": "vec_abc123",
                        "score": 0.92,
                        "document": "Agent compliance check passed",
                        "metadata": {
                            "agent_id": "compliance_agent",
                            "task": "compliance_check"
                        }
                    }
                ],
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "agent_1_memory",
                "processing_time_ms": 15
            }
        }


class EmbeddingCompareRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/embeddings/compare.

    Compare Embeddings Endpoint:
    - Generates embeddings for two texts
    - Calculates cosine similarity between them
    - Returns both embeddings and similarity score
    - Useful for semantic comparison and similarity analysis
    """
    text1: str = Field(
        ...,
        min_length=1,
        description="First text to compare"
    )
    text2: str = Field(
        ...,
        min_length=1,
        description="Second text to compare"
    )
    model: Optional[str] = Field(
        default=None,
        description=f"Embedding model to use. Defaults to '{DEFAULT_EMBEDDING_MODEL}' (384 dimensions)"
    )

    @validator('text1')
    def text1_not_empty(cls, v):
        """Ensure text1 is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("text1 cannot be empty or whitespace")
        return v.strip()

    @validator('text2')
    def text2_not_empty(cls, v):
        """Ensure text2 is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("text2 cannot be empty or whitespace")
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
                "text1": "Autonomous agent executing compliance check",
                "text2": "AI system performing regulatory verification",
                "model": "BAAI/bge-small-en-v1.5"
            }
        }


class EmbeddingCompareResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/embeddings/compare.

    Compare Embeddings Response:
    - Returns both embeddings for transparency
    - Calculates and returns cosine similarity (0.0-1.0)
    - Includes model and dimension information
    - Provides processing time for observability
    """
    text1: str = Field(
        ...,
        description="First input text"
    )
    text2: str = Field(
        ...,
        description="Second input text"
    )
    embedding1: List[float] = Field(
        ...,
        description="Embedding vector for text1"
    )
    embedding2: List[float] = Field(
        ...,
        description="Embedding vector for text2"
    )
    cosine_similarity: float = Field(
        ...,
        description="Cosine similarity score between embeddings (0.0-1.0, where 1.0 is identical)",
        ge=0.0,
        le=1.0
    )
    model: str = Field(
        ...,
        description="Model used for embedding generation"
    )
    dimensions: int = Field(
        ...,
        description="Dimensionality of the embedding vectors"
    )
    processing_time_ms: int = Field(
        ...,
        description="Processing time in milliseconds",
        ge=0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text1": "Autonomous agent executing compliance check",
                "text2": "AI system performing regulatory verification",
                "embedding1": [0.123, -0.456, 0.789, "..."],
                "embedding2": [0.115, -0.445, 0.798, "..."],
                "cosine_similarity": 0.87,
                "model": "BAAI/bge-small-en-v1.5",
                "dimensions": 384,
                "processing_time_ms": 92
            }
        }
