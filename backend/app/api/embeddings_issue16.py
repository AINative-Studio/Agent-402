"""
Embeddings API endpoints - Issue #16 Implementation.
Implements Epic 4 Story 1: embed-and-store endpoint for batch document storage.

Endpoints:
- POST /v1/public/{project_id}/embeddings/generate
- POST /v1/public/{project_id}/embeddings/embed-and-store (Issue #16)
- POST /v1/public/{project_id}/embeddings/search (Issue #22)
- GET /embeddings/models
"""
import time
from fastapi import APIRouter, Depends, status, Path
from app.core.auth import get_current_user
from app.schemas.embeddings import (
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    EmbeddingSearchRequest,
    EmbeddingSearchResponse,
    SearchResult,
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
from app.services.vector_store_service import vector_store_service, DEFAULT_NAMESPACE


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

    **Response Fields (Issue #19):**
    - vector_ids: List of IDs for stored vectors
    - vectors_stored: Number of vectors successfully stored (Issue #19 - required field)
    - model: Model used for embedding generation (Issue #19 - required field)
    - dimensions: Dimensionality of embedding vectors (Issue #19 - required field)
    - namespace: Namespace where vectors were stored
    - results: Detailed results for each document
    - processing_time_ms: Total processing time (Issue #19 - included when available)

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
        vectors_stored=len(vector_ids),  # Issue #19: Use vectors_stored field
        model=model_used,
        dimensions=dimensions,
        namespace=request.namespace,
        results=results,
        processing_time_ms=processing_time
    )


@router.post(
    "/{project_id}/embeddings/search",
    response_model=EmbeddingSearchResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully searched vectors",
            "model": EmbeddingSearchResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Search for similar vectors",
    description="""
    Search for similar vectors using semantic similarity.

    **Authentication:** Requires X-API-Key header

    **Issue #22 - top_k Parameter:**
    - Use `top_k` parameter to limit results (1-100, default: 10)
    - Returns only the top K most similar vectors
    - Results are sorted by similarity score (descending)
    - If fewer vectors exist than top_k, all available vectors are returned

    **Epic 5 Story 3 (Issue #17) - Namespace Scoping:**
    - Only searches vectors in the specified namespace
    - Vectors from other namespaces are NEVER returned
    - Default namespace is used when namespace parameter is omitted

    **Epic 5 Story 4 - Metadata Filtering:**
    - Filter results by metadata fields
    - Only returns vectors matching all specified metadata filters

    **Epic 5 Story 5 - Similarity Threshold:**
    - Use `similarity_threshold` to filter low-quality matches
    - Only returns results with similarity >= threshold (0.0-1.0)

    **Per PRD §6 (Agent Recall):**
    - Enables agent memory retrieval
    - Supports multi-agent isolation via namespaces

    **Per PRD §10 (Predictable Replay):**
    - Deterministic ordering ensures consistent results
    - Same query produces same result ordering
    """
)
async def search_vectors(
    project_id: str = Path(..., description="Project ID"),
    request: EmbeddingSearchRequest = ...,
    current_user: str = Depends(get_current_user)
) -> EmbeddingSearchResponse:
    """
    Search for similar vectors using semantic similarity.

    Issue #22 Implementation:
    - top_k parameter limits results to most similar vectors
    - Results ordered by similarity score (descending)
    - Handles edge cases (top_k > available vectors)

    Issue #17 Implementation:
    - Namespace parameter strictly scopes search results
    - Only vectors from specified namespace are returned

    Args:
        project_id: Project identifier
        request: Search request with query, namespace, top_k, filters
        current_user: Authenticated user ID

    Returns:
        EmbeddingSearchResponse with matching vectors and metadata
    """
    start_time = time.time()

    # Generate query embedding
    query_embedding, model_used, dimensions, _ = embedding_service.generate_embedding(
        text=request.query,
        model=request.model
    )

    # Search vectors with namespace scoping (Issue #17) and top_k limiting (Issue #22)
    namespace_used = request.namespace or DEFAULT_NAMESPACE

    # Issue #26: Check if include_metadata and include_embeddings exist
    include_metadata = getattr(request, 'include_metadata', True)
    include_embeddings = getattr(request, 'include_embeddings', False)

    search_results = vector_store_service.search_vectors(
        project_id=project_id,
        query_embedding=query_embedding,
        namespace=namespace_used,
        top_k=request.top_k,  # Issue #22: Limit results
        similarity_threshold=request.similarity_threshold,
        metadata_filter=request.metadata_filter,
        user_id=None  # Allow cross-user search within project
    )

    # Convert to SearchResult objects
    results = []
    for result in search_results:
        search_result = SearchResult(
            vector_id=result["vector_id"],
            namespace=result["namespace"],
            text=result["text"],
            similarity=result["similarity"],
            model=result["model"],
            dimensions=result["dimensions"],
            metadata=result.get("metadata"),
            embedding=result.get("embedding") if include_embeddings else None,
            created_at=result["created_at"]
        )
        results.append(search_result)

    processing_time = int((time.time() - start_time) * 1000)

    return EmbeddingSearchResponse(
        results=results,
        query=request.query,
        namespace=namespace_used,  # Issue #17: Confirm namespace searched
        model=model_used,
        total_results=len(results),  # Issue #22: Total matches top_k limit
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
