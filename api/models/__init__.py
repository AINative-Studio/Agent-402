"""
API Models for ZeroDB Platform
"""
# This is a compatibility layer - the actual implementation is in api/models_legacy.py
# to avoid circular imports with api.errors which needs the models

from .projects import (
    ProjectCreate,
    ProjectResponse,
    ProjectListResponse,
    ProjectStatus,
    ProjectTier,
)

# Import error models from legacy file
from api.models_legacy import (
    ErrorResponse,
    ValidationErrorResponse,
    ValidationErrorDetail,
)

# Aliases for compatibility with existing code
CreateProjectRequest = ProjectCreate

__all__ = [
    "ProjectCreate",
    "CreateProjectRequest",
    "ProjectResponse",
    "ProjectListResponse",
    "ProjectStatus",
    "ProjectTier",
    "ErrorResponse",
    "ValidationErrorResponse",
    "ValidationErrorDetail",
]
