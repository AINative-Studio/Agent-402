"""
Integration tests for X402 signature verification.
Tests the complete flow of creating and verifying X402 requests with DID signatures.

Implements Issue #75: DID-based ECDSA Signing and Verification.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.did_signer import DIDSigner


# Test API Key (from config)
TEST_API_KEY = "demo_key_user1_abc123"
TEST_PROJECT_ID = "test_project_123"


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_keypair():
    """Generate valid keypair for testing."""
    return DIDSigner.generate_keypair()


@pytest.fixture
def valid_x402_payload():
    """Create valid X402 request payload."""
    return {
        "type": "payment_authorization",
        "amount": "100.00",
        "currency": "USD",
        "recipient": "did:ethr:0xdef789abc012",
        "memo": "Payment for services rendered"
    }


class TestX402SignatureVerification:
    """Test X402 signature verification in API endpoints."""

    def test_create_x402_request_with_valid_signature(
        self,
        client,
        valid_keypair,
        valid_x402_payload
    ):
        """Should accept X402 request with valid signature."""
        private_key, did = valid_keypair

        # Sign the payload
        signature = DIDSigner.sign_payload(valid_x402_payload, private_key)

        # Create X402 request
        request_data = {
            "agent_id": did,
            "task_id": "task_payment_001",
            "run_id": "run_2026_01_11_001",
            "request_payload": valid_x402_payload,
            "signature": signature,
            "status": "PENDING"
        }

        # Make request to API
        response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/x402-requests",
            json=request_data,
            headers={"X-API-Key": TEST_API_KEY}
        )

        # Should succeed
        assert response.status_code == 201
        data = response.json()

        assert data["agent_id"] == did
        assert data["signature"] == signature
        assert data["status"] == "PENDING"

        # Should have verification metadata
        metadata = data.get("metadata", {})
        assert metadata.get("signature_verified") is True

    def test_create_x402_request_with_invalid_signature(
        self,
        client,
        valid_keypair,
        valid_x402_payload
    ):
        """Should reject X402 request with invalid signature."""
        private_key, did = valid_keypair

        # Sign the payload
        signature = DIDSigner.sign_payload(valid_x402_payload, private_key)

        # Tamper with signature
        tampered_signature = signature[:-2] + "ff"

        # Create X402 request with tampered signature
        request_data = {
            "agent_id": did,
            "task_id": "task_payment_001",
            "run_id": "run_2026_01_11_001",
            "request_payload": valid_x402_payload,
            "signature": tampered_signature,
            "status": "PENDING"
        }

        # Make request to API
        response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/x402-requests",
            json=request_data,
            headers={"X-API-Key": TEST_API_KEY}
        )

        # Should reject with 401
        assert response.status_code == 401
        data = response.json()

        assert "detail" in data
        assert "signature" in data["detail"].lower() or "invalid" in data["detail"].lower()

    def test_create_x402_request_with_wrong_did(
        self,
        client,
        valid_x402_payload
    ):
        """Should reject X402 request when signature doesn't match DID."""
        # Generate two different keypairs
        private_key1, did1 = DIDSigner.generate_keypair()
        private_key2, did2 = DIDSigner.generate_keypair()

        # Sign with first key
        signature = DIDSigner.sign_payload(valid_x402_payload, private_key1)

        # Try to use signature with second DID
        request_data = {
            "agent_id": did2,  # Different DID
            "task_id": "task_payment_001",
            "run_id": "run_2026_01_11_001",
            "request_payload": valid_x402_payload,
            "signature": signature,  # Signature from did1
            "status": "PENDING"
        }

        # Make request to API
        response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/x402-requests",
            json=request_data,
            headers={"X-API-Key": TEST_API_KEY}
        )

        # Should reject with 401
        assert response.status_code == 401

    def test_create_x402_request_with_tampered_payload(
        self,
        client,
        valid_keypair,
        valid_x402_payload
    ):
        """Should reject when payload is modified after signing."""
        private_key, did = valid_keypair

        # Sign the original payload
        signature = DIDSigner.sign_payload(valid_x402_payload, private_key)

        # Modify the payload
        tampered_payload = valid_x402_payload.copy()
        tampered_payload["amount"] = "200.00"  # Changed amount

        # Create X402 request with tampered payload
        request_data = {
            "agent_id": did,
            "task_id": "task_payment_001",
            "run_id": "run_2026_01_11_001",
            "request_payload": tampered_payload,  # Tampered
            "signature": signature,  # Original signature
            "status": "PENDING"
        }

        # Make request to API
        response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/x402-requests",
            json=request_data,
            headers={"X-API-Key": TEST_API_KEY}
        )

        # Should reject with 401
        assert response.status_code == 401

    def test_create_x402_request_with_malformed_signature(
        self,
        client,
        valid_keypair,
        valid_x402_payload
    ):
        """Should reject malformed signatures."""
        private_key, did = valid_keypair

        malformed_signatures = [
            "not_hex",
            "",
            "abc",
            "zzzz",
            "g" * 128,  # Invalid hex characters
        ]

        for malformed_sig in malformed_signatures:
            request_data = {
                "agent_id": did,
                "task_id": "task_payment_001",
                "run_id": "run_2026_01_11_001",
                "request_payload": valid_x402_payload,
                "signature": malformed_sig,
                "status": "PENDING"
            }

            response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/x402-requests",
                json=request_data,
                headers={"X-API-Key": TEST_API_KEY}
            )

            # Should reject
            assert response.status_code in [400, 401, 422], \
                f"Malformed signature '{malformed_sig}' should be rejected"

    def test_create_x402_request_with_invalid_did_format(
        self,
        client,
        valid_x402_payload
    ):
        """Should reject invalid DID formats."""
        private_key, valid_did = DIDSigner.generate_keypair()
        signature = DIDSigner.sign_payload(valid_x402_payload, private_key)

        invalid_dids = [
            "not_a_did",
            "did:invalid:format",
            "did:ethr:",  # Missing address
            "ethr:0x123",  # Missing did: prefix
            "",
        ]

        for invalid_did in invalid_dids:
            request_data = {
                "agent_id": invalid_did,
                "task_id": "task_payment_001",
                "run_id": "run_2026_01_11_001",
                "request_payload": valid_x402_payload,
                "signature": signature,
                "status": "PENDING"
            }

            response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/x402-requests",
                json=request_data,
                headers={"X-API-Key": TEST_API_KEY}
            )

            # Should reject
            assert response.status_code in [400, 401, 422], \
                f"Invalid DID '{invalid_did}' should be rejected"

    def test_signature_verification_performance(
        self,
        client,
        valid_keypair,
        valid_x402_payload
    ):
        """Should verify signatures efficiently (< 100ms per request)."""
        import time

        private_key, did = valid_keypair
        signature = DIDSigner.sign_payload(valid_x402_payload, private_key)

        request_data = {
            "agent_id": did,
            "task_id": "task_payment_001",
            "run_id": "run_2026_01_11_001",
            "request_payload": valid_x402_payload,
            "signature": signature,
            "status": "PENDING"
        }

        # Measure time for 5 requests
        start = time.time()
        for i in range(5):
            request_data["run_id"] = f"run_2026_01_11_{i:03d}"
            response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/x402-requests",
                json=request_data,
                headers={"X-API-Key": TEST_API_KEY}
            )
            assert response.status_code == 201

        elapsed = time.time() - start
        avg_time = elapsed / 5

        # Average should be under 100ms per request
        assert avg_time < 0.1, f"Signature verification too slow: {avg_time*1000:.2f}ms"


