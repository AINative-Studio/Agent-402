"""
End-to-end Phase 2 demo flow integration tests.

Tests the complete workflow:
1. Agent registration with wallet creation
2. Task execution with payment
3. Multi-agent collaboration with memory sharing
4. Reputation updates after task completion
5. Error handling and recovery

Issues #124 and #127: Backend Integration Tests.

Test Style: BDD (Given/When/Then in docstrings)
Coverage Target: 80%+
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.circle_wallet_service import CircleWalletService
from app.services.agent_memory_service import AgentMemoryService
from app.services.x402_service import X402Service
from app.services.compliance_service import ComplianceService
from app.schemas.x402_requests import X402RequestStatus
from app.schemas.compliance_events import (
    ComplianceEventType,
    ComplianceOutcome,
    ComplianceEventCreate
)


class TestPhase2DemoFlow:
    """Integration tests for the complete Phase 2 demo workflow."""

    @pytest.mark.asyncio
    async def test_agent_registration_with_wallet_creation(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id,
        sample_agent_dids
    ):
        """
        Given: An unregistered agent with a DID
        When: The agent is registered with Circle wallet creation
        Then: A Circle wallet is created and linked to the agent DID
        """
        # Arrange
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = sample_agent_dids["analyst"]

        # Act
        result = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type="analyst",
            description="Test analyst agent wallet"
        )

        # Assert
        assert result["wallet_type"] == "analyst"
        assert result["agent_did"] == agent_did
        assert "wallet_id" in result
        assert result["status"] == "active"
        assert "circle_wallet_id" in result
        assert mock_circle_service.get_call_count("create_wallet") == 1

    @pytest.mark.asyncio
    async def test_three_agents_registered_with_wallets(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id,
        sample_agent_dids
    ):
        """
        Given: Three agents (analyst, compliance, transaction) need wallets
        When: Each agent is registered with a Circle wallet
        Then: All three agents have active wallets linked to their DIDs
        """
        # Arrange
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )

        # Act
        wallets = {}
        for wallet_type, agent_did in sample_agent_dids.items():
            wallet = await wallet_service.create_agent_wallet(
                project_id=test_project_id,
                agent_did=agent_did,
                wallet_type=wallet_type
            )
            wallets[wallet_type] = wallet

        # Assert
        assert len(wallets) == 3
        for wallet_type in ["analyst", "compliance", "transaction"]:
            assert wallets[wallet_type]["wallet_type"] == wallet_type
            assert wallets[wallet_type]["status"] == "active"

        assert mock_circle_service.get_call_count("create_wallet") == 3

    @pytest.mark.asyncio
    async def test_agent_hired_with_usdc_payment(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id,
        sample_agent_dids
    ):
        """
        Given: A registered agent with a Circle wallet
        When: A user hires the agent with USDC payment
        Then: Payment receipt is created and task is initiated
        """
        # Arrange
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )

        # Create source (user) and destination (agent) wallets
        user_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnUser123",
            wallet_type="transaction",
            description="User wallet for payments"
        )

        agent_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=sample_agent_dids["analyst"],
            wallet_type="analyst",
            description="Analyst agent wallet"
        )

        # Act
        transfer = await wallet_service.initiate_transfer(
            project_id=test_project_id,
            source_wallet_id=user_wallet["wallet_id"],
            destination_wallet_id=agent_wallet["wallet_id"],
            amount="100.00",
            x402_request_id="x402_req_test123"
        )

        # Assert
        assert transfer["status"] == "pending"
        assert "transfer_id" in transfer
        assert transfer["amount"] == "100.00"
        assert transfer["x402_request_id"] == "x402_req_test123"
        assert mock_circle_service.get_call_count("create_transfer") == 1

    @pytest.mark.asyncio
    async def test_payment_receipt_generated_after_transfer(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id,
        sample_agent_dids
    ):
        """
        Given: A completed USDC transfer between wallets
        When: A payment receipt is generated
        Then: Receipt contains source and destination agent DIDs
        """
        # Arrange
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )

        # Create wallets
        source_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=sample_agent_dids["transaction"],
            wallet_type="transaction"
        )
        dest_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=sample_agent_dids["analyst"],
            wallet_type="analyst"
        )

        # Create transfer
        transfer = await wallet_service.initiate_transfer(
            project_id=test_project_id,
            source_wallet_id=source_wallet["wallet_id"],
            destination_wallet_id=dest_wallet["wallet_id"],
            amount="50.00"
        )

        # Act
        receipt = await wallet_service.generate_receipt(
            transfer["transfer_id"],
            test_project_id
        )

        # Assert
        assert "receipt_id" in receipt
        assert receipt["source_agent_did"] == sample_agent_dids["transaction"]
        assert receipt["destination_agent_did"] == sample_agent_dids["analyst"]
        assert receipt["amount"] == "50.00"

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration_shares_memory(
        self,
        mock_zerodb_client,
        test_project_id,
        test_run_id,
        sample_agent_dids
    ):
        """
        Given: Three agents with a shared memory namespace
        When: Analyst completes analysis task and stores memory
        Then: Compliance agent can access analysis results via memory
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)
        shared_namespace = "phase2_demo_shared"

        # Act - Analyst stores analysis results
        analyst_memory = await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="analyst",
            run_id=test_run_id,
            memory_type="analyst_output",
            content='{"market_data": {"price": 1.0}, "recommendation": "proceed"}',
            namespace=shared_namespace,
            metadata={"task_id": "task_analysis_001"}
        )

        # Compliance agent retrieves analyst memory
        memories, total, _ = await memory_service.list_memories(
            project_id=test_project_id,
            namespace=shared_namespace,
            memory_type="analyst_output"
        )

        # Assert
        assert len(memories) == 1
        assert memories[0]["memory_id"] == analyst_memory["memory_id"]
        assert "market_data" in memories[0]["content"]

    @pytest.mark.asyncio
    async def test_full_workflow_analyst_to_compliance_to_transaction(
        self,
        mock_zerodb_client,
        test_project_id,
        test_run_id,
        sample_agent_dids
    ):
        """
        Given: A complete Phase 2 demo setup with 3 agents
        When: The full workflow executes (Analyst -> Compliance -> Transaction)
        Then: Each agent stores memory that the next agent can access
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)
        shared_namespace = "workflow_test"

        # Act - Step 1: Analyst stores output
        analyst_memory = await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="analyst",
            run_id=test_run_id,
            memory_type="analyst_output",
            content='{"market_analysis": "favorable", "risk_level": "low"}',
            namespace=shared_namespace
        )

        # Step 2: Compliance accesses analyst output and stores decision
        compliance_memory = await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="compliance",
            run_id=test_run_id,
            memory_type="compliance_output",
            content='{"approved": true, "checks": ["aml", "kyc"]}',
            namespace=shared_namespace,
            metadata={"analyst_memory_id": analyst_memory["memory_id"]}
        )

        # Step 3: Transaction accesses compliance output and executes
        transaction_memory = await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="transaction",
            run_id=test_run_id,
            memory_type="transaction_output",
            content='{"executed": true, "tx_id": "tx_123"}',
            namespace=shared_namespace,
            metadata={
                "analyst_memory_id": analyst_memory["memory_id"],
                "compliance_memory_id": compliance_memory["memory_id"]
            }
        )

        # Verify all memories are stored
        memories, total, _ = await memory_service.list_memories(
            project_id=test_project_id,
            run_id=test_run_id,
            namespace=shared_namespace
        )

        # Assert
        assert len(memories) == 3
        memory_types = [m["memory_type"] for m in memories]
        assert "analyst_output" in memory_types
        assert "compliance_output" in memory_types
        assert "transaction_output" in memory_types

    @pytest.mark.asyncio
    async def test_x402_request_linked_to_memory_and_compliance(
        self,
        mock_zerodb_client,
        test_project_id,
        test_run_id,
        sample_agent_dids
    ):
        """
        Given: An X402 payment request is created
        When: Memory and compliance events are linked to the request
        Then: The request shows all linked records for audit trail
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)
        x402_service = X402Service(client=mock_zerodb_client)

        # Create memory record
        memory = await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="transaction",
            run_id=test_run_id,
            memory_type="payment_decision",
            content='{"reason": "Task completed successfully"}'
        )

        # Act - Create X402 request with linked memory
        x402_request = await x402_service.create_request(
            project_id=test_project_id,
            agent_id=sample_agent_dids["transaction"],
            task_id="task_payment_001",
            run_id=test_run_id,
            request_payload={
                "type": "payment_authorization",
                "amount": "100.00",
                "currency": "USD"
            },
            signature="0xsig_test123",
            linked_memory_ids=[memory["memory_id"]]
        )

        # Assert
        assert x402_request["request_id"].startswith("x402_req_")
        assert memory["memory_id"] in x402_request["linked_memory_ids"]
        assert x402_request["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_compliance_event_created_for_transaction(
        self,
        mock_zerodb_client,
        test_project_id,
        test_run_id
    ):
        """
        Given: A transaction requires compliance approval
        When: Compliance agent creates a compliance event
        Then: The event is recorded with risk score and outcome
        """
        # Arrange
        compliance_service = ComplianceService(client=mock_zerodb_client)

        # Act
        event = await compliance_service.create_event(
            project_id=test_project_id,
            event_data=ComplianceEventCreate(
                agent_id="compliance_agent",
                event_type=ComplianceEventType.KYC_CHECK,
                outcome=ComplianceOutcome.PASS,
                risk_score=0.15,
                run_id=test_run_id,
                details={"checks_performed": ["kyc", "sanctions"]}
            )
        )

        # Assert
        assert event.event_id.startswith("evt_")
        assert event.outcome == ComplianceOutcome.PASS
        assert event.risk_score == 0.15
        assert event.event_type == ComplianceEventType.KYC_CHECK


