"""
End-to-end integration tests for the full Hedera service stack.

Issue #253: All Hedera Integration Tests Green

Verifies that all Sprint 1-4 Hedera services work together in a complete
agent workflow:
  create wallet -> associate USDC -> transfer -> verify receipt ->
  anchor memory -> submit feedback -> calculate reputation ->
  discover via HCS-10

Uses mocked Hedera client (no real testnet calls).
BDD-style: class DescribeFullHederaIntegration / def it_*

Built by AINative Dev Team
Refs #253
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_hedera_client() -> AsyncMock:
    """
    Mocked Hedera client that satisfies all service interactions without
    hitting the testnet.
    """
    client = AsyncMock()

    # Wallet / account operations
    client.create_account = AsyncMock(return_value={
        "account_id": "0.0.77001",
        "public_key": "302a300506032b6570032100aabbccdd",
        "private_key": "302e020100300506032b657004220420eeff0011",
        "network": "testnet",
    })
    client.associate_token = AsyncMock(return_value={
        "transaction_id": "0.0.77001@1712000000.000000001",
        "status": "SUCCESS",
        "account_id": "0.0.77001",
    })
    client.get_account_balance = AsyncMock(return_value={
        "hbar": "10.0",
        "tokens": {"0.0.456858": "0"},
    })

    # Payment / transfer operations
    client.transfer_token = AsyncMock(return_value={
        "transaction_id": "0.0.77001@1712000001.000000002",
        "status": "SUCCESS",
        "hash": "abc123",
        "from_account": "0.0.77001",
        "to_account": "0.0.77002",
        "amount": 100_000_000,  # 100 USDC in smallest unit
        "token_id": "0.0.456858",
    })
    client.get_transaction_receipt = AsyncMock(return_value={
        "transaction_id": "0.0.77001@1712000001.000000002",
        "status": "SUCCESS",
        "consensus_timestamp": "1712000001.000000002",
        "hash": "abc123",
    })

    # HCS message operations — used by HCSAnchoringService and HederaReputationService
    client.submit_hcs_message = AsyncMock(return_value={
        "topic_id": "0.0.88001",
        "sequence_number": 42,
        "consensus_timestamp": "1712000002.000000003",
        "transaction_id": "0.0.77001@1712000002.000000003",
        "status": "SUCCESS",
    })
    client.query_hcs_topic = AsyncMock(return_value={
        "messages": [
            {
                "sequence_number": 1,
                "consensus_timestamp": "2026-04-01T00:00:00+00:00",
                "message": {
                    "type": "feedback",
                    "agent_did": "did:hedera:testnet:0.0.77001",
                    "rating": 5,
                    "comment": "excellent",
                    "task_id": "task-001",
                    "submitter_did": "did:hedera:testnet:0.0.77002",
                },
            },
            {
                "sequence_number": 2,
                "consensus_timestamp": "2026-04-02T00:00:00+00:00",
                "message": {
                    "type": "feedback",
                    "agent_did": "did:hedera:testnet:0.0.77001",
                    "rating": 4,
                    "comment": "good",
                    "task_id": "task-002",
                    "submitter_did": "did:hedera:testnet:0.0.77003",
                },
            },
        ]
    })

    # HCS-10 / directory operations — used by HCS14DirectoryService via nft_client
    client.submit_message = AsyncMock(return_value={
        "topic_id": "0.0.99001",
        "sequence_number": 10,
        "consensus_timestamp": "1712000003.000000004",
        "transaction_id": "0.0.77001@1712000003.000000004",
        "status": "SUCCESS",
    })
    client.get_messages = AsyncMock(return_value={
        "messages": [
            {
                "sequence_number": 1,
                "consensus_timestamp": "1712000003.000000001",
                "message": {
                    "type": "register",
                    "did": "did:hedera:testnet:0.0.77001",
                    "capabilities": ["finance", "compliance"],
                    "role": "analyst",
                    "reputation": 100,
                },
            }
        ]
    })

    # NFT / HTS identity operations
    client.create_nft_token = AsyncMock(return_value={
        "token_id": "0.0.55001",
        "transaction_id": "0.0.77001@1712000004.000000005",
        "status": "SUCCESS",
    })
    client.mint_nft = AsyncMock(return_value={
        "token_id": "0.0.55001",
        "serial_number": 1,
        "transaction_id": "0.0.77001@1712000005.000000006",
        "status": "SUCCESS",
    })

    return client


@pytest.fixture
def mock_hcs_client() -> AsyncMock:
    """
    Mocked HCS client specifically for HCSAnchoringService — calls
    submit_hcs_message with a `message` keyword argument.
    """
    client = AsyncMock()
    client.submit_hcs_message = AsyncMock(return_value={
        "topic_id": "0.0.88001",
        "sequence_number": 42,
        "consensus_timestamp": "1712000002.000000003",
        "transaction_id": "0.0.77001@1712000002.000000003",
        "status": "SUCCESS",
    })
    return client


@pytest.fixture
def mock_nft_client() -> AsyncMock:
    """
    Mocked HTS/NFT client for HCS14DirectoryService.
    Provides submit_hcs_message for writes and get_hcs_messages for reads.
    Messages are base64-encoded JSON to match the HCS mirror node format.
    """
    import base64
    import json

    client = AsyncMock()
    client.submit_hcs_message = AsyncMock(return_value={
        "topic_id": "0.0.99001",
        "sequence_number": 10,
        "consensus_timestamp": "1712000003.000000004",
        "transaction_id": "0.0.77001@1712000003.000000004",
        "status": "SUCCESS",
    })

    # Messages must be base64-encoded JSON strings to match the directory service
    register_msg = base64.b64encode(json.dumps({
        "type": "register",
        "did": "did:hedera:testnet:0.0.77001",
        "capabilities": ["finance", "compliance"],
        "role": "analyst",
        "reputation": 100,
        "timestamp": "2026-04-03T00:00:00+00:00",
    }).encode()).decode()

    client.get_hcs_messages = AsyncMock(return_value={
        "messages": [
            {
                "sequence_number": 1,
                "consensus_timestamp": "1712000003.000000001",
                "message": register_msg,
            }
        ]
    })
    return client


@pytest.fixture
def mock_zerodb_client() -> AsyncMock:
    """Mocked ZeroDB client for all in-memory persistence."""
    client = AsyncMock()
    client.insert_row = AsyncMock(return_value={"success": True, "id": "row-001"})
    client.query_rows = AsyncMock(return_value={"rows": [], "total": 0})
    client.update_row = AsyncMock(return_value={"success": True})
    return client


# ---------------------------------------------------------------------------
# Full workflow: end-to-end integration
# ---------------------------------------------------------------------------

class DescribeFullHederaIntegration:
    """
    BDD test class for the complete Agent-402 Hedera integration workflow.

    Workflow:
        1. create wallet
        2. associate USDC token
        3. transfer USDC
        4. verify receipt
        5. anchor memory to HCS
        6. submit reputation feedback
        7. calculate reputation score
        8. discover agent via HCS-10 directory
    """

    # ── Step 1: Create wallet ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def it_creates_an_agent_wallet_on_hedera(
        self,
        mock_hedera_client: AsyncMock,
        mock_zerodb_client: AsyncMock,
    ) -> None:
        """
        HederaWalletService.create_agent_wallet returns account_id and keys,
        calls hedera_client.create_account, and persists the record to ZeroDB.
        """
        from app.services.hedera_wallet_service import HederaWalletService

        service = HederaWalletService(
            zerodb_client=mock_zerodb_client,
            hedera_client=mock_hedera_client,
        )

        result = await service.create_agent_wallet(
            agent_id="agent-e2e-001",
            initial_balance=10,
        )

        assert result["account_id"] == "0.0.77001"
        assert result["agent_id"] == "agent-e2e-001"
        assert "public_key" in result
        mock_hedera_client.create_account.assert_called_once()

    # ── Step 2: Associate USDC ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def it_associates_usdc_token_with_new_wallet(
        self,
        mock_hedera_client: AsyncMock,
        mock_zerodb_client: AsyncMock,
    ) -> None:
        """
        HederaWalletService.associate_usdc_token associates the USDC HTS token
        and calls hedera_client.associate_token.
        """
        from app.services.hedera_wallet_service import HederaWalletService

        service = HederaWalletService(
            zerodb_client=mock_zerodb_client,
            hedera_client=mock_hedera_client,
        )

        result = await service.associate_usdc_token(account_id="0.0.77001")

        assert result["status"] == "SUCCESS"
        mock_hedera_client.associate_token.assert_called_once()

    # ── Step 3: Transfer USDC ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def it_transfers_usdc_between_agents(
        self,
        mock_hedera_client: AsyncMock,
        mock_zerodb_client: AsyncMock,
    ) -> None:
        """
        HederaPaymentService.transfer_usdc executes a USDC HTS transfer
        and returns a transaction_id with status SUCCESS.
        """
        from app.services.hedera_payment_service import HederaPaymentService

        service = HederaPaymentService(
            hedera_client=mock_hedera_client,
            zerodb_client=mock_zerodb_client,
        )

        result = await service.transfer_usdc(
            from_account="0.0.77001",
            to_account="0.0.77002",
            amount=100_000_000,  # 100 USDC
            memo="e2e payment test",
        )

        assert result["status"] == "SUCCESS"
        assert "transaction_id" in result
        mock_hedera_client.transfer_token.assert_called_once()

    # ── Step 4: Verify receipt ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def it_verifies_the_payment_receipt(
        self,
        mock_hedera_client: AsyncMock,
        mock_zerodb_client: AsyncMock,
    ) -> None:
        """
        HederaPaymentService.verify_receipt_on_mirror_node calls
        hedera_client.get_transaction_receipt and returns verified=True.
        """
        from app.services.hedera_payment_service import HederaPaymentService

        service = HederaPaymentService(
            hedera_client=mock_hedera_client,
            zerodb_client=mock_zerodb_client,
        )

        receipt = await service.verify_receipt_on_mirror_node(
            transaction_id="0.0.77001@1712000001.000000002"
        )

        assert receipt["verified"] is True
        assert "transaction_status" in receipt
        mock_hedera_client.get_transaction_receipt.assert_called_once_with(
            transaction_id="0.0.77001@1712000001.000000002"
        )

    # ── Step 5: Anchor memory to HCS ───────────────────────────────────────

    @pytest.mark.asyncio
    async def it_anchors_agent_memory_to_hcs(
        self,
        mock_hcs_client: AsyncMock,
    ) -> None:
        """
        HCSAnchoringService.anchor_memory submits a SHA-256 hash to HCS
        and returns sequence_number.
        """
        from app.services.hcs_anchoring_service import HCSAnchoringService

        service = HCSAnchoringService(hcs_client=mock_hcs_client)

        result = await service.anchor_memory(
            memory_id="mem-001",
            content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            agent_id="agent-e2e-001",
            namespace="default",
        )

        assert result["sequence_number"] == 42
        assert result["memory_id"] == "mem-001"
        mock_hcs_client.submit_hcs_message.assert_called_once()

    # ── Step 6: Submit reputation feedback ─────────────────────────────────

    @pytest.mark.asyncio
    async def it_submits_reputation_feedback_to_hcs(
        self,
        mock_hedera_client: AsyncMock,
    ) -> None:
        """
        HederaReputationService.submit_feedback sends feedback to an agent's
        HCS topic and returns sequence_number.
        """
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService(hedera_client=mock_hedera_client)

        result = await service.submit_feedback(
            agent_did="did:hedera:testnet:0.0.77001",
            rating=5,
            comment="excellent task completion",
            payment_proof_tx="0.0.77001@1712000001.000000002",
            task_id="task-001",
            submitter_did="did:hedera:testnet:0.0.77002",
        )

        assert result["sequence_number"] == 42
        mock_hedera_client.submit_hcs_message.assert_called()

    # ── Step 7: Calculate reputation score ─────────────────────────────────

    @pytest.mark.asyncio
    async def it_calculates_reputation_score_from_hcs_feedback(
        self,
        mock_hedera_client: AsyncMock,
    ) -> None:
        """
        HederaReputationService.calculate_reputation_score returns a weighted
        score in [0.0, 5.0] and a trust tier derived from HCS feedback.
        """
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService(hedera_client=mock_hedera_client)

        reputation = await service.calculate_reputation_score(
            agent_did="did:hedera:testnet:0.0.77001",
        )

        assert "score" in reputation
        assert "trust_tier" in reputation
        score = reputation["score"]
        assert 0.0 <= score <= 5.0
        mock_hedera_client.query_hcs_topic.assert_called()

    # ── Step 8: Discover agent via HCS-10 ──────────────────────────────────

    @pytest.mark.asyncio
    async def it_registers_and_queries_agent_in_hcs14_directory(
        self,
        mock_nft_client: AsyncMock,
    ) -> None:
        """
        HCS14DirectoryService.register_agent submits a register message to
        the HCS-14 directory topic, and query_directory retrieves it.
        """
        from app.services.hcs14_directory_service import HCS14DirectoryService

        service = HCS14DirectoryService(nft_client=mock_nft_client)

        reg_result = await service.register_agent(
            agent_did="did:hedera:testnet:0.0.77001",
            capabilities=["finance", "compliance"],
            role="analyst",
            reputation_score=100,
        )

        assert reg_result["did"] == "did:hedera:testnet:0.0.77001"
        mock_nft_client.submit_hcs_message.assert_called_once()

        # Also verify query_directory returns a dict with an agents list
        query_result = await service.query_directory(capability="finance")
        assert isinstance(query_result, dict)
        assert "agents" in query_result

    # ── Full pipeline: all steps chained ───────────────────────────────────

    @pytest.mark.asyncio
    async def it_executes_the_complete_hedera_agent_workflow(
        self,
        mock_hedera_client: AsyncMock,
        mock_hcs_client: AsyncMock,
        mock_nft_client: AsyncMock,
        mock_zerodb_client: AsyncMock,
    ) -> None:
        """
        A single integration scenario exercises all Hedera services in
        sequence, mirroring the 5-minute demo workflow. No real testnet calls.
        """
        from app.services.hedera_wallet_service import HederaWalletService
        from app.services.hedera_payment_service import HederaPaymentService
        from app.services.hcs_anchoring_service import HCSAnchoringService
        from app.services.hedera_reputation_service import HederaReputationService
        from app.services.hcs14_directory_service import HCS14DirectoryService

        # Step 1: create wallet
        wallet_service = HederaWalletService(
            zerodb_client=mock_zerodb_client,
            hedera_client=mock_hedera_client,
        )
        wallet = await wallet_service.create_agent_wallet(
            agent_id="agent-e2e-pipeline",
            initial_balance=10,
        )
        assert wallet["account_id"] == "0.0.77001"

        # Step 2: associate USDC
        association = await wallet_service.associate_usdc_token(
            account_id=wallet["account_id"],
        )
        assert association["status"] == "SUCCESS"

        # Step 3: transfer USDC
        payment_service = HederaPaymentService(
            hedera_client=mock_hedera_client,
            zerodb_client=mock_zerodb_client,
        )
        transfer = await payment_service.transfer_usdc(
            from_account=wallet["account_id"],
            to_account="0.0.77002",
            amount=10_000_000,  # 10 USDC
            memo="pipeline test",
        )
        assert transfer["status"] == "SUCCESS"
        tx_id = transfer["transaction_id"]

        # Step 4: verify receipt
        receipt = await payment_service.verify_receipt_on_mirror_node(
            transaction_id=tx_id
        )
        assert receipt["verified"] is True

        # Step 5: anchor memory
        anchor_service = HCSAnchoringService(hcs_client=mock_hcs_client)
        anchor = await anchor_service.anchor_memory(
            memory_id="mem-pipeline-001",
            content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            agent_id="agent-e2e-pipeline",
            namespace="default",
        )
        assert "sequence_number" in anchor

        # Step 6: submit feedback
        reputation_service = HederaReputationService(hedera_client=mock_hedera_client)
        feedback = await reputation_service.submit_feedback(
            agent_did="did:hedera:testnet:0.0.77001",
            rating=5,
            comment="pipeline complete",
            payment_proof_tx=tx_id,
            task_id="pipeline-task-001",
            submitter_did="did:hedera:testnet:0.0.99999",
        )
        assert "sequence_number" in feedback

        # Step 7: calculate score
        reputation = await reputation_service.calculate_reputation_score(
            agent_did="did:hedera:testnet:0.0.77001",
        )
        assert "score" in reputation

        # Step 8: register in HCS-14 directory
        directory_service = HCS14DirectoryService(nft_client=mock_nft_client)
        reg = await directory_service.register_agent(
            agent_did="did:hedera:testnet:0.0.77001",
            capabilities=["finance"],
            role="analyst",
            reputation_score=100,
        )
        assert reg["did"] == "did:hedera:testnet:0.0.77001"


# ---------------------------------------------------------------------------
# Issue #253 acceptance: individual service smoke tests
# ---------------------------------------------------------------------------

class DescribeHederaServicesSmokeTests:
    """
    Lightweight smoke tests confirming each Sprint 1-4 Hedera service
    is importable and instantiates without error.
    """

    def it_imports_hedera_wallet_service(self) -> None:
        """HederaWalletService is importable and instantiates."""
        from app.services.hedera_wallet_service import HederaWalletService
        service = HederaWalletService()
        assert service is not None

    def it_imports_hedera_payment_service(self) -> None:
        """HederaPaymentService is importable and instantiates."""
        from app.services.hedera_payment_service import HederaPaymentService
        service = HederaPaymentService()
        assert service is not None

    def it_imports_hcs_anchoring_service(self) -> None:
        """HCSAnchoringService is importable and instantiates."""
        from app.services.hcs_anchoring_service import HCSAnchoringService
        service = HCSAnchoringService()
        assert service is not None

    def it_imports_hedera_reputation_service(self) -> None:
        """HederaReputationService is importable and instantiates."""
        from app.services.hedera_reputation_service import HederaReputationService
        service = HederaReputationService()
        assert service is not None

    def it_imports_hedera_identity_service(self) -> None:
        """HederaIdentityService is importable and instantiates."""
        from app.services.hedera_identity_service import HederaIdentityService
        service = HederaIdentityService()
        assert service is not None

    def it_imports_hcs14_directory_service(self) -> None:
        """HCS14DirectoryService is importable and instantiates."""
        from app.services.hcs14_directory_service import HCS14DirectoryService
        service = HCS14DirectoryService()
        assert service is not None
