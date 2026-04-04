"""
Pydantic models and TypedDicts for ainative-agent SDK shapes.

Built by AINative Dev Team.
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent types
# ---------------------------------------------------------------------------


class AgentConfig(BaseModel):
    """Configuration payload for creating or updating an agent."""

    name: str
    role: str = "assistant"
    description: Optional[str] = None
    scope: Literal["RUN", "SESSION", "PERSISTENT"] = "RUN"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    """Represents a persisted agent resource."""

    id: str
    did: Optional[str] = None
    name: str
    role: str
    description: Optional[str] = None
    scope: str = "RUN"
    project_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Task types
# ---------------------------------------------------------------------------


class TaskConfig(BaseModel):
    """Optional runtime configuration for a task."""

    max_steps: Optional[int] = None
    timeout_seconds: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """Represents a persisted task resource."""

    id: str
    description: str
    agent_types: List[str] = Field(default_factory=list)
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    config: TaskConfig = Field(default_factory=TaskConfig)
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Memory types
# ---------------------------------------------------------------------------


class Memory(BaseModel):
    """Represents a persisted memory entry."""

    id: str
    content: str
    namespace: str = "default"
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class MemorySearchResult(BaseModel):
    """A single result from a memory recall/search query."""

    memory: Memory
    score: float = 0.0


class ReflectionResult(BaseModel):
    """Result of a memory reflection operation on an entity."""

    entity_id: str
    summary: str
    memories: List[Memory] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Graph types
# ---------------------------------------------------------------------------


class GraphEntity(BaseModel):
    """A node in the knowledge graph."""

    id: str
    type: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """A directed edge between two nodes in the knowledge graph."""

    source: str
    target: str
    relation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphTraversalResult(BaseModel):
    """Result of a graph traversal operation."""

    start_node: str
    nodes: List[GraphEntity] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class GraphRAGResult(BaseModel):
    """Result of a graph-augmented retrieval query."""

    query: str
    answer: Optional[str] = None
    supporting_nodes: List[GraphEntity] = Field(default_factory=list)
    supporting_edges: List[GraphEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Vector types
# ---------------------------------------------------------------------------


class VectorMetadata(BaseModel):
    """Metadata attached to a vector embedding."""

    document: str = ""
    model: str = "BAAI/bge-small-en-v1.5"
    namespace: str = "default"
    extra: Dict[str, Any] = Field(default_factory=dict)


class Vector(BaseModel):
    """Represents a persisted vector resource."""

    id: str
    embedding: List[float]
    metadata: VectorMetadata
    created: bool = False


class VectorSearchResult(BaseModel):
    """A single result from a vector similarity search."""

    id: str
    score: float
    metadata: VectorMetadata


# ---------------------------------------------------------------------------
# File types
# ---------------------------------------------------------------------------


class FileRecord(BaseModel):
    """Represents a persisted file resource."""

    id: str
    filename: str
    size: int = 0
    content_type: str = "application/octet-stream"
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
