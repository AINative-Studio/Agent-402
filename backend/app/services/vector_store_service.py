"""
Vector storage service with namespace isolation.

Implements Issue #17: Namespace scoping for vector storage and retrieval.

This service provides:
- Namespace-scoped vector storage
- Namespace-isolated vector retrieval
- Default namespace handling
- Cross-namespace isolation guarantees

Per PRD §6: Agent-scoped memory for multi-agent systems.
Per Epic 4 Story 2: Namespace scopes retrieval correctly.
"""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Default namespace constant
DEFAULT_NAMESPACE = "default"


class VectorStoreService:
    """
    Service for storing and retrieving vectors with namespace isolation.

    Issue #17 Requirements:
    - Vectors stored in one namespace MUST NOT appear in another namespace
    - Default namespace MUST be isolated from named namespaces
    - Namespace parameter properly scopes both storage and retrieval
    - Namespace validation and filtering enforced at storage layer

    Storage Structure:
    - Vectors are indexed by: project_id -> namespace -> vector_id
    - Each namespace is completely isolated
    - Default namespace ("default") is a first-class namespace
    """

    def __init__(self):
        """Initialize the vector store service."""
        # In-memory storage for MVP: project_id -> namespace -> vector_id -> vector_data
        self._vectors: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        logger.info("VectorStoreService initialized")

    def _validate_namespace(self, namespace: Optional[str] = None) -> str:
        """
        Validate and normalize namespace parameter.

        Args:
            namespace: Optional namespace string

        Returns:
            str: Validated namespace (defaults to DEFAULT_NAMESPACE if None)

        Raises:
            ValueError: If namespace contains invalid characters
        """
        if namespace is None:
            return DEFAULT_NAMESPACE

        # Namespace validation rules
        if not isinstance(namespace, str):
            raise ValueError("Namespace must be a string")

        if not namespace.strip():
            raise ValueError("Namespace cannot be empty or whitespace")

        # Allow alphanumeric, hyphens, underscores, and dots
        # Prevent path traversal and injection attacks
        if not all(c.isalnum() or c in ['-', '_', '.'] for c in namespace):
            raise ValueError(
                "Namespace can only contain alphanumeric characters, hyphens, underscores, and dots"
            )

        if len(namespace) > 128:
            raise ValueError("Namespace cannot exceed 128 characters")

        return namespace

    def _ensure_project_namespace(self, project_id: str, namespace: str) -> None:
        """
        Ensure the project and namespace exist in storage.

        Args:
            project_id: Project identifier
            namespace: Validated namespace
        """
        if project_id not in self._vectors:
            self._vectors[project_id] = {}

        if namespace not in self._vectors[project_id]:
            self._vectors[project_id][namespace] = {}

    def store_vector(
        self,
        project_id: str,
        user_id: str,
        text: str,
        embedding: List[float],
        model: str,
        dimensions: int,
        namespace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        vector_id: Optional[str] = None,
        upsert: bool = False
    ) -> Dict[str, Any]:
        """
        Store a vector in the specified namespace.

        Issue #17: Namespace isolation is enforced here.
        - Each vector is stored in a specific namespace
        - Vectors in different namespaces are completely isolated
        - Default namespace is used when namespace parameter is None

        Args:
            project_id: Project identifier
            user_id: User/agent identifier
            text: Original text that was embedded
            embedding: Generated embedding vector
            model: Model used for generation
            dimensions: Embedding dimensionality
            namespace: Optional namespace (defaults to "default")
            metadata: Optional additional metadata
            vector_id: Optional vector ID (generated if not provided)
            upsert: Whether to update existing vector with same ID

        Returns:
            Dictionary with storage confirmation and vector metadata

        Raises:
            ValueError: If namespace is invalid
            ValueError: If vector_id already exists and upsert=False
        """
        # Validate and normalize namespace
        validated_namespace = self._validate_namespace(namespace)

        # Ensure storage structure exists
        self._ensure_project_namespace(project_id, validated_namespace)

        # Generate or use provided vector_id
        if vector_id is None:
            vector_id = str(uuid.uuid4())

        # Check for existing vector
        namespace_vectors = self._vectors[project_id][validated_namespace]
        existing_vector = namespace_vectors.get(vector_id)

        if existing_vector and not upsert:
            raise ValueError(
                f"Vector with ID '{vector_id}' already exists in namespace '{validated_namespace}'. "
                f"Use upsert=True to update."
            )

        # Determine if this is a create or update operation
        is_update = existing_vector is not None
        created_at = existing_vector["created_at"] if is_update else datetime.utcnow().isoformat()

        # Store vector with all metadata
        vector_data = {
            "vector_id": vector_id,
            "project_id": project_id,
            "user_id": user_id,
            "namespace": validated_namespace,
            "text": text,
            "embedding": embedding,
            "model": model,
            "dimensions": dimensions,
            "metadata": metadata or {},
            "created_at": created_at,
            "updated_at": datetime.utcnow().isoformat()
        }

        # Store in namespace-scoped location
        namespace_vectors[vector_id] = vector_data

        logger.info(
            f"Stored vector in namespace '{validated_namespace}'",
            extra={
                "project_id": project_id,
                "namespace": validated_namespace,
                "vector_id": vector_id,
                "user_id": user_id,
                "dimensions": dimensions,
                "upsert": upsert
            }
        )

        return {
            "vector_id": vector_id,
            "namespace": validated_namespace,
            "stored": True,
            "created": not is_update,  # True if new vector created, False if updated
            "upsert": upsert,
            "dimensions": dimensions,
            "model": model,
            "created_at": vector_data["created_at"],
            "updated_at": vector_data["updated_at"]
        }

    def search_vectors(
        self,
        project_id: str,
        query_embedding: List[float],
        namespace: Optional[str] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the specified namespace.

        Issue #17: Namespace scoping is strictly enforced.
        - Only vectors from the specified namespace are searched
        - Vectors from other namespaces are completely invisible
        - Default namespace is searched when namespace parameter is None

        Args:
            project_id: Project identifier
            query_embedding: Query vector for similarity search
            namespace: Optional namespace to search (defaults to "default")
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            metadata_filter: Optional metadata filters
            user_id: Optional user filter

        Returns:
            List of similar vectors with scores, scoped to namespace

        Raises:
            ValueError: If namespace is invalid
        """
        # Validate and normalize namespace
        validated_namespace = self._validate_namespace(namespace)

        # Check if project and namespace exist
        if project_id not in self._vectors:
            logger.info(f"No vectors found for project {project_id}")
            return []

        if validated_namespace not in self._vectors[project_id]:
            logger.info(
                f"No vectors found in namespace '{validated_namespace}' for project {project_id}"
            )
            return []

        # Get vectors ONLY from the specified namespace
        namespace_vectors = self._vectors[project_id][validated_namespace]

        # Filter vectors by user_id if provided
        filtered_vectors = {}
        for vid, vdata in namespace_vectors.items():
            # Apply user filter if specified
            if user_id and vdata.get("user_id") != user_id:
                continue

            # Apply metadata filter if specified
            if metadata_filter:
                vector_metadata = vdata.get("metadata", {})
                if not all(
                    vector_metadata.get(k) == v
                    for k, v in metadata_filter.items()
                ):
                    continue

            filtered_vectors[vid] = vdata

        if not filtered_vectors:
            logger.info(
                f"No vectors match filters in namespace '{validated_namespace}'",
                extra={
                    "project_id": project_id,
                    "namespace": validated_namespace,
                    "user_id": user_id,
                    "metadata_filter": metadata_filter
                }
            )
            return []

        # Calculate cosine similarity for each vector
        results = []
        for vector_id, vector_data in filtered_vectors.items():
            embedding = vector_data["embedding"]
            similarity = self._cosine_similarity(query_embedding, embedding)

            if similarity >= similarity_threshold:
                results.append({
                    "vector_id": vector_id,
                    "namespace": validated_namespace,
                    "text": vector_data["text"],
                    "similarity": similarity,
                    "model": vector_data["model"],
                    "dimensions": vector_data["dimensions"],
                    "metadata": vector_data["metadata"],
                    "created_at": vector_data["created_at"]
                })

        # Sort by similarity descending and limit to top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:top_k]

        logger.info(
            f"Found {len(results)} vectors in namespace '{validated_namespace}'",
            extra={
                "project_id": project_id,
                "namespace": validated_namespace,
                "top_k": top_k,
                "threshold": similarity_threshold
            }
        )

        return results

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        similarity = dot_product / (magnitude1 * magnitude2)

        # Normalize to 0.0 to 1.0 range
        return max(0.0, min(1.0, (similarity + 1.0) / 2.0))

    def get_namespace_stats(
        self,
        project_id: str,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for a specific namespace.

        Args:
            project_id: Project identifier
            namespace: Optional namespace (defaults to "default")

        Returns:
            Dictionary with namespace statistics

        Raises:
            ValueError: If namespace is invalid
        """
        validated_namespace = self._validate_namespace(namespace)

        if project_id not in self._vectors:
            return {
                "namespace": validated_namespace,
                "vector_count": 0,
                "exists": False
            }

        if validated_namespace not in self._vectors[project_id]:
            return {
                "namespace": validated_namespace,
                "vector_count": 0,
                "exists": False
            }

        namespace_vectors = self._vectors[project_id][validated_namespace]

        return {
            "namespace": validated_namespace,
            "vector_count": len(namespace_vectors),
            "exists": True
        }

    def list_namespaces(self, project_id: str) -> List[str]:
        """
        List all namespaces in a project.

        Args:
            project_id: Project identifier

        Returns:
            List of namespace names
        """
        if project_id not in self._vectors:
            return []

        return list(self._vectors[project_id].keys())

    def get_vector(
        self,
        project_id: str,
        vector_id: str,
        namespace: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific vector by ID from a namespace.

        Args:
            project_id: Project identifier
            vector_id: Vector identifier
            namespace: Optional namespace (defaults to "default")

        Returns:
            Vector data or None if not found
        """
        validated_namespace = self._validate_namespace(namespace)

        if project_id not in self._vectors:
            return None

        if validated_namespace not in self._vectors[project_id]:
            return None

        return self._vectors[project_id][validated_namespace].get(vector_id)

    def clear_all_vectors(self):
        """
        Clear all vectors from storage.

        This method is primarily for testing purposes.
        """
        self._vectors.clear()
        logger.warning("All vectors cleared from storage")


# Singleton instance
vector_store_service = VectorStoreService()
