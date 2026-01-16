"""
Vector storage service with namespace isolation.
Uses ZeroDB API for persistent vector storage and semantic search.

Implements Issue #17: Namespace scoping for vector storage and retrieval.
Implements Issue #24: Metadata filtering for search results.

This service provides:
- Namespace-scoped vector storage via ZeroDB
- Namespace-isolated vector retrieval
- Default namespace handling
- Cross-namespace isolation guarantees
- Advanced metadata filtering (equals, contains, in, etc.)
- Real semantic search via ZeroDB

Per PRD Section 6: Agent-scoped memory for multi-agent systems.
Per Epic 4 Story 2: Namespace scopes retrieval correctly.
Per Epic 5 Story 4 (Issue #24): Filter search results by metadata.

Issue #17 Namespace Rules:
- Valid characters: a-z, A-Z, 0-9, underscore, hyphen
- Max length: 64 characters
- Cannot start with underscore or hyphen
- Cannot be empty if provided
- INVALID_NAMESPACE (422) for invalid format
"""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from app.services.metadata_filter import MetadataFilter

from app.core.namespace_validator import (
    validate_namespace,
    NamespaceValidationError,
    DEFAULT_NAMESPACE
)
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Service for storing and retrieving vectors with namespace isolation.

    Issue #17 Requirements:
    - Vectors stored in one namespace MUST NOT appear in another namespace
    - Default namespace MUST be isolated from named namespaces
    - Namespace parameter properly scopes both storage and retrieval
    - Namespace validation and filtering enforced at storage layer

    Issue #17 Namespace Rules:
    - Valid characters: a-z, A-Z, 0-9, underscore, hyphen
    - Max length: 64 characters
    - Cannot start with underscore or hyphen
    - Cannot be empty if provided

    Storage Structure:
    - Vectors are indexed by: project_id -> namespace -> vector_id
    - Each namespace is completely isolated
    - Default namespace ("default") is a first-class namespace
    """

    def __init__(self):
        """Initialize the vector store service with ZeroDB client."""
        # In-memory storage as fallback: project_id -> namespace -> vector_id -> vector_data
        self._vectors: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        self._zerodb_available = False
        try:
            self._zerodb_client = get_zerodb_client()
            self._zerodb_available = True
            logger.info("VectorStoreService initialized with ZeroDB client")
        except ValueError as e:
            logger.warning(f"ZeroDB client not available, using in-memory storage: {e}")
            self._zerodb_client = None

    def _validate_namespace(self, namespace: Optional[str] = None) -> str:
        """
        Validate and normalize namespace parameter using centralized validator.

        Issue #17: Uses centralized namespace_validator module for consistent
        validation across all API endpoints.

        Args:
            namespace: Optional namespace string

        Returns:
            str: Validated namespace (defaults to DEFAULT_NAMESPACE if None)

        Raises:
            ValueError: If namespace format is invalid per Issue #17 rules
        """
        try:
            return validate_namespace(namespace)
        except NamespaceValidationError as e:
            # Convert to ValueError for backward compatibility
            raise ValueError(e.message)

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

    async def store_vector(
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
        Store a vector in the specified namespace via ZeroDB.

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
            ValueError: If namespace is invalid per Issue #17 rules
            ValueError: If vector_id already exists and upsert=False
        """
        # Validate and normalize namespace using centralized validator
        validated_namespace = self._validate_namespace(namespace)

        # Generate or use provided vector_id
        if vector_id is None:
            vector_id = str(uuid.uuid4())

        # Try ZeroDB first if available
        if self._zerodb_available and self._zerodb_client:
            try:
                # Prepare metadata with context
                vector_metadata = metadata.copy() if metadata else {}
                vector_metadata["user_id"] = user_id
                vector_metadata["project_id"] = project_id
                vector_metadata["model"] = model
                vector_metadata["dimensions"] = dimensions

                # Store vector in ZeroDB
                result = await self._zerodb_client.upsert_vector(
                    vector_embedding=embedding,
                    document=text,
                    namespace=validated_namespace,
                    vector_id=vector_id,
                    vector_metadata=vector_metadata
                )

                created = result.get("created", True)
                updated_at = datetime.utcnow().isoformat()

                logger.info(
                    f"Stored vector in ZeroDB namespace '{validated_namespace}'",
                    extra={
                        "project_id": project_id,
                        "namespace": validated_namespace,
                        "vector_id": vector_id,
                        "dimensions": dimensions
                    }
                )

                return {
                    "vector_id": vector_id,
                    "namespace": validated_namespace,
                    "stored": True,
                    "created": created,
                    "upsert": upsert,
                    "dimensions": dimensions,
                    "model": model,
                    "created_at": updated_at if created else result.get("created_at", updated_at),
                    "updated_at": updated_at
                }

            except Exception as e:
                logger.warning(f"ZeroDB storage failed, falling back to local: {e}")
                # Fall through to local storage

        # Fallback: Local in-memory storage
        # Ensure storage structure exists
        self._ensure_project_namespace(project_id, validated_namespace)

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
            f"Stored vector in local namespace '{validated_namespace}'",
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

    async def search_vectors(
        self,
        project_id: str,
        query_embedding: List[float],
        namespace: Optional[str] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        include_metadata: bool = True,
        include_embeddings: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the specified namespace via ZeroDB.

        Issue #23 (Namespace Scoping): Namespace scoping is strictly enforced.
        - Only vectors from the specified namespace are searched
        - Vectors from other namespaces are completely invisible
        - Default namespace ("default") is searched when namespace parameter is None
        - If namespace doesn't exist, returns empty results (not an error)
        - Uses centralized namespace validator from Epic 4

        Issue #22: top_k limits results for predictable replay.
        - Results are sorted by similarity score (highest first)
        - Limited to top_k results (default: 10, min: 1, max: 100)
        - If fewer matches exist than top_k, all matches are returned

        Issue #24: Metadata filtering applied AFTER similarity search.
        - Supports common operations: equals, contains, in list, gt, gte, lt, lte, exists
        - Filters are applied to refine similarity results
        - Returns only vectors matching both similarity AND metadata criteria

        Issue #26: Conditional field inclusion for response optimization.
        - include_metadata: Controls whether metadata is included (default: True)
        - include_embeddings: Controls whether embeddings are included (default: False)
        - Reduces response size based on use case requirements

        Args:
            project_id: Project identifier
            query_embedding: Query vector for similarity search
            namespace: Optional namespace to search (defaults to "default")
            top_k: Maximum number of results to return (Issue #22: 1-100, default 10)
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            metadata_filter: Optional metadata filters (Issue #24)
                Examples:
                - Simple: {"agent_id": "agent_1", "source": "memory"}
                - Advanced: {"score": {"$gte": 0.8}, "tags": {"$in": ["fintech"]}}
            user_id: Optional user filter
            include_metadata: Whether to include metadata in results (Issue #26)
            include_embeddings: Whether to include embedding vectors in results (Issue #26)

        Returns:
            List of similar vectors with scores, scoped to namespace and filtered by metadata

        Raises:
            ValueError: If namespace format is invalid
            InvalidMetadataFilterError: If metadata_filter format is invalid (HTTP 422)
        """
        # Issue #24: Validate metadata filter format
        # Raises InvalidMetadataFilterError (422 INVALID_METADATA_FILTER) if invalid
        MetadataFilter.validate_filter(metadata_filter)

        # Validate and normalize namespace using centralized validator (Issue #17/23)
        validated_namespace = self._validate_namespace(namespace)

        # Try ZeroDB first if available
        if self._zerodb_available and self._zerodb_client:
            try:
                # Use ZeroDB vector search
                result = await self._zerodb_client.search_vectors(
                    query_vector=query_embedding,
                    limit=top_k,
                    namespace=validated_namespace,
                    threshold=similarity_threshold,
                    metadata_filter=metadata_filter
                )

                vectors = result.get("results", []) or result.get("vectors", [])

                # Transform ZeroDB results to our format
                results = []
                for vec in vectors:
                    item = {
                        "vector_id": vec.get("vector_id", vec.get("id", "")),
                        "namespace": validated_namespace,
                        "text": vec.get("document", vec.get("text", "")),
                        "similarity": vec.get("similarity", vec.get("score", 0.0)),
                        "model": vec.get("metadata", {}).get("model", ""),
                        "dimensions": vec.get("metadata", {}).get("dimensions", len(query_embedding)),
                        "created_at": vec.get("created_at", ""),
                    }

                    if include_metadata:
                        item["metadata"] = vec.get("metadata", {})
                    if include_embeddings:
                        item["embedding"] = vec.get("embedding", vec.get("vector", []))

                    results.append(item)

                logger.info(
                    f"Found {len(results)} vectors via ZeroDB in namespace '{validated_namespace}'",
                    extra={
                        "project_id": project_id,
                        "namespace": validated_namespace,
                        "top_k": top_k
                    }
                )

                return results

            except Exception as e:
                logger.warning(f"ZeroDB search failed, falling back to local: {e}")
                # Fall through to local search

        # Fallback: Local in-memory search
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

        # Filter vectors by user_id if provided (legacy filter)
        filtered_vectors = {}
        for vid, vdata in namespace_vectors.items():
            # Apply user filter if specified
            if user_id and vdata.get("user_id") != user_id:
                continue

            filtered_vectors[vid] = vdata

        if not filtered_vectors:
            logger.info(
                f"No vectors match user filter in namespace '{validated_namespace}'",
                extra={
                    "project_id": project_id,
                    "namespace": validated_namespace,
                    "user_id": user_id
                }
            )
            return []

        # Calculate cosine similarity for each vector
        # Issue #25: Apply similarity threshold first
        results = []
        for vector_id, vector_data in filtered_vectors.items():
            embedding = vector_data["embedding"]
            similarity = self._cosine_similarity(query_embedding, embedding)

            # Issue #25: Only include results >= similarity_threshold
            if similarity >= similarity_threshold:
                # Build result with ALL fields initially (for filtering)
                # Issue #26: Conditional inclusion happens AFTER filtering
                result = {
                    "vector_id": vector_id,
                    "namespace": validated_namespace,
                    "text": vector_data["text"],
                    "similarity": similarity,
                    "model": vector_data["model"],
                    "dimensions": vector_data["dimensions"],
                    "created_at": vector_data["created_at"],
                    "metadata": vector_data["metadata"],  # Always include for filtering
                    "embedding": embedding  # Always include initially
                }

                results.append(result)

        # Issue #25: Sort by similarity descending BEFORE metadata filtering and top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Issue #24: Apply metadata filters AFTER similarity search and sorting, BEFORE top_k
        # This ensures threshold is applied first, then metadata filters, then top_k limiting
        if metadata_filter:
            before_count = len(results)
            results = MetadataFilter.filter_results(results, metadata_filter)
            logger.info(
                f"Metadata filter reduced results from {before_count} to {len(results)}",
                extra={
                    "project_id": project_id,
                    "namespace": validated_namespace,
                    "filter": metadata_filter
                }
            )

        # Issue #22, #25: Apply top_k AFTER threshold and metadata filtering
        # This ensures we return the top K results that pass both threshold and filters
        results = results[:top_k]

        # Issue #26: Remove metadata and/or embeddings from results if not requested
        # This happens AFTER filtering so filters can access metadata
        for result in results:
            if not include_metadata:
                result.pop("metadata", None)
            if not include_embeddings:
                result.pop("embedding", None)

        logger.info(
            f"Found {len(results)} vectors in namespace '{validated_namespace}'",
            extra={
                "project_id": project_id,
                "namespace": validated_namespace,
                "top_k": top_k,
                "threshold": similarity_threshold,
                "metadata_filter_applied": metadata_filter is not None,
                "include_metadata": include_metadata,
                "include_embeddings": include_embeddings
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

    async def get_namespace_stats(
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
            ValueError: If namespace is invalid per Issue #17 rules
        """
        validated_namespace = self._validate_namespace(namespace)

        # Try ZeroDB first if available
        if self._zerodb_available and self._zerodb_client:
            try:
                result = await self._zerodb_client.get_vector_stats()
                return {
                    "namespace": validated_namespace,
                    "vector_count": result.get("total_vectors", 0),
                    "exists": True,
                    "storage_used_bytes": result.get("storage_used_bytes", 0)
                }
            except Exception as e:
                logger.warning(f"ZeroDB stats failed, using local: {e}")

        # Fallback: Local in-memory stats
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

    async def list_namespaces(self, project_id: str) -> List[str]:
        """
        List all namespaces in a project.

        Args:
            project_id: Project identifier

        Returns:
            List of namespace names
        """
        # ZeroDB doesn't have a direct list_namespaces API
        # Fall back to local storage
        if project_id not in self._vectors:
            return []

        return list(self._vectors[project_id].keys())

    async def get_vector(
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

        # ZeroDB doesn't have a direct get_vector by ID API
        # Fall back to local storage
        if project_id not in self._vectors:
            return None

        if validated_namespace not in self._vectors[project_id]:
            return None

        return self._vectors[project_id][validated_namespace].get(vector_id)

    async def clear_all_vectors(self):
        """
        Clear all vectors from storage.

        This method is primarily for testing purposes.
        """
        self._vectors.clear()
        logger.warning("All vectors cleared from local storage")


# Singleton instance
vector_store_service = VectorStoreService()
