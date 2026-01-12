"""
Integration tests for Agent PATCH and DELETE endpoints.
Tests the new endpoints added to close frontend integration gaps.

Tests:
- PATCH /v1/public/{project_id}/agents/{agent_id} - Update agent profile
- DELETE /v1/public/{project_id}/agents/{agent_id} - Delete agent profile
"""
import pytest
from fastapi import status


class TestUpdateAgentEndpoint:
    """Test suite for PATCH /v1/public/{project_id}/agents/{agent_id} endpoint."""

    def test_update_agent_all_fields(self, client, auth_headers_user1):
        """Test updating all updatable fields of an agent."""
        project_id = "proj_demo_u1_001"

        # Create an agent first
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:update-test-01",
                "role": "researcher",
                "name": "Original Name",
                "description": "Original description",
                "scope": "PROJECT"
            },
            headers=auth_headers_user1
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        agent_id = create_response.json()["id"]

        # Update all fields
        update_response = client.patch(
            f"/v1/public/{project_id}/agents/{agent_id}",
            json={
                "role": "analyst",
                "name": "Updated Name",
                "description": "Updated description",
                "scope": "GLOBAL"
            },
            headers=auth_headers_user1
        )

        assert update_response.status_code == status.HTTP_200_OK

        data = update_response.json()
        assert data["id"] == agent_id
        assert data["agent_id"] == agent_id
        assert data["role"] == "analyst"
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["scope"] == "GLOBAL"
        # DID should remain unchanged
        assert data["did"] == "did:web:agent.example.com:update-test-01"

    def test_update_agent_partial_fields(self, client, auth_headers_user1):
        """Test updating only some fields (partial update)."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:partial-update",
                "role": "researcher",
                "name": "Original Name",
                "description": "Original description",
                "scope": "PROJECT"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Update only name and role
        update_response = client.patch(
            f"/v1/public/{project_id}/agents/{agent_id}",
            json={
                "name": "New Name",
                "role": "executor"
            },
            headers=auth_headers_user1
        )

        assert update_response.status_code == status.HTTP_200_OK

        data = update_response.json()
        assert data["name"] == "New Name"
        assert data["role"] == "executor"
        # Other fields should remain unchanged
        assert data["description"] == "Original description"
        assert data["scope"] == "PROJECT"

    def test_update_agent_only_description(self, client, auth_headers_user1):
        """Test updating only the description field."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:desc-update",
                "role": "researcher",
                "name": "Test Agent"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Update only description
        update_response = client.patch(
            f"/v1/public/{project_id}/agents/{agent_id}",
            json={
                "description": "Newly added description"
            },
            headers=auth_headers_user1
        )

        assert update_response.status_code == status.HTTP_200_OK

        data = update_response.json()
        assert data["description"] == "Newly added description"
        assert data["name"] == "Test Agent"
        assert data["role"] == "researcher"

    def test_update_agent_response_includes_agent_id(self, client, auth_headers_user1):
        """Test that update response includes both id and agent_id fields."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:agent-id-test",
                "role": "researcher",
                "name": "Agent ID Test"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Update agent
        update_response = client.patch(
            f"/v1/public/{project_id}/agents/{agent_id}",
            json={"name": "Updated"},
            headers=auth_headers_user1
        )

        assert update_response.status_code == status.HTTP_200_OK

        data = update_response.json()
        assert "id" in data
        assert "agent_id" in data
        assert data["id"] == agent_id
        assert data["agent_id"] == agent_id

    def test_update_agent_not_found(self, client, auth_headers_user1):
        """Test updating non-existent agent returns 404."""
        project_id = "proj_demo_u1_001"
        nonexistent_agent_id = "agent_nonexistent123"

        response = client.patch(
            f"/v1/public/{project_id}/agents/{nonexistent_agent_id}",
            json={"name": "Updated Name"},
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert nonexistent_agent_id in data["detail"]

    def test_update_agent_wrong_project(self, client, auth_headers_user1):
        """Test updating agent from wrong project returns 404."""
        # Create agent in first project
        create_response = client.post(
            "/v1/public/proj_demo_u1_001/agents",
            json={
                "did": "did:web:agent.example.com:wrong-proj-update",
                "role": "researcher",
                "name": "Test Agent"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Try to update it from second project
        response = client.patch(
            f"/v1/public/proj_demo_u1_002/agents/{agent_id}",
            json={"name": "Updated Name"},
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_agent_unauthorized_project(self, client, auth_headers_user1):
        """Test updating agent from another user's project returns 403."""
        project_id = "proj_demo_u2_001"

        response = client.patch(
            f"/v1/public/{project_id}/agents/agent_123",
            json={"name": "Updated Name"},
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_agent_missing_api_key(self, client):
        """Test missing X-API-Key header returns 401."""
        project_id = "proj_demo_u1_001"
        agent_id = "agent_123"

        response = client.patch(
            f"/v1/public/{project_id}/agents/{agent_id}",
            json={"name": "Updated Name"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_agent_invalid_scope(self, client, auth_headers_user1):
        """Test updating with invalid scope value returns 422."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:invalid-scope-update",
                "role": "researcher",
                "name": "Test Agent"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Try to update with invalid scope
        response = client.patch(
            f"/v1/public/{project_id}/agents/{agent_id}",
            json={"scope": "INVALID_SCOPE"},
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_agent_empty_string_validation(self, client, auth_headers_user1):
        """Test that empty strings fail validation."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:empty-validation",
                "role": "researcher",
                "name": "Test Agent"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Try to update with empty name
        response = client.patch(
            f"/v1/public/{project_id}/agents/{agent_id}",
            json={"name": ""},
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_agent_empty_body(self, client, auth_headers_user1):
        """Test updating with empty body (no fields) - should succeed but not change anything."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:empty-body",
                "role": "researcher",
                "name": "Test Agent",
                "description": "Test description"
            },
            headers=auth_headers_user1
        )
        created_data = create_response.json()
        agent_id = created_data["id"]

        # Update with empty body
        response = client.patch(
            f"/v1/public/{project_id}/agents/{agent_id}",
            json={},
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # All fields should remain the same
        assert data["role"] == created_data["role"]
        assert data["name"] == created_data["name"]
        assert data["description"] == created_data["description"]


class TestDeleteAgentEndpoint:
    """Test suite for DELETE /v1/public/{project_id}/agents/{agent_id} endpoint."""

    def test_delete_agent_success(self, client, auth_headers_user1):
        """Test successfully deleting an agent."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:delete-test",
                "role": "researcher",
                "name": "Agent to Delete"
            },
            headers=auth_headers_user1
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        agent_id = create_response.json()["id"]

        # Delete the agent
        delete_response = client.delete(
            f"/v1/public/{project_id}/agents/{agent_id}",
            headers=auth_headers_user1
        )

        assert delete_response.status_code == status.HTTP_200_OK

        data = delete_response.json()
        assert "message" in data
        assert data["agent_id"] == agent_id

        # Verify agent is deleted by trying to get it
        get_response = client.get(
            f"/v1/public/{project_id}/agents/{agent_id}",
            headers=auth_headers_user1
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_agent_not_found(self, client, auth_headers_user1):
        """Test deleting non-existent agent returns 404."""
        project_id = "proj_demo_u1_001"
        nonexistent_agent_id = "agent_nonexistent123"

        response = client.delete(
            f"/v1/public/{project_id}/agents/{nonexistent_agent_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_agent_wrong_project(self, client, auth_headers_user1):
        """Test deleting agent from wrong project returns 404."""
        # Create agent in first project
        create_response = client.post(
            "/v1/public/proj_demo_u1_001/agents",
            json={
                "did": "did:web:agent.example.com:wrong-proj-delete",
                "role": "researcher",
                "name": "Test Agent"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Try to delete it from second project
        response = client.delete(
            f"/v1/public/proj_demo_u1_002/agents/{agent_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_agent_unauthorized_project(self, client, auth_headers_user1):
        """Test deleting agent from another user's project returns 403."""
        project_id = "proj_demo_u2_001"

        response = client.delete(
            f"/v1/public/{project_id}/agents/agent_123",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_agent_missing_api_key(self, client):
        """Test missing X-API-Key header returns 401."""
        project_id = "proj_demo_u1_001"
        agent_id = "agent_123"

        response = client.delete(
            f"/v1/public/{project_id}/agents/{agent_id}"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_agent_project_not_found(self, client, auth_headers_user1):
        """Test deleting agent from non-existent project returns 404."""
        response = client.delete(
            "/v1/public/nonexistent_project/agents/agent_123",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_agent_removes_from_list(self, client, auth_headers_user1):
        """Test that deleted agent no longer appears in list."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:list-delete-test",
                "role": "researcher",
                "name": "List Delete Test"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Get initial list count
        list_before = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )
        count_before = list_before.json()["total"]

        # Delete the agent
        client.delete(
            f"/v1/public/{project_id}/agents/{agent_id}",
            headers=auth_headers_user1
        )

        # Get list after deletion
        list_after = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )
        data = list_after.json()

        # Count should be one less
        assert data["total"] == count_before - 1

        # Agent should not be in the list
        agent_ids = {agent["id"] for agent in data["agents"]}
        assert agent_id not in agent_ids


class TestAgentResponseSchema:
    """Test that agent responses include both id and agent_id fields."""

    def test_create_response_includes_agent_id(self, client, auth_headers_user1):
        """Test that create response includes both id and agent_id."""
        project_id = "proj_demo_u1_001"

        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:schema-test",
                "role": "researcher",
                "name": "Schema Test"
            },
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "id" in data
        assert "agent_id" in data
        assert data["id"] == data["agent_id"]

    def test_get_response_includes_agent_id(self, client, auth_headers_user1):
        """Test that get response includes both id and agent_id."""
        project_id = "proj_demo_u1_001"

        # Create agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:get-schema-test",
                "role": "researcher",
                "name": "Get Schema Test"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Get agent
        response = client.get(
            f"/v1/public/{project_id}/agents/{agent_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "id" in data
        assert "agent_id" in data
        assert data["id"] == data["agent_id"]

    def test_list_response_includes_agent_id(self, client, auth_headers_user1):
        """Test that list response includes both id and agent_id for each agent."""
        project_id = "proj_demo_u1_001"

        # Create agent
        client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:list-schema-test",
                "role": "researcher",
                "name": "List Schema Test"
            },
            headers=auth_headers_user1
        )

        # List agents
        response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check each agent in the list
        for agent in data["agents"]:
            assert "id" in agent
            assert "agent_id" in agent
            assert agent["id"] == agent["agent_id"]
