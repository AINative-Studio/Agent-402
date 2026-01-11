"""
Core configuration for ZeroDB Public API.

Defines tier-based project limits and system-wide settings.
"""
from enum import Enum
from typing import Dict

from pydantic_settings import BaseSettings


class Tier(str, Enum):
    """Valid project tier values."""
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # API Configuration
    api_title: str = "ZeroDB Public API"
    api_version: str = "v1"
    api_prefix: str = "/v1/public"

    # Security
    api_key_header: str = "X-API-Key"

    # Database (mock for now, can be extended)
    database_url: str = "sqlite:///./zerodb.db"

    # Tier-based project limits
    # Maps tier name to maximum number of projects allowed
    tier_project_limits: Dict[str, int] = {
        Tier.FREE: 3,
        Tier.STARTER: 10,
        Tier.PRO: 50,
        Tier.ENTERPRISE: 999999  # Effectively unlimited
    }

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_project_limit(tier: str) -> int:
    """
    Get the maximum number of projects allowed for a given tier.

    Args:
        tier: The tier name (free, starter, pro, enterprise)

    Returns:
        Maximum number of projects allowed for the tier

    Raises:
        ValueError: If tier is not recognized
    """
    tier_lower = tier.lower()
    if tier_lower not in settings.tier_project_limits:
        raise ValueError(f"Invalid tier: {tier}")
    return settings.tier_project_limits[tier_lower]
