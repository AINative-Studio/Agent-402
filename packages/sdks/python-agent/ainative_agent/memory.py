"""
Memory and Knowledge-Graph operations for ainative-agent SDK.

Built by AINative Dev Team.
"""
from __future__ import annotations

from typing import Any

from .client import AsyncHTTPClient
from .types import (
    GraphEdge,
    GraphEntity,
    GraphRAGResult,
    GraphTraversalResult,
    Memory,
    MemorySearchResult,
    ReflectionResult,
)


class GraphOperations:
    """
    Knowledge-graph sub-operations accessible via sdk.memory.graph.
    """

    def __init__(self, client: AsyncHTTPClient) -> None:
        self._client = client

    async def add_entity(self, entity: dict[str, Any]) -> GraphEntity:
        """
        Add a node to the knowledge graph.

        Args:
            entity: Dict with at least 'id' and 'type' keys.

        Returns:
            The created GraphEntity.
        """
        data = await self._client.post("/memory/graph/entities", json=entity)
        return GraphEntity.model_validate(data)

    async def add_edge(self, edge: dict[str, Any]) -> GraphEdge:
        """
        Add a directed edge between two nodes.

        Args:
            edge: Dict with 'source', 'target', and 'relation' keys.

        Returns:
            The created GraphEdge.
        """
        data = await self._client.post("/memory/graph/edges", json=edge)
        return GraphEdge.model_validate(data)

    async def traverse(self, start_node: str, **options: Any) -> GraphTraversalResult:
        """
        Traverse the graph starting from a given node.

        Args:
            start_node: ID of the starting node.
            **options: Optional kwargs (depth, direction, limit, …).

        Returns:
            GraphTraversalResult with discovered nodes and edges.
        """
        params: dict[str, Any] = {"start_node": start_node, **options}
        data = await self._client.get("/memory/graph/traverse", params=params)
        return GraphTraversalResult.model_validate(data)

    async def graphrag(self, query: str, **options: Any) -> GraphRAGResult:
        """
        Execute a graph-augmented retrieval query.

        Args:
            query: Natural-language query.
            **options: Optional kwargs forwarded to the endpoint.

        Returns:
            GraphRAGResult with answer and supporting graph context.
        """
        payload: dict[str, Any] = {"query": query, **options}
        data = await self._client.post("/memory/graph/rag", json=payload)
        return GraphRAGResult.model_validate(data)


class MemoryOperations:
    """
    Memory persistence operations accessible via sdk.memory.

    Exposes a `graph` attribute for knowledge-graph sub-operations.
    """

    def __init__(self, client: AsyncHTTPClient) -> None:
        self._client = client
        self.graph = GraphOperations(client)

    async def remember(self, content: str, **options: Any) -> Memory:
        """
        Store a new memory entry.

        Args:
            content: Text content to remember.
            **options: Optional kwargs (namespace, agent_id, run_id, metadata, …).

        Returns:
            The created Memory.
        """
        payload: dict[str, Any] = {"content": content, **options}
        data = await self._client.post("/memory", json=payload)
        return Memory.model_validate(data)

    async def recall(self, query: str, **options: Any) -> list[MemorySearchResult]:
        """
        Semantic search over stored memories.

        Args:
            query: Query string for similarity search.
            **options: Optional kwargs (limit, namespace, agent_id, threshold, …).

        Returns:
            List of MemorySearchResult ordered by relevance.
        """
        payload: dict[str, Any] = {"query": query, **options}
        data = await self._client.post("/memory/recall", json=payload)
        if isinstance(data, list):
            return [MemorySearchResult.model_validate(item) for item in data]
        items = data.get("results", data.get("memories", []))
        return [MemorySearchResult.model_validate(item) for item in items]

    async def forget(self, memory_id: str) -> None:
        """
        Delete a memory entry by ID.

        Args:
            memory_id: The memory's unique identifier (mem_…).
        """
        await self._client.delete(f"/memory/{memory_id}")

    async def reflect(self, entity_id: str, **options: Any) -> ReflectionResult:
        """
        Generate a reflection / summary over all memories for an entity.

        Args:
            entity_id: The entity to reflect on (agent_id, user_id, etc.).
            **options: Optional kwargs forwarded to the endpoint.

        Returns:
            ReflectionResult with summary and related memories.
        """
        payload: dict[str, Any] = {"entity_id": entity_id, **options}
        data = await self._client.post("/memory/reflect", json=payload)
        return ReflectionResult.model_validate(data)
