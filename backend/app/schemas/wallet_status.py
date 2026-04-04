"""
Wallet status management schemas.
Issue #156: Add wallet freeze and revoke controls.

These schemas define the contract for wallet status update operations:
- WalletStatusUpdate: Request to change wallet status
- WalletStatusResponse: Response after status update with audit trail
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.schemas.circle import WalletStatus


class WalletStatusUpdate(BaseModel):
    """
    Request to update wallet status.

    Status transitions:
    - active → paused (temporary stop)
    - active → frozen (security hold)
    - active → inactive (permanent decommission)
    - paused → active (resume operations)
    - frozen → active (after security review)
    - inactive → (no transitions allowed)

    Frozen and inactive require a reason.
    """
    status: WalletStatus = Field(
        ...,
        description="New wallet status",
        examples=["frozen"]
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for status change (required for frozen/inactive)",
        max_length=500,
        examples=["Suspicious activity detected"]
    )
    frozen_until: Optional[str] = Field(
        default=None,
        description="ISO timestamp for automatic unfreeze (optional)",
        max_length=64,
        examples=["2026-02-10T00:00:00Z"]
    )

    @field_validator('frozen_until')
    @classmethod
    def validate_frozen_until_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate frozen_until is valid ISO timestamp if provided."""
        if v is None:
            return v

        # Basic ISO format validation
        if not v.endswith('Z') and '+' not in v and '-' not in v[-6:]:
            raise ValueError("frozen_until must be valid ISO 8601 timestamp")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "frozen",
                "reason": "Suspicious activity detected",
                "frozen_until": "2026-02-10T00:00:00Z"
            }
        }


class WalletStatusResponse(BaseModel):
    """
    Response after wallet status update.

    Includes full audit trail of the status change:
    - What changed (previous_status → status)
    - Why (reason)
    - When (updated_at)
    - Who (updated_by)
    """
    wallet_id: str = Field(
        ...,
        description="Wallet identifier"
    )
    status: WalletStatus = Field(
        ...,
        description="New wallet status"
    )
    previous_status: WalletStatus = Field(
        ...,
        description="Previous wallet status"
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for status change"
    )
    frozen_until: Optional[str] = Field(
        None,
        description="ISO timestamp for automatic unfreeze"
    )
    updated_at: str = Field(
        ...,
        description="Timestamp of status update"
    )
    updated_by: str = Field(
        ...,
        description="User ID who performed the update"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "wallet_abc123",
                "status": "frozen",
                "previous_status": "active",
                "reason": "Suspicious activity detected",
                "frozen_until": "2026-02-10T00:00:00Z",
                "updated_at": "2026-02-03T12:00:00Z",
                "updated_by": "admin_user_123"
            }
        }
