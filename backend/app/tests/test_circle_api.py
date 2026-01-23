"""
Integration tests for Circle API endpoints.
Tests Issue #114: Circle Wallets and USDC Payments - API Layer.

TDD Approach: Tests written FIRST, then implementation.

Test Coverage:
- POST /circle/wallets - Create wallet for agent
- GET /circle/wallets/{wallet_id} - Get wallet details
- GET /circle/wallets - List wallets
- POST /circle/transfers - Initiate USDC transfer
- GET /circle/transfers/{transfer_id} - Get transfer status
- GET /circle/transfers - List transfers
- Error handling and validation
"""
import pytest
from fastapi import status


class TestCreateWalletEndpoint:
    """Test suite for POST /v1/public/{project_id}/circle/wallets endpoint."""

    def test_create_wallet_successfully(self, client, auth_headers_user1):
        """
        Test successful wallet creation.
        Issue #114: Create wallet for agent.
        """
        project_id = "proj_demo_u1_001"
        request_body = {
            "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "wallet_type": "transaction",
            "description": "Transaction agent wallet for USDC payments"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "wallet_id" in data
        assert data["wallet_id"].startswith("wallet_")
        assert data["agent_did"] == request_body["agent_did"]
        assert data["wallet_type"] == request_body["wallet_type"]
        assert data["status"] == "active"
        assert "blockchain_address" in data
        assert "circle_wallet_id" in data
        assert "created_at" in data

    def test_create_analyst_wallet(self, client, auth_headers_user1):
        """Test creating analyst wallet type."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnAnalyst",
            "wallet_type": "analyst"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["wallet_type"] == "analyst"

    def test_create_compliance_wallet(self, client, auth_headers_user1):
        """Test creating compliance wallet type."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbCompliance",
            "wallet_type": "compliance"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["wallet_type"] == "compliance"

    def test_reject_invalid_agent_did_format(self, client, auth_headers_user1):
        """Test that invalid DID format is rejected."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "agent_did": "invalid:did:format",
            "wallet_type": "transaction"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_reject_invalid_wallet_type(self, client, auth_headers_user1):
        """Test that invalid wallet type is rejected."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "wallet_type": "invalid_type"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_reject_missing_required_fields(self, client, auth_headers_user1):
        """Test that missing required fields are rejected."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "description": "Missing required fields"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_return_401_for_missing_api_key(self, client):
        """Test that missing API key returns 401."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "wallet_type": "transaction"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json=request_body
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_return_409_for_duplicate_wallet(self, client, auth_headers_user1):
        """Test that duplicate wallet creation returns 409."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbDuplicate",
            "wallet_type": "transaction"
        }

        # First creation should succeed
        response1 = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json=request_body,
            headers=auth_headers_user1
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Second creation should fail
        response2 = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json=request_body,
            headers=auth_headers_user1
        )
        assert response2.status_code == status.HTTP_409_CONFLICT
        data = response2.json()
        assert data["error_code"] == "DUPLICATE_WALLET"


class TestGetWalletEndpoint:
    """Test suite for GET /v1/public/{project_id}/circle/wallets/{wallet_id} endpoint."""

    def test_get_wallet_by_id(self, client, auth_headers_user1):
        """Test retrieving wallet by ID."""
        project_id = "proj_demo_u1_001"

        # First create a wallet
        create_response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json={
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGetTest",
                "wallet_type": "analyst"
            },
            headers=auth_headers_user1
        )
        wallet_id = create_response.json()["wallet_id"]

        # Then retrieve it
        response = client.get(
            f"/v1/public/{project_id}/circle/wallets/{wallet_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["wallet_id"] == wallet_id
        assert "balance" in data
        assert "blockchain_address" in data

    def test_return_404_for_nonexistent_wallet(self, client, auth_headers_user1):
        """Test that nonexistent wallet returns 404."""
        project_id = "proj_demo_u1_001"

        response = client.get(
            f"/v1/public/{project_id}/circle/wallets/wallet_nonexistent",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "WALLET_NOT_FOUND"

    def test_include_balance_in_response(self, client, auth_headers_user1):
        """Test that wallet response includes balance."""
        project_id = "proj_demo_u1_001"

        # Create wallet
        create_response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json={
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLBalTest",
                "wallet_type": "transaction"
            },
            headers=auth_headers_user1
        )
        wallet_id = create_response.json()["wallet_id"]

        # Get wallet with balance
        response = client.get(
            f"/v1/public/{project_id}/circle/wallets/{wallet_id}",
            headers=auth_headers_user1
        )

        data = response.json()
        assert "balance" in data
        # Balance should be a string representing USDC amount
        assert isinstance(data["balance"], str)


class TestListWalletsEndpoint:
    """Test suite for GET /v1/public/{project_id}/circle/wallets endpoint."""

    def test_list_all_wallets(self, client, auth_headers_user1):
        """Test listing all wallets in project."""
        project_id = "proj_demo_u1_001"

        response = client.get(
            f"/v1/public/{project_id}/circle/wallets",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "wallets" in data
        assert "total" in data
        assert isinstance(data["wallets"], list)

    def test_filter_by_wallet_type(self, client, auth_headers_user1):
        """Test filtering wallets by type."""
        project_id = "proj_demo_u1_001"

        # Create a wallet first
        client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json={
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLFilterType",
                "wallet_type": "analyst"
            },
            headers=auth_headers_user1
        )

        response = client.get(
            f"/v1/public/{project_id}/circle/wallets?wallet_type=analyst",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for wallet in data["wallets"]:
            assert wallet["wallet_type"] == "analyst"

    def test_filter_by_agent_did(self, client, auth_headers_user1):
        """Test filtering wallets by agent DID."""
        project_id = "proj_demo_u1_001"
        agent_did = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLFilterDID"

        # Create a wallet for this agent
        client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json={"agent_did": agent_did, "wallet_type": "compliance"},
            headers=auth_headers_user1
        )

        response = client.get(
            f"/v1/public/{project_id}/circle/wallets?agent_did={agent_did}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for wallet in data["wallets"]:
            assert wallet["agent_did"] == agent_did


class TestCreateTransferEndpoint:
    """Test suite for POST /v1/public/{project_id}/circle/transfers endpoint."""

    @pytest.fixture
    def setup_wallets(self, client, auth_headers_user1):
        """Create source and destination wallets for transfer tests."""
        project_id = "proj_demo_u1_001"

        # Create source wallet
        source_response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json={
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLXfrSource",
                "wallet_type": "transaction"
            },
            headers=auth_headers_user1
        )
        source_wallet_id = source_response.json()["wallet_id"]

        # Create destination wallet
        dest_response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json={
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLXfrDest",
                "wallet_type": "analyst"
            },
            headers=auth_headers_user1
        )
        dest_wallet_id = dest_response.json()["wallet_id"]

        return {"source": source_wallet_id, "dest": dest_wallet_id}

    def test_create_transfer_successfully(self, client, auth_headers_user1, setup_wallets):
        """
        Test successful USDC transfer creation.
        Issue #114: X402 payments can trigger USDC transfers.
        """
        project_id = "proj_demo_u1_001"
        request_body = {
            "source_wallet_id": setup_wallets["source"],
            "destination_wallet_id": setup_wallets["dest"],
            "amount": "100.50",
            "currency": "USD"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/transfers",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "transfer_id" in data
        assert data["transfer_id"].startswith("transfer_")
        assert data["source_wallet_id"] == request_body["source_wallet_id"]
        assert data["destination_wallet_id"] == request_body["destination_wallet_id"]
        assert data["amount"] == request_body["amount"]
        assert data["status"] in ["pending", "complete"]
        assert "created_at" in data

    def test_link_transfer_to_x402_request(self, client, auth_headers_user1, setup_wallets):
        """Test linking transfer to X402 request."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "source_wallet_id": setup_wallets["source"],
            "destination_wallet_id": setup_wallets["dest"],
            "amount": "50.00",
            "x402_request_id": "x402_req_abc123"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/transfers",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["x402_request_id"] == "x402_req_abc123"

    def test_reject_invalid_amount(self, client, auth_headers_user1, setup_wallets):
        """Test that invalid amount format is rejected."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "source_wallet_id": setup_wallets["source"],
            "destination_wallet_id": setup_wallets["dest"],
            "amount": "invalid"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/transfers",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_reject_negative_amount(self, client, auth_headers_user1, setup_wallets):
        """Test that negative amount is rejected."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "source_wallet_id": setup_wallets["source"],
            "destination_wallet_id": setup_wallets["dest"],
            "amount": "-100.00"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/transfers",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_reject_zero_amount(self, client, auth_headers_user1, setup_wallets):
        """Test that zero amount is rejected."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "source_wallet_id": setup_wallets["source"],
            "destination_wallet_id": setup_wallets["dest"],
            "amount": "0"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/transfers",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_return_404_for_nonexistent_source_wallet(self, client, auth_headers_user1, setup_wallets):
        """Test that nonexistent source wallet returns 404."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "source_wallet_id": "wallet_nonexistent",
            "destination_wallet_id": setup_wallets["dest"],
            "amount": "100.00"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/transfers",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_return_401_for_missing_api_key(self, client, setup_wallets):
        """Test that missing API key returns 401."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "source_wallet_id": setup_wallets["source"],
            "destination_wallet_id": setup_wallets["dest"],
            "amount": "100.00"
        }

        response = client.post(
            f"/v1/public/{project_id}/circle/transfers",
            json=request_body
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetTransferEndpoint:
    """Test suite for GET /v1/public/{project_id}/circle/transfers/{transfer_id} endpoint."""

    def test_get_transfer_by_id(self, client, auth_headers_user1):
        """Test retrieving transfer by ID."""
        project_id = "proj_demo_u1_001"

        # First create wallets
        source_response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json={
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGetXfr1",
                "wallet_type": "transaction"
            },
            headers=auth_headers_user1
        )
        source_id = source_response.json()["wallet_id"]

        dest_response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json={
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGetXfr2",
                "wallet_type": "analyst"
            },
            headers=auth_headers_user1
        )
        dest_id = dest_response.json()["wallet_id"]

        # Create transfer
        transfer_response = client.post(
            f"/v1/public/{project_id}/circle/transfers",
            json={
                "source_wallet_id": source_id,
                "destination_wallet_id": dest_id,
                "amount": "75.00"
            },
            headers=auth_headers_user1
        )
        transfer_id = transfer_response.json()["transfer_id"]

        # Get transfer
        response = client.get(
            f"/v1/public/{project_id}/circle/transfers/{transfer_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["transfer_id"] == transfer_id
        assert "status" in data
        assert "amount" in data

    def test_return_404_for_nonexistent_transfer(self, client, auth_headers_user1):
        """Test that nonexistent transfer returns 404."""
        project_id = "proj_demo_u1_001"

        response = client.get(
            f"/v1/public/{project_id}/circle/transfers/transfer_nonexistent",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "TRANSFER_NOT_FOUND"


class TestListTransfersEndpoint:
    """Test suite for GET /v1/public/{project_id}/circle/transfers endpoint."""

    def test_list_all_transfers(self, client, auth_headers_user1):
        """Test listing all transfers."""
        project_id = "proj_demo_u1_001"

        response = client.get(
            f"/v1/public/{project_id}/circle/transfers",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "transfers" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    def test_support_pagination(self, client, auth_headers_user1):
        """Test pagination support."""
        project_id = "proj_demo_u1_001"

        response = client.get(
            f"/v1/public/{project_id}/circle/transfers?limit=5&offset=0",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestCircleAPIIntegration:
    """Integration tests for complete Circle workflows."""

    def test_complete_full_payment_workflow(self, client, auth_headers_user1):
        """
        Test complete payment workflow:
        1. Create wallets for 3 agents
        2. Initiate transfer
        3. Verify transfer status
        """
        project_id = "proj_demo_u1_001"

        # Step 1: Create wallets for all 3 agent types
        agent_wallets = {}
        for wallet_type in ["analyst", "compliance", "transaction"]:
            response = client.post(
                f"/v1/public/{project_id}/circle/wallets",
                json={
                    "agent_did": f"did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKL{wallet_type.title()}Wf",
                    "wallet_type": wallet_type,
                    "description": f"{wallet_type.title()} agent wallet"
                },
                headers=auth_headers_user1
            )
            assert response.status_code == status.HTTP_201_CREATED
            agent_wallets[wallet_type] = response.json()

        # Verify all 3 wallets created
        assert len(agent_wallets) == 3
        assert all(w["status"] == "active" for w in agent_wallets.values())

        # Step 2: Initiate transfer from transaction to analyst
        transfer_response = client.post(
            f"/v1/public/{project_id}/circle/transfers",
            json={
                "source_wallet_id": agent_wallets["transaction"]["wallet_id"],
                "destination_wallet_id": agent_wallets["analyst"]["wallet_id"],
                "amount": "250.00",
                "x402_request_id": "x402_req_workflow_test"
            },
            headers=auth_headers_user1
        )
        assert transfer_response.status_code == status.HTTP_201_CREATED
        transfer = transfer_response.json()
        transfer_id = transfer["transfer_id"]

        # Step 3: Get transfer status
        status_response = client.get(
            f"/v1/public/{project_id}/circle/transfers/{transfer_id}",
            headers=auth_headers_user1
        )
        assert status_response.status_code == status.HTTP_200_OK
        assert status_response.json()["x402_request_id"] == "x402_req_workflow_test"

        # Step 4: List transfers should include our transfer
        list_response = client.get(
            f"/v1/public/{project_id}/circle/transfers",
            headers=auth_headers_user1
        )
        assert list_response.status_code == status.HTTP_200_OK
        transfer_ids = [t["transfer_id"] for t in list_response.json()["transfers"]]
        assert transfer_id in transfer_ids

    def test_handle_error_responses_consistently(self, client, auth_headers_user1):
        """
        Test that all error responses follow DX Contract format.
        All errors should return { detail, error_code }.
        """
        project_id = "proj_demo_u1_001"

        # 401 - Missing API key
        response = client.get(f"/v1/public/{project_id}/circle/wallets")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

        # 404 - Wallet not found
        response = client.get(
            f"/v1/public/{project_id}/circle/wallets/wallet_nonexistent",
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

        # 404 - Transfer not found
        response = client.get(
            f"/v1/public/{project_id}/circle/transfers/transfer_nonexistent",
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

        # 422 - Validation error
        response = client.post(
            f"/v1/public/{project_id}/circle/wallets",
            json={"invalid": "data"},
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
