"""
ZeroDB Client for Agent402.
Implements real API calls to ZeroDB as documented in zerodb-endpoints-ocean.md.

Base URL: https://api.ainative.studio
Authentication: X-API-Key header

Endpoints implemented:
- Database Status: GET /v1/public/zerodb/{project_id}/database
- Tables: CRUD operations
- Rows: CRUD with query support
- Vectors: Upsert, search, list
- Embeddings: Generate, embed-and-store, semantic search
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class ZeroDBClient:
    """
    HTTP client for ZeroDB API.

    Usage:
        client = ZeroDBClient()
        await client.create_table("runs", {...})
        await client.insert_row("runs", {"run_id": "...", ...})
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize ZeroDB client.

        Args:
            api_key: ZeroDB API key (defaults to ZERODB_API_KEY env var)
            project_id: Project ID (defaults to ZERODB_PROJECT_ID env var)
            base_url: API base URL (defaults to ZERODB_BASE_URL env var)
        """
        self.api_key = api_key or os.getenv("ZERODB_API_KEY")
        self.project_id = project_id or os.getenv("ZERODB_PROJECT_ID")
        self.base_url = base_url or os.getenv("ZERODB_BASE_URL", "https://api.ainative.studio/v1/public")

        if not self.api_key:
            raise ValueError("ZERODB_API_KEY is required")
        if not self.project_id:
            raise ValueError("ZERODB_PROJECT_ID is required")

        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Construct base endpoint
        self._db_base = f"{self.base_url}/zerodb/{self.project_id}/database"
        self._embed_base = f"{self.base_url}/zerodb/{self.project_id}/embeddings"

        logger.info(f"ZeroDBClient initialized for project {self.project_id}")

    # =========================================================================
    # Database Status
    # =========================================================================

    async def get_database_status(self) -> Dict[str, Any]:
        """
        Get database status.

        GET /v1/public/zerodb/{project_id}/database

        Returns:
            Database status including enabled features and usage stats
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self._db_base,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # Table Management
    # =========================================================================

    async def list_tables(self) -> Dict[str, Any]:
        """
        List all tables in the project.

        GET /v1/public/zerodb/{project_id}/database/tables

        Returns:
            Paginated list of tables
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._db_base}/tables",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def create_table(
        self,
        table_name: str,
        schema_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new table with schema.

        POST /v1/public/zerodb/{project_id}/database/tables

        Args:
            table_name: Unique table name
            schema_definition: Schema with columns array

        Returns:
            Created table info
        """
        payload = {
            "table_name": table_name,
            "schema_definition": schema_definition
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._db_base}/tables",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def get_table(self, table_id: str) -> Dict[str, Any]:
        """
        Get table details.

        GET /v1/public/zerodb/{project_id}/database/tables/{table_id}
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._db_base}/tables/{table_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def delete_table(self, table_name: str) -> Dict[str, Any]:
        """
        Delete a table by name.

        DELETE /v1/public/zerodb/{project_id}/database/tables/{table_name}
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self._db_base}/tables/{table_name}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # Row Operations
    # =========================================================================

    async def insert_row(
        self,
        table_name: str,
        row_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Insert a row into a table.

        POST /v1/public/zerodb/{project_id}/database/tables/{table_name}/rows

        Args:
            table_name: Target table name
            row_data: Row data as key-value pairs

        Returns:
            Created row with row_id
        """
        payload = {"row_data": row_data}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._db_base}/tables/{table_name}/rows",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def list_rows(
        self,
        table_name: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        List rows in a table with pagination.

        GET /v1/public/zerodb/{project_id}/database/tables/{table_name}/rows
        """
        params = {"skip": skip, "limit": limit}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._db_base}/tables/{table_name}/rows",
                headers=self.headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def get_row(
        self,
        table_name: str,
        row_id: str
    ) -> Dict[str, Any]:
        """
        Get a single row by ID.

        GET /v1/public/zerodb/{project_id}/database/tables/{table_name}/rows/{row_id}
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._db_base}/tables/{table_name}/rows/{row_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def update_row(
        self,
        table_name: str,
        row_id: str,
        row_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a row.

        PUT /v1/public/zerodb/{project_id}/database/tables/{table_name}/rows/{row_id}
        """
        payload = {"row_data": row_data}

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self._db_base}/tables/{table_name}/rows/{row_id}",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def delete_row(
        self,
        table_name: str,
        row_id: str
    ) -> Dict[str, Any]:
        """
        Delete a row.

        DELETE /v1/public/zerodb/{project_id}/database/tables/{table_name}/rows/{row_id}
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self._db_base}/tables/{table_name}/rows/{row_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def query_rows(
        self,
        table_name: str,
        filter: Dict[str, Any],
        limit: int = 100,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Query rows with MongoDB-style filter.

        POST /v1/public/zerodb/{project_id}/database/tables/{table_name}/query
        """
        payload = {
            "filter": filter,
            "limit": limit,
            "skip": skip
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._db_base}/tables/{table_name}/query",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # Vector Operations
    # =========================================================================

    async def upsert_vector(
        self,
        vector_embedding: List[float],
        document: str,
        namespace: str = "default",
        vector_id: Optional[str] = None,
        vector_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upsert a vector embedding.

        POST /v1/public/zerodb/{project_id}/database/vectors/upsert
        """
        payload = {
            "vector_embedding": vector_embedding,
            "document": document,
            "namespace": namespace
        }
        if vector_id:
            payload["vector_id"] = vector_id
        if vector_metadata:
            payload["vector_metadata"] = vector_metadata

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._db_base}/vectors/upsert",
                headers=self.headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

    async def search_vectors(
        self,
        query_vector: List[float],
        limit: int = 10,
        namespace: Optional[str] = None,
        threshold: float = 0.7,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search vectors by similarity.

        POST /v1/public/zerodb/{project_id}/database/vectors/search
        """
        payload = {
            "query_vector": query_vector,
            "limit": limit,
            "threshold": threshold
        }
        if namespace:
            payload["namespace"] = namespace
        if metadata_filter:
            payload["metadata_filter"] = metadata_filter

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._db_base}/vectors/search",
                headers=self.headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

    async def list_vectors(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List vectors with pagination.

        GET /v1/public/zerodb/{project_id}/database/vectors
        """
        params = {"limit": limit, "offset": offset}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._db_base}/vectors",
                headers=self.headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def get_vector_stats(self) -> Dict[str, Any]:
        """
        Get vector statistics.

        GET /v1/public/zerodb/{project_id}/database/vectors/stats
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._db_base}/vectors/stats",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # Embeddings Operations
    # =========================================================================

    async def list_embedding_models(self) -> List[Dict[str, Any]]:
        """
        List available embedding models.

        GET /v1/public/zerodb/{project_id}/embeddings/models
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._embed_base}/models",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def generate_embeddings(
        self,
        texts: List[str],
        model: str = "BAAI/bge-small-en-v1.5"
    ) -> Dict[str, Any]:
        """
        Generate embeddings for texts.

        POST /v1/public/zerodb/{project_id}/embeddings/generate
        """
        payload = {
            "texts": texts,
            "model": model
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._embed_base}/generate",
                headers=self.headers,
                json=payload,
                timeout=120.0  # Embeddings can take time
            )
            response.raise_for_status()
            return response.json()

    async def embed_and_store(
        self,
        texts: List[str],
        namespace: str = "default",
        metadata: Optional[List[Dict[str, Any]]] = None,
        model: str = "BAAI/bge-small-en-v1.5"
    ) -> Dict[str, Any]:
        """
        Generate embeddings and store in one call.

        POST /v1/public/zerodb/{project_id}/embeddings/embed-and-store
        """
        payload = {
            "texts": texts,
            "namespace": namespace,
            "model": model
        }
        if metadata:
            payload["metadata"] = metadata

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._embed_base}/embed-and-store",
                headers=self.headers,
                json=payload,
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        namespace: str = "default",
        model: str = "BAAI/bge-small-en-v1.5"
    ) -> Dict[str, Any]:
        """
        Search using text query (auto-embeds).

        POST /v1/public/zerodb/{project_id}/embeddings/search
        """
        payload = {
            "query": query,
            "top_k": top_k,
            "namespace": namespace,
            "model": model
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._embed_base}/search",
                headers=self.headers,
                json=payload,
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()


# Singleton instance
_client: Optional[ZeroDBClient] = None


def get_zerodb_client() -> ZeroDBClient:
    """Get or create the ZeroDB client singleton."""
    global _client
    if _client is None:
        _client = ZeroDBClient()
    return _client


async def init_zerodb_client() -> ZeroDBClient:
    """Initialize and verify ZeroDB connection."""
    client = get_zerodb_client()
    status = await client.get_database_status()
    logger.info(f"ZeroDB connected: database_enabled={status.get('database_enabled')}")
    return client
