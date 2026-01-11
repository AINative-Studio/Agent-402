"""
Vector API schemas for request/response validation.
Implements Epic 6 (Vector Operations API) per backlog.md and PRD §6.
GitHub Issue #27: Direct vector upsert operations.
GitHub Issue #28: Strict dimension length enforcement.

Per DX Contract §4 (Endpoint Prefixing):
- All vector operations require /database/ prefix
- Missing /database/ returns 404 Not Found

Per Epic 6 Story 1 (Issue #27):
- Upsert vectors via /database/vectors/upsert
- Support vector_id, vector_embedding, document, metadata
- Insert if new, update if exists (idempotent)
- Require X-API-Key authentication

Per Epic 6 Story 2 (Issue #28 - Strict Dimension Validation):
- Validate vector_embedding array length matches expected dimensions
- Enforce strict validation before storage
- Only allow supported dimensions: 384, 768, 1024, 1536
- Return clear error if length mismatch
- Support project-level dimension configuration
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


# Supported vector dimensions per DX Contract §3 and Issue #28
SUPPORTED_DIMENSIONS = [384, 768, 1024, 1536]
DEFAULT_DIMENSION = 384


class VectorUpsertRequest(BaseModel):
    """
    Request schema for POST /database/vectors/upsert.

    Epic 6 Story 1 (Issue #27): Upsert vectors via /database/vectors/upsert.
    Epic 6 Story 2: Dimension length is enforced strictly.
    Epic 6 Story 5: Vector upsert supports metadata and namespace.

    DX Contract Guarantee:
    - Upsert behavior: insert if new, update if exists
    - Idempotent operation - same request produces same result
    - Dimension validation enforced (384, 768, 1024, 1536)
    - Namespace isolation supported
    """
    vector_id: Optional[str] = Field(
        default=None,
        description="Optional vector ID. If not provided, auto-generated. If provided and exists, vector is updated"
    )
    vector_embedding: List[float] = Field(
        ...,
        description="Vector embedding array (must be 384, 768, 1024, or 1536 dimensions)"
    )
    document: str = Field(
        ...,
        min_length=1,
        description="Source document text associated with this vector (required, non-empty)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata to store with the vector for filtering and classification"
    )
    namespace: Optional[str] = Field(
        default=None,
        description="Namespace for vector isolation. Defaults to 'default'. Vectors in different namespaces are isolated"
    )

    @validator('document')
    def document_not_empty(cls, v):
        """Ensure document is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Document cannot be empty or whitespace")
        return v.strip()

    @validator('vector_embedding')
    def validate_dimensions(cls, v):
        """
        Strict dimension validation for vector embeddings.

        Issue #28 Core Requirements:
        - Validate vector_embedding array length matches expected dimensions
        - Enforce strict validation before storage
        - Only allow supported dimensions: 384, 768, 1024, 1536
        - Return clear error if length mismatch

        Epic 6 Story 2: Dimension length is enforced strictly.
        Epic 6 Story 3: Mismatches return DIMENSION_MISMATCH.

        Per PRD §10 (Determinism):
        - Same input always produces same validation result
        - Validation is deterministic and consistent
        """
        if not v:
            raise ValueError("Vector embedding cannot be empty")

        dimensions = len(v)

        # Issue #28: Only supported dimensions allowed
        if dimensions not in SUPPORTED_DIMENSIONS:
            supported_str = ", ".join(map(str, sorted(SUPPORTED_DIMENSIONS)))
            raise ValueError(
                f"Dimension {dimensions} is not supported. "
                f"Supported dimensions: {supported_str}. "
                f"Vector embedding has {dimensions} elements which does not match any supported dimension size."
            )

        # Validate all values are numeric (floats or ints)
        for i, val in enumerate(v):
            if not isinstance(val, (int, float)):
                raise ValueError(
                    f"Vector embedding must contain only numeric values. "
                    f"Found {type(val).__name__} at index {i}"
                )

        return v

    @validator('vector_id')
    def validate_vector_id(cls, v):
        """Validate vector ID format if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Vector ID cannot be empty or whitespace")
            if len(v) < 3:
                raise ValueError("Vector ID must be at least 3 characters")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "vector_id": "vec_compliance_check_001",
                "vector_embedding": [0.123, -0.456, 0.789],  # Truncated for example - actual would be 384/768/1024/1536 dims
                "document": "Autonomous fintech agent executing compliance check",
                "metadata": {
                    "source": "agent_memory",
                    "agent_id": "compliance_agent",
                    "task_type": "compliance_verification"
                },
                "namespace": "agent_1_memory"
            }
        }


class VectorUpsertResponse(BaseModel):
    """
    Response schema for POST /database/vectors/upsert.

    Epic 6 Story 1 (Issue #27): Upsert behavior confirmation.
    Epic 6 Story 2: Return dimensions for verification.
    Epic 6 Story 5: Confirm metadata and namespace.

    Technical Details:
    - Returns vector_id (generated or provided)
    - Indicates whether vector was created (new) or updated (existing)
    - Confirms dimensions for validation
    - Returns namespace for isolation confirmation
    - Includes metadata for verification
    """
    vector_id: str = Field(
        ...,
        description="Unique identifier for the upserted vector"
    )
    created: bool = Field(
        ...,
        description="True if new vector was created, False if existing vector was updated"
    )
    dimensions: int = Field(
        ...,
        description="Dimensionality of the embedding vector"
    )
    namespace: str = Field(
        ...,
        description="Namespace where vector was stored"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata stored with the vector"
    )
    stored_at: str = Field(
        ...,
        description="ISO timestamp when vector was stored"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vector_id": "vec_compliance_check_001",
                "created": False,
                "dimensions": 384,
                "namespace": "agent_1_memory",
                "metadata": {
                    "source": "agent_memory",
                    "agent_id": "compliance_agent",
                    "task_type": "compliance_verification"
                },
                "stored_at": "2026-01-10T12:34:56.789Z"
            }
        }


class VectorListResponse(BaseModel):
    """Response schema for listing vectors in a namespace."""
    vectors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of vectors in the namespace"
    )
    namespace: str = Field(
        ...,
        description="Namespace that was queried"
    )
    total: int = Field(
        ...,
        description="Total number of vectors in the namespace"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vectors": [
                    {
                        "vector_id": "vec_001",
                        "dimensions": 384,
                        "document": "Sample document",
                        "metadata": {},
                        "stored_at": "2026-01-10T12:34:56.789Z"
                    }
                ],
                "namespace": "default",
                "total": 1
            }
        }
