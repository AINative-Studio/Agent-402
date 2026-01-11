"""
Embeddings API endpoints - Issue #16, Issue #18, Issue #19, and Issue #21 Implementation.
Implements Epic 4 Story 1: embed-and-store endpoint for batch document storage.
Implements Epic 4 Story 3 (Issue #18): upsert behavior for vector updates.
Implements Epic 4 Story 4 (Issue #19): Response includes vectors_stored, model, dimensions.
Implements Epic 5 Story 1 (Issue #21): Search via /embeddings/search.

Endpoints:
- POST /v1/public/{project_id}/embeddings/generate
- POST /v1/public/{project_id}/embeddings/embed-and-store (Issue #16, #18, #19)
- POST /v1/public/{project_id}/embeddings/search (Issue #21, #22)
- GET /embeddings/models

Issue #21 - Search Endpoint:
- Request: query, model, namespace, top_k, similarity_threshold, metadata_filter, include_metadata, include_embeddings
- Response: results (id, score, document, metadata, embedding), model, namespace, processing_time_ms
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
    VectorStorageResult,
    VectorDetail
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
    embedding, model_used, dimensions, processing_time = await embedding_service.generate_embedding(
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
        409: {
            "description": "Vector already exists (when upsert=false and vector_id exists)",
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

    **Epic 4 Story 3 (Issue #18) - Upsert Behavior (PRD §10 Replayability):**
    - When `upsert=true` and `vector_id` exists: UPDATE existing vector (idempotent)
    - When `upsert=false` (default) and `vector_id` exists: Return 409 VECTOR_ALREADY_EXISTS
    - When `upsert=true` and `vector_id` doesn't exist: INSERT as new vector
    - Response includes `vectors_inserted` and `vectors_updated` counts
    - Enables deterministic replay of agent workflows

    **Per PRD §6 (Agent memory foundation):**
    - Store document text and embedding vector in ZeroDB
    - Support metadata for document classification
    - Support namespace for logical separation

    **Default Behavior:**
    - When `model` is omitted, uses BAAI/bge-small-en-v1.5 (384 dimensions)
    - When `namespace` is omitted, uses 'default'
    - When `upsert` is omitted, defaults to false (error on duplicate)
    - Metadata is optional and can be provided per document

    **Response Fields (Issue #18, #19):**
    - success: Boolean indicating operation success (always true for 200 response)
    - vectors_stored: Total number of vectors stored (Issue #19 - required field)
    - vectors_inserted: Number of new vectors created (Issue #18)
    - vectors_updated: Number of existing vectors updated (Issue #18)
    - model: Model used for embedding generation (Issue #19 - required field)
    - dimensions: Dimensionality of embedding vectors (Issue #19 - required field)
    - namespace: Namespace where vectors were stored (Issue #19 - required field)
    - vector_ids: List of all vector IDs (Issue #19 - required field)
    - processing_time_ms: Total processing time in ms (Issue #19 - required field)
    - details: Per-vector status (only if include_details=true)

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

    Issue #18 Implementation:
    - Supports upsert parameter for update vs create behavior
    - Tracks vectors_inserted and vectors_updated counts

    Issue #19 Implementation:
    - Returns comprehensive metadata: success, vectors_stored, model, dimensions
    - Optional include_details parameter for per-vector status

    Args:
        project_id: Project identifier
        request: Embed and store request with documents, model, metadata, namespace
        current_user: Authenticated user ID

    Returns:
        EmbedAndStoreResponse with success, vector IDs, count, and metadata
    """
    # Generate embeddings and store for all documents
    # Issue #18: Pass upsert and vector_ids parameters
    vector_ids, model_used, dimensions, processing_time, created_flags = (
        embedding_service.batch_embed_and_store(
            documents=request.documents,
            model=request.model,
            metadata_list=request.metadata,
            namespace=request.namespace,
            project_id=project_id,
            user_id=current_user,
            upsert=request.upsert,
            vector_ids=request.vector_ids
        )
    )

    # Issue #18: Calculate inserted vs updated counts
    vectors_inserted = sum(1 for created in created_flags if created)
    vectors_updated = sum(1 for created in created_flags if not created)

    # Issue #19: Build details array if include_details=true
    details = None
    if request.include_details:
        details = []
        for idx, vector_id in enumerate(vector_ids):
            # Create text preview (first 50 chars with ellipsis if longer)
            text = request.documents[idx]
            text_preview = text[:47] + "..." if len(text) > 50 else text

            # Determine status based on created flag
            status = "inserted" if created_flags[idx] else "updated"

            details.append(VectorDetail(
                vector_id=vector_id,
                text_preview=text_preview,
                status=status
            ))

    # Build legacy results for backward compatibility (optional)
    results = []
    for idx, vector_id in enumerate(vector_ids):
        result = VectorStorageResult(
            vector_id=vector_id,
            document=request.documents[idx],
            metadata=request.metadata[idx] if request.metadata else None,
            created=created_flags[idx]
        )
        results.append(result)

    # Issue #18/#19: Return complete response with all required fields
    return EmbedAndStoreResponse(
        vectors_stored=len(vector_ids),
        vectors_inserted=vectors_inserted,  # Issue #18: New vectors created
        vectors_updated=vectors_updated,  # Issue #18: Existing vectors updated
        model=model_used,
        dimensions=dimensions,
        vector_ids=vector_ids,
        namespace=request.namespace,
        results=results,
        processing_time_ms=processing_time,
        details=details  # Issue #18/#19: Per-vector status if include_details=true
    )


