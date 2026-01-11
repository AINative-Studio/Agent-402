"""
Mock ZeroDB Client for testing.
Provides in-memory data storage to avoid real API calls during testing.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


class MockZeroDBClient:
    """
    Mock ZeroDB client for testing.

    Provides in-memory storage and tracks all method calls for verification.
    Implements the same interface as the real ZeroDBClient.
    """

    def __init__(self):
        """Initialize the mock client with empty data structures."""
        # In-memory data storage: table_name -> list of rows
        self.data: Dict[str, List[Dict[str, Any]]] = {}

        # Call history for verification in tests
        self.call_history: List[Dict[str, Any]] = []

        # Vector storage
        self.vectors: List[Dict[str, Any]] = []

        # Auto-incrementing row IDs per table
        self._row_id_counters: Dict[str, int] = {}

    def _track_call(self, method: str, **kwargs):
        """Track a method call for verification."""
        self.call_history.append({
            "method": method,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **kwargs
        })

    def _get_next_row_id(self, table_name: str) -> int:
        """Get the next auto-incrementing ID for a table."""
        if table_name not in self._row_id_counters:
            self._row_id_counters[table_name] = 1
        current = self._row_id_counters[table_name]
        self._row_id_counters[table_name] += 1
        return current

    async def insert_row(
        self,
        table_name: str,
        row_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Insert a row into a table.

        Args:
            table_name: Target table name
            row_data: Row data as key-value pairs

        Returns:
            Created row with row_id
        """
        self._track_call("insert_row", table_name=table_name, row_data=row_data)

        # Initialize table if it doesn't exist
        if table_name not in self.data:
            self.data[table_name] = []

        # Generate row_id
        row_id = self._get_next_row_id(table_name)

        # Create row with row_id
        row = {
            "id": row_id,
            "row_id": row_id,
            **row_data
        }

        # Store row
        self.data[table_name].append(row)

        # Return success response
        return {
            "success": True,
            "row_id": row_id,
            "row_data": row
        }

    async def query_rows(
        self,
        table_name: str,
        filter: Dict[str, Any] = None,
        limit: int = 100,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Query rows from a table with filters.

        Args:
            table_name: Table name
            filter: MongoDB-style query filter
            limit: Maximum number of results
            skip: Pagination offset

        Returns:
            Query results with rows and total count
        """
        self._track_call(
            "query_rows",
            table_name=table_name,
            filter=filter,
            limit=limit,
            skip=skip
        )

        # Get all rows from table
        if table_name not in self.data:
            return {"rows": [], "total": 0}

        all_rows = self.data[table_name]

        # Apply filters
        filtered_rows = all_rows
        if filter:
            filtered_rows = self._apply_filter(all_rows, filter)

        # Apply pagination
        total = len(filtered_rows)
        paginated_rows = filtered_rows[skip:skip + limit]

        return {
            "rows": paginated_rows,
            "total": total
        }

    def _apply_filter(
        self,
        rows: List[Dict[str, Any]],
        filter_query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply MongoDB-style filter to rows.

        Supports:
        - Direct equality: {"field": "value"}
        - $eq operator: {"field": {"$eq": "value"}}
        - $gte, $lte operators for comparisons
        """
        result = []

        for row in rows:
            if self._row_matches_filter(row, filter_query):
                result.append(row)

        return result

    def _row_matches_filter(
        self,
        row: Dict[str, Any],
        filter_query: Dict[str, Any]
    ) -> bool:
        """Check if a row matches a filter query."""
        for field, condition in filter_query.items():
            if isinstance(condition, dict):
                # Handle operators
                for op, value in condition.items():
                    if op == "$eq":
                        if row.get(field) != value:
                            return False
                    elif op == "$gte":
                        if not (row.get(field) is not None and row.get(field) >= value):
                            return False
                    elif op == "$lte":
                        if not (row.get(field) is not None and row.get(field) <= value):
                            return False
                    elif op == "$gt":
                        if not (row.get(field) is not None and row.get(field) > value):
                            return False
                    elif op == "$lt":
                        if not (row.get(field) is not None and row.get(field) < value):
                            return False
            else:
                # Direct equality
                if row.get(field) != condition:
                    return False

        return True

    async def update_row(
        self,
        table_name: str,
        row_id: str,
        row_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a row by ID.

        Args:
            table_name: Table name
            row_id: Row ID to update
            row_data: New row data

        Returns:
            Updated row
        """
        self._track_call(
            "update_row",
            table_name=table_name,
            row_id=row_id,
            row_data=row_data
        )

        if table_name not in self.data:
            raise ValueError(f"Table {table_name} not found")

        # Find row by ID
        row_id_int = int(row_id) if isinstance(row_id, str) else row_id

        for i, row in enumerate(self.data[table_name]):
            if row.get("id") == row_id_int or row.get("row_id") == row_id_int:
                # Update row
                updated_row = {
                    "id": row_id_int,
                    "row_id": row_id_int,
                    **row_data
                }
                self.data[table_name][i] = updated_row

                return {
                    "success": True,
                    "row_id": row_id_int,
                    "row_data": updated_row
                }

        raise ValueError(f"Row {row_id} not found in table {table_name}")

    async def delete_row(
        self,
        table_name: str,
        row_id: str
    ) -> Dict[str, Any]:
        """
        Delete a row by ID.

        Args:
            table_name: Table name
            row_id: Row ID to delete

        Returns:
            Success response
        """
        self._track_call("delete_row", table_name=table_name, row_id=row_id)

        if table_name not in self.data:
            raise ValueError(f"Table {table_name} not found")

        # Find and remove row
        row_id_int = int(row_id) if isinstance(row_id, str) else row_id

        for i, row in enumerate(self.data[table_name]):
            if row.get("id") == row_id_int or row.get("row_id") == row_id_int:
                self.data[table_name].pop(i)
                return {"success": True, "row_id": row_id_int}

        raise ValueError(f"Row {row_id} not found in table {table_name}")

    async def list_rows(
        self,
        table_name: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        List rows in a table with pagination.

        Args:
            table_name: Table name
            skip: Pagination offset
            limit: Maximum number of results

        Returns:
            Paginated list of rows
        """
        return await self.query_rows(table_name, filter={}, skip=skip, limit=limit)

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

        Args:
            vector_embedding: Vector data
            document: Source document
            namespace: Vector namespace
            vector_id: Optional vector ID
            vector_metadata: Optional metadata

        Returns:
            Upsert response with vector_id
        """
        self._track_call(
            "upsert_vector",
            document=document,
            namespace=namespace,
            vector_id=vector_id
        )

        # Generate vector ID if not provided
        if not vector_id:
            vector_id = f"vec_{uuid.uuid4().hex[:16]}"

        # Store vector
        vector = {
            "vector_id": vector_id,
            "vector_embedding": vector_embedding,
            "document": document,
            "namespace": namespace,
            "metadata": vector_metadata or {}
        }

        # Check if vector exists and update, otherwise insert
        for i, v in enumerate(self.vectors):
            if v.get("vector_id") == vector_id:
                self.vectors[i] = vector
                return {"success": True, "vector_id": vector_id, "updated": True}

        self.vectors.append(vector)
        return {"success": True, "vector_id": vector_id, "updated": False}

    async def embed_and_store(
        self,
        texts: List[str],
        namespace: str = "default",
        metadata: Optional[List[Dict[str, Any]]] = None,
        model: str = "BAAI/bge-small-en-v1.5"
    ) -> Dict[str, Any]:
        """
        Generate embeddings and store in one call (mock).

        Args:
            texts: List of texts to embed
            namespace: Vector namespace
            metadata: Optional metadata for each text
            model: Embedding model name

        Returns:
            Response with vector IDs
        """
        self._track_call(
            "embed_and_store",
            texts=texts,
            namespace=namespace,
            model=model
        )

        vector_ids = []

        for i, text in enumerate(texts):
            # Create mock embedding (just zeros for testing)
            mock_embedding = [0.0] * 384  # BAAI/bge-small-en-v1.5 dimension

            # Get metadata for this text
            text_metadata = metadata[i] if metadata and i < len(metadata) else {}

            # Store vector
            result = await self.upsert_vector(
                vector_embedding=mock_embedding,
                document=text,
                namespace=namespace,
                vector_metadata=text_metadata
            )

            vector_ids.append(result["vector_id"])

        return {
            "success": True,
            "vector_ids": vector_ids,
            "count": len(vector_ids)
        }

    async def generate_embeddings(
        self,
        texts: List[str],
        model: str = "BAAI/bge-small-en-v1.5"
    ) -> Dict[str, Any]:
        """
        Generate embeddings for texts (mock).

        Issue #79: Returns embeddings with correct dimensions for the model.

        Args:
            texts: List of texts to generate embeddings for
            model: Embedding model name

        Returns:
            Dictionary with embeddings array
        """
        self._track_call(
            "generate_embeddings",
            texts=texts,
            model=model
        )

        # Model dimension mapping per Issue #79
        from app.core.config import SUPPORTED_MODELS, DEFAULT_EMBEDDING_DIMENSIONS

        # Get dimensions for the model, default to 384
        dimensions = SUPPORTED_MODELS.get(model, DEFAULT_EMBEDDING_DIMENSIONS)

        # Generate mock embeddings with correct dimensions
        embeddings = []
        for _ in texts:
            # Create deterministic mock embedding
            mock_embedding = [0.1] * dimensions
            embeddings.append(mock_embedding)

        return {
            "embeddings": embeddings,
            "model": model,
            "dimensions": dimensions
        }

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        namespace: str = "default",
        model: str = "BAAI/bge-small-en-v1.5"
    ) -> Dict[str, Any]:
        """
        Search using text query (mock).

        Args:
            query: Search query text
            top_k: Number of results
            namespace: Vector namespace
            model: Embedding model

        Returns:
            Search results with matches
        """
        self._track_call(
            "semantic_search",
            query=query,
            top_k=top_k,
            namespace=namespace
        )

        # Filter vectors by namespace
        namespace_vectors = [
            v for v in self.vectors
            if v.get("namespace") == namespace
        ]

        # Return top_k vectors (mock - no actual similarity calculation)
        matches = []
        for vector in namespace_vectors[:top_k]:
            matches.append({
                "vector_id": vector["vector_id"],
                "document": vector["document"],
                "metadata": vector.get("metadata", {}),
                "score": 0.9  # Mock similarity score
            })

        return {
            "matches": matches,
            "count": len(matches)
        }

    def reset(self):
        """Clear all data and call history."""
        self.data.clear()
        self.call_history.clear()
        self.vectors.clear()
        self._row_id_counters.clear()

    def get_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all rows from a table (test helper)."""
        return self.data.get(table_name, [])

    def get_call_count(self, method: str) -> int:
        """Count how many times a method was called (test helper)."""
        return sum(1 for call in self.call_history if call["method"] == method)