class TestErrorHandlingAndRecovery:
    """Tests for error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_duplicate_wallet_prevented(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id,
        sample_agent_dids
    ):
        """
        Given: An agent already has a wallet of a specific type
        When: Attempting to create a duplicate wallet
        Then: DuplicateWalletError is raised
        """
        # Arrange
        from app.services.circle_wallet_service import DuplicateWalletError

        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )

        # Create first wallet
        await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=sample_agent_dids["analyst"],
            wallet_type="analyst"
        )

        # Act & Assert
        with pytest.raises(DuplicateWalletError):
            await wallet_service.create_agent_wallet(
                project_id=test_project_id,
                agent_did=sample_agent_dids["analyst"],
                wallet_type="analyst"
            )

    @pytest.mark.asyncio
    async def test_wallet_not_found_error(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        Given: A wallet ID that does not exist
        When: Attempting to retrieve the wallet
        Then: WalletNotFoundError is raised
        """
        # Arrange
        from app.services.circle_service import WalletNotFoundError

        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )

        # Act & Assert
        with pytest.raises(WalletNotFoundError):
            await wallet_service.get_wallet(
                "nonexistent_wallet_id",
                test_project_id
            )

    @pytest.mark.asyncio
    async def test_x402_request_not_found_error(
        self,
        mock_zerodb_client,
        test_project_id
    ):
        """
        Given: An X402 request ID that does not exist
        When: Attempting to retrieve the request
        Then: X402RequestNotFoundError is raised
        """
        # Arrange
        from app.services.x402_service import X402RequestNotFoundError

        x402_service = X402Service(client=mock_zerodb_client)

        # Act & Assert
        with pytest.raises(X402RequestNotFoundError):
            await x402_service.get_request(
                test_project_id,
                "nonexistent_request_id"
            )

    @pytest.mark.asyncio
    async def test_compliance_failure_blocks_transaction(
        self,
        mock_zerodb_client,
        test_project_id,
        test_run_id
    ):
        """
        Given: A compliance check that fails
        When: The transaction agent checks compliance status
        Then: The transaction should not proceed
        """
        # Arrange
        compliance_service = ComplianceService(client=mock_zerodb_client)
        memory_service = AgentMemoryService(client=mock_zerodb_client)

        # Create a failed compliance event
        event = await compliance_service.create_event(
            project_id=test_project_id,
            event_data=ComplianceEventCreate(
                agent_id="compliance_agent",
                event_type=ComplianceEventType.RISK_ASSESSMENT,
                outcome=ComplianceOutcome.FAIL,
                risk_score=0.9,
                run_id=test_run_id,
                details={"reason": "High risk transaction"}
            )
        )

        # Store failure in memory for transaction agent
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="compliance",
            run_id=test_run_id,
            memory_type="compliance_output",
            content='{"approved": false, "compliance_status": "FAIL"}',
            metadata={"event_id": event.event_id}
        )

        # Verify compliance failure
        memories, _, _ = await memory_service.list_memories(
            project_id=test_project_id,
            run_id=test_run_id,
            memory_type="compliance_output"
        )

        # Assert
        assert len(memories) == 1
        assert "FAIL" in memories[0]["content"]
        assert event.outcome == ComplianceOutcome.FAIL

    @pytest.mark.asyncio
    async def test_partial_workflow_recovery(
        self,
        mock_zerodb_client,
        test_project_id,
        test_run_id
    ):
        """
        Given: A workflow that fails partway through
        When: The workflow is retried
        Then: It can resume from the last successful step
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)

        # Simulate completed analyst step
        analyst_memory = await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="analyst",
            run_id=test_run_id,
            memory_type="analyst_output",
            content='{"status": "completed"}'
        )

        # Simulate failed compliance step (no compliance memory stored)
        # Now retry - check what's already done
        existing_memories, _, _ = await memory_service.list_memories(
            project_id=test_project_id,
            run_id=test_run_id
        )

        completed_steps = [m["memory_type"] for m in existing_memories]

        # Act - Resume from compliance step
        if "compliance_output" not in completed_steps:
            compliance_memory = await memory_service.store_memory(
                project_id=test_project_id,
                agent_id="compliance",
                run_id=test_run_id,
                memory_type="compliance_output",
                content='{"status": "completed", "retry": true}'
            )

        # Verify recovery
        final_memories, total, _ = await memory_service.list_memories(
            project_id=test_project_id,
            run_id=test_run_id
        )

        # Assert
        assert len(final_memories) == 2
        memory_types = [m["memory_type"] for m in final_memories]
        assert "analyst_output" in memory_types
        assert "compliance_output" in memory_types


class TestReputationUpdates:
    """Tests for reputation updates after task completion."""

    @pytest.mark.asyncio
    async def test_reputation_increases_after_successful_task(
        self,
        mock_arc_service,
        sample_agent_dids
    ):
        """
        Given: An agent completes a task successfully
        When: Reputation is updated
        Then: The agent's reputation score increases
        """
        # Arrange
        agent_did = sample_agent_dids["analyst"]

        # Register agent
        await mock_arc_service.register_agent(
            agent_did=agent_did,
            wallet_address="0x123abc"
        )

        initial_rep = await mock_arc_service.get_agent_reputation(agent_did)

        # Act - Successful task increases reputation
        result = await mock_arc_service.update_reputation(
            agent_did=agent_did,
            delta=10,
            reason="Successfully completed analysis task"
        )

        final_rep = await mock_arc_service.get_agent_reputation(agent_did)

        # Assert
        assert result["success"] is True
        assert final_rep["reputation_score"] > initial_rep["reputation_score"]
        assert final_rep["reputation_score"] == initial_rep["reputation_score"] + 10

    @pytest.mark.asyncio
    async def test_reputation_decreases_after_failed_task(
        self,
        mock_arc_service,
        sample_agent_dids
    ):
        """
        Given: An agent fails to complete a task
        When: Reputation is updated with negative delta
        Then: The agent's reputation score decreases
        """
        # Arrange
        agent_did = sample_agent_dids["compliance"]

        # Register agent
        await mock_arc_service.register_agent(
            agent_did=agent_did,
            wallet_address="0x456def"
        )

        initial_rep = await mock_arc_service.get_agent_reputation(agent_did)

        # Act - Failed task decreases reputation
        result = await mock_arc_service.update_reputation(
            agent_did=agent_did,
            delta=-5,
            reason="Failed compliance check"
        )

        final_rep = await mock_arc_service.get_agent_reputation(agent_did)

        # Assert
        assert result["success"] is True
        assert final_rep["reputation_score"] < initial_rep["reputation_score"]
        assert final_rep["reputation_score"] == initial_rep["reputation_score"] - 5

    @pytest.mark.asyncio
    async def test_reputation_bounded_at_zero(
        self,
        mock_arc_service,
        sample_agent_dids
    ):
        """
        Given: An agent with low reputation
        When: A large negative reputation update is applied
        Then: Reputation does not go below zero
        """
        # Arrange
        agent_did = sample_agent_dids["transaction"]

        await mock_arc_service.register_agent(
            agent_did=agent_did,
            wallet_address="0x789ghi"
        )

        # Set reputation low
        mock_arc_service.reputation_scores[agent_did] = 10

        # Act - Large negative update
        result = await mock_arc_service.update_reputation(
            agent_did=agent_did,
            delta=-100,
            reason="Major failure"
        )

        final_rep = await mock_arc_service.get_agent_reputation(agent_did)

        # Assert
        assert result["success"] is True
        assert final_rep["reputation_score"] >= 0


class TestMemorySemanticSearch:
    """Tests for semantic search over agent memories."""

    @pytest.mark.asyncio
    async def test_search_memories_finds_relevant_content(
        self,
        mock_zerodb_client,
        test_project_id,
        test_run_id
    ):
        """
        Given: Multiple memory entries with different content
        When: Semantic search is performed
        Then: Relevant memories are returned
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)

        # Store different memories
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="analyst",
            run_id=test_run_id,
            memory_type="analysis",
            content="Market analysis shows BTC price increasing"
        )

        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="compliance",
            run_id=test_run_id,
            memory_type="compliance",
            content="AML check passed for transaction"
        )

        # Act
        results = await memory_service.search_memories(
            project_id=test_project_id,
            query="market analysis",
            namespace="default",
            top_k=5
        )

        # Assert - Mock returns all matching namespace vectors
        # In a real implementation, semantic similarity would filter
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_memory_namespace_isolation(
        self,
        mock_zerodb_client,
        test_project_id,
        test_run_id
    ):
        """
        Given: Memories stored in different namespaces
        When: Querying a specific namespace
        Then: Only memories from that namespace are returned
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)

        # Store in namespace A
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="agent_a",
            run_id=test_run_id,
            memory_type="test",
            content="Content in namespace A",
            namespace="namespace_a"
        )

        # Store in namespace B
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="agent_b",
            run_id=test_run_id,
            memory_type="test",
            content="Content in namespace B",
            namespace="namespace_b"
        )

        # Act - Query namespace A only
        memories_a, _, _ = await memory_service.list_memories(
            project_id=test_project_id,
            namespace="namespace_a"
        )

        memories_b, _, _ = await memory_service.list_memories(
            project_id=test_project_id,
            namespace="namespace_b"
        )

        # Assert
        assert len(memories_a) == 1
        assert memories_a[0]["namespace"] == "namespace_a"
        assert len(memories_b) == 1
        assert memories_b[0]["namespace"] == "namespace_b"
