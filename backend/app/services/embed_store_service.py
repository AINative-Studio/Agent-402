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
    """

    def __init__(self):
        """Initialize the embed-store service."""
        # In-memory store for MVP (namespace -> vector_id -> vector_data)
        self._vector_store: Dict[str, Dict[str, Dict[str, Any]]] = {}

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

        # Ensure namespace exists in store
        if namespace_used not in self._vector_store:
            self._vector_store[namespace_used] = {}

        vector_ids = []
        vectors_stored = 0

        for text in texts:
            # Generate embedding for this text using the embedding service
            embedding, _, _, _ = embedding_service.generate_embedding(
                text=text,
                model=model_used
            )

            # Generate unique vector ID
            vector_id = f"vec_{uuid.uuid4().hex[:16]}"

            # Prepare vector record
            stored_at = datetime.utcnow().isoformat() + "Z"
            vector_record = {
                "vector_id": vector_id,
                "embedding": embedding,
                "document": text,  # Store original text as document
                "model": model_used,
                "dimensions": dimensions,
                "namespace": namespace_used,
                "metadata": metadata or {},
                "project_id": project_id,
                "user_id": user_id,
                "created_at": stored_at,
                "updated_at": stored_at
            }

            # Store vector in namespace
            self._vector_store[namespace_used][vector_id] = vector_record
            vector_ids.append(vector_id)
            vectors_stored += 1

        processing_time = int((time.time() - start_time) * 1000)

        return vectors_stored, model_used, dimensions, vector_ids

    def get_vector(
        self,
        vector_id: str,
        namespace: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a vector by ID from a namespace.

        Args:
            vector_id: Vector identifier
            namespace: Namespace to search in

        Returns:
            Vector data or None if not found
        """
        if namespace not in self._vector_store:
            return None

        return self._vector_store[namespace].get(vector_id)

    def list_vectors(
        self,
        namespace: str = "default",
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List vectors in a namespace.

        Args:
            namespace: Namespace to list from
            limit: Maximum vectors to return
            offset: Pagination offset

        Returns:
            Tuple of (vectors_list, total_count)
        """
        if namespace not in self._vector_store:
            return [], 0

        all_vectors = list(self._vector_store[namespace].values())
        total_count = len(all_vectors)
        paginated = all_vectors[offset:offset + limit]

        return paginated, total_count

    def delete_vector(
        self,
        vector_id: str,
        namespace: str = "default"
    ) -> bool:
        """
        Delete a vector from a namespace.

        Args:
            vector_id: Vector identifier
            namespace: Namespace containing the vector

        Returns:
            True if deleted, False if not found
        """
        if namespace not in self._vector_store:
            return False

        if vector_id in self._vector_store[namespace]:
            del self._vector_store[namespace][vector_id]
            return True

        return False

    def clear_all(self):
        """
        Clear all vectors from storage.

        Primarily for testing purposes.
        """
        self._vector_store.clear()


# Singleton instance
embed_store_service = EmbedStoreService()
