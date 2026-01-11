"""
Embed-and-store service for Epic 4, Issue #16.

Implements batch embedding generation and vector storage for agent memory foundation.

Per PRD Section 6 (Agent memory foundation):
- Generate embeddings for multiple texts in a single operation
- Store each embedding as a vector with the original text as document
- Support namespace for vector isolation
- Support metadata for vector annotation
- Support upsert behavior for idempotent operations

DX Contract Compliance:
- Default model: BAAI/bge-small-en-v1.5 (384 dimensions)
- Deterministic behavior per PRD Section 10
- Error responses follow { detail, error_code } format

Built by AINative Dev Team
"""
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    get_model_dimensions,
    is_model_supported
)
from app.core.errors import APIError
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store_service


class EmbedStoreService:
    """
    Service for embedding and storing multiple texts.

    Issue #16 Requirements:
    - Accept texts (array of strings) and generate embeddings for each
    - Store each embedding as a vector with the original text as document
    - Support optional model, namespace, metadata, and upsert parameters
    - Return vectors_stored count, model, dimensions, and vector_ids

    Per PRD Section 6:
    - Agent memory foundation for multi-agent systems
    - Namespace isolation for vector scoping
    - Metadata support for auditability and compliance

    Integration with shared vector_store_service:
    - Uses the same backend as the search endpoint for consistency
    - Enables proper namespace scoping across endpoints
    """

    def __init__(self):
        """Initialize the embed-store service."""
        # Use shared vector_store_service for consistency with search endpoint
        pass

    def get_model_or_default(self, model: Optional[str] = None) -> str:
        """
        Get the model to use, applying default if not provided.

        Per Issue #16: Default model is BAAI/bge-small-en-v1.5 (384 dims).

        Args:
            model: Optional model name from request

        Returns:
            str: Model name to use (either provided or default)

        Raises:
            APIError: If provided model is not supported
        """
        if model is None:
            return DEFAULT_EMBEDDING_MODEL

        if not is_model_supported(model):
            supported_models = ["BAAI/bge-small-en-v1.5", "BAAI/bge-base-en-v1.5", "BAAI/bge-large-en-v1.5"]
            raise APIError(
                status_code=404,
                error_code="MODEL_NOT_FOUND",
                detail=f"Model '{model}' not found. Supported models: {', '.join(supported_models)}"
            )

        return model

    def embed_and_store(
        self,
        texts: List[str],
        model: Optional[str] = None,
        namespace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        upsert: bool = False,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[int, str, int, List[str]]:
        """
        Generate embeddings for multiple texts and store them as vectors.

        Issue #16 Implementation:
        - Accept texts (array of strings) and generate embeddings for each
        - Store each embedding as a vector with the original text as document
        - Support namespace for vector isolation
        - Support metadata for vector annotation
        - Support upsert for update vs create behavior

        Args:
            texts: Array of text strings to embed and store
            model: Optional model name (defaults to BAAI/bge-small-en-v1.5)
            namespace: Optional namespace for vector isolation (defaults to 'default')
            metadata: Optional metadata to attach to all vectors
            upsert: Whether to update existing vectors (default: False)
            project_id: Project identifier for scoping
            user_id: User/agent identifier

        Returns:
            Tuple of (vectors_stored, model_used, dimensions, vector_ids)

        Raises:
            APIError: If model is not supported or validation fails
        """
        start_time = time.time()

        # Apply default model if not provided
        model_used = self.get_model_or_default(model)
        dimensions = get_model_dimensions(model_used)

        # Normalize namespace
        namespace_used = namespace if namespace else "default"

        vector_ids = []
        vectors_stored = 0

        for text in texts:
            # Generate embedding for this text using the embedding service
            embedding, _, _, _ = embedding_service.generate_embedding(
                text=text,
                model=model_used
            )

            # Store vector using shared vector_store_service
            # This ensures consistency with the search endpoint
            store_result = vector_store_service.store_vector(
                project_id=project_id or "default_project",
                user_id=user_id or "default_user",
                text=text,
                embedding=embedding,
                model=model_used,
                dimensions=dimensions,
                namespace=namespace_used,
                metadata=metadata,
                vector_id=None,  # Auto-generate
                upsert=upsert
            )

            vector_ids.append(store_result["vector_id"])
            vectors_stored += 1

        processing_time = int((time.time() - start_time) * 1000)

        return vectors_stored, model_used, dimensions, vector_ids

    def get_vector(
        self,
        vector_id: str,
        namespace: str = "default",
        project_id: str = "default_project"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a vector by ID from a namespace.

        Args:
            vector_id: Vector identifier
            namespace: Namespace to search in
            project_id: Project identifier

        Returns:
            Vector data or None if not found
        """
        return vector_store_service.get_vector(
            project_id=project_id,
            vector_id=vector_id,
            namespace=namespace
        )

    def list_vectors(
        self,
        namespace: str = "default",
        project_id: str = "default_project",
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List vectors in a namespace.

        Args:
            namespace: Namespace to list from
            project_id: Project identifier
            limit: Maximum vectors to return
            offset: Pagination offset

        Returns:
            Tuple of (vectors_list, total_count)
        """
        stats = vector_store_service.get_namespace_stats(project_id, namespace)
        total_count = stats.get("vector_count", 0)

        # Note: Pagination not fully supported by vector_store_service yet
        # This is a simplified implementation
        return [], total_count

    def delete_vector(
        self,
        vector_id: str,
        namespace: str = "default",
        project_id: str = "default_project"
    ) -> bool:
        """
        Delete a vector from a namespace.

        Args:
            vector_id: Vector identifier
            namespace: Namespace containing the vector
            project_id: Project identifier

        Returns:
            True if deleted, False if not found
        """
        # Note: vector_store_service doesn't have delete yet
        # This is a placeholder
        return False

    def clear_all(self):
        """
        Clear all vectors from storage.

        Primarily for testing purposes.
        """
        vector_store_service.clear_all_vectors()


# Singleton instance
embed_store_service = EmbedStoreService()
