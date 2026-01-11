"""
Embeddings API endpoints - Issue #16 Implementation.
Implements Epic 4 Story 1: embed-and-store endpoint for batch document storage.

Endpoints:
- POST /v1/public/{project_id}/embeddings/generate
- POST /v1/public/{project_id}/embeddings/embed-and-store (Issue #16)
- GET /embeddings/models
"""
from fastapi import APIRouter, Depends, status, Path
from app.core.auth import get_current_user
from app.schemas.embeddings import (
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    ModelInfo,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_DIMENSIONS,
    SUPPORTED_MODELS
)
from app.schemas.embeddings_store import (
    EmbedAndStoreRequest,
    EmbedAndStoreResponse,
    VectorStorageResult
)
from app.schemas.project import ErrorResponse
from app.services.embedding_service import embedding_service


router = APIRouter(
    prefix="/v1/public",
    tags=["embeddings"]
)


@router.post(
    "/{project_id}/embeddings/generate",
    response_model=EmbeddingGenerateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully generated embedding",
            "model": EmbeddingGenerateResponse
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
    summary="Generate text embedding",
    description="""
    Generate an embedding vector for the provided text.

    **Authentication:** Requires X-API-Key header

    **Issue #12 - Default Model Behavior:**
    - When `model` parameter is omitted, uses BAAI/bge-small-en-v1.5 (384 dimensions)
    - Response MUST indicate which model was actually used
    - Behavior is deterministic and consistent per DX Contract

    **Supported Models:**
    - BAAI/bge-small-en-v1.5: 384 dimensions (default)
    - BAAI/bge-base-en-v1.5: 768 dimensions
    - BAAI/bge-large-en-v1.5: 1024 dimensions

    **Per Epic 3 Story 2:**
    - API defaults to 384-dim embeddings when model is omitted

    **Per PRD §10:**
    - Behavior must be deterministic and documented
    - Same input always produces same output
    """
)
async def generate_embedding(
    project_id: str = Path(..., description="Project ID"),
    request: EmbeddingGenerateRequest = ...,
    current_user: str = Depends(get_current_user)
) -> EmbeddingGenerateResponse:
    """
    Generate an embedding for the provided text.

    Issue #12 Implementation:
    - Applies default model (BAAI/bge-small-en-v1.5) when model is None
    - Returns actual model used in response (for determinism)
    - Generates exactly 384 dimensions for default model

    Args:
        project_id: Project identifier
        request: Embedding generation request with text and optional model
        current_user: Authenticated user ID

    Returns:
        EmbeddingGenerateResponse with embedding vector and metadata
    """
    # Generate embedding (service handles default model logic)
    embedding, model_used, dimensions, processing_time = embedding_service.generate_embedding(
        text=request.text,
        model=request.model
    )

    return EmbeddingGenerateResponse(
        embedding=embedding,
        model=model_used,
        dimensions=dimensions,
        text=request.text,
        processing_time_ms=processing_time
    )


@router.post(
    "/{project_id}/embeddings/embed-and-store",
    response_model=EmbedAndStoreResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully embedded and stored documents",
            "model": EmbedAndStoreResponse
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
    summary="Generate embeddings and store documents in vector database",
    description="""
    Generate embedding vectors for multiple documents and store them.

    **Authentication:** Requires X-API-Key header

    **Epic 4 Story 1 (Issue #16) - Batch Document Storage:**
    - Accept multiple documents and generate embeddings for each
    - Store all embeddings with their metadata in ZeroDB
    - Support optional namespace for logical organization
    - Return vector IDs for all stored documents

    **Per PRD §6 (Agent memory foundation):**
    - Store document text and embedding vector in ZeroDB
    - Support metadata for document classification
    - Support namespace for logical separation

    **Default Behavior:**
    - When `model` is omitted, uses BAAI/bge-small-en-v1.5 (384 dimensions)
    - When `namespace` is omitted, uses 'default'
    - Metadata is optional and can be provided per document

    **Response Fields:**
    - vector_ids: List of IDs for stored vectors
    - stored_count: Number of documents successfully stored
    - model: Model used for embedding generation
    - dimensions: Dimensionality of embedding vectors
    - namespace: Namespace where vectors were stored
    - results: Detailed results for each document
    - processing_time_ms: Total processing time

    **Supported Models:**
    - BAAI/bge-small-en-v1.5: 384 dimensions (default)
    - BAAI/bge-base-en-v1.5: 768 dimensions
    - BAAI/bge-large-en-v1.5: 1024 dimensions
    """
)
async def embed_and_store(
    project_id: str = Path(..., description="Project ID"),
    request: EmbedAndStoreRequest = ...,
    current_user: str = Depends(get_current_user)
) -> EmbedAndStoreResponse:
    """
    Generate embeddings for documents and store them in the vector database.

    Issue #16 Implementation:
    - Accepts multiple documents and generates embeddings for each
    - Stores all embeddings with optional metadata
    - Supports namespace for logical organization
    - Returns vector IDs and confirmation for all stored documents

    Args:
        project_id: Project identifier
        request: Embed and store request with documents, model, metadata, namespace
        current_user: Authenticated user ID

    Returns:
        EmbedAndStoreResponse with vector IDs, count, and detailed results
    """
    # Generate embeddings and store for all documents
    vector_ids, model_used, dimensions, processing_time = (
        embedding_service.batch_embed_and_store(
            documents=request.documents,
            model=request.model,
            metadata_list=request.metadata,
            namespace=request.namespace,
            project_id=project_id,
            user_id=current_user
        )
    )

    # Build detailed results for each document
    results = []
    for idx, vector_id in enumerate(vector_ids):
        result = VectorStorageResult(
            vector_id=vector_id,
            document=request.documents[idx],
            metadata=request.metadata[idx] if request.metadata else None
        )
        results.append(result)

    return EmbedAndStoreResponse(
        vector_ids=vector_ids,
        stored_count=len(vector_ids),
        model=model_used,
        dimensions=dimensions,
        namespace=request.namespace,
        results=results,
        processing_time_ms=processing_time
    )


@router.get(
    "/embeddings/models",
    response_model=list[ModelInfo],
    status_code=status.HTTP_200_OK,
    summary="List supported embedding models",
    description="""
    List all supported embedding models with their dimensions.

    **Issue #12:** Documents the default model and all supported models.

    **Authentication:** Optional (public endpoint for documentation)
    """
)
async def list_models() -> list[ModelInfo]:
    """
    List all supported embedding models.

    Returns:
        List of ModelInfo objects describing available models
    """
    from app.core.embedding_models import EMBEDDING_MODEL_SPECS

    models = []
    default_model_str = DEFAULT_EMBEDDING_MODEL

    for model_enum, spec in EMBEDDING_MODEL_SPECS.items():
        model_name = model_enum.value if hasattr(model_enum, 'value') else str(model_enum)
        is_default = (model_name == default_model_str)

        models.append(ModelInfo(
            name=model_name,
            dimensions=spec["dimensions"],
            description=spec["description"],
            is_default=is_default
        ))

    return models
