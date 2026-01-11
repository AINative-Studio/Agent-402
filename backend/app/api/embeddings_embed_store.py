"""
Embeddings embed-and-store API endpoint for Epic 4, Issue #16.

As a developer, I can embed and store documents via embed-and-store endpoint.

Endpoint:
- POST /v1/public/{project_id}/embeddings/embed-and-store

Per PRD Section 6 (Agent memory foundation):
- Generate embeddings for multiple texts using the embedding service
- Store each embedding as a vector with the original text as document
- Support optional model, namespace, metadata, and upsert parameters
- Return vectors_stored count, model, dimensions, and vector_ids

Authentication:
- Requires X-API-Key header (per Epic 2)

DX Contract Compliance:
- Default model: BAAI/bge-small-en-v1.5 (384 dimensions)
- Error responses follow { detail, error_code } format
- Deterministic behavior per PRD Section 10

Built by AINative Dev Team
"""
from fastapi import APIRouter, Depends, status, Path
from app.core.auth import get_current_user
from app.schemas.embed_store import (
    EmbedStoreRequest,
    EmbedStoreResponse
)
from app.schemas.project import ErrorResponse
from app.services.embed_store_service import embed_store_service


router = APIRouter(
    prefix="/v1/public",
    tags=["embeddings"]
)


@router.post(
    "/{project_id}/embeddings/embed-and-store",
    response_model=EmbedStoreResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully embedded and stored vectors",
            "model": EmbedStoreResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Model not found",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Generate embeddings and store as vectors",
    description="""
    Generate embedding vectors for multiple texts and store them in the vector database.

    **Authentication:** Requires X-API-Key header

    **Epic 4 Story 1 (Issue #16) - Embed and Store:**
    - Accept texts (array of strings) to embed and store
    - Generate embeddings using the specified model (default: BAAI/bge-small-en-v1.5)
    - Store each embedding as a vector with the original text as document
    - Return vectors_stored count, model, dimensions, and vector_ids

    **Request Parameters:**
    - `texts`: Array of text strings to embed and store (required)
    - `model`: Embedding model to use (optional, defaults to BAAI/bge-small-en-v1.5, 384 dims)
    - `namespace`: Namespace for vector isolation (optional, defaults to 'default')
    - `metadata`: Metadata to attach to all vectors (optional)
    - `upsert`: Update existing vectors if IDs match (optional, defaults to false)

    **Response Fields:**
    - `vectors_stored`: Number of vectors successfully stored
    - `model`: Model used for embedding generation
    - `dimensions`: Dimensionality of the embedding vectors
    - `vector_ids`: Array of vector IDs for all stored texts

    **Per PRD Section 6 (Agent memory foundation):**
    - Enables agent recall and learning through vector storage
    - Supports multi-agent isolation via namespaces
    - Metadata enables auditability and compliance tracking

    **Supported Models:**
    - BAAI/bge-small-en-v1.5: 384 dimensions (default)
    - BAAI/bge-base-en-v1.5: 768 dimensions
    - BAAI/bge-large-en-v1.5: 1024 dimensions

    **Per PRD Section 10 (Determinism):**
    - Same input always produces same embedding
    - Behavior is deterministic and documented
    """
)
async def embed_and_store(
    project_id: str = Path(..., description="Project ID"),
    request: EmbedStoreRequest = ...,
    current_user: str = Depends(get_current_user)
) -> EmbedStoreResponse:
    """
    Generate embeddings for texts and store them in the vector database.

    Issue #16 Implementation:
    - Accepts texts (array of strings)
    - Generates embeddings for each text using the specified model
    - Stores each embedding as a vector with the original text as document
    - Returns vectors_stored count, model, dimensions, and vector_ids

    Args:
        project_id: Project identifier
        request: Embed-and-store request with texts, model, namespace, metadata, upsert
        current_user: Authenticated user ID (from X-API-Key)

    Returns:
        EmbedStoreResponse with vectors_stored, model, dimensions, vector_ids
    """
    # Call embed-store service to generate embeddings and store vectors
    vectors_stored, model_used, dimensions, vector_ids = embed_store_service.embed_and_store(
        texts=request.texts,
        model=request.model,
        namespace=request.namespace,
        metadata=request.metadata,
        upsert=request.upsert,
        project_id=project_id,
        user_id=current_user
    )

    return EmbedStoreResponse(
        vectors_stored=vectors_stored,
        model=model_used,
        dimensions=dimensions,
        vector_ids=vector_ids
    )
