"""
Tests for ainative_agent.memory — MemoryOperations and GraphOperations.

Describes: remember, recall, forget, reflect, and knowledge-graph operations.

Built by AINative Dev Team.
"""
from __future__ import annotations

import pytest

from ainative_agent.errors import NotFoundError
from ainative_agent.types import (
    GraphEdge,
    GraphEntity,
    GraphRAGResult,
    GraphTraversalResult,
    Memory,
    MemorySearchResult,
    ReflectionResult,
)
from tests.conftest import make_response

# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

MEMORY_PAYLOAD = {
    "id": "mem_abc1234567890123",
    "content": "Important context",
    "namespace": "default",
    "agent_id": "agent_abc",
    "run_id": "run_xyz",
    "metadata": {},
    "created_at": "2024-01-01T00:00:00Z",
}

MEMORY_SEARCH_RESULT = {
    "memory": MEMORY_PAYLOAD,
    "score": 0.92,
}

REFLECTION_PAYLOAD = {
    "entity_id": "agent_abc",
    "summary": "This agent has been working on AI research.",
    "memories": [MEMORY_PAYLOAD],
}

ENTITY_PAYLOAD = {
    "id": "entity_001",
    "type": "person",
    "name": "Alice",
    "metadata": {},
}

EDGE_PAYLOAD = {
    "source": "entity_001",
    "target": "entity_002",
    "relation": "knows",
    "metadata": {},
}

TRAVERSAL_PAYLOAD = {
    "start_node": "entity_001",
    "nodes": [ENTITY_PAYLOAD],
    "edges": [EDGE_PAYLOAD],
}

GRAPHRAG_PAYLOAD = {
    "query": "Who knows Alice?",
    "answer": "Bob knows Alice.",
    "supporting_nodes": [ENTITY_PAYLOAD],
    "supporting_edges": [EDGE_PAYLOAD],
}


# ---------------------------------------------------------------------------
# describe: MemoryOperations.remember
# ---------------------------------------------------------------------------


class DescribeRemember:
    async def it_returns_memory_model_on_success(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=MEMORY_PAYLOAD)
        memory = await sdk.memory.remember("Important context")
        assert isinstance(memory, Memory)
        assert memory.id == "mem_abc1234567890123"
        assert memory.content == "Important context"

    async def it_posts_to_memory_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=MEMORY_PAYLOAD)
        await sdk.memory.remember("Important context")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["method"] == "POST"
        assert "/memory" in call.kwargs["url"]

    async def it_includes_content_in_payload(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=MEMORY_PAYLOAD)
        await sdk.memory.remember("test content")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["content"] == "test content"

    async def it_forwards_optional_kwargs_in_payload(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=MEMORY_PAYLOAD)
        await sdk.memory.remember("content", namespace="custom", agent_id="agent_abc")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["namespace"] == "custom"
        assert call.kwargs["json"]["agent_id"] == "agent_abc"


# ---------------------------------------------------------------------------
# describe: MemoryOperations.recall
# ---------------------------------------------------------------------------


