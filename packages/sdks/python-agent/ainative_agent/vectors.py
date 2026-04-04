"""
Vector embedding operations for ainative-agent SDK.

Built by AINative Dev Team.
"""
from __future__ import annotations

from typing import Any

from .client import AsyncHTTPClient
from .errors import DimensionError
from .types import Vector, VectorMetadata, VectorSearchResult

_SUPPORTED_DIMENSIONS = (384, 768, 1024, 1536)


class VectorOperations:
    """
    Vector embedding CRUD + similarity search.

    Validates embedding dimensions before any network call.
    """

    def __init__(self, client: AsyncHTTPClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def upsert(
        self,
        embedding: list[float],
        metadata: dict[str, Any],
        vector_id: str | None = None,
    ) -> Vector:
        """
        Upsert a vector embedding.

        Args:
            embedding: Float list whose length must be one of 384/768/1024/1536.
            metadata: Metadata dict (document, model, namespace, …).
            vector_id: Optional idempotency key.

        Returns:
            The upserted Vector.

        Raises:
            DimensionError: When the embedding length is not supported.
        """
        self._validate_dimension(embedding)
        payload: dict[str, Any] = {
            "embedding": embedding,
            "metadata": metadata,
        }
        if vector_id is not None:
            payload["vector_id"] = vector_id

        data = await self._client.post("/vectors", json=payload)
        return self._parse_vector(data)

    async def search(
        self,
        query: str,
        limit: int = 10,
        **options: Any,
    ) -> list[VectorSearchResult]:
        """
        Search for similar vectors.

        Args:
            query: Text query to embed and compare against.
            limit: Maximum number of results.
            **options: Additional options (namespace, threshold, …).

        Returns:
            List of VectorSearchResult ordered by similarity.
        """
        payload: dict[str, Any] = {"query": query, "limit": limit, **options}
        data = await self._client.post("/vectors/search", json=payload)
        if isinstance(data, list):
            return [VectorSearchResult.model_validate(item) for item in data]
        items = data.get("results", data.get("vectors", []))
        return [VectorSearchResult.model_validate(item) for item in items]

    async def delete(self, vector_id: str) -> None:
        """
        Delete a vector by ID.

        Args:
            vector_id: The vector's unique identifier (vec_…).
        """
        await self._client.delete(f"/vectors/{vector_id}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_dimension(embedding: list[float]) -> None:
        dim = len(embedding)
        if dim not in _SUPPORTED_DIMENSIONS:
            raise DimensionError(dim)

    @staticmethod
    def _parse_vector(data: dict[str, Any]) -> Vector:
        meta_raw = data.get("metadata", {})
        metadata = VectorMetadata.model_validate(meta_raw) if meta_raw else VectorMetadata()
        return Vector(
            id=data.get("id", data.get("vector_id", "")),
            embedding=data.get("embedding", []),
            metadata=metadata,
            created=data.get("created", False),
        )