@router.post(
    "/{project_id}/embeddings/search",
    response_model=EmbeddingSearchResponse,
    response_model_exclude_none=True,  # Issue #26: Omit None fields (metadata/embedding) from response
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

    **Issue #21 - Search Endpoint Implementation:**
    - POST /v1/public/{project_id}/embeddings/search
    - Request: query (required), model, namespace, top_k, similarity_threshold, metadata_filter, include_metadata, include_embeddings
    - Response: results (id, score, document, metadata, embedding), model, namespace, processing_time_ms

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

    **Issue #26 - Conditional Response Fields (PRD Section 9):**
    - include_metadata (default: true): Include metadata in results
    - include_embeddings (default: false): Include embedding vectors in results
    - When false, fields are OMITTED from response (not set to null)
    - Reduces response payload size for efficiency

    **Per PRD Section 6 (Agent Recall):**
    - Enables agent memory retrieval
    - Supports multi-agent isolation via namespaces

    **Per PRD Section 10 (Predictable Replay):**
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

    Issue #21 Implementation:
    - POST /v1/public/{project_id}/embeddings/search
    - Request body: query, model, namespace, top_k, similarity_threshold, metadata_filter, include_metadata, include_embeddings
    - Response: results (id, score, document, metadata, embedding), model, namespace, processing_time_ms

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
    query_embedding, model_used, dimensions, _ = await embedding_service.generate_embedding(
        text=request.query,
        model=request.model
    )

    # Search vectors with namespace scoping (Issue #17) and top_k limiting (Issue #22)
    namespace_used = request.namespace or DEFAULT_NAMESPACE

    # Issue #26: Pass include_metadata and include_embeddings to service
    search_results = vector_store_service.search_vectors(
        project_id=project_id,
        query_embedding=query_embedding,
        namespace=namespace_used,
        top_k=request.top_k,  # Issue #22: Limit results
        similarity_threshold=request.similarity_threshold,
        metadata_filter=request.metadata_filter,
        user_id=None,  # Allow cross-user search within project
        include_metadata=request.include_metadata,  # Issue #26: Toggle metadata in results
        include_embeddings=request.include_embeddings  # Issue #26: Toggle embeddings in results
    )

    # Convert to SearchResult objects per Issue #21 specification
    results = []
    for result in search_results:
        # Issue #21: Map service fields to API response fields
        # - vector_id -> id
        # - similarity -> score
        # - text -> document
        # Issue #26: Metadata and embeddings are conditionally included by service
        search_result = SearchResult(
            id=result["vector_id"],
            score=result["similarity"],
            document=result["text"],
            metadata=result.get("metadata"),  # None if include_metadata=false
            embedding=result.get("embedding")  # None if include_embeddings=false
        )
        results.append(search_result)

    processing_time = int((time.time() - start_time) * 1000)

    # Issue #21: Response includes results, model, namespace, processing_time_ms
    return EmbeddingSearchResponse(
        results=results,
        model=model_used,
        namespace=namespace_used,  # Issue #17: Confirm namespace searched
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
