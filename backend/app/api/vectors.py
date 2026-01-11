"""
Vector API endpoints with strict dimension validation.
Implements Epic 6 (Vector Operations API) per backlog.md.
GitHub Issue #27: Direct vector upsert operations.
GitHub Issue #28: Strict dimension length enforcement.
GitHub Issue #31: Metadata and namespace support (NEW).

Endpoints:
- POST /v1/public/{project_id}/database/vectors/upsert (Epic 6, Issue #27, #28, #31)
- POST /v1/public/{project_id}/database/vectors/search (Vector search)

Per DX Contract §4 (Endpoint Prefixing):
- All vector operations MUST include /database/ prefix
- This is a permanent requirement per DX Contract

Per Issue #28 (Strict Dimension Validation):
- Validate vector_embedding array length matches expected dimensions
- Enforce strict validation before storage
- Only allow supported dimensions: 384, 768, 1024, 1536
- Return clear error if length mismatch
- Follow PRD §10 for determinism

Per Issue #31 (Metadata & Namespace Support - NEW):
- Support metadata field (optional JSON object) for vector annotation
- Support namespace field for multi-tenancy and logical isolation
- Metadata is queryable and filterable in search operations
- Namespace enables agent isolation and environment separation
- Follow PRD §6 for auditability and compliance tracking
"""
import time
from datetime import datetime
from fastapi import APIRouter, Depends, status, Path
from app.core.auth import get_current_user
from app.schemas.vectors import (
    VectorUpsertRequest,
    VectorUpsertResponse,
    VectorSearchRequest,
    VectorSearchResponse
)
from app.schemas.project import ErrorResponse
from app.services.zerodb_vector_service import zerodb_vector_service


router = APIRouter(
    prefix="/v1/public",
    tags=["vectors"]
)


