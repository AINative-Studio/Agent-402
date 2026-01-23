"""
Project domain model.
Represents internal project structure.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ProjectStatus(str, Enum):
    """Project status enumeration."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ProjectTier(str, Enum):
    """Project tier enumeration."""
    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


@dataclass
class Project:
    """
    Internal project model.
    Represents a ZeroDB project owned by a user.
    """
    id: str
    name: str
    status: ProjectStatus
    tier: ProjectTier
    user_id: str
    description: Optional[str] = None
    database_enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "tier": self.tier.value,
            "user_id": self.user_id,
            "description": self.description,
            "database_enabled": self.database_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
