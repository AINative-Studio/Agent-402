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
"""
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.core.errors import APIError

logger = logging.getLogger(__name__)


class AgentMemoryService:
    """
    Service for storing and retrieving agent memory entries.

    This service provides the data layer for agent memory persistence.
    It integrates with ZeroDB for storage and supports multi-agent
    isolation through namespaces.

    For MVP: Uses in-memory storage simulation
    For Production: Will use actual ZeroDB MCP tools
    """

    def __init__(self):
        """Initialize the agent memory service."""
        # In-memory store for MVP
        # Structure: project_id -> namespace -> memory_id -> memory_data
        self._memory_store: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        logger.info("AgentMemoryService initialized")

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

    def store_memory(
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
        # Generate memory ID and timestamp
        memory_id = self.generate_memory_id()
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Prepare memory record
        memory_record = {
            "memory_id": memory_id,
            "agent_id": agent_id,
            "run_id": run_id,
            "memory_type": memory_type,
            "content": content,
            "metadata": metadata or {},
            "namespace": namespace,
            "timestamp": timestamp,
            "project_id": project_id
        }

        # Initialize project namespace if needed
        if project_id not in self._memory_store:
            self._memory_store[project_id] = {}

        if namespace not in self._memory_store[project_id]:
            self._memory_store[project_id][namespace] = {}

        # Store the memory
        self._memory_store[project_id][namespace][memory_id] = memory_record

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

    def get_memory(
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
            namespace: Optional namespace filter (searches all if not provided)

        Returns:
            Memory record dictionary or None if not found
        """
        if project_id not in self._memory_store:
            return None

        # If namespace specified, search only that namespace
        if namespace:
            if namespace not in self._memory_store[project_id]:
                return None
            return self._memory_store[project_id][namespace].get(memory_id)

        # Search all namespaces in the project
        for ns_memories in self._memory_store[project_id].values():
            if memory_id in ns_memories:
                return ns_memories[memory_id]

        return None

    def list_memories(
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
            namespace: Optional filter by namespace
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (memories list, total count, filters applied)
        """
        filters_applied = {}

        if project_id not in self._memory_store:
            return [], 0, filters_applied

        # Collect all memories from target namespaces
        all_memories = []

        if namespace:
            # Filter to specific namespace
            filters_applied["namespace"] = namespace
            if namespace in self._memory_store[project_id]:
                all_memories.extend(
                    self._memory_store[project_id][namespace].values()
                )
        else:
            # Collect from all namespaces
            for ns_memories in self._memory_store[project_id].values():
                all_memories.extend(ns_memories.values())

        # Apply filters
        if agent_id:
            filters_applied["agent_id"] = agent_id
            all_memories = [m for m in all_memories if m["agent_id"] == agent_id]

        if run_id:
            filters_applied["run_id"] = run_id
            all_memories = [m for m in all_memories if m["run_id"] == run_id]

        if memory_type:
            filters_applied["memory_type"] = memory_type
            all_memories = [m for m in all_memories if m["memory_type"] == memory_type]

        # Sort by timestamp descending (most recent first)
        all_memories.sort(key=lambda x: x["timestamp"], reverse=True)

        # Get total count before pagination
        total = len(all_memories)

        # Apply pagination
        paginated_memories = all_memories[offset:offset + limit]

        logger.info(
            f"Listed {len(paginated_memories)} memories for project {project_id}",
            extra={
                "project_id": project_id,
                "total": total,
                "limit": limit,
                "offset": offset,
                "filters": filters_applied
            }
        )

        return paginated_memories, total, filters_applied

    def delete_memory(
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
            namespace: Optional namespace (searches all if not provided)

        Returns:
            True if deleted, False if not found
        """
        if project_id not in self._memory_store:
            return False

        if namespace:
            if namespace not in self._memory_store[project_id]:
                return False
            if memory_id in self._memory_store[project_id][namespace]:
                del self._memory_store[project_id][namespace][memory_id]
                logger.info(f"Deleted memory {memory_id} from project {project_id}")
                return True
            return False

        # Search all namespaces
        for ns in list(self._memory_store[project_id].keys()):
            if memory_id in self._memory_store[project_id][ns]:
                del self._memory_store[project_id][ns][memory_id]
                logger.info(f"Deleted memory {memory_id} from project {project_id}")
                return True

        return False

    def get_namespace_stats(
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
        if project_id not in self._memory_store:
            return {
                "project_id": project_id,
                "namespace": namespace,
                "memory_count": 0,
                "agents": [],
                "memory_types": []
            }

        if namespace not in self._memory_store[project_id]:
            return {
                "project_id": project_id,
                "namespace": namespace,
                "memory_count": 0,
                "agents": [],
                "memory_types": []
            }

        memories = self._memory_store[project_id][namespace].values()
        agents = list(set(m["agent_id"] for m in memories))
        memory_types = list(set(m["memory_type"] for m in memories))

        return {
            "project_id": project_id,
            "namespace": namespace,
            "memory_count": len(memories),
            "agents": agents,
            "memory_types": memory_types
        }


# Singleton instance
agent_memory_service = AgentMemoryService()
