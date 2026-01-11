"""
Row data store.
For MVP demo (PRD Section 9), we use deterministic in-memory storage.
In production, this would connect to ZeroDB or a database.
Epic 7, Issue 2: Row insertion support.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from app.models.row import Row


class RowStore:
    """
    In-memory row store for deterministic demo.
    Per PRD Section 9: Demo setup must be deterministic.
    """

    def __init__(self):
        # Dictionary keyed by row_id for O(1) lookups
        self._rows: Dict[str, Row] = {}
        # Index for table_id -> row_ids for efficient table queries
        self._table_index: Dict[str, List[str]] = {}
        self._initialize_demo_rows()

    def _initialize_demo_rows(self):
        """
        Initialize deterministic demo rows per PRD Section 9.
        Creates predefined rows for demo tables.
        """
        demo_rows = [
            # Rows for tbl_demo_001 (customers)
            Row(
                id="row_demo_001",
                table_id="tbl_demo_001",
                project_id="proj_demo_u1_001",
                data={
                    "name": "Alice Smith",
                    "email": "alice@example.com",
                    "age": 30,
                    "active": True
                },
                created_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            ),
            Row(
                id="row_demo_002",
                table_id="tbl_demo_001",
                project_id="proj_demo_u1_001",
                data={
                    "name": "Bob Johnson",
                    "email": "bob@example.com",
                    "age": 45,
                    "active": True
                },
                created_at=datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
            ),
            Row(
                id="row_demo_003",
                table_id="tbl_demo_001",
                project_id="proj_demo_u1_001",
                data={
                    "name": "Charlie Brown",
                    "email": "charlie@example.com",
                    "age": 25,
                    "active": False
                },
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ),
            # Rows for tbl_demo_002 (transactions)
            Row(
                id="row_demo_004",
                table_id="tbl_demo_002",
                project_id="proj_demo_u1_001",
                data={
                    "amount": 100.50,
                    "currency": "USD",
                    "timestamp": "2025-01-01T10:30:00Z",
                    "metadata": {"type": "payment", "reference": "PAY-001"}
                },
                created_at=datetime(2025, 1, 2, 10, 30, 0, tzinfo=timezone.utc),
            ),
            Row(
                id="row_demo_005",
                table_id="tbl_demo_002",
                project_id="proj_demo_u1_001",
                data={
                    "amount": 250.00,
                    "currency": "EUR",
                    "timestamp": "2025-01-02T14:00:00Z",
                    "metadata": {"type": "transfer", "reference": "TRF-002"}
                },
                created_at=datetime(2025, 1, 2, 14, 0, 0, tzinfo=timezone.utc),
            ),
            # Rows for tbl_demo_004 (analytics)
            Row(
                id="row_demo_006",
                table_id="tbl_demo_004",
                project_id="proj_demo_u2_001",
                data={
                    "metric_name": "cpu_usage",
                    "value": 75.5,
                    "tags": ["production", "server-1"]
                },
                created_at=datetime(2025, 1, 4, 8, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        for row in demo_rows:
            self._rows[row.id] = row
            # Update table index
            if row.table_id not in self._table_index:
                self._table_index[row.table_id] = []
            self._table_index[row.table_id].append(row.id)

    def get_by_id(self, row_id: str) -> Optional[Row]:
        """Get row by ID."""
        return self._rows.get(row_id)

    def get_by_table_id(
        self,
        table_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Row]:
        """
        Get all rows for a table with pagination.
        Returns empty list if no rows exist.
        """
        row_ids = self._table_index.get(table_id, [])
        # Apply pagination
        paginated_ids = row_ids[offset:offset + limit]
        return [self._rows[row_id] for row_id in paginated_ids if row_id in self._rows]

    def count_by_table_id(self, table_id: str) -> int:
        """Count rows in a table."""
        return len(self._table_index.get(table_id, []))

    def create(self, row: Row) -> Row:
        """
        Create a new row.
        For production, this would insert into ZeroDB.
        """
        self._rows[row.id] = row
        # Update table index
        if row.table_id not in self._table_index:
            self._table_index[row.table_id] = []
        self._table_index[row.table_id].append(row.id)
        return row

    def create_batch(self, rows: List[Row]) -> List[Row]:
        """
        Create multiple rows in batch.
        For production, this would use batch insert to ZeroDB.
        """
        for row in rows:
            self._rows[row.id] = row
            # Update table index
            if row.table_id not in self._table_index:
                self._table_index[row.table_id] = []
            self._table_index[row.table_id].append(row.id)
        return rows

    def update(self, row: Row) -> Row:
        """Update an existing row."""
        if row.id not in self._rows:
            raise ValueError(f"Row not found: {row.id}")
        row.updated_at = datetime.now(timezone.utc)
        self._rows[row.id] = row
        return row

    def delete(self, row_id: str) -> bool:
        """Delete a row by ID."""
        if row_id in self._rows:
            row = self._rows[row_id]
            # Remove from table index
            if row.table_id in self._table_index:
                if row_id in self._table_index[row.table_id]:
                    self._table_index[row.table_id].remove(row_id)
            del self._rows[row_id]
            return True
        return False

    def delete_by_table_id(self, table_id: str) -> int:
        """
        Delete all rows for a table.
        Returns count of deleted rows.
        """
        row_ids = self._table_index.get(table_id, []).copy()
        count = 0
        for row_id in row_ids:
            if self.delete(row_id):
                count += 1
        return count

    def exists(self, row_id: str) -> bool:
        """Check if a row exists."""
        return row_id in self._rows


# Global singleton instance for demo
row_store = RowStore()