class TestEndToEndWorkflow:
    """Test complete end-to-end X402 workflow."""

    def test_complete_x402_workflow(self, client):
        """Should complete full workflow from keypair generation to request creation."""
        # 1. Generate keypair
        private_key, did = DIDSigner.generate_keypair()
        assert did.startswith("did:ethr:0x")

        # 2. Create payment payload
        payload = {
            "type": "payment_authorization",
            "amount": "250.00",
            "currency": "USD",
            "recipient": "did:ethr:0xabc123def456",
            "memo": "Consulting services Q1 2026",
            "timestamp": "2026-01-11T12:00:00Z"
        }

        # 3. Sign payload
        signature = DIDSigner.sign_payload(payload, private_key)
        assert len(signature) > 0

        # 4. Verify signature locally
        is_valid = DIDSigner.verify_signature(payload, signature, did)
        assert is_valid is True

        # 5. Create X402 request via API
        request_data = {
            "agent_id": did,
            "task_id": "consulting_payment_q1",
            "run_id": "run_2026_01_11_workflow",
            "request_payload": payload,
            "signature": signature,
            "status": "PENDING",
            "metadata": {
                "department": "consulting",
                "quarter": "Q1-2026"
            }
        }

        response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/x402-requests",
            json=request_data,
            headers={"X-API-Key": TEST_API_KEY}
        )

        # 6. Verify request was created successfully
        assert response.status_code == 201
        data = response.json()

        assert data["agent_id"] == did
        assert data["task_id"] == "consulting_payment_q1"
        assert data["signature"] == signature
        assert data["status"] == "PENDING"
        assert "request_id" in data

        # 7. Retrieve the created request
        request_id = data["request_id"]
        get_response = client.get(
            f"/v1/public/{TEST_PROJECT_ID}/x402-requests/{request_id}",
            headers={"X-API-Key": TEST_API_KEY}
        )

        assert get_response.status_code == 200
        retrieved = get_response.json()

        assert retrieved["request_id"] == request_id
        assert retrieved["agent_id"] == did
        assert retrieved["signature"] == signature
