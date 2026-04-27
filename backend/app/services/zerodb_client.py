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

Mock mode: when no credentials are provided, CRUD operations are served
from an in-memory store instead of issuing HTTP requests. This keeps
workshop/local setups functional without ZeroDB credentials (closes #345).
"""
import os
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)


class _InMemoryStore:
    """Minimal in-memory backing for `ZeroDBClient` mock mode.

    Supports direct-equality filters and the `$eq`, `$gt`, `$gte`, `$lt`,
    `$lte` operators — enough for the workshop tutorials and current
    service-layer callers. Rows are keyed by a generated string `id`.
    """

    def __init__(self) -> None:
        self.tables: Dict[str, Dict[str, Any]] = {}
        self.rows: Dict[str, List[Dict[str, Any]]] = {}
        self.vectors: List[Dict[str, Any]] = []

    def _table(self, name: str) -> List[Dict[str, Any]]:
        return self.rows.setdefault(name, [])

    @staticmethod
    def _matches(row: Dict[str, Any], query: Dict[str, Any]) -> bool:
        for field, condition in query.items():
            value = row.get(field)
            if isinstance(condition, dict):
                for op, operand in condition.items():
                    if op == "$eq" and value != operand:
                        return False
                    if op == "$gte" and (value is None or value < operand):
                        return False
                    if op == "$lte" and (value is None or value > operand):
                        return False
                    if op == "$gt" and (value is None or value <= operand):
                        return False
                    if op == "$lt" and (value is None or value >= operand):
                        return False
            else:
                if value != condition:
                    return False
        return True

    def insert_row(self, table: str, row_data: Dict[str, Any]) -> Dict[str, Any]:
        rows = self._table(table)
        row_id = str(uuid.uuid4())
        row = {"id": row_id, "row_id": row_id, **row_data}
        rows.append(row)
        return {"success": True, "row_id": row_id, "row_data": row}

    def query_rows(
        self,
        table: str,
        filter_query: Optional[Dict[str, Any]],
        limit: int,
        skip: int,
    ) -> Dict[str, Any]:
        rows = self.rows.get(table, [])
        filtered = (
            [r for r in rows if self._matches(r, filter_query)]
            if filter_query
            else list(rows)
        )
        total = len(filtered)
        page = filtered[skip : skip + limit]
        return {"rows": page, "total": total}

    def list_rows(self, table: str, skip: int, limit: int) -> Dict[str, Any]:
        return self.query_rows(table, None, limit=limit, skip=skip)

    def _find_row(
        self, table: str, row_id: str
    ) -> Optional[Dict[str, Any]]:
        for row in self.rows.get(table, []):
            if str(row.get("id")) == str(row_id) or str(row.get("row_id")) == str(row_id):
                return row
        return None

    def get_row(self, table: str, row_id: str) -> Dict[str, Any]:
        row = self._find_row(table, row_id)
        if row is None:
            raise KeyError(f"Row {row_id} not found in table {table}")
        return {"row_id": row.get("id"), "row_data": row}

    def update_row(
        self, table: str, row_id: str, row_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        rows = self.rows.get(table)
        if not rows:
            raise KeyError(f"Table {table} not found")
        for i, row in enumerate(rows):
            if str(row.get("id")) == str(row_id) or str(row.get("row_id")) == str(row_id):
                stored_id = row.get("id")
                updated = {**row_data, "id": stored_id, "row_id": stored_id}
                rows[i] = updated
                return {"success": True, "row_id": stored_id, "row_data": updated}
        raise KeyError(f"Row {row_id} not found in table {table}")

    def delete_row(self, table: str, row_id: str) -> Dict[str, Any]:
        rows = self.rows.get(table)
        if not rows:
            raise KeyError(f"Table {table} not found")
        for i, row in enumerate(rows):
            if str(row.get("id")) == str(row_id) or str(row.get("row_id")) == str(row_id):
                stored_id = row.get("id")
                rows.pop(i)
                return {"success": True, "row_id": stored_id}
        raise KeyError(f"Row {row_id} not found in table {table}")

    def create_table(
        self, table_name: str, schema_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        meta = {
            "id": f"tbl_{uuid.uuid4().hex[:12]}",
            "table_name": table_name,
            "schema": schema_definition,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.tables[table_name] = meta
        self.rows.setdefault(table_name, [])
        return meta

    def list_tables(self) -> Dict[str, Any]:
        return {"tables": list(self.tables.values()), "total": len(self.tables)}

    def get_table(self, table_id: str) -> Dict[str, Any]:
        for meta in self.tables.values():
            if meta.get("id") == table_id or meta.get("table_name") == table_id:
                return meta
        raise KeyError(f"Table {table_id} not found")

    def delete_table(self, table_name: str) -> Dict[str, Any]:
        self.tables.pop(table_name, None)
        self.rows.pop(table_name, None)
        return {"success": True, "table_name": table_name}

    def upsert_vector(
        self,
        vector_embedding: List[float],
        document: str,
        namespace: str,
        vector_id: Optional[str],
        vector_metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        vid = vector_id or f"vec_{uuid.uuid4().hex[:16]}"
        record = {
            "vector_id": vid,
            "vector_embedding": vector_embedding,
            "document": document,
            "namespace": namespace,
            "metadata": vector_metadata or {},
        }
        for i, existing in enumerate(self.vectors):
            if existing.get("vector_id") == vid:
                self.vectors[i] = record
                return {"success": True, "vector_id": vid, "updated": True}
        self.vectors.append(record)
        return {"success": True, "vector_id": vid, "updated": False}

    def search_vectors(
        self,
        namespace: Optional[str],
        limit: int,
    ) -> Dict[str, Any]:
        pool = [
            v for v in self.vectors
            if namespace is None or v.get("namespace") == namespace
        ]
        matches = [
            {
                "vector_id": v["vector_id"],
                "document": v["document"],
                "metadata": v.get("metadata", {}),
                "score": 0.9,
            }
            for v in pool[:limit]
        ]
        return {"matches": matches, "count": len(matches)}

    def list_vectors(self, limit: int, offset: int) -> Dict[str, Any]:
        page = self.vectors[offset : offset + limit]
        return {"vectors": page, "total": len(self.vectors)}

    def vector_stats(self) -> Dict[str, Any]:
        return {"total_vectors": len(self.vectors)}


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
        self.base_url = base_url or os.getenv("ZERODB_BASE_URL", "https://api.ainative.studio/api/v1")

        # Allow client to work without credentials (will use mock storage)
        self._mock_mode = not (self.api_key and self.project_id)

        self._store: Optional[_InMemoryStore] = None
        if self._mock_mode:
            logger.warning("ZeroDBClient running in mock mode - credentials not provided")
            self.api_key = "mock_key"
            self.project_id = "mock_project"
            self._store = _InMemoryStore()

        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Construct base endpoint — production paths are /api/v1/projects/{id}/database
        self._db_base = f"{self.base_url}/projects/{self.project_id}/database"
        self._embed_base = f"{self.base_url}/projects/{self.project_id}/embeddings"

        if not self._mock_mode:
            logger.info(f"ZeroDBClient initialized for project {self.project_id}")
        else:
            logger.info("ZeroDBClient initialized in MOCK MODE")

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
        if self._mock_mode:
            return {
                "database_enabled": True,
                "project_id": self.project_id,
                "mock": True,
                "tables": len(self._store.tables),
                "vectors": len(self._store.vectors),
            }

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
        if self._mock_mode:
            return self._store.list_tables()

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

        if self._mock_mode:
            return self._store.create_table(table_name, schema_definition)

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
        if self._mock_mode:
            return self._store.get_table(table_id)

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
        if self._mock_mode:
            return self._store.delete_table(table_name)

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

        if self._mock_mode:
            return self._store.insert_row(table_name, row_data)

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

        if self._mock_mode:
            return self._store.list_rows(table_name, skip=skip, limit=limit)

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
        if self._mock_mode:
            return self._store.get_row(table_name, row_id)

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

        if self._mock_mode:
            return self._store.update_row(table_name, row_id, row_data)

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
        if self._mock_mode:
            return self._store.delete_row(table_name, row_id)

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

        if self._mock_mode:
            return self._store.query_rows(
                table_name, filter, limit=limit, skip=skip
            )

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

        if self._mock_mode:
            return self._store.upsert_vector(
                vector_embedding=vector_embedding,
                document=document,
                namespace=namespace,
                vector_id=vector_id,
                vector_metadata=vector_metadata,
            )

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

        if self._mock_mode:
            return self._store.search_vectors(namespace=namespace, limit=limit)

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

        if self._mock_mode:
            return self._store.list_vectors(limit=limit, offset=offset)

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
        if self._mock_mode:
            return self._store.vector_stats()

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
        if self._mock_mode:
            return [{"model": "BAAI/bge-small-en-v1.5", "dimensions": 384, "mock": True}]

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

        Note: ZeroDB API expects 'texts' (plural array).
        """
        payload = {
            "texts": texts,
            "model": model
        }

        if self._mock_mode:
            try:
                from app.core.config import SUPPORTED_MODELS, DEFAULT_EMBEDDING_DIMENSIONS
                dims = SUPPORTED_MODELS.get(model, DEFAULT_EMBEDDING_DIMENSIONS)
            except Exception:
                dims = 384
            return {
                "embeddings": [[0.1] * dims for _ in texts],
                "model": model,
                "dimensions": dims,
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

        Note: ZeroDB API expects 'texts' (plural array), not 'documents'.
        """
        payload = {
            "texts": texts,
            "namespace": namespace,
            "model": model
        }
        if metadata:
            payload["metadata"] = metadata

        if self._mock_mode:
            vector_ids: List[str] = []
            for i, text in enumerate(texts):
                text_meta = metadata[i] if metadata and i < len(metadata) else {}
                stored = self._store.upsert_vector(
                    vector_embedding=[0.0] * 384,
                    document=text,
                    namespace=namespace,
                    vector_id=None,
                    vector_metadata=text_meta,
                )
                vector_ids.append(stored["vector_id"])
            return {
                "success": True,
                "vector_ids": vector_ids,
                "count": len(vector_ids),
            }

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

        if self._mock_mode:
            return self._store.search_vectors(namespace=namespace, limit=top_k)

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
