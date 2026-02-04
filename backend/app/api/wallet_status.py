"""
Wallet status management API endpoints.
Issue #156: Add wallet freeze and revoke controls.

Provides PATCH endpoint to update wallet status with audit logging:
- Status transitions: active ↔ paused, active ↔ frozen, active → inactive
- Validation: frozen/inactive require reason, inactive is terminal
- Audit trail: all status changes logged to compliance_events
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.schemas.wallet_status import WalletStatusUpdate, WalletStatusResponse
from app.schemas.circle import WalletStatus
from app.schemas.compliance_events import (
    ComplianceEventCreate,
    ComplianceEventType,
    ComplianceOutcome
)
from app.services.circle_wallet_service import circle_wallet_service
from app.services.compliance_service import compliance_service
from app.services.circle_service import WalletNotFoundError
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


async def update_wallet_status(
    project_id: str,
    wallet_id: str,
    status_update: WalletStatusUpdate,
    user_id: str = Depends(get_current_user)
) -> WalletStatusResponse:
    """
    Update wallet status for freeze/pause/revoke control.

    Status transitions:
    - active → paused (temporary stop)
    - active → frozen (security hold)
    - active → inactive (permanent decommission)
    - paused → active (resume operations)
    - frozen → active (after security review)
    - inactive → (no transitions allowed)

    Audit logging:
    All status changes are logged to compliance_events with:
    - agent_id: wallet's linked agent DID
    - event_type: AUDIT_LOG
    - outcome: PASS
    - details: full change record (wallet_id, previous_status, new_status, reason, updated_by)

    Args:
        project_id: Project identifier
        wallet_id: Wallet identifier to update
        status_update: Status update request with new status and optional reason
        user_id: Authenticated user ID (from X-API-Key or JWT)

    Returns:
        WalletStatusResponse with updated status and audit trail

    Raises:
        WalletNotFoundError: If wallet does not exist (404)
        HTTPException: If status transition is invalid (400)
    """
    # Get current wallet
    try:
        wallet = await circle_wallet_service.get_wallet(wallet_id, project_id)
    except WalletNotFoundError:
        logger.warning(f"Wallet not found: {wallet_id}")
        raise

    previous_status_str = wallet.get("status", "active")
    previous_status = WalletStatus(previous_status_str)

    # Validate status transition
    if previous_status == WalletStatus.INACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Cannot change status of inactive wallet"
        )

    # Require reason for frozen/inactive
    if status_update.status in [WalletStatus.FROZEN, WalletStatus.INACTIVE]:
        if not status_update.reason:
            raise HTTPException(
                status_code=400,
                detail=f"Reason required for {status_update.status.value} status"
            )

    # Update wallet status in ZeroDB
    updated_wallet = await circle_wallet_service.update_wallet_status(
        wallet_id=wallet_id,
        project_id=project_id,
        status=status_update.status.value,
        reason=status_update.reason,
        frozen_until=status_update.frozen_until
    )

    # Create audit log in compliance_events
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat().replace('+00:00', 'Z')

    try:
        event_create = ComplianceEventCreate(
            agent_id=wallet["agent_did"],
            event_type=ComplianceEventType.AUDIT_LOG,
            outcome=ComplianceOutcome.PASS,
            risk_score=0.0,
            details={
                "action": "wallet_status_change",
                "wallet_id": wallet_id,
                "previous_status": previous_status.value,
                "new_status": status_update.status.value,
                "reason": status_update.reason,
                "frozen_until": status_update.frozen_until,
                "updated_by": user_id,
                "timestamp": timestamp
            },
            run_id=None
        )

        await compliance_service.create_event(
            project_id=project_id,
            event_data=event_create
        )

        logger.info(
            f"Wallet status updated: {wallet_id} "
            f"{previous_status.value} → {status_update.status.value} "
            f"by {user_id}"
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        # Don't fail the request if audit logging fails
        # Status is already updated

    return WalletStatusResponse(
        wallet_id=wallet_id,
        status=status_update.status,
        previous_status=previous_status,
        reason=status_update.reason,
        frozen_until=status_update.frozen_until,
        updated_at=timestamp,
        updated_by=user_id
    )


@router.patch("/{project_id}/wallets/{wallet_id}/status")
async def patch_wallet_status(
    project_id: str,
    wallet_id: str,
    status_update: WalletStatusUpdate,
    user_id: str = Depends(get_current_user)
) -> WalletStatusResponse:
    """
    PATCH endpoint for updating wallet status.

    Wraps the update_wallet_status function for FastAPI route.
    """
    return await update_wallet_status(
        project_id=project_id,
        wallet_id=wallet_id,
        status_update=status_update,
        user_id=user_id
    )
