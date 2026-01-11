"""
ZeroDB Vector Storage Service for Issue #16.

Implements integration with ZeroDB vector storage API for storing and retrieving embeddings.

Per PRD §6 (ZeroDB Integration):
- Store document text and embedding vectors in ZeroDB
- Support namespaces for logical organization
- Support metadata for document classification
- Use ZeroDB MCP tools for vector operations

DX Contract Compliance:
- Uses 384-dim default model (BAAI/bge-small-en-v1.5)
- Validates dimensions match model specifications
- Returns deterministic error codes
"""
import uuid
import time
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.core.errors import APIError
from app.core.embedding_models import get_model_dimensions


class ZeroDBVectorService:
    """
    Service for storing and retrieving vectors from ZeroDB.

    This service integrates with ZeroDB's vector storage capabilities
    via the MCP tools or direct API calls.

    For MVP: Uses in-memory storage simulation
    For Production: Will use actual ZeroDB MCP tools
    """

    def __init__(self):
        """Initialize the ZeroDB vector service."""
        # In-memory store for MVP (namespace -> vector_id -> vector_data)
        self._vector_store: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._zerodb_api_key = settings.zerodb_api_key
        self._zerodb_project_id = settings.zerodb_project_id
        self._zerodb_base_url = settings.zerodb_base_url

    def generate_vector_id(self) -> str:
        """
        Generate a unique vector ID.

        Per PRD §10 (Determinism):
        - IDs are unique and non-colliding
        - Format: vec_{uuid}

        Returns:
            str: Unique vector identifier
        """
        return f"vec_{uuid.uuid4().hex[:16]}"

    def store_vector(
        self,
        vector_embedding: List[float],
        document: str,
        model: str,
        namespace: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        vector_id: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Store a vector embedding in ZeroDB.

        Args:
            vector_embedding: The embedding vector to store
            document: Original document text
            model: Model used to generate embedding
            namespace: Logical namespace for organization
            metadata: Optional metadata dictionary
            vector_id: Optional vector ID (auto-generated if not provided)

        Returns:
            Tuple of (vector_id, created) where created is True if new vector

        Raises:
            APIError: If storage fails or validation errors occur
        """
        # Generate vector ID if not provided
        if not vector_id:
            vector_id = self.generate_vector_id()
            created = True
        else:
            # Check if vector already exists
            created = not self._vector_exists(vector_id, namespace)

        # Validate dimensions
        expected_dimensions = get_model_dimensions(model)
        if len(vector_embedding) != expected_dimensions:
            raise APIError(
                status_code=422,
                error_code="DIMENSION_MISMATCH",
                detail=f"Embedding dimensions ({len(vector_embedding)}) do not match model '{model}' expected dimensions ({expected_dimensions})"
            )

        # Prepare vector data
        vector_data = {
            "vector_id": vector_id,
            "embedding": vector_embedding,
            "document": document,
            "model": model,
            "dimensions": len(vector_embedding),
            "metadata": metadata or {},
            "namespace": namespace,
            "stored_at": time.time()
        }

        # Store in namespace
        if namespace not in self._vector_store:
            self._vector_store[namespace] = {}

        self._vector_store[namespace][vector_id] = vector_data

        return vector_id, created

    def batch_store_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> List[Tuple[str, bool]]:
        """
        Store multiple vectors in a batch operation.

        Args:
            vectors: List of vector data dictionaries containing:
                - vector_embedding: The embedding vector
                - document: Original document text
                - model: Model used to generate embedding
                - metadata: Optional metadata dictionary
                - vector_id: Optional vector ID
            namespace: Logical namespace for organization

        Returns:
            List of tuples (vector_id, created) for each stored vector

        Raises:
            APIError: If batch storage fails
        """
        results = []

        for vector_data in vectors:
            vector_id, created = self.store_vector(
                vector_embedding=vector_data["vector_embedding"],
                document=vector_data["document"],
                model=vector_data["model"],
                namespace=namespace,
                metadata=vector_data.get("metadata"),
                vector_id=vector_data.get("vector_id")
            )
            results.append((vector_id, created))

        return results

    def get_vector(
        self,
        vector_id: str,
        namespace: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a vector by ID from a namespace.

        Args:
            vector_id: The vector identifier
            namespace: The namespace to search in

        Returns:
            Vector data dictionary or None if not found
        """
        if namespace not in self._vector_store:
            return None

        return self._vector_store[namespace].get(vector_id)

    def list_vectors(
        self,
        namespace: str = "default",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List vectors in a namespace.

        Args:
            namespace: The namespace to list from
            limit: Maximum number of vectors to return
            offset: Offset for pagination

        Returns:
            List of vector data dictionaries
        """
        if namespace not in self._vector_store:
            return []

        all_vectors = list(self._vector_store[namespace].values())
        return all_vectors[offset:offset + limit]

    def delete_vector(
        self,
        vector_id: str,
        namespace: str = "default"
    ) -> bool:
        """
        Delete a vector from a namespace.

        Args:
            vector_id: The vector identifier
            namespace: The namespace containing the vector

        Returns:
            True if vector was deleted, False if not found
        """
        if namespace not in self._vector_store:
            return False

        if vector_id in self._vector_store[namespace]:
            del self._vector_store[namespace][vector_id]
            return True

        return False

    def _vector_exists(
        self,
        vector_id: str,
        namespace: str = "default"
    ) -> bool:
        """
        Check if a vector exists in a namespace.

        Args:
            vector_id: The vector identifier
            namespace: The namespace to check

        Returns:
            True if vector exists, False otherwise
        """
        if namespace not in self._vector_store:
            return False

        return vector_id in self._vector_store[namespace]

    def get_namespace_stats(
        self,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Get statistics for a namespace.

        Args:
            namespace: The namespace to get stats for

        Returns:
            Dictionary with namespace statistics
        """
        if namespace not in self._vector_store:
            return {
                "namespace": namespace,
                "vector_count": 0,
                "models_used": []
            }

        vectors = self._vector_store[namespace].values()
        models_used = list(set(v["model"] for v in vectors))

        return {
            "namespace": namespace,
            "vector_count": len(vectors),
            "models_used": models_used
        }


# Singleton instance
zerodb_vector_service = ZeroDBVectorService()
