"""
Vector operations API schemas with strict dimension validation.
Implements Epic 6 (Vector Operations API), Issue #28 and Issue #31.

This module enforces strict dimension length validation before vector storage.
Only supported dimensions are allowed: 384, 768, 1024, 1536.

Per DX Contract (PRD §10 - Determinism):
- Dimension validation is STRICT and enforced at request schema level
- Array length MUST match declared dimensions exactly
- Clear error messages for dimension mismatches
- Project-level dimension configuration supported
- All validations are deterministic and consistent

GitHub Issue #28 Requirements:
- Validate vector_embedding array length matches expected dimensions
- Enforce strict validation before storage
- Only allow supported dimensions: 384, 768, 1024, 1536
- Return clear error if length mismatch
- Support project-level dimension configuration

GitHub Issue #31 Requirements (NEW):
- Support metadata field (optional JSON object) for vector annotation
- Support namespace field for multi-tenancy and logical isolation
- Metadata is queryable and filterable in search operations
- Namespace enables agent isolation and environment separation
- Follow PRD §6 for auditability and compliance tracking
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from app.core.errors import APIError


# Supported vector dimensions per Issue #28
SUPPORTED_DIMENSIONS = {384, 768, 1024, 1536}

# Default dimension (matches default embedding model)
DEFAULT_DIMENSION = 384


class VectorUpsertRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/database/vectors/upsert.

    Epic 6 Story 1: Upsert vectors via /database/vectors/upsert.
    Epic 6 Story 2 (Issue #28): Dimension length is enforced strictly.
    Epic 6 Story 5 (Issue #31): Vector upsert supports metadata and namespace.

    DX Contract Guarantee (PRD §10):
    - vector_embedding array length MUST match dimensions parameter exactly
    - Only supported dimensions are allowed: 384, 768, 1024, 1536
    - Validation occurs at schema level before any storage operations
    - Clear error messages for dimension mismatches

    GitHub Issue #28 Implementation:
    - Strict dimension validation before storage
    - Array length verification
    - Support for project-level dimension configuration
    - Deterministic validation behavior

    GitHub Issue #31 Implementation (NEW):
    - Metadata field enables auditability and compliance tracking
    - Namespace field provides multi-tenancy and logical isolation
    - Metadata is queryable in search operations
    - Namespace isolates vectors across agents/environments/tenants
    - Supports agent-native workflows per PRD §6

    Metadata Best Practices (Issue #31):
    - Use for agent_id, task_id, source, timestamp, tags, etc.
    - Enable filtering by metadata in search operations
    - Support compliance and audit trail requirements
    - Store structured data for decision provenance

    Namespace Best Practices (Issue #31):
    - Use for agent isolation (e.g., "agent_1", "agent_2")
    - Separate environments (e.g., "dev", "staging", "prod")
    - Multi-tenant applications (e.g., "tenant_abc", "tenant_xyz")
    - Different data categories (e.g., "memory", "documents", "events")
    """
    vector_embedding: List[float] = Field(
        ...,
        description=(
            "Vector embedding array. Length must match dimensions parameter exactly. "
            "Supported dimensions: 384, 768, 1024, 1536"
        )
    )
    dimensions: int = Field(
        ...,
        description=(
            "Expected dimensionality of the vector. "
            "Supported values: 384, 768, 1024, 1536. "
            "Must match vector_embedding array length exactly."
        )
    )
    document: str = Field(
        ...,
        min_length=1,
        description="Source document or text associated with this vector"
    )
    namespace: Optional[str] = Field(
        default="default",
        description=(
            "Namespace for vector scoping and isolation (Issue #31). "
            "Defaults to 'default'. Enables multi-tenancy and logical separation. "
            "Vectors in different namespaces are completely isolated. "
            "Use for: agent isolation, environment separation, tenant separation, data categorization. "
            "Namespace is queryable and enforced in search operations."
        )
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Additional metadata for the vector (Issue #31). "
            "Optional JSON object for annotation, filtering, and auditability. "
            "Common fields: agent_id, task_id, source, timestamp, category, tags, risk_score, etc. "
            "Metadata is queryable and filterable in search operations. "
            "Supports compliance tracking and decision provenance per PRD §6. "
            "Example: {'agent_id': 'did:ethr:0xabc', 'task': 'compliance', 'passed': true}"
        )
    )
    vector_id: Optional[str] = Field(
        default=None,
        description="Optional vector ID. If provided, updates existing vector (upsert)"
    )

    @validator('dimensions')
    def validate_dimensions_supported(cls, v):
        """
        Validate that dimensions value is in supported set.

        Issue #28: Only allow supported dimensions: 384, 768, 1024, 1536.
        Epic 6 Story 3: Mismatches return DIMENSION_MISMATCH error.

        Args:
            v: Dimensions value to validate

        Returns:
            Validated dimensions value

        Raises:
            ValueError: If dimensions not in SUPPORTED_DIMENSIONS
        """
        if v not in SUPPORTED_DIMENSIONS:
            supported_str = ", ".join(str(d) for d in sorted(SUPPORTED_DIMENSIONS))
            raise ValueError(
                f"Dimension {v} is not supported. "
                f"Supported dimensions: {supported_str}"
            )
        return v

    @validator('vector_embedding')
    def validate_vector_not_empty(cls, v):
        """
        Ensure vector_embedding is not empty.

        Args:
            v: Vector embedding array

        Returns:
            Validated vector embedding

        Raises:
            ValueError: If vector is empty
        """
        if not v or len(v) == 0:
            raise ValueError("vector_embedding cannot be empty")
        return v

    @validator('vector_embedding', always=True)
    def validate_dimension_length_match(cls, v, values):
        """
        Strict validation that vector_embedding length matches dimensions.

        Issue #28 Core Requirement:
        - Validate vector_embedding array length matches expected dimensions
        - Enforce strict validation before storage
        - Return clear error if length mismatch

        This validator ensures deterministic behavior per PRD §10.

        Args:
            v: Vector embedding array
            values: Dictionary of previously validated fields

        Returns:
            Validated vector embedding

        Raises:
            ValueError: If vector length does not match dimensions exactly
        """
        if 'dimensions' not in values:
            # dimensions field failed validation, will be caught separately
            return v

        declared_dims = values['dimensions']
        actual_length = len(v)

        if actual_length != declared_dims:
            raise ValueError(
                f"Vector dimension mismatch: "
                f"declared dimensions={declared_dims}, "
                f"but vector_embedding has {actual_length} elements. "
                f"Array length must match dimensions parameter exactly."
            )

        return v

    @validator('document')
    def document_not_empty(cls, v):
        """Ensure document is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("document cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "vector_embedding": [0.123, -0.456, 0.789] + [0.0] * 381,  # 384 elements
                "dimensions": 384,
                "document": "Compliance check for agent transaction",
                "namespace": "agent_memory",
                "metadata": {
                    "agent_id": "compliance_agent",
                    "task_type": "compliance_check",
                    "timestamp": "2026-01-10T12:00:00Z"
                },
                "vector_id": "vec_abc123"
            }
        }


class VectorUpsertResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/database/vectors/upsert.

    Epic 6 Story 5 (Issue #31): Vector upsert supports metadata and namespace.

    Returns confirmation of vector storage with dimension validation.
    Includes metadata and namespace for auditability per PRD §6.
    """
    vector_id: str = Field(
        ...,
        description="Unique identifier for the stored vector"
    )
    dimensions: int = Field(
        ...,
        description="Confirmed dimensionality of the stored vector"
    )
    namespace: str = Field(
        ...,
        description="Namespace where vector was stored (Issue #31 - confirms isolation)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata stored with the vector (Issue #31 - confirms auditability)"
    )
    created: bool = Field(
        ...,
        description="True if new vector was created, False if existing vector was updated"
    )
    processing_time_ms: int = Field(
        ...,
        description="Processing time in milliseconds",
        ge=0
    )
    stored_at: str = Field(
        ...,
        description="ISO timestamp when vector was stored"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vector_id": "vec_abc123",
                "dimensions": 384,
                "namespace": "compliance_agent_memory",
                "metadata": {
                    "agent_id": "did:ethr:0xabc123",
                    "task_id": "task_compliance_001",
                    "source": "compliance_engine",
                    "passed": True,
                    "risk_score": 0.15
                },
                "created": False,
                "processing_time_ms": 8,
                "stored_at": "2026-01-10T12:34:56.789Z"
            }
        }


class VectorSearchRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/database/vectors/search.

    Direct vector search with strict dimension validation.

    Issue #26 - Toggle metadata and embeddings in results:
    - include_metadata: Control whether metadata is included in results (default: true)
    - include_embeddings: Control whether embeddings are included in results (default: false)
    - Optimizes response size based on use case
    """
    query_vector: List[float] = Field(
        ...,
        description=(
            "Query vector for similarity search. "
            "Length must match dimensions parameter exactly."
        )
    )
    dimensions: int = Field(
        ...,
        description="Dimensionality of the query vector (384, 768, 1024, or 1536)"
    )
    namespace: Optional[str] = Field(
        default="default",
        description="Namespace to search within"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return (1-100)"
    )
    similarity_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0.0-1.0)"
    )
    metadata_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filters"
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

    @validator('dimensions')
    def validate_dimensions_supported(cls, v):
        """Validate dimensions is in supported set."""
        if v not in SUPPORTED_DIMENSIONS:
            supported_str = ", ".join(str(d) for d in sorted(SUPPORTED_DIMENSIONS))
            raise ValueError(
                f"Dimension {v} is not supported. "
                f"Supported dimensions: {supported_str}"
            )
        return v

    @validator('query_vector', always=True)
    def validate_dimension_length_match(cls, v, values):
        """Strict validation that query_vector length matches dimensions."""
        if 'dimensions' not in values:
            return v

        declared_dims = values['dimensions']
        actual_length = len(v)

        if actual_length != declared_dims:
            raise ValueError(
                f"Query vector dimension mismatch: "
                f"declared dimensions={declared_dims}, "
                f"but query_vector has {actual_length} elements. "
                f"Array length must match dimensions parameter exactly."
            )

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query_vector": [0.123, -0.456, 0.789] + [0.0] * 381,
                "dimensions": 384,
                "namespace": "agent_memory",
                "top_k": 5,
                "similarity_threshold": 0.7,
                "metadata_filter": {
                    "agent_id": "compliance_agent"
                },
                "include_metadata": True,
                "include_embeddings": False
            }
        }


class VectorResult(BaseModel):
    """
    Individual vector search result.

    Issue #26 - Conditional field inclusion:
    - metadata: Optional, only included if include_metadata=true
    - embedding: Optional, only included if include_embeddings=true
    """
    vector_id: str = Field(..., description="Unique identifier of the matched vector")
    namespace: str = Field(..., description="Namespace where vector was found")
    document: str = Field(..., description="Original document/text of the vector")
    similarity: float = Field(..., description="Similarity score (0.0-1.0)", ge=0.0, le=1.0)
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


class VectorSearchResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/database/vectors/search.
    """
    results: List[VectorResult] = Field(
        ...,
        description="List of similar vectors, sorted by similarity (descending)"
    )
    namespace: str = Field(
        ...,
        description="Namespace that was searched"
    )
    dimensions: int = Field(
        ...,
        description="Dimensionality used for search"
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
                        "namespace": "agent_memory",
                        "document": "Agent compliance check passed",
                        "similarity": 0.92,
                        "dimensions": 384,
                        "metadata": {
                            "agent_id": "compliance_agent",
                            "task_type": "compliance_check"
                        },
                        "created_at": "2026-01-10T12:30:00.000Z"
                    }
                ],
                "namespace": "agent_memory",
                "dimensions": 384,
                "total_results": 1,
                "processing_time_ms": 15
            }
        }


class DimensionValidationError(BaseModel):
    """
    Error response for dimension validation failures.

    Epic 6 Story 3: Mismatches return DIMENSION_MISMATCH error.
    """
    detail: str = Field(
        ...,
        description="Human-readable error message explaining the dimension mismatch"
    )
    error_code: str = Field(
        default="DIMENSION_MISMATCH",
        description="Machine-readable error code"
    )
    declared_dimensions: int = Field(
        ...,
        description="Dimensions parameter value from request"
    )
    actual_length: int = Field(
        ...,
        description="Actual length of vector_embedding array"
    )
    supported_dimensions: List[int] = Field(
        default_factory=lambda: sorted(SUPPORTED_DIMENSIONS),
        description="List of supported dimension values"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Vector dimension mismatch: declared dimensions=384, but vector_embedding has 512 elements. Array length must match dimensions parameter exactly.",
                "error_code": "DIMENSION_MISMATCH",
                "declared_dimensions": 384,
                "actual_length": 512,
                "supported_dimensions": [384, 768, 1024, 1536]
            }
        }
