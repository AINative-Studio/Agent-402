"""
Pydantic schemas for agent spend limits and rate limiting.
Issue #239: Agent Spend Limits Enforcement.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class SpendLimitConfig(BaseModel):
    """Configuration for agent spend and rate limits."""

    max_daily_spend: Optional[Decimal] = Field(
        None,
        description="Maximum total spend per UTC calendar day in USDC. None = unlimited.",
        ge=0,
    )
    max_per_tx_spend: Optional[Decimal] = Field(
        None,
        description="Maximum spend per single transaction in USDC. None = unlimited.",
        ge=0,
    )
    max_requests_per_minute: Optional[int] = Field(
        None,
        description="Maximum API requests per 60-second sliding window. None = unlimited.",
        ge=1,
    )


class SpendLimitStatus(BaseModel):
    """Current spend and rate limit status for an agent."""

    agent_id: str = Field(..., description="Agent DID or identifier.")
    daily_spend: Decimal = Field(..., description="Total confirmed spend today (UTC).")
    remaining_daily: Optional[Decimal] = Field(
        None,
        description="Remaining daily budget. None when no daily limit is configured.",
    )
    per_tx_limit: Optional[Decimal] = Field(
        None,
        description="Per-transaction limit. None when no per-tx limit is configured.",
    )
    requests_this_minute: int = Field(
        0,
        description="Number of API requests made in the current 60-second window.",
    )


class RateLimitExceededResponse(BaseModel):
    """Response body returned when a rate limit is exceeded (HTTP 429)."""

    detail: str = Field(..., description="Human-readable explanation of the rate limit.")
    error_code: str = Field(
        "RATE_LIMIT_EXCEEDED",
        description="Machine-readable error code.",
    )
    retry_after_seconds: int = Field(
        ...,
        description="Number of seconds the client should wait before retrying.",
        ge=1,
    )
