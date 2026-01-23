"""
Tests for Enhanced Projects API - Issue #123.

TDD: Tests written FIRST before implementation.

Tests cover:
- Agent association/disassociation with projects
- Task tracking per project
- Payment linking and summary
- Status workflow (draft -> active -> completed -> archived)
- Error cases and validation
"""
import pytest
from fastapi import status


class TestProjectAgentAssociation:
    """Test suite for project-agent association endpoints."""

    def test_associate_agent_success(self, client, auth_headers_user1):
        """
        Test associating an agent with a project.
        POST /v1/public/projects/{id}/agents
        """
        # Use the demo project ID from project_store
        project_id = "proj_demo_u1_001"
        payload = {
            "agent_did": "did:example:agent123",
            "role": "executor"
        }

        response = client.post(
            f"/v1/public/projects/{project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["project_id"] == project_id
        assert data["agent_did"] == payload["agent_did"]
        assert data["role"] == payload["role"]
        assert "associated_at" in data

    def test_associate_agent_default_role(self, client, auth_headers_user1):
        """
        Test associating an agent with default role 'member'.
        """
        project_id = "proj_demo_u1_001"
        payload = {
            "agent_did": "did:example:agent456"
        }

        response = client.post(
            f"/v1/public/projects/{project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["role"] == "member"

    def test_associate_agent_duplicate_fails(self, client, auth_headers_user1):
        """
        Test that associating same agent twice returns 409 Conflict.
        """
        project_id = "proj_demo_u1_001"
        payload = {
            "agent_did": "did:example:duplicate_agent",
            "role": "executor"
        }

        # First association should succeed
        response1 = client.post(
            f"/v1/public/projects/{project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Second association should fail
        response2 = client.post(
            f"/v1/public/projects/{project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )
        assert response2.status_code == status.HTTP_409_CONFLICT

        data = response2.json()
        assert data["error_code"] == "AGENT_ALREADY_ASSOCIATED"

    def test_associate_agent_project_not_found(self, client, auth_headers_user1):
        """
        Test associating agent with non-existent project returns 404.
        """
        payload = {
            "agent_did": "did:example:agent789",
            "role": "executor"
        }

        response = client.post(
            "/v1/public/projects/nonexistent_project/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert data["error_code"] == "PROJECT_NOT_FOUND"

    def test_associate_agent_unauthorized(self, client, auth_headers_user2):
        """
        Test associating agent with another user's project returns 403.
        """
        # User 2 trying to access User 1's project
        project_id = "proj_demo_u1_001"
        payload = {
            "agent_did": "did:example:agent_unauth"
        }

        response = client.post(
            f"/v1/public/projects/{project_id}/agents",
            json=payload,
            headers=auth_headers_user2
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert data["error_code"] == "UNAUTHORIZED"

    def test_disassociate_agent_success(self, client, auth_headers_user1):
        """
        Test disassociating an agent from a project.
        DELETE /v1/public/projects/{id}/agents/{agent_did}
        """
        project_id = "proj_demo_u1_001"
        agent_did = "did:example:agent_to_remove"

        # First associate the agent
        client.post(
            f"/v1/public/projects/{project_id}/agents",
            json={"agent_did": agent_did, "role": "executor"},
            headers=auth_headers_user1
        )

        # Then disassociate
        response = client.delete(
            f"/v1/public/projects/{project_id}/agents/{agent_did}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_disassociate_agent_not_associated(self, client, auth_headers_user1):
        """
        Test disassociating an agent that was never associated returns 404.
        """
        project_id = "proj_demo_u1_001"
        agent_did = "did:example:never_associated"

        response = client.delete(
            f"/v1/public/projects/{project_id}/agents/{agent_did}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert data["error_code"] == "AGENT_NOT_ASSOCIATED"

    def test_list_project_agents_success(self, client, auth_headers_user1):
        """
        Test listing all agents associated with a project.
        GET /v1/public/projects/{id}/agents
        """
        project_id = "proj_demo_u1_001"

        # Associate some agents first
        agents = [
            {"agent_did": "did:example:list_agent1", "role": "executor"},
            {"agent_did": "did:example:list_agent2", "role": "observer"}
        ]
        for agent in agents:
            client.post(
                f"/v1/public/projects/{project_id}/agents",
                json=agent,
                headers=auth_headers_user1
            )

        # List agents
        response = client.get(
            f"/v1/public/projects/{project_id}/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "agents" in data
        assert "total" in data
        assert isinstance(data["agents"], list)
        assert data["total"] >= 2

    def test_list_project_agents_empty(self, client, auth_headers_user1):
        """
        Test listing agents for a project with no agents returns empty list.
        """
        project_id = "proj_demo_u1_002"

        response = client.get(
            f"/v1/public/projects/{project_id}/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["agents"] == []
        assert data["total"] == 0


class TestProjectTaskTracking:
    """Test suite for project task tracking endpoints."""

    def test_track_task_success(self, client, auth_headers_user1):
        """
        Test tracking a task under a project.
        POST /v1/public/projects/{id}/tasks
        """
        project_id = "proj_demo_u1_001"
        payload = {
            "task_id": "task_abc123",
            "status": "pending",
            "agent_did": "did:example:task_agent"
        }

        response = client.post(
            f"/v1/public/projects/{project_id}/tasks",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["project_id"] == project_id
        assert data["task_id"] == payload["task_id"]
        assert data["status"] == payload["status"]
        assert "tracked_at" in data

    def test_track_task_with_result(self, client, auth_headers_user1):
        """
        Test tracking a completed task with result.
        """
        project_id = "proj_demo_u1_001"
        payload = {
            "task_id": "task_completed_xyz",
            "status": "completed",
            "result": {"output": "success", "data": [1, 2, 3]}
        }

        response = client.post(
            f"/v1/public/projects/{project_id}/tasks",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] == payload["result"]

    def test_track_task_update_status(self, client, auth_headers_user1):
        """
        Test updating task status (retracking same task).
        """
        project_id = "proj_demo_u1_001"
        task_id = "task_update_test"

        # Initial tracking
        payload1 = {"task_id": task_id, "status": "pending"}
        response1 = client.post(
            f"/v1/public/projects/{project_id}/tasks",
            json=payload1,
            headers=auth_headers_user1
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Update tracking with new status
        payload2 = {"task_id": task_id, "status": "in_progress"}
        response2 = client.post(
            f"/v1/public/projects/{project_id}/tasks",
            json=payload2,
            headers=auth_headers_user1
        )
        assert response2.status_code == status.HTTP_201_CREATED
        assert response2.json()["status"] == "in_progress"

    def test_get_project_tasks(self, client, auth_headers_user1):
        """
        Test getting all tasks for a project.
        GET /v1/public/projects/{id}/tasks
        """
        project_id = "proj_demo_u1_001"

        # Track some tasks first
        tasks = [
            {"task_id": "get_task_1", "status": "completed"},
            {"task_id": "get_task_2", "status": "pending"},
            {"task_id": "get_task_3", "status": "in_progress"}
        ]
        for task in tasks:
            client.post(
                f"/v1/public/projects/{project_id}/tasks",
                json=task,
                headers=auth_headers_user1
            )

        # Get tasks
        response = client.get(
            f"/v1/public/projects/{project_id}/tasks",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert data["total"] >= 3

    def test_get_project_tasks_filter_by_status(self, client, auth_headers_user1):
        """
        Test filtering tasks by status.
        """
        project_id = "proj_demo_u1_001"

        # Get only completed tasks
        response = client.get(
            f"/v1/public/projects/{project_id}/tasks?status=completed",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        for task in data["tasks"]:
            assert task["status"] == "completed"


class TestProjectPaymentTracking:
    """Test suite for project payment tracking endpoints."""

    def test_link_payment_success(self, client, auth_headers_user1):
        """
        Test linking a payment receipt to a project.
        POST /v1/public/projects/{id}/payments
        """
        project_id = "proj_demo_u1_001"
        payload = {
            "payment_receipt_id": "x402_req_abc123",
            "amount": 100.50,
            "currency": "USD"
        }

        response = client.post(
            f"/v1/public/projects/{project_id}/payments",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["project_id"] == project_id
        assert data["payment_receipt_id"] == payload["payment_receipt_id"]
        assert data["amount"] == payload["amount"]
        assert "linked_at" in data

    def test_get_payment_summary(self, client, auth_headers_user1):
        """
        Test getting payment summary for a project.
        GET /v1/public/projects/{id}/payments
        """
        project_id = "proj_demo_u1_001"

        # Link some payments first
        payments = [
            {"payment_receipt_id": "pay_1", "amount": 50.00, "currency": "USD"},
            {"payment_receipt_id": "pay_2", "amount": 75.25, "currency": "USD"},
            {"payment_receipt_id": "pay_3", "amount": 100.00, "currency": "USD"}
        ]
        for payment in payments:
            client.post(
                f"/v1/public/projects/{project_id}/payments",
                json=payment,
                headers=auth_headers_user1
            )

        # Get summary
        response = client.get(
            f"/v1/public/projects/{project_id}/payments",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "total_spent" in data
        assert "payment_count" in data
        assert "payments" in data
        assert data["payment_count"] >= 3
        assert data["total_spent"] >= 225.25


class TestProjectStatusWorkflow:
    """Test suite for project status workflow."""

    def test_update_status_draft_to_active(self, client, auth_headers_user1):
        """
        Test updating project status from draft to active.
        PATCH /v1/public/projects/{id}/status
        """
        project_id = "proj_demo_u1_001"
        payload = {"status": "ACTIVE"}

        response = client.patch(
            f"/v1/public/projects/{project_id}/status",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["id"] == project_id
        assert data["status"] == "ACTIVE"

    def test_update_status_active_to_completed(self, client, auth_headers_user1):
        """
        Test updating project status from active to completed.
        """
        project_id = "proj_demo_u1_001"
        payload = {"status": "COMPLETED"}

        response = client.patch(
            f"/v1/public/projects/{project_id}/status",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "COMPLETED"

    def test_update_status_to_archived(self, client, auth_headers_user1):
        """
        Test archiving a project.
        """
        project_id = "proj_demo_u1_001"
        payload = {"status": "ARCHIVED"}

        response = client.patch(
            f"/v1/public/projects/{project_id}/status",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "ARCHIVED"

    def test_update_status_invalid_status(self, client, auth_headers_user1):
        """
        Test updating to an invalid status returns 422.
        """
        project_id = "proj_demo_u1_001"
        payload = {"status": "invalid_status"}

        response = client.patch(
            f"/v1/public/projects/{project_id}/status",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_status_unauthorized(self, client, auth_headers_user2):
        """
        Test updating another user's project status returns 403.
        """
        project_id = "proj_demo_u1_001"
        payload = {"status": "ACTIVE"}

        response = client.patch(
            f"/v1/public/projects/{project_id}/status",
            json=payload,
            headers=auth_headers_user2
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestProjectAPIErrorHandling:
    """Test suite for error handling across all new endpoints."""

    def test_missing_api_key_agents_endpoint(self, client):
        """
        Test missing API key returns 401 for agents endpoint.
        """
        response = client.get("/v1/public/projects/proj_demo_u1_001/agents")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_missing_api_key_tasks_endpoint(self, client):
        """
        Test missing API key returns 401 for tasks endpoint.
        """
        response = client.get("/v1/public/projects/proj_demo_u1_001/tasks")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_api_key_payments_endpoint(self, client):
        """
        Test missing API key returns 401 for payments endpoint.
        """
        response = client.get("/v1/public/projects/proj_demo_u1_001/payments")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_project_id_format(self, client, auth_headers_user1):
        """
        Test that endpoints handle any project_id format.
        (They return 404 if not found, not validation error)
        """
        response = client.get(
            "/v1/public/projects/any-format-id/agents",
            headers=auth_headers_user1
        )

        # Should return 404 (not found), not 422 (validation error)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProjectAgentRoleValidation:
    """Test suite for agent role validation."""

    def test_valid_roles(self, client, auth_headers_user1):
        """
        Test that valid roles are accepted.
        """
        project_id = "proj_demo_u1_001"
        valid_roles = ["executor", "observer", "admin", "member"]

        for i, role in enumerate(valid_roles):
            payload = {
                "agent_did": f"did:example:role_test_{i}",
                "role": role
            }
            response = client.post(
                f"/v1/public/projects/{project_id}/agents",
                json=payload,
                headers=auth_headers_user1
            )
            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["role"] == role

    def test_invalid_role_rejected(self, client, auth_headers_user1):
        """
        Test that invalid roles are rejected.
        """
        project_id = "proj_demo_u1_001"
        payload = {
            "agent_did": "did:example:invalid_role",
            "role": "superadmin"  # Invalid role
        }

        response = client.post(
            f"/v1/public/projects/{project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestBackwardCompatibility:
    """Test suite ensuring backward compatibility with existing endpoints."""

    def test_list_projects_still_works(self, client, auth_headers_user1):
        """
        Test that GET /v1/public/projects still works as before.
        """
        response = client.get("/v1/public/projects", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "projects" in data
        assert "total" in data
        # Original schema should still work
        for project in data["projects"]:
            assert "id" in project
            assert "name" in project
            assert "status" in project
            assert "tier" in project

    def test_project_response_includes_new_fields(self, client, auth_headers_user1):
        """
        Test that project response can optionally include new fields.
        This ensures new fields don't break existing clients.
        """
        response = client.get("/v1/public/projects", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_200_OK

        # Original fields must exist
        data = response.json()
        for project in data["projects"]:
            assert "id" in project
            assert "name" in project
            assert "status" in project
            assert "tier" in project
