"""
Embeddings API endpoints.
Implements Epic 3 (Embeddings: Generate), Epic 4 (Embed & Store), Epic 5 (Search).

Endpoints:
- POST /v1/public/{project_id}/embeddings/generate (Epic 3, Issue #12)
- POST /v1/public/{project_id}/embeddings/embed-and-store (Epic 4, Issue #17, #18, #19)
- POST /v1/public/{project_id}/embeddings/search (Epic 5, Issue #21, #22, #17)

Issue #21 - Search Endpoint:
- Request: query, model, namespace, top_k, similarity_threshold, metadata_filter, include_metadata, include_embeddings
- Response: results (id, score, document, metadata, embedding), model, namespace, processing_time_ms
"""
import time
from fastapi import APIRouter, Depends, status, Path, HTTPException
from app.core.auth import get_current_user
from app.schemas.embeddings import (
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    EmbedAndStoreRequest,
    EmbedAndStoreResponse,
    EmbeddingSearchRequest,
    EmbeddingSearchResponse,
    SearchResult,
    ModelInfo,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_DIMENSIONS,
    SUPPORTED_MODELS
)
from app.schemas.project import ErrorResponse
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store_service
from app.core.errors import APIError


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
            "description": "Successfully embedded and stored vector",
            "model": EmbedAndStoreResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        409: {
            "description": "Vector already exists (when upsert=false)",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Generate embedding and store in vector database",
    description="""
    Generate an embedding vector for the provided text and store it.

    **Authentication:** Requires X-API-Key header

    **Epic 4 Story 3 (Issue #18) - Upsert Behavior:**
    - When `upsert=true`: Updates existing vector if `vector_id` exists (idempotent)
    - When `upsert=false` (default): Creates new vector or returns 409 error if `vector_id` exists
    - Prevents duplicate vectors with same ID when upsert=false

    **Epic 4 Story 4 (Issue #19) - Response Fields:**
    - Response MUST include: vectors_stored, model, dimensions
    - Returns created=true for new vectors, created=false for updates
    - Includes processing_time_ms for observability

    **Per PRD §10 (Replayability):**
    - Same request with upsert=true produces identical result (idempotent)
    - Deterministic behavior for agent workflows

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
    Generate an embedding and store it in the vector database.

    Issue #18 Implementation:
    - Supports upsert parameter for update vs create behavior
    - When upsert=true: Updates existing vector (idempotent)
    - When upsert=false: Errors if vector_id exists (prevents duplicates)

    Issue #19 Implementation:
    - Returns vectors_stored, model, dimensions in response
    - Provides processing_time_ms for observability

    Args:
        project_id: Project identifier
        request: Embed and store request with text, model, metadata, vector_id, upsert
        current_user: Authenticated user ID

    Returns:
        EmbedAndStoreResponse with storage confirmation and metadata
    """
    # Call embedding service with namespace support (Issue #17) and upsert logic (Issue #19)
    vectors_stored, vector_id, model_used, dimensions, created, processing_time, stored_at = (
        embedding_service.embed_and_store(
            text=request.text,
            model=request.model,
            namespace=request.namespace,  # Issue #17: Pass namespace for isolation
            metadata=request.metadata,
            vector_id=request.vector_id,
            upsert=request.upsert,
            project_id=project_id,
            user_id=current_user
        )
    )

    # Issue #17: Get namespace from request or use default
    from app.services.vector_store_service import DEFAULT_NAMESPACE
    namespace_used = request.namespace or DEFAULT_NAMESPACE

    return EmbedAndStoreResponse(
        vectors_stored=vectors_stored,  # Issue #19: Required field - count from service
        vector_id=vector_id,
        namespace=namespace_used,  # Issue #17: Confirm namespace
        model=model_used,  # Issue #19: Required field
        dimensions=dimensions,  # Issue #19: Required field
        text=request.text,
        created=created,
        processing_time_ms=processing_time,
        stored_at=stored_at
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
            "description": "Validation error (INVALID_METADATA_FILTER, INVALID_NAMESPACE, or validation error)",
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

    **Epic 5 Story 3 (Issue #23) - Namespace Scoping:**
    - Only searches vectors in the specified namespace
    - Vectors from other namespaces are NEVER returned
    - Default namespace ("default") is used when namespace parameter is omitted
    - If namespace doesn't exist, returns empty results (not an error)
    - Namespace isolation is strictly enforced
    - Uses centralized namespace validator from Epic 4

    **Epic 5 Story 2 (Issue #22) - Limit Results via top_k:**
    - Use `top_k` parameter to limit results (default: 10, min: 1, max: 100)
    - Results are sorted by similarity score (descending)
    - If fewer matches exist than top_k, all available matches are returned
    - Returns 422 VALIDATION_ERROR if top_k is out of range (1-100)

    **Epic 5 Story 4 (Issue #24) - Metadata Filtering:**
    - Filter results by metadata fields using MongoDB-style operators
    - Supported operators: $eq (default), $ne, $gt, $gte, $lt, $lte, $in, $nin, $exists, $contains
    - Filters are applied AFTER similarity search to refine results
    - Returns 422 INVALID_METADATA_FILTER for invalid filter format
    - Only returns vectors matching all specified metadata filters (AND logic)

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

    Issue #23 Implementation (Namespace Scoping):
    - Namespace parameter strictly scopes search results
    - Only vectors from specified namespace are returned
    - Default namespace ("default") is used when namespace is omitted
    - If namespace doesn't exist, returns empty results (not an error)
    - Namespace validation uses centralized validator from Epic 4

    Args:
        project_id: Project identifier
        request: Search request with query, namespace, filters
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

    # Search vectors with namespace scoping (Issue #23)
    # Note: request.namespace is validated and defaults to "default" via centralized validator
    namespace_used = request.namespace

    # Issue #26: Pass include_metadata and include_embeddings to service
    search_results = vector_store_service.search_vectors(
        project_id=project_id,
        query_embedding=query_embedding,
        namespace=namespace_used,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
        metadata_filter=request.metadata_filter,
        user_id=None,  # Don't filter by user for search (allow cross-user search within project)
        include_metadata=request.include_metadata,  # Issue #26: Toggle metadata in results
        include_embeddings=request.include_embeddings  # Issue #21, #26: Toggle embeddings in results
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
