"""
Tests for Issue #64: X402 requests linked to agent + task that produced them.

Test Coverage:
- GET /v1/public/{project_id}/agents/{agent_id}/x402-requests - Get all requests by agent
- Validates agent_id and task_id are required in X402RequestCreate
- Tests linkage integrity and filtering

TDD Approach (Red-Green-Refactor):
1. Write FAILING tests first
2. Implement functionality
3. Verify tests PASS
4. Coverage >= 80% required
"""
import pytest
from unittest.mock import patch
from fastapi import status


class TestAgentX402RequestsEndpoint:
    """Test suite for GET /v1/public/{project_id}/agents/{agent_id}/x402-requests endpoint."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, client, auth_headers_user1):
        """Create test X402 requests for multiple agents."""
        project_id = "proj_demo_user1_001"

        # Mock signature verification to always return True for test data setup
        with patch('app.api.x402_requests.DIDSigner.verify_signature', return_value=True):
            # Create requests for agent_alpha
            for i in range(3):
                client.post(
                    f"/v1/public/{project_id}/x402-requests",
                    json={
                        "agent_id": "agent_alpha",
                        "task_id": f"task_alpha_{i}",
                        "run_id": f"run_alpha_{i}",
                        "request_payload": {"amount": f"{100 * (i + 1)}.00"},
                        "signature": f"0xsig_alpha_{i}"
                    },
                    headers=auth_headers_user1
                )

            # Create requests for agent_beta
            for i in range(2):
                client.post(
                    f"/v1/public/{project_id}/x402-requests",
                    json={
                        "agent_id": "agent_beta",
                        "task_id": f"task_beta_{i}",
                        "run_id": f"run_beta_{i}",
                        "request_payload": {"amount": f"{200 * (i + 1)}.00"},
                        "signature": f"0xsig_beta_{i}"
                    },
                    headers=auth_headers_user1
                )

            # Create requests for agent_gamma
            client.post(
                f"/v1/public/{project_id}/x402-requests",
                json={
                    "agent_id": "agent_gamma",
                    "task_id": "task_gamma_1",
                    "run_id": "run_gamma_1",
                    "request_payload": {"amount": "500.00"},
                    "signature": "0xsig_gamma_1"
                },
                headers=auth_headers_user1
            )

    def test_get_requests_by_agent_success(self, client, auth_headers_user1):
        """
        Test GET /agents/{agent_id}/x402-requests returns all requests for agent.
        Issue #64: Verify endpoint returns all X402 requests by agent_id.
        """
        project_id = "proj_demo_user1_001"
        agent_id = "agent_alpha"

        response = client.get(
            f"/v1/public/{project_id}/agents/{agent_id}/x402-requests",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "requests" in data
        assert "total" in data
        assert data["total"] == 3

        # All requests should be for agent_alpha
        for request in data["requests"]:
            assert request["agent_id"] == "agent_alpha"

    def test_get_requests_by_agent_different_agent(self, client, auth_headers_user1):
        """
        Test GET /agents/{agent_id}/x402-requests for agent_beta.
        Issue #64: Verify agent-specific filtering works correctly.
        """
        project_id = "proj_demo_user1_001"
        agent_id = "agent_beta"

        response = client.get(
            f"/v1/public/{project_id}/agents/{agent_id}/x402-requests",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 2

        # All requests should be for agent_beta
        for request in data["requests"]:
            assert request["agent_id"] == "agent_beta"

    def test_get_requests_by_agent_no_requests(self, client, auth_headers_user1):
        """
        Test GET /agents/{agent_id}/x402-requests for agent with no requests.
        Issue #64: Verify endpoint returns empty list for agents with no requests.
        """
        project_id = "proj_demo_user1_001"
        agent_id = "agent_nonexistent"

        response = client.get(
            f"/v1/public/{project_id}/agents/{agent_id}/x402-requests",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 0
        assert len(data["requests"]) == 0


class TestX402LinkageIntegrity:
    """Test suite for validating agent_id and task_id linkage integrity."""

    def test_create_request_agent_id_required(self, client, auth_headers_user1):
        """
        Test that agent_id is required when creating X402 request.
        Issue #64: Validate agent_id is mandatory.
        """
        project_id = "proj_demo_user1_001"
        request_data = {
            # Missing agent_id
            "task_id": "task_missing_agent",
            "run_id": "run_missing_agent",
            "request_payload": {"amount": "100.00"},
            "signature": "0xsig_missing_agent"
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_request_task_id_required(self, client, auth_headers_user1):
        """
        Test that task_id is required when creating X402 request.
        Issue #64: Validate task_id is mandatory.
        """
        project_id = "proj_demo_user1_001"
        request_data = {
            "agent_id": "agent_missing_task",
            # Missing task_id
            "run_id": "run_missing_task",
            "request_payload": {"amount": "100.00"},
            "signature": "0xsig_missing_task"
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_single_request_returns_agent_and_task(self, client, auth_headers_user1):
        """
        Test GET /x402-requests/{request_id} returns linked agent and task info.
        Issue #64: Verify single request retrieval includes agent_id and task_id.
        """
        project_id = "proj_demo_user1_001"

        # Create request
        request_data = {
            "agent_id": "agent_linkage_test",
            "task_id": "task_linkage_test",
            "run_id": "run_linkage_test",
            "request_payload": {"amount": "999.99"},
            "signature": "0xsig_linkage_test"
        }

        with patch('app.api.x402_requests.DIDSigner.verify_signature', return_value=True):
            create_response = client.post(
                f"/v1/public/{project_id}/x402-requests",
                json=request_data,
                headers=auth_headers_user1
            )

        assert create_response.status_code == status.HTTP_201_CREATED
        request_id = create_response.json()["request_id"]

        # Get single request
        get_response = client.get(
            f"/v1/public/{project_id}/x402-requests/{request_id}",
            headers=auth_headers_user1
        )

        assert get_response.status_code == status.HTTP_200_OK

        data = get_response.json()
        assert data["agent_id"] == "agent_linkage_test"
        assert data["task_id"] == "task_linkage_test"
