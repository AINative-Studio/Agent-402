"""
Agent Memory Service for persisting agent decisions and context.
Implements Epic 12 Issue 2: Agent memory persistence.

Per PRD Section 6 (ZeroDB Integration):
- Store agent decisions in agent_memory collection
- Support namespace scoping for multi-agent isolation
- Enable retrieval with filtering by agent_id, run_id

Service Responsibilities:
- Generate unique memory IDs
- Store memory entries with proper timestamps
- Retrieve memories with filtering and pagination
- Support namespace isolation
- Semantic search over agent memories
"""
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import httpx
from app.core.errors import APIError
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

# Constants
TABLE_NAME = "agent_memory"
EMBEDDING_NAMESPACE = "agent_memory"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class AgentMemoryService:
    """
    Service for storing and retrieving agent memory entries.

    This service provides the data layer for agent memory persistence.
    It integrates with ZeroDB for storage and supports multi-agent
    isolation through namespaces.

    Uses ZeroDB API for:
    - Row storage in agent_memory table
    - Semantic search via embeddings endpoints
    """

    def __init__(self):
        """Initialize the agent memory service."""
        self._client = None

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client
        logger.info("AgentMemoryService initialized")

    def _get_client(self):
        """Get ZeroDB client lazily to avoid initialization issues."""
        if self._client is None:
            self._client = None

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client
        return self._client

    def generate_memory_id(self) -> str:
        """
        Generate a unique memory ID.

        Per PRD Section 10 (Determinism):
        - IDs are unique and non-colliding
        - Format: mem_{uuid}

        Returns:
            str: Unique memory identifier
        """
        return f"mem_{uuid.uuid4().hex[:16]}"

    async def store_memory(
        self,
        project_id: str,
        agent_id: str,
        run_id: str,
        memory_type: str,
        content: str,
        namespace: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store an agent memory entry.

        Args:
            project_id: Project identifier
            agent_id: Agent identifier
            run_id: Execution run identifier
            memory_type: Type of memory (decision, context, state, etc.)
            content: Memory content
            namespace: Namespace for isolation
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with stored memory details

        Raises:
            APIError: If storage fails
        """
        client = self._get_client()
        memory_id = self.generate_memory_id()
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Prepare row data for agent_memory table
        row_data = {
            "memory_id": memory_id,
            "run_id": run_id,
            "project_id": project_id,
            "agent_id": agent_id,
            "memory_type": memory_type,
            "content": content,
            "metadata": metadata or {},
            "created_at": timestamp,
            "updated_at": timestamp
        }

        try:
            # Insert row into agent_memory table
            result = await client.insert_row(TABLE_NAME, row_data)

            # Also store embedding for semantic search
            embedding_id = None
            try:
                embed_result = await client.embed_and_store(
                    texts=[content],
                    namespace=f"{EMBEDDING_NAMESPACE}_{namespace}",
                    metadata=[{
                        "memory_id": memory_id,
                        "agent_id": agent_id,
                        "run_id": run_id,
                        "project_id": project_id,
                        "memory_type": memory_type
                    }],
                    model=EMBEDDING_MODEL
                )
                # Extract embedding ID if available
                if embed_result.get("vector_ids"):
                    embedding_id = embed_result["vector_ids"][0]
            except Exception as embed_error:
                # Log but don't fail - embedding is supplementary
                logger.warning(
                    f"Failed to store embedding for memory {memory_id}: {embed_error}"
                )

            # Build response record
            memory_record = {
                "memory_id": memory_id,
                "agent_id": agent_id,
                "run_id": run_id,
                "memory_type": memory_type,
                "content": content,
                "metadata": metadata or {},
                "namespace": namespace,
                "timestamp": timestamp,
                "project_id": project_id,
                "embedding_id": embedding_id
            }

            logger.info(
                f"Stored agent memory for agent {agent_id} in project {project_id}",
                extra={
                    "memory_id": memory_id,
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "memory_type": memory_type,
                    "namespace": namespace,
                    "project_id": project_id
                }
            )

            return memory_record

        except httpx.HTTPStatusError as e:
            logger.error(f"ZeroDB API error storing memory: {e}")
            raise APIError(
                message=f"Failed to store agent memory: {str(e)}",
                status_code=502,
                error_code="ZERODB_ERROR"
            )
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise APIError(
                message=f"Failed to store agent memory: {str(e)}",
                status_code=500,
                error_code="MEMORY_STORE_ERROR"
            )

    async def get_memory(
        self,
        project_id: str,
        memory_id: str,
        namespace: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single memory entry by ID.

        Args:
            project_id: Project identifier
            memory_id: Memory entry identifier
            namespace: Optional namespace filter (not used in DB query, kept for interface)

        Returns:
            Memory record dictionary or None if not found
        """
        client = self._get_client()

        try:
            # Query by memory_id and project_id
            filter_query = {
                "memory_id": {"$eq": memory_id},
                "project_id": {"$eq": project_id}
            }

            result = await client.query_rows(TABLE_NAME, filter_query, limit=1)

            rows = result.get("rows", [])
            if not rows:
                return None

            row = rows[0]
            # Map DB row to memory record format
            return self._row_to_memory_record(row, namespace)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"ZeroDB API error getting memory: {e}")
            raise APIError(
                message=f"Failed to retrieve memory: {str(e)}",
                status_code=502,
                error_code="ZERODB_ERROR"
            )
        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            return None

    async def list_memories(
        self,
        project_id: str,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        namespace: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """
        List agent memories with optional filtering.

        Args:
            project_id: Project identifier
            agent_id: Optional filter by agent ID
            run_id: Optional filter by run ID
            memory_type: Optional filter by memory type
            namespace: Optional filter by namespace (stored in metadata)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (memories list, total count, filters applied)
        """
        client = self._get_client()
        filters_applied = {}

        # Build MongoDB-style filter
        filter_query: Dict[str, Any] = {
            "project_id": {"$eq": project_id}
        }

        if agent_id:
            filter_query["agent_id"] = {"$eq": agent_id}
            filters_applied["agent_id"] = agent_id

        if run_id:
            filter_query["run_id"] = {"$eq": run_id}
            filters_applied["run_id"] = run_id

        if memory_type:
            filter_query["memory_type"] = {"$eq": memory_type}
            filters_applied["memory_type"] = memory_type

        try:
            # Query rows with filter
            result = await client.query_rows(
                TABLE_NAME,
                filter_query,
                limit=limit,
                skip=offset
            )

            rows = result.get("rows", [])
            total = result.get("total", len(rows))

            # Convert rows to memory records
            memories = [
                self._row_to_memory_record(row, namespace)
                for row in rows
            ]

            # Sort by created_at descending (most recent first)
            memories.sort(
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )

            logger.info(
                f"Listed {len(memories)} memories for project {project_id}",
                extra={
                    "project_id": project_id,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "filters": filters_applied
                }
            )

            return memories, total, filters_applied

        except httpx.HTTPStatusError as e:
            logger.error(f"ZeroDB API error listing memories: {e}")
            raise APIError(
                message=f"Failed to list memories: {str(e)}",
                status_code=502,
                error_code="ZERODB_ERROR"
            )
        except Exception as e:
            logger.error(f"Error listing memories: {e}")
            return [], 0, filters_applied

    async def delete_memory(
        self,
        project_id: str,
        memory_id: str,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete a memory entry.

        Args:
            project_id: Project identifier
            memory_id: Memory entry identifier
            namespace: Optional namespace (not used, kept for interface)

        Returns:
            True if deleted, False if not found
        """
        client = self._get_client()

        try:
            # First get the memory to find the row_id
            filter_query = {
                "memory_id": {"$eq": memory_id},
                "project_id": {"$eq": project_id}
            }

            result = await client.query_rows(TABLE_NAME, filter_query, limit=1)
            rows = result.get("rows", [])

            if not rows:
                return False

            row = rows[0]
            row_id = row.get("id") or row.get("row_id")

            if not row_id:
                logger.warning(f"No row_id found for memory {memory_id}")
                return False

            # Delete the row
            await client.delete_row(TABLE_NAME, str(row_id))
            logger.info(f"Deleted memory {memory_id} from project {project_id}")
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            logger.error(f"ZeroDB API error deleting memory: {e}")
            raise APIError(
                message=f"Failed to delete memory: {str(e)}",
                status_code=502,
                error_code="ZERODB_ERROR"
            )
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False

    async def get_namespace_stats(
        self,
        project_id: str,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Get statistics for a namespace within a project.

        Args:
            project_id: Project identifier
            namespace: Namespace to get stats for

        Returns:
            Dictionary with namespace statistics
        """
        client = self._get_client()

        try:
            # Query all memories for the project
            filter_query = {
                "project_id": {"$eq": project_id}
            }

            result = await client.query_rows(TABLE_NAME, filter_query, limit=1000)
            rows = result.get("rows", [])

            if not rows:
                return {
                    "project_id": project_id,
                    "namespace": namespace,
                    "memory_count": 0,
                    "agents": [],
                    "memory_types": []
                }

            # Extract unique agents and memory types
            agents = list(set(row.get("agent_id") for row in rows if row.get("agent_id")))
            memory_types = list(set(row.get("memory_type") for row in rows if row.get("memory_type")))

            return {
                "project_id": project_id,
                "namespace": namespace,
                "memory_count": len(rows),
                "agents": agents,
                "memory_types": memory_types
            }

        except Exception as e:
            logger.error(f"Error getting namespace stats: {e}")
            return {
                "project_id": project_id,
                "namespace": namespace,
                "memory_count": 0,
                "agents": [],
                "memory_types": []
            }

    async def search_memories(
        self,
        project_id: str,
        query: str,
        namespace: str = "default",
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over agent memories.

        Args:
            project_id: Project identifier
            query: Search query text
            namespace: Namespace to search in
            top_k: Number of results to return

        Returns:
            List of matching memory records with similarity scores
        """
        client = self._get_client()

        try:
            # Use semantic search endpoint
            result = await client.semantic_search(
                query=query,
                top_k=top_k,
                namespace=f"{EMBEDDING_NAMESPACE}_{namespace}",
                model=EMBEDDING_MODEL
            )

            matches = result.get("matches", [])
            memories = []

            for match in matches:
                metadata = match.get("metadata", {})
                # Only include memories from this project
                if metadata.get("project_id") == project_id:
                    memory_id = metadata.get("memory_id")
                    if memory_id:
                        # Fetch full memory record
                        memory = await self.get_memory(project_id, memory_id, namespace)
                        if memory:
                            memory["similarity_score"] = match.get("score", 0.0)
                            memories.append(memory)

            logger.info(
                f"Semantic search found {len(memories)} memories for query in project {project_id}"
            )

            return memories

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    def _row_to_memory_record(
        self,
        row: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert a database row to a memory record format.

        Args:
            row: Database row dictionary
            namespace: Optional namespace to include

        Returns:
            Memory record dictionary
        """
        return {
            "memory_id": row.get("memory_id"),
            "agent_id": row.get("agent_id"),
            "run_id": row.get("run_id"),
            "memory_type": row.get("memory_type"),
            "content": row.get("content"),
            "metadata": row.get("metadata", {}),
            "namespace": namespace or "default",
            "timestamp": row.get("created_at"),
            "project_id": row.get("project_id"),
            "embedding_id": row.get("embedding_id")
        }


# Singleton instance
_agent_memory_service: Optional[AgentMemoryService] = None


def get_agent_memory_service() -> AgentMemoryService:
    """Get or create the AgentMemoryService singleton."""
    global _agent_memory_service
    if _agent_memory_service is None:
        _agent_memory_service = AgentMemoryService()
    return _agent_memory_service


# For backward compatibility
agent_memory_service = AgentMemoryService()
