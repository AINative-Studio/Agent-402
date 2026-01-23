"""
Arc Blockchain Service.
Issues #119 + #122: X402 Payment Tracking and Agent Interaction APIs.

Per PRD Section 10 (Non-repudiation):
- Read from Arc blockchain (ReputationRegistry, AgentTreasury)
- Submit transactions via RPC
- Event emission for reputation updates

Contract addresses are loaded from contracts/deployments/arc-testnet.json
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Feedback types matching ReputationRegistry contract."""
    POSITIVE = 0
    NEGATIVE = 1
    NEUTRAL = 2
    REPORT = 3


@dataclass
class ArcDeployment:
    """Arc blockchain deployment information."""
    network: str
    agent_registry: str
    reputation_registry: str
    agent_treasury: str
    deployer: str


class ArcBlockchainService:
    """
    Service for interacting with Arc blockchain contracts.

    Provides read operations for:
    - ReputationRegistry: Agent scores, trust tiers, feedback
    - AgentTreasury: Treasury balances, payments, transactions

    Note: Write operations (transactions) require a signer/wallet.
    For MVP, read operations are primary use case.
    """

    def __init__(self, rpc_url: Optional[str] = None):
        """
        Initialize the Arc Blockchain service.

        Args:
            rpc_url: Optional RPC URL override (defaults to env var)
        """
        self.rpc_url = rpc_url or os.getenv("ARC_RPC_URL", "https://sepolia.arc.io")
        self._deployment: Optional[ArcDeployment] = None
        self._load_deployment()

    def _load_deployment(self) -> None:
        """Load deployment info from arc-testnet.json."""
        try:
            deployment_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "contracts",
                "deployments",
                "arc-testnet.json"
            )

            # Normalize path
            deployment_path = os.path.normpath(deployment_path)

            if os.path.exists(deployment_path):
                with open(deployment_path, "r") as f:
                    data = json.load(f)
                    contracts = data.get("contracts", {})
                    self._deployment = ArcDeployment(
                        network=data.get("network", "arc-testnet"),
                        agent_registry=contracts.get("AgentRegistry", ""),
                        reputation_registry=contracts.get("ReputationRegistry", ""),
                        agent_treasury=contracts.get("AgentTreasury", ""),
                        deployer=data.get("deployer", "")
                    )
                    logger.info(f"Loaded Arc deployment for network: {self._deployment.network}")
            else:
                logger.warning(f"Arc deployment file not found at {deployment_path}")
                # Use mock deployment for testing
                self._deployment = ArcDeployment(
                    network="mock",
                    agent_registry="0x0000000000000000000000000000000000000000",
                    reputation_registry="0x0000000000000000000000000000000000000000",
                    agent_treasury="0x0000000000000000000000000000000000000000",
                    deployer=""
                )

        except Exception as e:
            logger.error(f"Failed to load Arc deployment: {e}")
            self._deployment = None

    @property
    def deployment(self) -> Optional[ArcDeployment]:
        """Get the current deployment info."""
        return self._deployment

    # =========================================================================
    # ReputationRegistry Read Operations
    # =========================================================================

    async def get_agent_reputation(
        self,
        agent_token_id: int
    ) -> Dict[str, Any]:
        """
        Get agent reputation summary from ReputationRegistry.

        Args:
            agent_token_id: Agent token ID from AgentRegistry

        Returns:
            Dict with totalScore, feedbackCount, averageScore, trustTier
        """
        # In production: Call ReputationRegistry.getAgentReputationSummary(agentTokenId)
        # For MVP: Return mock data based on token ID

        # Mock implementation
        mock_data = {
            "agent_token_id": agent_token_id,
            "total_score": 85 + (agent_token_id * 5) % 100,
            "feedback_count": 50 + (agent_token_id * 10) % 100,
            "average_score": 7 + (agent_token_id % 3),
            "trust_tier": min(4, agent_token_id % 5)
        }

        logger.debug(f"Retrieved reputation for agent {agent_token_id}: {mock_data}")
        return mock_data

    async def get_agent_trust_tier(
        self,
        agent_token_id: int
    ) -> int:
        """
        Get agent trust tier (0-4) from ReputationRegistry.

        Tier calculation (from PRD Progressive Trust Tiers):
        - Tier 0: < 10 feedback or avg score < 0
        - Tier 1: >= 10 feedback, avg >= 0, < 5
        - Tier 2: >= 25 feedback, avg >= 5, < 7
        - Tier 3: >= 50 feedback, avg >= 7, < 9
        - Tier 4: >= 100 feedback, avg >= 9

        Args:
            agent_token_id: Agent token ID

        Returns:
            Trust tier (0-4)
        """
        reputation = await self.get_agent_reputation(agent_token_id)
        return reputation.get("trust_tier", 0)

    async def get_agent_feedback_count(
        self,
        agent_token_id: int
    ) -> int:
        """
        Get total feedback count for an agent.

        Args:
            agent_token_id: Agent token ID

        Returns:
            Number of feedback submissions
        """
        reputation = await self.get_agent_reputation(agent_token_id)
        return reputation.get("feedback_count", 0)

    # =========================================================================
    # AgentTreasury Read Operations
    # =========================================================================

    async def get_treasury_balance(
        self,
        treasury_id: int
    ) -> Dict[str, Any]:
        """
        Get treasury balance from AgentTreasury contract.

        Args:
            treasury_id: Treasury ID

        Returns:
            Dict with treasury_id, balance_usdc (in smallest unit)
        """
        # In production: Call AgentTreasury.getTreasuryBalance(treasuryId)
        # For MVP: Return mock data

        mock_balance = 1000000000 + (treasury_id * 100000000)  # Mock: 1000+ USDC

        return {
            "treasury_id": treasury_id,
            "balance_usdc": mock_balance,
            "balance_usdc_formatted": f"{mock_balance / 1000000:.6f}"
        }

    async def get_treasury_by_agent(
        self,
        agent_token_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get treasury info for an agent.

        Args:
            agent_token_id: Agent token ID from AgentRegistry

        Returns:
            Dict with treasury info or None if not found
        """
        # In production: Call AgentTreasury.getTreasuryByAgent(agentTokenId)
        # For MVP: Return mock data

        # Treasury ID is typically agent_token_id + 1 (since treasury IDs start at 1)
        treasury_id = agent_token_id + 1

        return {
            "treasury_id": treasury_id,
            "agent_token_id": agent_token_id,
            "owner": self._deployment.deployer if self._deployment else "",
            "active": True,
            "created_at": "2026-01-23T05:49:48Z"
        }

    async def get_payment(
        self,
        payment_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get payment details from AgentTreasury contract.

        Args:
            payment_id: Payment ID

        Returns:
            Dict with payment details or None if not found
        """
        # In production: Call AgentTreasury.getPayment(paymentId)
        # For MVP: Return mock data

        return {
            "payment_id": payment_id,
            "from_treasury_id": 1,
            "to_treasury_id": 2,
            "amount": 1000000,  # 1 USDC
            "purpose": "x402-api-call",
            "x402_receipt_hash": f"0x{payment_id:064x}",
            "timestamp": "2026-01-23T12:00:00Z"
        }

    async def get_treasury_payments(
        self,
        treasury_id: int
    ) -> List[int]:
        """
        Get all payment IDs for a treasury.

        Args:
            treasury_id: Treasury ID

        Returns:
            List of payment IDs
        """
        # In production: Call AgentTreasury.getTreasuryPayments(treasuryId)
        # For MVP: Return mock data

        # Mock: Return some payment IDs based on treasury
        return list(range(treasury_id * 10, treasury_id * 10 + 5))

    # =========================================================================
    # Transaction Preparation (for future write operations)
    # =========================================================================

    def prepare_submit_feedback_tx(
        self,
        agent_token_id: int,
        feedback_type: FeedbackType,
        score: int,
        comment: str,
        transaction_hash: str
    ) -> Dict[str, Any]:
        """
        Prepare a submitFeedback transaction for ReputationRegistry.

        This returns the transaction data that can be signed and submitted
        by a wallet/signer.

        Args:
            agent_token_id: Agent token ID
            feedback_type: Type of feedback (POSITIVE, NEGATIVE, etc.)
            score: Score from -10 to +10
            comment: Optional comment
            transaction_hash: Related transaction hash

        Returns:
            Dict with transaction data (to, data, value)
        """
        if not self._deployment:
            raise ValueError("Arc deployment not loaded")

        if score < -10 or score > 10:
            raise ValueError("Score must be between -10 and +10")

        # In production: Encode function call using web3
        # For MVP: Return structure with parameters

        return {
            "to": self._deployment.reputation_registry,
            "function": "submitFeedback",
            "params": {
                "agentTokenId": agent_token_id,
                "feedbackType": feedback_type.value,
                "score": score,
                "comment": comment,
                "transactionHash": transaction_hash
            },
            "value": 0
        }

    def prepare_process_payment_tx(
        self,
        from_treasury_id: int,
        to_treasury_id: int,
        amount: int,
        purpose: str,
        x402_receipt_hash: str
    ) -> Dict[str, Any]:
        """
        Prepare a processPayment transaction for AgentTreasury.

        Args:
            from_treasury_id: Source treasury ID
            to_treasury_id: Destination treasury ID
            amount: Amount in USDC (6 decimals)
            purpose: Payment purpose
            x402_receipt_hash: X402 receipt hash for audit

        Returns:
            Dict with transaction data
        """
        if not self._deployment:
            raise ValueError("Arc deployment not loaded")

        return {
            "to": self._deployment.agent_treasury,
            "function": "processPayment",
            "params": {
                "fromTreasuryId": from_treasury_id,
                "toTreasuryId": to_treasury_id,
                "amount": amount,
                "purpose": purpose,
                "x402ReceiptHash": x402_receipt_hash
            },
            "value": 0
        }


# Global service instance
arc_blockchain_service = ArcBlockchainService()