class DescribeRecall:
    async def it_returns_list_of_memory_search_results(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body=[MEMORY_SEARCH_RESULT]
        )
        results = await sdk.memory.recall("AI research")
        assert len(results) == 1
        assert isinstance(results[0], MemorySearchResult)
        assert results[0].score == 0.92

    async def it_posts_query_to_recall_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        await sdk.memory.recall("query text")
        call = mock_httpx_client.request.call_args
        assert "/memory/recall" in call.kwargs["url"]
        assert call.kwargs["json"]["query"] == "query text"

    async def it_forwards_limit_option(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        await sdk.memory.recall("query", limit=5)
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["limit"] == 5

    async def it_returns_results_from_wrapped_response(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body={"results": [MEMORY_SEARCH_RESULT]}
        )
        results = await sdk.memory.recall("query")
        assert len(results) == 1

    async def it_returns_empty_list_when_no_results(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        results = await sdk.memory.recall("obscure query")
        assert results == []


# ---------------------------------------------------------------------------
# describe: MemoryOperations.forget
# ---------------------------------------------------------------------------


class DescribeForget:
    async def it_sends_delete_request(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(204, content=b"")
        await sdk.memory.forget("mem_abc1234567890123")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["method"] == "DELETE"
        assert "/memory/mem_abc1234567890123" in call.kwargs["url"]

    async def it_returns_none_on_success(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(204, content=b"")
        result = await sdk.memory.forget("mem_abc1234567890123")
        assert result is None

    async def it_raises_not_found_for_unknown_memory(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(404, text_body="Not found")
        with pytest.raises(NotFoundError):
            await sdk.memory.forget("mem_missing")


# ---------------------------------------------------------------------------
# describe: MemoryOperations.reflect
# ---------------------------------------------------------------------------


class DescribeReflect:
    async def it_returns_reflection_result(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body=REFLECTION_PAYLOAD
        )
        result = await sdk.memory.reflect("agent_abc")
        assert isinstance(result, ReflectionResult)
        assert result.entity_id == "agent_abc"
        assert "AI research" in result.summary

    async def it_posts_entity_id_to_reflect_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body=REFLECTION_PAYLOAD
        )
        await sdk.memory.reflect("agent_abc")
        call = mock_httpx_client.request.call_args
        assert "/memory/reflect" in call.kwargs["url"]
        assert call.kwargs["json"]["entity_id"] == "agent_abc"

    async def it_includes_memories_in_result(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body=REFLECTION_PAYLOAD
        )
        result = await sdk.memory.reflect("agent_abc")
        assert len(result.memories) == 1
        assert isinstance(result.memories[0], Memory)


# ---------------------------------------------------------------------------
# describe: GraphOperations.add_entity
# ---------------------------------------------------------------------------


class DescribeGraphAddEntity:
    async def it_returns_graph_entity_model(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            201, json_body=ENTITY_PAYLOAD
        )
        entity = await sdk.memory.graph.add_entity(
            {"id": "entity_001", "type": "person", "name": "Alice"}
        )
        assert isinstance(entity, GraphEntity)
        assert entity.id == "entity_001"
        assert entity.type == "person"

    async def it_posts_to_graph_entities_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=ENTITY_PAYLOAD)
        await sdk.memory.graph.add_entity({"id": "e1", "type": "concept"})
        call = mock_httpx_client.request.call_args
        assert "/memory/graph/entities" in call.kwargs["url"]
        assert call.kwargs["method"] == "POST"


# ---------------------------------------------------------------------------
# describe: GraphOperations.add_edge
# ---------------------------------------------------------------------------


class DescribeGraphAddEdge:
    async def it_returns_graph_edge_model(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=EDGE_PAYLOAD)
        edge = await sdk.memory.graph.add_edge(
            {"source": "entity_001", "target": "entity_002", "relation": "knows"}
        )
        assert isinstance(edge, GraphEdge)
        assert edge.source == "entity_001"
        assert edge.relation == "knows"

    async def it_posts_to_graph_edges_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=EDGE_PAYLOAD)
        await sdk.memory.graph.add_edge({"source": "e1", "target": "e2", "relation": "r"})
        call = mock_httpx_client.request.call_args
        assert "/memory/graph/edges" in call.kwargs["url"]


# ---------------------------------------------------------------------------
# describe: GraphOperations.traverse
# ---------------------------------------------------------------------------


class DescribeGraphTraverse:
    async def it_returns_traversal_result(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body=TRAVERSAL_PAYLOAD
        )
        result = await sdk.memory.graph.traverse("entity_001")
        assert isinstance(result, GraphTraversalResult)
        assert result.start_node == "entity_001"
        assert len(result.nodes) == 1

    async def it_gets_traverse_endpoint_with_start_node_param(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body=TRAVERSAL_PAYLOAD
        )
        await sdk.memory.graph.traverse("entity_001", depth=2)
        call = mock_httpx_client.request.call_args
        assert "/memory/graph/traverse" in call.kwargs["url"]
        assert call.kwargs["params"]["start_node"] == "entity_001"
        assert call.kwargs["params"]["depth"] == 2


# ---------------------------------------------------------------------------
# describe: GraphOperations.graphrag
# ---------------------------------------------------------------------------


class DescribeGraphRAG:
    async def it_returns_graphrag_result(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body=GRAPHRAG_PAYLOAD
        )
        result = await sdk.memory.graph.graphrag("Who knows Alice?")
        assert isinstance(result, GraphRAGResult)
        assert result.query == "Who knows Alice?"
        assert "Bob" in result.answer

    async def it_posts_query_to_rag_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body=GRAPHRAG_PAYLOAD
        )
        await sdk.memory.graph.graphrag("query")
        call = mock_httpx_client.request.call_args
        assert "/memory/graph/rag" in call.kwargs["url"]
        assert call.kwargs["json"]["query"] == "query"