@router.post(
    "/{project_id}/database/vectors/upsert",
    response_model=VectorUpsertResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully upserted vector",
            "model": VectorUpsertResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error (dimension mismatch, invalid input)",
            "model": ErrorResponse
        }
    },
    summary="Upsert vector embedding (Issue #31: Metadata & Namespace)",
    description="""
    Upsert (insert or update) a vector embedding with raw vector data.

    **Authentication:** Requires X-API-Key header

    **Epic 6 Story 1 (Issue #27):**
    - Direct vector upsert via POST /database/vectors/upsert
    - Insert if vector_id is new or not provided
    - Update if vector_id already exists
    - Idempotent operation - same request produces same result

    **Epic 6 Story 2 (Issue #28 - Strict Dimension Validation):**
    - Validates vector_embedding array length matches expected dimensions
    - Enforces strict validation before storage
    - Supported dimensions: 384, 768, 1024, 1536
    - Returns clear DIMENSION_MISMATCH error for invalid dimensions
    - Array length must match one of the supported dimension sizes exactly
    - Validation is deterministic per PRD §10

    **Epic 6 Story 5 (Issue #31 - Metadata & Namespace Support - NEW):**
    - Supports metadata field (optional JSON object) for vector annotation
    - Supports namespace field for multi-tenancy and logical isolation
    - Metadata is queryable and filterable in search operations
    - Namespace enables agent isolation and environment separation
    - Follow PRD §6 for auditability and compliance tracking
    - Metadata best practices: agent_id, task_id, source, timestamp, tags, etc.
    - Namespace best practices: agent isolation, environment separation, multi-tenancy

    **Per DX Contract §4:**
    - Endpoint MUST include /database/ prefix
    - Missing /database/ returns 404 Not Found

    **Per PRD §6 (Low-level control):**
    - Provides direct vector storage without text embedding
    - Useful for pre-computed embeddings from external sources
    - Complements embeddings API for flexibility

    **Upsert Behavior:**
    - vector_id provided + exists → UPDATE (created=false)
    - vector_id provided + not exists → INSERT (created=true)
    - vector_id not provided → INSERT with auto-generated ID (created=true)

    **Supported Dimensions:**
    - 384 (BAAI/bge-small-en-v1.5)
    - 768 (BAAI/bge-base-en-v1.5)
    - 1024 (BAAI/bge-large-en-v1.5)
    - 1536 (OpenAI embeddings)
    """
)
async def upsert_vector(
    project_id: str = Path(..., description="Project ID"),
    request: VectorUpsertRequest = ...,
    current_user: str = Depends(get_current_user)
) -> VectorUpsertResponse:
    """
    Upsert a vector embedding with metadata and namespace support.

    Issue #27 Implementation:
    - Accepts vector_id, vector_embedding, document, metadata, namespace
    - Validates vector dimensions (384, 768, 1024, 1536)
    - Implements upsert behavior: insert if new, update if exists
    - Returns created flag to indicate insert vs update
    - Requires X-API-Key authentication

    Issue #31 Implementation (NEW):
    - Metadata field enables auditability and compliance tracking
    - Namespace field provides multi-tenancy and logical isolation
    - Returns metadata and namespace in response for confirmation
    - Supports agent-native workflows per PRD §6

    Args:
        project_id: Project identifier
        request: Vector upsert request with embedding data, metadata, namespace
        current_user: Authenticated user ID

    Returns:
        VectorUpsertResponse with upsert confirmation, metadata, and namespace

    Raises:
        APIError: If dimension validation fails (DIMENSION_MISMATCH)
    """
    start_time = time.time()

    # Determine namespace (default if not provided)
    namespace = request.namespace or "default"

    # Determine model from dimensions (for compatibility)
    dimension_to_model = {
        384: "BAAI/bge-small-en-v1.5",
        768: "BAAI/bge-base-en-v1.5",
        1024: "BAAI/bge-large-en-v1.5",
        1536: "openai-text-embedding-ada-002"
    }
    model = dimension_to_model.get(request.dimensions, "BAAI/bge-small-en-v1.5")

    # Upsert vector using ZeroDB vector service (Issue #31: with metadata and namespace)
    vector_id, created = zerodb_vector_service.store_vector(
        vector_embedding=request.vector_embedding,
        document=request.document,
        model=model,
        namespace=namespace,
        metadata=request.metadata or {},
        vector_id=request.vector_id
    )

    processing_time = int((time.time() - start_time) * 1000)

    return VectorUpsertResponse(
        vector_id=vector_id,
        dimensions=request.dimensions,
        namespace=namespace,
        metadata=request.metadata or {},
        created=created,
        processing_time_ms=processing_time,
        stored_at=datetime.utcnow().isoformat() + "Z"
    )


@router.get(
    "/vectors/{namespace}",
    response_model=VectorListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved vectors",
            "model": VectorListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    },
    summary="List vectors in namespace",
    description="""
    List all vectors in a specific namespace.

    **Authentication:** Requires X-API-Key header

    **Per DX Contract §4:**
    - Endpoint MUST include /database/ prefix

    **Namespace Isolation:**
    - Only returns vectors from the specified namespace
    - Vectors from other namespaces are not included
    """
)
async def list_vectors(
    namespace: str,
    current_user: str = Depends(get_current_user)
) -> VectorListResponse:
    """
    List vectors in a namespace.

    Args:
        namespace: Namespace to list vectors from
        current_user: Authenticated user ID

    Returns:
        VectorListResponse with vector list and count
    """
    vectors, total = vector_service.list_vectors(namespace=namespace)

    # Remove embedding data from response (too large)
    vectors_without_embeddings = []
    for vector in vectors:
        vector_copy = {
            "vector_id": vector["vector_id"],
            "dimensions": vector["dimensions"],
            "document": vector["document"],
            "metadata": vector["metadata"],
            "stored_at": vector["stored_at"]
        }
        vectors_without_embeddings.append(vector_copy)

    return VectorListResponse(
        vectors=vectors_without_embeddings,
        namespace=namespace,
        total=total
    )
