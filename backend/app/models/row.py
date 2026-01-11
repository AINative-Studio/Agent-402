"""
Row domain model.
Represents rows within a NoSQL table.
Epic 7, Issue 2: Row insertion support.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any


@dataclass
class Row:
    """
    Internal row model.
    Represents a single row of data within a table.

    Attributes:
        id: Unique row identifier (auto-generated)
        table_id: Table this row belongs to
        project_id: Project this row belongs to (denormalized for query efficiency)
        data: Row data as key-value pairs
        created_at: Timestamp of row creation
        updated_at: Timestamp of last update
    """
    id: str
    table_id: str
    project_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "table_id": self.table_id,
            "project_id": self.project_id,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
