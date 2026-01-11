"""
Comprehensive tests for X402 Request Linking API.
Tests Epic 12 Issue 4: X402 requests linked to agent + task.

Test Coverage:
- POST /v1/public/{project_id}/x402-requests - Create X402 request
- GET /v1/public/{project_id}/x402-requests - List requests with filters
- GET /v1/public/{project_id}/x402-requests/{request_id} - Get single request with links

Tests all statuses: PENDING, APPROVED, REJECTED, EXPIRED, COMPLETED
Tests filtering by agent_id, task_id, run_id, status
Tests linking to agent_memory and compliance_events records
Tests error cases: request not found, invalid status
"""
import pytest
from fastapi import status


class TestCreateX402Request:
    """Test suite for POST /v1/public/{project_id}/x402-requests endpoint."""

    def test_create_x402_request_success(self, client, auth_headers_user1):
        """
        Test successful creation of X402 request.
        Epic 12 Issue 4: Create X402 request linked to agent and task.
        """
        project_id = "proj_demo_user1_001"
        request_data = {
            "agent_id": "did:ethr:0xabc123def456",
            "task_id": "task_payment_001",
            "run_id": "run_2026_01_10_001",
            "request_payload": {
                "type": "payment_authorization",
                "amount": "100.00",
                "currency": "USD",
                "recipient": "did:ethr:0xdef789abc012",
                "memo": "Service payment for task completion"
            },
            "signature": "0xsig123abc456def789...",
            "status": "PENDING",
            "linked_memory_ids": ["mem_abc123", "mem_def456"],
            "linked_compliance_ids": ["comp_evt_001"],
            "metadata": {
                "priority": "high",
                "source": "payment_agent"
            }
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "request_id" in data
        assert data["project_id"] == project_id
        assert data["agent_id"] == request_data["agent_id"]
        assert data["task_id"] == request_data["task_id"]
        assert data["run_id"] == request_data["run_id"]
        assert data["request_payload"] == request_data["request_payload"]
        assert data["signature"] == request_data["signature"]
        assert data["status"] == "PENDING"
        assert "timestamp" in data
        assert data["linked_memory_ids"] == request_data["linked_memory_ids"]
        assert data["linked_compliance_ids"] == request_data["linked_compliance_ids"]
        assert data["metadata"] == request_data["metadata"]

    def test_create_x402_request_minimal(self, client, auth_headers_user1):
        """
        Test creation with minimal required fields.
        Linked IDs and metadata are optional.
        """
        project_id = "proj_demo_user1_001"
        request_data = {
            "agent_id": "did:ethr:0xminimal123",
            "task_id": "task_minimal_001",
            "run_id": "run_minimal_001",
            "request_payload": {
                "type": "payment_authorization",
                "amount": "50.00"
            },
            "signature": "0xsigMinimal123..."
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["agent_id"] == request_data["agent_id"]
        assert data["status"] == "PENDING"  # Default status
        assert data["linked_memory_ids"] == []
        assert data["linked_compliance_ids"] == []
        assert data["metadata"] is None

    def test_create_x402_request_all_statuses(self, client, auth_headers_user1):
        """
        Test creation with all valid status values.
        Statuses: PENDING, APPROVED, REJECTED, EXPIRED, COMPLETED
        """
        project_id = "proj_demo_user1_001"
        statuses = ["PENDING", "APPROVED", "REJECTED", "EXPIRED", "COMPLETED"]

        for idx, test_status in enumerate(statuses):
            request_data = {
                "agent_id": f"did:ethr:0xstatus{idx}",
                "task_id": f"task_status_{idx}",
                "run_id": f"run_status_{idx}",
                "request_payload": {"type": "payment", "amount": "10.00"},
                "signature": f"0xsigStatus{idx}",
                "status": test_status
            }

            response = client.post(
                f"/v1/public/{project_id}/x402-requests",
                json=request_data,
                headers=auth_headers_user1
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["status"] == test_status

    def test_create_x402_request_empty_payload_fails(self, client, auth_headers_user1):
        """
        Test that empty request_payload is rejected.
        Validation: request_payload cannot be empty.
        """
        project_id = "proj_demo_user1_001"
        request_data = {
            "agent_id": "did:ethr:0xempty123",
            "task_id": "task_empty_001",
            "run_id": "run_empty_001",
            "request_payload": {},  # Empty payload
            "signature": "0xsigEmpty123..."
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_x402_request_empty_signature_fails(self, client, auth_headers_user1):
        """
        Test that empty signature is rejected.
        Validation: signature cannot be empty or whitespace.
        """
        project_id = "proj_demo_user1_001"
        request_data = {
            "agent_id": "did:ethr:0xnosig123",
            "task_id": "task_nosig_001",
            "run_id": "run_nosig_001",
            "request_payload": {"type": "payment", "amount": "10.00"},
            "signature": "   "  # Whitespace only
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_x402_request_missing_required_field(self, client, auth_headers_user1):
        """
        Test that missing required fields are rejected.
        Required: agent_id, task_id, run_id, request_payload, signature
        """
        project_id = "proj_demo_user1_001"

        # Missing agent_id
        request_data = {
            "task_id": "task_missing_001",
            "run_id": "run_missing_001",
            "request_payload": {"type": "payment"},
            "signature": "0xsigMissing..."
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_x402_request_missing_api_key(self, client):
        """
        Test missing X-API-Key header returns 401.
        Authentication requirement for X402 API.
        """
        project_id = "proj_demo_user1_001"
        request_data = {
            "agent_id": "did:ethr:0xnoauth123",
            "task_id": "task_noauth_001",
            "run_id": "run_noauth_001",
            "request_payload": {"type": "payment"},
            "signature": "0xsigNoAuth..."
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_create_x402_request_with_memory_links(self, client, auth_headers_user1):
        """
        Test creation with linked agent_memory records.
        Epic 12 Issue 4: Link X402 requests to agent memory.
        """
        project_id = "proj_demo_user1_001"
        request_data = {
            "agent_id": "did:ethr:0xmemory123",
            "task_id": "task_memory_001",
            "run_id": "run_memory_001",
            "request_payload": {"type": "payment", "amount": "200.00"},
            "signature": "0xsigMemory...",
            "linked_memory_ids": ["mem_001", "mem_002", "mem_003"]
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert len(data["linked_memory_ids"]) == 3
        assert "mem_001" in data["linked_memory_ids"]
        assert "mem_002" in data["linked_memory_ids"]
        assert "mem_003" in data["linked_memory_ids"]

    def test_create_x402_request_with_compliance_links(self, client, auth_headers_user1):
        """
        Test creation with linked compliance_events records.
        Epic 12 Issue 4: Link X402 requests to compliance events.
        """
        project_id = "proj_demo_user1_001"
        request_data = {
            "agent_id": "did:ethr:0xcompliance123",
            "task_id": "task_compliance_001",
            "run_id": "run_compliance_001",
            "request_payload": {"type": "payment", "amount": "150.00"},
            "signature": "0xsigCompliance...",
            "linked_compliance_ids": ["comp_001", "comp_002"]
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert len(data["linked_compliance_ids"]) == 2
        assert "comp_001" in data["linked_compliance_ids"]
        assert "comp_002" in data["linked_compliance_ids"]


class TestListX402Requests:
    """Test suite for GET /v1/public/{project_id}/x402-requests endpoint."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, client, auth_headers_user1):
        """Create test X402 requests for filtering tests."""
        # Clean up previous test data
        from app.services.x402_service import x402_service
        x402_service._request_store.clear()

        project_id = "proj_demo_user1_001"

        # Create requests with different agents, tasks, runs, statuses
        test_requests = [
            {
                "agent_id": "agent_001",
                "task_id": "task_001",
                "run_id": "run_001",
                "status": "PENDING",
                "request_payload": {"amount": "100.00"},
                "signature": "0xsig1"
            },
            {
                "agent_id": "agent_001",
                "task_id": "task_001",
                "run_id": "run_001",
                "status": "APPROVED",
                "request_payload": {"amount": "200.00"},
                "signature": "0xsig2"
            },
            {
                "agent_id": "agent_001",
                "task_id": "task_002",
                "run_id": "run_002",
                "status": "COMPLETED",
                "request_payload": {"amount": "300.00"},
                "signature": "0xsig3"
            },
            {
                "agent_id": "agent_002",
                "task_id": "task_003",
                "run_id": "run_003",
                "status": "REJECTED",
                "request_payload": {"amount": "400.00"},
                "signature": "0xsig4"
            },
            {
                "agent_id": "agent_002",
                "task_id": "task_003",
                "run_id": "run_003",
                "status": "EXPIRED",
                "request_payload": {"amount": "500.00"},
                "signature": "0xsig5"
            },
        ]

        for req_data in test_requests:
            client.post(
                f"/v1/public/{project_id}/x402-requests",
                json=req_data,
                headers=auth_headers_user1
            )

    def test_list_all_requests(self, client, auth_headers_user1):
        """
        Test listing all X402 requests without filters.
        Should return all requests with pagination metadata.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "requests" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        # Should have 5 requests from setup
        assert data["total"] == 5
        assert len(data["requests"]) == 5
        assert data["limit"] == 100
        assert data["offset"] == 0

    def test_list_requests_filter_by_agent_id(self, client, auth_headers_user1):
        """
        Test filtering requests by agent_id.
        Epic 12 Issue 4: Filter X402 requests by agent.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?agent_id=agent_001",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 3  # agent_001 has 3 requests
        assert len(data["requests"]) == 3

        # All requests should be for agent_001
        for request in data["requests"]:
            assert request["agent_id"] == "agent_001"

    def test_list_requests_filter_by_task_id(self, client, auth_headers_user1):
        """
        Test filtering requests by task_id.
        Epic 12 Issue 4: Filter X402 requests by task.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?task_id=task_001",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 2  # task_001 has 2 requests
        assert len(data["requests"]) == 2

        # All requests should be for task_001
        for request in data["requests"]:
            assert request["task_id"] == "task_001"

    def test_list_requests_filter_by_run_id(self, client, auth_headers_user1):
        """
        Test filtering requests by run_id.
        Epic 12 Issue 4: Filter X402 requests by run.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?run_id=run_003",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 2  # run_003 has 2 requests
        assert len(data["requests"]) == 2

        # All requests should be for run_003
        for request in data["requests"]:
            assert request["run_id"] == "run_003"

    def test_list_requests_filter_by_status_pending(self, client, auth_headers_user1):
        """
        Test filtering requests by status PENDING.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?status=PENDING",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 1
        assert len(data["requests"]) == 1
        assert data["requests"][0]["status"] == "PENDING"

    def test_list_requests_filter_by_status_approved(self, client, auth_headers_user1):
        """
        Test filtering requests by status APPROVED.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?status=APPROVED",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 1
        assert data["requests"][0]["status"] == "APPROVED"

    def test_list_requests_filter_by_status_rejected(self, client, auth_headers_user1):
        """
        Test filtering requests by status REJECTED.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?status=REJECTED",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 1
        assert data["requests"][0]["status"] == "REJECTED"

    def test_list_requests_filter_by_status_expired(self, client, auth_headers_user1):
        """
        Test filtering requests by status EXPIRED.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?status=EXPIRED",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 1
        assert data["requests"][0]["status"] == "EXPIRED"

    def test_list_requests_filter_by_status_completed(self, client, auth_headers_user1):
        """
        Test filtering requests by status COMPLETED.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?status=COMPLETED",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 1
        assert data["requests"][0]["status"] == "COMPLETED"

    def test_list_requests_combined_filters(self, client, auth_headers_user1):
        """
        Test combining multiple filters (agent_id + task_id).
        Filters should be combined with AND logic.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?agent_id=agent_001&task_id=task_001",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 2

        # All results should match both filters
        for request in data["requests"]:
            assert request["agent_id"] == "agent_001"
            assert request["task_id"] == "task_001"

    def test_list_requests_pagination_limit(self, client, auth_headers_user1):
        """
        Test pagination with custom limit.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?limit=2",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 5  # Total count unchanged
        assert len(data["requests"]) == 2  # Limited to 2
        assert data["limit"] == 2

    def test_list_requests_pagination_offset(self, client, auth_headers_user1):
        """
        Test pagination with offset.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests?limit=2&offset=2",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 5
        assert len(data["requests"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 2

    def test_list_requests_missing_api_key(self, client):
        """
        Test missing X-API-Key header returns 401.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(f"/v1/public/{project_id}/x402-requests")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_list_requests_empty_project(self, client, auth_headers_user1):
        """
        Test listing requests from project with no requests.
        """
        project_id = "proj_empty_12345"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 0
        assert len(data["requests"]) == 0

    def test_list_requests_response_schema(self, client, auth_headers_user1):
        """
        Test response schema matches documented contract.
        """
        project_id = "proj_demo_user1_001"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Top-level schema
        assert set(data.keys()) == {"requests", "total", "limit", "offset"}

        # Requests array
        assert isinstance(data["requests"], list)

        # Each request schema
        for request in data["requests"]:
            required_fields = {
                "request_id", "project_id", "agent_id", "task_id", "run_id",
                "request_payload", "signature", "status", "timestamp",
                "linked_memory_ids", "linked_compliance_ids", "metadata"
            }
            assert required_fields.issubset(set(request.keys()))


class TestGetSingleX402Request:
    """Test suite for GET /v1/public/{project_id}/x402-requests/{request_id} endpoint."""

    @pytest.fixture
    def created_request(self, client, auth_headers_user1):
        """Create a test request with links."""
        project_id = "proj_demo_user1_001"
        request_data = {
            "agent_id": "agent_single_test",
            "task_id": "task_single_test",
            "run_id": "run_single_test",
            "request_payload": {"amount": "999.00", "type": "test"},
            "signature": "0xsigSingleTest",
            "status": "COMPLETED",
            "linked_memory_ids": ["mem_single_001", "mem_single_002"],
            "linked_compliance_ids": ["comp_single_001"]
        }

        response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        return response.json()

    def test_get_single_request_success(self, client, auth_headers_user1, created_request):
        """
        Test successfully retrieving a single X402 request.
        Epic 12 Issue 4: Get X402 request with linked records.
        """
        project_id = "proj_demo_user1_001"
        request_id = created_request["request_id"]

        response = client.get(
            f"/v1/public/{project_id}/x402-requests/{request_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["request_id"] == request_id
        assert data["agent_id"] == "agent_single_test"
        assert data["task_id"] == "task_single_test"
        assert data["run_id"] == "run_single_test"
        assert data["status"] == "COMPLETED"

    def test_get_single_request_with_linked_memories(self, client, auth_headers_user1, created_request):
        """
        Test that linked_memories are included in response.
        Epic 12 Issue 4: Include full linked agent_memory records.
        """
        project_id = "proj_demo_user1_001"
        request_id = created_request["request_id"]

        response = client.get(
            f"/v1/public/{project_id}/x402-requests/{request_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "linked_memories" in data
        assert isinstance(data["linked_memories"], list)
        assert len(data["linked_memories"]) == 2

        # Verify memory record structure
        for memory in data["linked_memories"]:
            assert "memory_id" in memory
            assert "content" in memory
            assert "created_at" in memory

    def test_get_single_request_with_linked_compliance_events(self, client, auth_headers_user1, created_request):
        """
        Test that linked_compliance_events are included in response.
        Epic 12 Issue 4: Include full linked compliance_events records.
        """
        project_id = "proj_demo_user1_001"
        request_id = created_request["request_id"]

        response = client.get(
            f"/v1/public/{project_id}/x402-requests/{request_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "linked_compliance_events" in data
        assert isinstance(data["linked_compliance_events"], list)
        assert len(data["linked_compliance_events"]) == 1

        # Verify compliance event structure
        for event in data["linked_compliance_events"]:
            assert "event_id" in event
            assert "event_type" in event
            assert "passed" in event
            assert "created_at" in event

    def test_get_single_request_not_found(self, client, auth_headers_user1):
        """
        Test requesting non-existent request returns 404.
        Error case: X402_REQUEST_NOT_FOUND
        """
        project_id = "proj_demo_user1_001"
        request_id = "x402_req_nonexistent"

        response = client.get(
            f"/v1/public/{project_id}/x402-requests/{request_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "X402_REQUEST_NOT_FOUND"
        assert request_id in data["detail"]

    def test_get_single_request_wrong_project(self, client, auth_headers_user1, created_request):
        """
        Test requesting request from wrong project returns 404.
        """
        project_id = "proj_wrong_12345"
        request_id = created_request["request_id"]

        response = client.get(
            f"/v1/public/{project_id}/x402-requests/{request_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert data["error_code"] == "X402_REQUEST_NOT_FOUND"

    def test_get_single_request_missing_api_key(self, client, created_request):
        """
        Test missing X-API-Key header returns 401.
        """
        project_id = "proj_demo_user1_001"
        request_id = created_request["request_id"]

        response = client.get(
            f"/v1/public/{project_id}/x402-requests/{request_id}"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_get_single_request_response_schema(self, client, auth_headers_user1, created_request):
        """
        Test response schema includes all expected fields.
        Response should have base fields + linked_memories + linked_compliance_events.
        """
        project_id = "proj_demo_user1_001"
        request_id = created_request["request_id"]

        response = client.get(
            f"/v1/public/{project_id}/x402-requests/{request_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Base fields (from X402RequestResponse)
        base_fields = {
            "request_id", "project_id", "agent_id", "task_id", "run_id",
            "request_payload", "signature", "status", "timestamp",
            "linked_memory_ids", "linked_compliance_ids", "metadata"
        }

        # Extended fields (from X402RequestWithLinks)
        extended_fields = {"linked_memories", "linked_compliance_events"}

        all_required_fields = base_fields.union(extended_fields)
        assert all_required_fields.issubset(set(data.keys()))


class TestX402RequestsIntegration:
    """Integration tests for complete X402 request workflows."""

    def test_create_and_retrieve_workflow(self, client, auth_headers_user1):
        """
        Test complete workflow: create request, list it, retrieve single.
        """
        project_id = "proj_demo_user1_001"

        # Step 1: Create request
        request_data = {
            "agent_id": "agent_workflow_test",
            "task_id": "task_workflow_test",
            "run_id": "run_workflow_test",
            "request_payload": {"amount": "777.77"},
            "signature": "0xsigWorkflow"
        }

        create_response = client.post(
            f"/v1/public/{project_id}/x402-requests",
            json=request_data,
            headers=auth_headers_user1
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        created_data = create_response.json()
        request_id = created_data["request_id"]

        # Step 2: List all requests (should include newly created)
        list_response = client.get(
            f"/v1/public/{project_id}/x402-requests",
            headers=auth_headers_user1
        )

        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()

        request_ids = [req["request_id"] for req in list_data["requests"]]
        assert request_id in request_ids

        # Step 3: Get single request
        get_response = client.get(
            f"/v1/public/{project_id}/x402-requests/{request_id}",
            headers=auth_headers_user1
        )

        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()
        assert get_data["request_id"] == request_id
        assert get_data["agent_id"] == request_data["agent_id"]

    def test_filter_by_multiple_criteria(self, client, auth_headers_user1):
        """
        Test creating multiple requests and filtering by various criteria.
        """
        project_id = "proj_demo_user1_001"

        # Create requests with specific patterns
        agent_id = "agent_filter_test"
        task_id_1 = "task_filter_a"
        task_id_2 = "task_filter_b"

        # Create 3 requests for task_a, 2 for task_b
        for i in range(3):
            client.post(
                f"/v1/public/{project_id}/x402-requests",
                json={
                    "agent_id": agent_id,
                    "task_id": task_id_1,
                    "run_id": f"run_{i}",
                    "request_payload": {"index": i},
                    "signature": f"0xsig{i}"
                },
                headers=auth_headers_user1
            )

        for i in range(2):
            client.post(
                f"/v1/public/{project_id}/x402-requests",
                json={
                    "agent_id": agent_id,
                    "task_id": task_id_2,
                    "run_id": f"run_{i}",
                    "request_payload": {"index": i},
                    "signature": f"0xsigB{i}"
                },
                headers=auth_headers_user1
            )

        # Filter by agent only - should get 5
        response = client.get(
            f"/v1/public/{project_id}/x402-requests?agent_id={agent_id}",
            headers=auth_headers_user1
        )
        assert response.json()["total"] == 5

        # Filter by agent + task_a - should get 3
        response = client.get(
            f"/v1/public/{project_id}/x402-requests?agent_id={agent_id}&task_id={task_id_1}",
            headers=auth_headers_user1
        )
        assert response.json()["total"] == 3

        # Filter by agent + task_b - should get 2
        response = client.get(
            f"/v1/public/{project_id}/x402-requests?agent_id={agent_id}&task_id={task_id_2}",
            headers=auth_headers_user1
        )
        assert response.json()["total"] == 2

    def test_timestamp_ordering(self, client, auth_headers_user1):
        """
        Test that requests are returned in descending timestamp order (newest first).
        """
        project_id = "proj_demo_user1_001"

        # Create 3 requests sequentially
        request_ids = []
        for i in range(3):
            response = client.post(
                f"/v1/public/{project_id}/x402-requests",
                json={
                    "agent_id": f"agent_order_{i}",
                    "task_id": "task_order",
                    "run_id": "run_order",
                    "request_payload": {"order": i},
                    "signature": f"0xsigOrder{i}"
                },
                headers=auth_headers_user1
            )
            request_ids.append(response.json()["request_id"])

        # List all requests
        response = client.get(
            f"/v1/public/{project_id}/x402-requests?task_id=task_order",
            headers=auth_headers_user1
        )

        data = response.json()
        returned_ids = [req["request_id"] for req in data["requests"]]

        # Most recent should be first (reversed order)
        assert returned_ids[0] == request_ids[2]
        assert returned_ids[1] == request_ids[1]
        assert returned_ids[2] == request_ids[0]
