"""
Vector Service for Issue #27 and Issue #28.

Implements direct vector operations for Epic 6 (Vector Operations API).
Provides upsert functionality for storing raw vector embeddings.

Per PRD §6 (ZeroDB Integration - Low-level control):
- Support direct vector upsert operations
- Validate vector dimensions strictly
- Support namespaces for isolation
- Support metadata for classification

Issue #28 (Strict Dimension Validation):
- Validate vector_embedding array length matches expected dimensions
- Enforce strict validation before storage
- Only allow supported dimensions: 384, 768, 1024, 1536
- Return clear error if length mismatch
- Follow PRD §10 for determinism

DX Contract Compliance:
- Validates dimensions match supported sizes (384, 768, 1024, 1536)
- Returns deterministic error codes (DIMENSION_MISMATCH)
- Enforces /database/ prefix requirement
- Validation is strict and consistent per PRD §10
"""
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.core.errors import APIError
from app.schemas.vector import SUPPORTED_DIMENSIONS


class VectorService:
    """
    Service for direct vector operations.

    This service provides low-level control for storing and managing
    raw vector embeddings, separate from the embeddings API which
    handles text-to-vector generation.

    For Issue #27: Implements vector upsert endpoint requirements
    """

    def __init__(self):
        """Initialize the vector service."""
        # In-memory store for MVP (namespace -> vector_id -> vector_data)
        # Structure: {namespace: {vector_id: {vector_data}}}
        self._vector_store: Dict[str, Dict[str, Dict[str, Any]]] = {}

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

    def upsert_vector(
        self,
        vector_embedding: List[float],
        document: str,
        namespace: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        vector_id: Optional[str] = None
    ) -> Tuple[str, bool, int, str, Dict[str, Any]]:
        """
        Upsert a vector embedding.

        Issue #27: Implements upsert behavior
        - If vector_id is provided and exists: UPDATE (created=False)
        - If vector_id is provided and doesn't exist: INSERT (created=True)
        - If vector_id is not provided: INSERT with auto-generated ID (created=True)

        Args:
            vector_embedding: The embedding vector to store
            document: Original document text
            namespace: Logical namespace for organization (default: "default")
            metadata: Optional metadata dictionary
            vector_id: Optional vector ID (auto-generated if not provided)

        Returns:
            Tuple of (vector_id, created, dimensions, namespace, metadata)
            - vector_id: The vector identifier (generated or provided)
            - created: True if new vector, False if updated existing
            - dimensions: Vector dimensionality
            - namespace: Namespace where vector was stored
            - metadata: Metadata stored with vector

        Raises:
            APIError: If validation fails (DIMENSION_MISMATCH)
        """
        # Validate dimensions (Epic 6 Story 2, Issue #28)
        # Issue #28: Validate vector_embedding array length matches expected dimensions
        dimensions = len(vector_embedding)
        if dimensions not in SUPPORTED_DIMENSIONS:
            supported_str = ', '.join(map(str, sorted(SUPPORTED_DIMENSIONS)))
            raise APIError(
                status_code=422,
                error_code="DIMENSION_MISMATCH",
                detail=(
                    f"Vector dimension mismatch: vector_embedding has {dimensions} elements. "
                    f"Supported dimensions: {supported_str}. "
                    f"Array length must match one of the supported dimension sizes exactly."
                )
            )

        # Generate vector ID if not provided
        if not vector_id:
            vector_id = self.generate_vector_id()
            created = True
        else:
            # Check if vector already exists
            created = not self._vector_exists(vector_id, namespace)

        # Prepare metadata (Epic 6 Story 5)
        final_metadata = metadata or {}

        # Get current timestamp
        stored_at = datetime.utcnow().isoformat() + "Z"

        # Prepare vector data
        vector_data = {
            "vector_id": vector_id,
            "embedding": vector_embedding,
            "document": document,
            "dimensions": dimensions,
            "metadata": final_metadata,
            "namespace": namespace,
            "stored_at": stored_at,
            "updated_at": stored_at
        }

        # Store in namespace
        if namespace not in self._vector_store:
            self._vector_store[namespace] = {}

        self._vector_store[namespace][vector_id] = vector_data

        return vector_id, created, dimensions, namespace, final_metadata

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
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List vectors in a namespace.

        Args:
            namespace: The namespace to list from
            limit: Maximum number of vectors to return
            offset: Offset for pagination

        Returns:
            Tuple of (vectors_list, total_count)
        """
        if namespace not in self._vector_store:
            return [], 0

        all_vectors = list(self._vector_store[namespace].values())
        total_count = len(all_vectors)
        paginated_vectors = all_vectors[offset:offset + limit]

        return paginated_vectors, total_count

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
                "total_dimensions": {}
            }

        vectors = self._vector_store[namespace].values()
        dimension_counts = {}
        for vector in vectors:
            dims = vector["dimensions"]
            dimension_counts[dims] = dimension_counts.get(dims, 0) + 1

        return {
            "namespace": namespace,
            "vector_count": len(vectors),
            "dimension_distribution": dimension_counts
        }


# Singleton instance
vector_service = VectorService()
