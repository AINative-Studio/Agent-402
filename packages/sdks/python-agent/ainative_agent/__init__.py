"""
ainative-agent — Python SDK for the AINative platform.

Built by AINative Dev Team.
"""
from __future__ import annotations

from typing import Any

from .agents import AgentOperations, TaskOperations
from .client import AsyncHTTPClient
from .errors import (
    AINativeError,
    AuthError,
    DimensionError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from .files import FileOperations
from .memory import GraphOperations, MemoryOperations
from .types import (
    Agent,
    AgentConfig,
    FileRecord,
    GraphEdge,
    GraphEntity,
    GraphRAGResult,
    GraphTraversalResult,
    Memory,
    MemorySearchResult,
    ReflectionResult,
    Task,
    TaskConfig,
    Vector,
    VectorMetadata,
    VectorSearchResult,
)
from .vectors import VectorOperations

__version__ = "0.1.0"
__all__ = [
    # Main entry-point
    "AINativeSDK",
    # Errors
    "AINativeError",
    "AuthError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "DimensionError",
    # Types
    "Agent",
    "AgentConfig",
    "Task",
    "TaskConfig",
    "Memory",
    "MemorySearchResult",
    "ReflectionResult",
    "GraphEntity",
    "GraphEdge",
    "GraphTraversalResult",
    "GraphRAGResult",
    "Vector",
    "VectorMetadata",
    "VectorSearchResult",
    "FileRecord",
    # Version
    "__version__",
]


class AINativeSDK:
    """
    Main entry-point for the AINative Python SDK.

    Usage::

        async with AINativeSDK(api_key="sk-...") as sdk:
            agent = await sdk.agents.create({"name": "bot", "role": "assistant"})

    Supports both API-key and JWT authentication.
    """

    def __init__(
        self,
        api_key: str | None = None,
        jwt: str | None = None,
        base_url: str = "https://api.ainative.studio/api/v1",
        timeout: float = 30.0,
        # Escape hatch: inject a pre-configured httpx client (useful in tests)
        _http_client: Any = None,
    ) -> None:
        self._http = AsyncHTTPClient(
            api_key=api_key,
            jwt=jwt,
            base_url=base_url,
            timeout=timeout,
            httpx_client=_http_client,
        )
        self.agents = AgentOperations(self._http)
        self.tasks = TaskOperations(self._http)
        self.memory = MemoryOperations(self._http)
        self.vectors = VectorOperations(self._http)
        self.files = FileOperations(self._http)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> "AINativeSDK":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()
