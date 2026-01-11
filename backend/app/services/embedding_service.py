"""
Embedding service for generating and managing vector embeddings.
Implements Issue #12: Default 384-dim embeddings when model is omitted.

This service provides:
- Deterministic default model behavior (BAAI/bge-small-en-v1.5)
- Support for multiple embedding models
- Consistent dimension validation
- Mock implementation for MVP (will integrate with actual embedding libraries later)

Per PRD §10: Behavior must be deterministic and documented.
"""
import time
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    get_model_dimensions,
    is_model_supported,
    EMBEDDING_MODEL_SPECS
)
from app.core.errors import APIError


class EmbeddingService:
    """
    Service for generating and managing embeddings.

    Issue #12 Requirements:
    - When model parameter is omitted, use DEFAULT_EMBEDDING_MODEL
    - Default model must generate exactly 384 dimensions
    - Behavior must be deterministic and consistent
    - Response must indicate which model was used

    Issue #18 Requirements:
    - Support upsert parameter for vector storage
    - When upsert=true: Update existing vector if ID exists (idempotent)
    - When upsert=false: Create new vector or error if ID exists
    - Prevent duplicate vectors with same ID
    """

    def __init__(self):
        """Initialize the embedding service."""
        self._vector_store: Dict[str, Dict[str, Any]] = {}  # In-memory store for MVP

    def get_model_or_default(self, model: Optional[str] = None) -> str:
        """
        Get the model to use, applying default if not provided.

        Per Issue #12:
        - If model is None, return DEFAULT_EMBEDDING_MODEL
        - If model is provided, validate it's supported

        Args:
            model: Optional model name from request

        Returns:
            str: Model name to use (either provided or default)

        Raises:
            APIError: If provided model is not supported
        """
        if model is None:
            return DEFAULT_EMBEDDING_MODEL

        # Convert enum keys to string values for comparison
        model_names = {k.value if hasattr(k, 'value') else str(k): v for k, v in EMBEDDING_MODEL_SPECS.items()}

        if model not in model_names:
            supported = ", ".join(model_names.keys())
            raise APIError(
                status_code=404,
                error_code="MODEL_NOT_FOUND",
                detail=f"Model '{model}' not found. Supported models: {supported}"
            )

        return model

    def get_dimensions_for_model(self, model: str) -> int:
        """
        Get the dimension count for a given model.

        Args:
            model: Model name (must be in EMBEDDING_MODEL_SPECS)

        Returns:
            int: Number of dimensions for the model

        Raises:
            APIError: If model is not supported
        """
        try:
            return get_model_dimensions(model)
        except ValueError as e:
            raise APIError(
                status_code=404,
                error_code="MODEL_NOT_FOUND",
                detail=str(e)
            )

    def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Tuple[List[float], str, int, float]:
        """
        Generate an embedding for the given text.

        Issue #12 Implementation:
        - Applies default model when model parameter is None
        - Returns the actual model used (for determinism)
        - Generates exactly the correct number of dimensions for the model

        Args:
            text: Text to generate embedding for
            model: Optional model name (defaults to DEFAULT_EMBEDDING_MODEL)

        Returns:
            Tuple of (embedding, model_used, dimensions, processing_time_ms)

        Raises:
            APIError: If model is not supported
        """
        start_time = time.time()

        # Apply default model if not provided (Issue #12)
        model_used = self.get_model_or_default(model)
        dimensions = self.get_dimensions_for_model(model_used)

        # Generate deterministic mock embedding based on text
        # For MVP, we create a reproducible embedding using hash-based generation
        # In production, this would call an actual embedding model
        embedding = self._generate_mock_embedding(text, dimensions)

        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds as int

        return embedding, model_used, dimensions, processing_time

    def _generate_mock_embedding(self, text: str, dimensions: int) -> List[float]:
        """
        Generate a deterministic mock embedding for MVP.

        This creates a reproducible vector based on the text content.
        In production, this would be replaced with actual embedding model calls.

        Args:
            text: Input text
            dimensions: Number of dimensions to generate

        Returns:
            List of floats representing the embedding vector
        """
        # Create a deterministic hash-based seed
        text_hash = hashlib.sha256(text.encode('utf-8')).digest()

        # Generate deterministic pseudo-random values
        embedding = []
        for i in range(dimensions):
            # Use hash bytes in a rolling window to create values
            byte_index = i % len(text_hash)
            value = (text_hash[byte_index] / 255.0) * 2.0 - 1.0  # Normalize to [-1, 1]
            embedding.append(round(value, 6))

        return embedding

    def embed_and_store(
        self,
        text: str,
        model: Optional[str] = None,
        namespace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        vector_id: Optional[str] = None,
        upsert: bool = False,
        project_id: str = None,
        user_id: str = None
    ) -> Tuple[int, str, str, int, bool, int, str]:
        """
        Generate embedding and store it in the vector store.

        Issue #17 Implementation:
        - Supports namespace parameter for vector isolation
        - Vectors in different namespaces are completely isolated
        - Defaults to "default" namespace if not specified

        Issue #18 Implementation:
        - When upsert=true: Update existing vector if vector_id exists (idempotent)
        - When upsert=false: Create new vector or error if vector_id exists
        - Prevents duplicate vectors with same ID

        Issue #19 Implementation:
        - Returns vectors_stored count (always 1 for single text input)
        - Returns model used for embedding generation
        - Returns dimensions of the stored vector
        - Returns processing time in milliseconds

        Args:
            text: Text to generate embedding for
            model: Optional model name (defaults to DEFAULT_EMBEDDING_MODEL)
            namespace: Optional namespace for isolation (defaults to "default")
            metadata: Optional metadata to store with the vector
            vector_id: Optional vector ID (auto-generated if not provided)
            upsert: Whether to update existing vectors (default: False)
            project_id: Project identifier for scoping
            user_id: User/agent identifier

        Returns:
            Tuple of (vectors_stored, vector_id, model_used, dimensions, created, processing_time_ms, stored_at)

        Raises:
            APIError: If vector_id exists and upsert=false (VECTOR_ALREADY_EXISTS)
            APIError: If model is not supported
            APIError: If namespace is invalid
        """
        from app.services.vector_store_service import vector_store_service
        from datetime import datetime

        start_time = time.time()

        # Generate embedding
        embedding, model_used, dimensions, _ = self.generate_embedding(text, model)

        # Store vector using vector_store_service (Issue #17: with namespace support)
        try:
            storage_result = vector_store_service.store_vector(
                project_id=project_id,
                user_id=user_id,
                text=text,
                embedding=embedding,
                model=model_used,
                dimensions=dimensions,
                namespace=namespace,
                metadata=metadata,
                vector_id=vector_id,
                upsert=upsert
            )
        except ValueError as e:
            # Convert ValueError from vector_store_service to APIError
            if "already exists" in str(e):
                raise APIError(
                    status_code=409,
                    error_code="VECTOR_ALREADY_EXISTS",
                    detail=str(e)
                )
            elif "Namespace" in str(e):
                raise APIError(
                    status_code=422,
                    error_code="INVALID_NAMESPACE",
                    detail=str(e)
                )
            else:
                raise APIError(
                    status_code=400,
                    error_code="STORAGE_ERROR",
                    detail=str(e)
                )

        processing_time = int((time.time() - start_time) * 1000)

        # Issue #19: Return vectors_stored count (always 1 for single operation)
        vectors_stored = 1

        # Issue #18: Get created status from storage_result
        created = storage_result.get("created", True)

        return (
            vectors_stored,
            storage_result["vector_id"],
            model_used,
            dimensions,
            created,
            processing_time,
            storage_result["updated_at"]  # Use updated_at for stored_at timestamp
        )

    def get_vector(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a vector by ID.

        Args:
            vector_id: Vector identifier

        Returns:
            Vector record or None if not found
        """
        return self._vector_store.get(vector_id)

    def vector_exists(self, vector_id: str) -> bool:
        """
        Check if a vector ID exists in the store.

        Args:
            vector_id: Vector identifier

        Returns:
            True if vector exists, False otherwise
        """
        return vector_id in self._vector_store

    def clear_vectors(self):
        """
        Clear all vectors from the store.

        This method is primarily for testing purposes.
        """
        self._vector_store.clear()

    def batch_embed_and_store(
        self,
        documents: List[str],
        model: Optional[str] = None,
        metadata_list: Optional[List[Dict[str, Any]]] = None,
        namespace: str = "default",
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        upsert: bool = False,
        vector_ids: Optional[List[str]] = None
    ) -> Tuple[List[str], str, int, int, List[bool]]:
        """
        Generate embeddings for multiple documents and store them.

        Issue #16 Implementation:
        - Accept multiple documents and generate embeddings for each
        - Store all embeddings with their metadata
        - Support optional namespace for logical organization
        - Return vector IDs for all stored documents

        Issue #18 Implementation (PRD §10 Replayability):
        - When upsert=true and vector_id exists: UPDATE the existing vector
        - When upsert=false and vector_id exists: Raise VECTOR_ALREADY_EXISTS error
        - When upsert=true and vector_id doesn't exist: INSERT as new vector
        - Track and return which vectors were inserted vs updated
        - Ensure idempotent behavior for replay scenarios

        Args:
            documents: List of text documents to embed and store
            model: Optional model name (defaults to DEFAULT_EMBEDDING_MODEL)
            metadata_list: Optional list of metadata dicts (must match documents length)
            namespace: Logical namespace for organization
            project_id: Project identifier for scoping
            user_id: User/agent identifier
            upsert: Whether to update existing vectors (default: False)
            vector_ids: Optional list of custom vector IDs

        Returns:
            Tuple of (vector_ids, model_used, dimensions, processing_time_ms, created_flags)
            - created_flags: List of booleans (True=inserted, False=updated)

        Raises:
            APIError: If model is not supported
            APIError: If vector_id exists and upsert=false (VECTOR_ALREADY_EXISTS)
            ValueError: If metadata_list length doesn't match documents length
            ValueError: If vector_ids length doesn't match documents length
        """
        from app.services.vector_store_service import vector_store_service
        from app.core.errors import VectorAlreadyExistsError

        start_time = time.time()

        # Validate metadata_list length if provided
        if metadata_list is not None and len(metadata_list) != len(documents):
            raise ValueError(
                f"Metadata list length ({len(metadata_list)}) must match documents length ({len(documents)})"
            )

        # Validate vector_ids length if provided
        if vector_ids is not None and len(vector_ids) != len(documents):
            raise ValueError(
                f"vector_ids length ({len(vector_ids)}) must match documents length ({len(documents)})"
            )

        # Apply default model if not provided
        model_used = self.get_model_or_default(model)
        dimensions = self.get_dimensions_for_model(model_used)

        result_vector_ids = []
        created_flags = []  # Track whether each vector was inserted (True) or updated (False)

        # Process each document
        for idx, document in enumerate(documents):
            # Generate embedding for this document
            embedding, _, _, _ = self.generate_embedding(document, model_used)

            # Get vector_id for this document (provided or auto-generated)
            if vector_ids is not None:
                vector_id = vector_ids[idx]
            else:
                vector_id = f"vec_{uuid.uuid4().hex[:16]}"

            # Get metadata for this document if provided
            doc_metadata = metadata_list[idx] if metadata_list else {}

            # Store vector using vector_store_service (Issue #17: with namespace support)
            # Issue #18: Handle upsert behavior
            try:
                storage_result = vector_store_service.store_vector(
                    project_id=project_id or "default",
                    user_id=user_id or "system",
                    text=document,
                    embedding=embedding,
                    model=model_used,
                    dimensions=dimensions,
                    namespace=namespace,
                    metadata=doc_metadata,
                    vector_id=vector_id,
                    upsert=upsert
                )
                result_vector_ids.append(storage_result["vector_id"])
                created_flags.append(storage_result["created"])
            except ValueError as e:
                # Convert ValueError from vector_store_service to APIError
                if "already exists" in str(e):
                    raise VectorAlreadyExistsError(
                        vector_id=vector_id,
                        namespace=namespace
                    )
                else:
                    raise

        processing_time = int((time.time() - start_time) * 1000)

        return result_vector_ids, model_used, dimensions, processing_time, created_flags


# Singleton instance
embedding_service = EmbeddingService()
