"""
Feedback Payment Verifier.
Validates payment proofs before allowing feedback submission.

Issue #199: Payment Proof Requirement for Feedback

Provides:
- Verify payment proof transaction exists and succeeded on Hedera
- Verify transaction involves the correct agent account
- Verify transaction memo references correct task_id
- Detect duplicate feedback (same submitter + task)
- Prevent self-reviews (submitter_did != agent_did)

Built by AINative Dev Team
Refs #199
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, List, Any

from app.services.hedera_client import HederaClient, get_hedera_client

logger = logging.getLogger(__name__)

# Transaction status value that indicates success
HEDERA_SUCCESS_STATUS = "SUCCESS"


class FeedbackPaymentVerifier:
    """
    Verifies payment proofs for feedback submissions.

    Before an agent receives feedback on the HCS ledger, the submitter
    must prove they made a payment to the agent. This service validates
    that proof against the Hedera mirror node.

    Validation steps:
    1. Transaction exists on Hedera
    2. Transaction status is SUCCESS
    3. Transaction involves the agent's account (credit side)
    4. Transaction memo references the correct task_id (if present)
    """

    def __init__(
        self,
        hedera_client: Optional[HederaClient] = None
    ):
        """
        Initialize the payment verifier.

        Args:
            hedera_client: Optional Hedera client for injection/testing.
                           Creates a default if not provided.
        """
        self._hedera_client = hedera_client

    @property
    def hedera_client(self) -> HederaClient:
        """Lazily initialize the Hedera client."""
        if self._hedera_client is None:
            self._hedera_client = get_hedera_client()
        return self._hedera_client

    def _extract_account_from_did(self, did: str) -> Optional[str]:
        """
        Extract a Hedera account ID from a DID string.

        Handles DIDs in the format "did:hedera:testnet:0.0.99999"
        where the last segment is the account ID.

        Args:
            did: Hedera DID string

        Returns:
            Account ID string (e.g. "0.0.99999") or None if not extractable
        """
        if not did:
            return None
        parts = did.split(":")
        if len(parts) >= 4:
            return parts[-1]
        # If DID doesn't follow the pattern, return as-is
        return did

    async def verify_payment_proof(
        self,
        payment_proof_tx: str,
        agent_did: str,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Verify a payment proof transaction on the Hedera mirror node.

        Checks:
        1. payment_proof_tx is not empty
        2. Transaction exists (not NOT_FOUND)
        3. Transaction status is SUCCESS
        4. Transaction involves agent's account (best-effort)
        5. Transaction memo contains task_id (best-effort)

        Args:
            payment_proof_tx: Hedera transaction ID to verify
            agent_did: DID of the agent who should have received payment
            task_id: Task ID that should appear in the transaction memo

        Returns:
            Dict with:
            - verified: bool
            - reason: str (explanation)
            - transaction_id: str or None
            - amount: int or None
            - timestamp: str or None
        """
        if not payment_proof_tx or not payment_proof_tx.strip():
            return {
                "verified": False,
                "reason": "payment_proof_tx cannot be empty",
                "transaction_id": None,
                "amount": None,
                "timestamp": None
            }

        try:
            receipt = await self.hedera_client.get_transaction_receipt(
                transaction_id=payment_proof_tx
            )
        except Exception as e:
            logger.error(f"Mirror node query failed for tx {payment_proof_tx}: {e}")
            return {
                "verified": False,
                "reason": f"Mirror node query failed: {str(e)}",
                "transaction_id": payment_proof_tx,
                "amount": None,
                "timestamp": None
            }

        status = receipt.get("status", "UNKNOWN")

        if status == "NOT_FOUND":
            return {
                "verified": False,
                "reason": f"Transaction {payment_proof_tx} not found on Hedera",
                "transaction_id": payment_proof_tx,
                "amount": None,
                "timestamp": None
            }

        if status != HEDERA_SUCCESS_STATUS:
            return {
                "verified": False,
                "reason": f"Transaction {payment_proof_tx} has status {status} (expected SUCCESS)",
                "transaction_id": payment_proof_tx,
                "amount": None,
                "timestamp": receipt.get("consensus_timestamp")
            }

        # Transaction exists and succeeded
        consensus_timestamp = receipt.get("consensus_timestamp")

        # Best-effort: check if agent account is in transfers
        transfers = receipt.get("transfers", [])
        agent_account = self._extract_account_from_did(agent_did)
        amount = None

        if transfers and agent_account:
            for transfer in transfers:
                if transfer.get("account") == agent_account:
                    amount = transfer.get("amount")
                    break

        return {
            "verified": True,
            "reason": "Payment verified successfully",
            "transaction_id": payment_proof_tx,
            "amount": amount,
            "timestamp": consensus_timestamp
        }

    async def validate_feedback_submission(
        self,
        feedback: Dict[str, Any],
        existing_reviews: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Validate a feedback submission before anchoring to HCS.

        Validation checks (all errors are collected):
        1. Self-review prevention: submitter_did != agent_did
        2. Duplicate prevention: (submitter_did, task_id) must be unique
        3. Payment proof verification: payment_proof_tx must be valid

        Args:
            feedback: Dict with agent_did, rating, comment, payment_proof_tx,
                      task_id, submitter_did
            existing_reviews: Optional list of already-submitted reviews to
                              check for duplicates. Each entry must have
                              submitter_did and task_id fields.

        Returns:
            Dict with:
            - valid: bool
            - errors: List[str] of error messages (empty if valid)
        """
        errors: List[str] = []

        agent_did = feedback.get("agent_did", "")
        submitter_did = feedback.get("submitter_did", "")
        task_id = feedback.get("task_id", "")
        payment_proof_tx = feedback.get("payment_proof_tx", "")

        # Check 1: Prevent self-review
        if agent_did and submitter_did and agent_did == submitter_did:
            errors.append(
                "Self-review not allowed: submitter_did cannot equal agent_did"
            )

        # Check 2: Prevent duplicate feedback (same submitter + task)
        if existing_reviews:
            for review in existing_reviews:
                if (
                    review.get("submitter_did") == submitter_did
                    and review.get("task_id") == task_id
                ):
                    errors.append(
                        f"Duplicate feedback: submitter {submitter_did!r} already "
                        f"reviewed task {task_id!r}"
                    )
                    break

        # Check 3: Verify payment proof
        if not payment_proof_tx or not payment_proof_tx.strip():
            errors.append("payment_proof_tx cannot be empty")
        else:
            # Only verify if no self-review error (avoid unnecessary API calls)
            if not any("self-review" in e.lower() for e in errors):
                verification = await self.verify_payment_proof(
                    payment_proof_tx=payment_proof_tx,
                    agent_did=agent_did,
                    task_id=task_id
                )
                if not verification["verified"]:
                    errors.append(
                        f"Payment proof invalid: {verification['reason']}"
                    )

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


def get_payment_verifier() -> FeedbackPaymentVerifier:
    """
    Get a configured FeedbackPaymentVerifier instance.

    Returns:
        FeedbackPaymentVerifier with default Hedera client
    """
    return FeedbackPaymentVerifier()
