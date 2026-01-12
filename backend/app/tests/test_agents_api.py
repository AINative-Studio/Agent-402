"""
Integration tests for Agent Profiles API.
Tests Epic 12, Issue 1 requirements.

Tests:
- POST /v1/public/{project_id}/agents - Create agent profile
- GET /v1/public/{project_id}/agents - List agents
- GET /v1/public/{project_id}/agents/{agent_id} - Get single agent
"""
import pytest
from fastapi import status


class TestCreateAgentEndpoint:
    """Test suite for POST /v1/public/{project_id}/agents endpoint."""

    def test_create_agent_success(self, client, auth_headers_user1):
        """
        Test successful agent creation.
        Epic 12, Issue 1: Create agent with did, role, name, description, scope.
        """
        project_id = "proj_demo_u1_001"
        request_body = {
            "did": "did:web:agent.example.com:researcher-01",
            "role": "researcher",
            "name": "Research Agent Alpha",
            "description": "Specialized agent for financial research and data gathering",
            "scope": "PROJECT"
        }

        response = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "id" in data
        assert data["did"] == request_body["did"]
        assert data["role"] == request_body["role"]
        assert data["name"] == request_body["name"]
        assert data["description"] == request_body["description"]
        assert data["scope"] == request_body["scope"]
        assert data["project_id"] == project_id
        assert "created_at" in data
        assert "updated_at" in data

        # Verify ID format
        assert data["id"].startswith("agent_")
        assert len(data["id"]) > len("agent_")

    def test_create_agent_minimal_fields(self, client, auth_headers_user1):
        """
        Test agent creation with only required fields.
        Optional fields: description should default to None, scope to PROJECT.
        """
        project_id = "proj_demo_u1_001"
        request_body = {
            "did": "did:web:agent.example.com:analyst-01",
            "role": "analyst",
            "name": "Analysis Agent Beta"
        }

        response = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["did"] == request_body["did"]
        assert data["role"] == request_body["role"]
        assert data["name"] == request_body["name"]
        assert data["description"] is None
        assert data["scope"] == "PROJECT"  # Default value

    def test_create_agent_different_scopes(self, client, auth_headers_user1):
        """Test creating agents with different scope values."""
        project_id = "proj_demo_u1_001"

        scopes = ["PROJECT", "GLOBAL", "RESTRICTED"]

        for idx, scope in enumerate(scopes):
            request_body = {
                "did": f"did:web:agent.example.com:executor-0{idx}",
                "role": "executor",
                "name": f"Executor Agent {idx}",
                "scope": scope
            }

            response = client.post(
                f"/v1/public/{project_id}/agents",
                json=request_body,
                headers=auth_headers_user1
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["scope"] == scope

    def test_create_agent_missing_required_field_did(self, client, auth_headers_user1):
        """Test that missing 'did' field returns 422 validation error."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "role": "researcher",
            "name": "Research Agent"
        }

        response = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_agent_missing_required_field_role(self, client, auth_headers_user1):
        """Test that missing 'role' field returns 422 validation error."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "did": "did:web:agent.example.com:test",
            "name": "Test Agent"
        }

        response = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_agent_missing_required_field_name(self, client, auth_headers_user1):
        """Test that missing 'name' field returns 422 validation error."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "did": "did:web:agent.example.com:test",
            "role": "researcher"
        }

        response = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_agent_empty_string_fields(self, client, auth_headers_user1):
        """Test that empty strings in required fields fail validation."""
        project_id = "proj_demo_u1_001"

        # Empty DID
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={"did": "", "role": "researcher", "name": "Test"},
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Empty role
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={"did": "did:test", "role": "", "name": "Test"},
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Empty name
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={"did": "did:test", "role": "researcher", "name": ""},
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_agent_duplicate_did_in_project(self, client, auth_headers_user1):
        """
        Test that creating an agent with duplicate DID in same project returns 409.
        Epic 12: Each agent has a unique DID (unique within project).
        """
        project_id = "proj_demo_u1_001"
        request_body = {
            "did": "did:web:agent.example.com:duplicate-test",
            "role": "researcher",
            "name": "Duplicate Test Agent"
        }

        # First creation should succeed
        response1 = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=auth_headers_user1
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Second creation with same DID should fail
        response2 = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=auth_headers_user1
        )
        assert response2.status_code == status.HTTP_409_CONFLICT

        data = response2.json()
        assert "detail" in data
        assert "duplicate-test" in data["detail"].lower()

    def test_create_agent_same_did_different_projects(self, client, auth_headers_user1):
        """
        Test that same DID can exist in different projects.
        DID uniqueness is scoped to project.
        """
        request_body = {
            "did": "did:web:agent.example.com:cross-project",
            "role": "researcher",
            "name": "Cross Project Agent"
        }

        # Create in first project
        response1 = client.post(
            f"/v1/public/proj_demo_u1_001/agents",
            json=request_body,
            headers=auth_headers_user1
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Create in second project (same user, different project)
        response2 = client.post(
            f"/v1/public/proj_demo_u1_002/agents",
            json=request_body,
            headers=auth_headers_user1
        )
        assert response2.status_code == status.HTTP_201_CREATED

        # Both should have different IDs but same DID
        data1 = response1.json()
        data2 = response2.json()
        assert data1["id"] != data2["id"]
        assert data1["did"] == data2["did"]
        assert data1["project_id"] != data2["project_id"]

    def test_create_agent_invalid_scope_value(self, client, auth_headers_user1):
        """Test that invalid scope value returns 422 validation error."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "did": "did:web:agent.example.com:invalid-scope",
            "role": "researcher",
            "name": "Invalid Scope Agent",
            "scope": "INVALID_SCOPE"
        }

        response = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_agent_project_not_found(self, client, auth_headers_user1):
        """Test creating agent in non-existent project returns 404."""
        request_body = {
            "did": "did:web:agent.example.com:test",
            "role": "researcher",
            "name": "Test Agent"
        }

        response = client.post(
            "/v1/public/nonexistent_project/agents",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_create_agent_unauthorized_project(self, client, auth_headers_user1, auth_headers_user2):
        """
        Test creating agent in another user's project returns 403.
        Epic 12: Validate project access.
        """
        # User 2's project
        project_id = "proj_demo_u2_001"
        request_body = {
            "did": "did:web:agent.example.com:unauthorized",
            "role": "researcher",
            "name": "Unauthorized Agent"
        }

        # User 1 trying to create agent in User 2's project
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_create_agent_missing_api_key(self, client):
        """Test missing X-API-Key header returns 401."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "did": "did:web:agent.example.com:test",
            "role": "researcher",
            "name": "Test Agent"
        }

        response = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_create_agent_invalid_api_key(self, client, invalid_auth_headers):
        """Test invalid API key returns 401."""
        project_id = "proj_demo_u1_001"
        request_body = {
            "did": "did:web:agent.example.com:test",
            "role": "researcher",
            "name": "Test Agent"
        }

        response = client.post(
            f"/v1/public/{project_id}/agents",
            json=request_body,
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_create_agent_field_length_validation(self, client, auth_headers_user1):
        """Test field length constraints."""
        project_id = "proj_demo_u1_001"

        # DID too long (max 256)
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:" + "x" * 300,
                "role": "researcher",
                "name": "Test Agent"
            },
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Role too long (max 100)
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:test",
                "role": "r" * 150,
                "name": "Test Agent"
            },
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Name too long (max 200)
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:test",
                "role": "researcher",
                "name": "n" * 250
            },
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Description too long (max 1000)
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:test",
                "role": "researcher",
                "name": "Test Agent",
                "description": "d" * 1500
            },
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListAgentsEndpoint:
    """Test suite for GET /v1/public/{project_id}/agents endpoint."""

    def test_list_agents_empty_project(self, client, auth_headers_user1):
        """
        Test listing agents in project structure.
        Verifies correct response schema even when agents exist from other tests.
        Note: Due to in-memory storage, agents may exist from previous tests.
        """
        project_id = "proj_demo_u1_001"

        response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "agents" in data
        assert "total" in data
        assert isinstance(data["agents"], list)
        assert isinstance(data["total"], int)
        # Total should match the length of the agents array
        assert data["total"] == len(data["agents"])
        # Total should be non-negative
        assert data["total"] >= 0

    def test_list_agents_with_agents(self, client, auth_headers_user1):
        """Test listing agents after creating multiple agents."""
        project_id = "proj_demo_u1_001"

        # Create multiple agents
        agents_to_create = [
            {
                "did": "did:web:agent.example.com:list-test-01",
                "role": "researcher",
                "name": "List Test Agent 1"
            },
            {
                "did": "did:web:agent.example.com:list-test-02",
                "role": "analyst",
                "name": "List Test Agent 2"
            },
            {
                "did": "did:web:agent.example.com:list-test-03",
                "role": "executor",
                "name": "List Test Agent 3"
            }
        ]

        for agent_data in agents_to_create:
            response = client.post(
                f"/v1/public/{project_id}/agents",
                json=agent_data,
                headers=auth_headers_user1
            )
            assert response.status_code == status.HTTP_201_CREATED

        # List agents
        response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] >= 3  # At least the 3 we created
        assert len(data["agents"]) >= 3

        # Verify all created agents are in the list
        agent_dids = {agent["did"] for agent in data["agents"]}
        for agent_data in agents_to_create:
            assert agent_data["did"] in agent_dids

    def test_list_agents_response_schema(self, client, auth_headers_user1):
        """Test response schema matches documented contract."""
        project_id = "proj_demo_u1_001"

        # Create an agent first
        client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:schema-test",
                "role": "researcher",
                "name": "Schema Test Agent",
                "description": "Testing schema",
                "scope": "PROJECT"
            },
            headers=auth_headers_user1
        )

        response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Top-level schema
        assert isinstance(data, dict)
        assert set(data.keys()) == {"agents", "total"}

        # Agents array
        assert isinstance(data["agents"], list)

        # Each agent schema
        for agent in data["agents"]:
            assert isinstance(agent, dict)
            assert "id" in agent
            assert "did" in agent
            assert "role" in agent
            assert "name" in agent
            assert "description" in agent
            assert "scope" in agent
            assert "project_id" in agent
            assert "created_at" in agent
            assert "updated_at" in agent

            assert isinstance(agent["id"], str)
            assert isinstance(agent["did"], str)
            assert isinstance(agent["role"], str)
            assert isinstance(agent["name"], str)
            assert isinstance(agent["scope"], str)
            assert isinstance(agent["project_id"], str)
            assert isinstance(agent["created_at"], str)

    def test_list_agents_project_isolation(self, client, auth_headers_user1):
        """
        Test that listing agents only returns agents from the specified project.
        Agents from other projects should not be included.
        """
        # Create agent in first project
        response1 = client.post(
            "/v1/public/proj_demo_u1_001/agents",
            json={
                "did": "did:web:agent.example.com:isolation-test-1",
                "role": "researcher",
                "name": "Isolation Test Agent 1"
            },
            headers=auth_headers_user1
        )
        assert response1.status_code == status.HTTP_201_CREATED
        agent1_id = response1.json()["id"]

        # Create agent in second project
        response2 = client.post(
            "/v1/public/proj_demo_u1_002/agents",
            json={
                "did": "did:web:agent.example.com:isolation-test-2",
                "role": "analyst",
                "name": "Isolation Test Agent 2"
            },
            headers=auth_headers_user1
        )
        assert response2.status_code == status.HTTP_201_CREATED
        agent2_id = response2.json()["id"]

        # List agents from first project
        response = client.get(
            "/v1/public/proj_demo_u1_001/agents",
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_200_OK
        data1 = response.json()
        agent1_ids = {agent["id"] for agent in data1["agents"]}

        # Should contain agent1 but not agent2
        assert agent1_id in agent1_ids
        assert agent2_id not in agent1_ids

        # List agents from second project
        response = client.get(
            "/v1/public/proj_demo_u1_002/agents",
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_200_OK
        data2 = response.json()
        agent2_ids = {agent["id"] for agent in data2["agents"]}

        # Should contain agent2 but not agent1
        assert agent2_id in agent2_ids
        assert agent1_id not in agent2_ids

    def test_list_agents_project_not_found(self, client, auth_headers_user1):
        """Test listing agents from non-existent project returns 404."""
        response = client.get(
            "/v1/public/nonexistent_project/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_list_agents_unauthorized_project(self, client, auth_headers_user1):
        """Test listing agents from another user's project returns 403."""
        # User 2's project
        project_id = "proj_demo_u2_001"

        response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_list_agents_missing_api_key(self, client):
        """Test missing X-API-Key header returns 401."""
        project_id = "proj_demo_u1_001"

        response = client.get(f"/v1/public/{project_id}/agents")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_list_agents_invalid_api_key(self, client, invalid_auth_headers):
        """Test invalid API key returns 401."""
        project_id = "proj_demo_u1_001"

        response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"


class TestGetSingleAgentEndpoint:
    """Test suite for GET /v1/public/{project_id}/agents/{agent_id} endpoint."""

    def test_get_agent_success(self, client, auth_headers_user1):
        """Test successfully retrieving a single agent."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:get-test",
                "role": "researcher",
                "name": "Get Test Agent",
                "description": "Agent for testing GET endpoint",
                "scope": "GLOBAL"
            },
            headers=auth_headers_user1
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        created_agent = create_response.json()
        agent_id = created_agent["id"]

        # Get the agent
        response = client.get(
            f"/v1/public/{project_id}/agents/{agent_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["id"] == agent_id
        assert data["did"] == created_agent["did"]
        assert data["role"] == created_agent["role"]
        assert data["name"] == created_agent["name"]
        assert data["description"] == created_agent["description"]
        assert data["scope"] == created_agent["scope"]
        assert data["project_id"] == project_id
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_agent_response_schema(self, client, auth_headers_user1):
        """Test response schema matches documented contract."""
        project_id = "proj_demo_u1_001"

        # Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:schema-get-test",
                "role": "analyst",
                "name": "Schema GET Test Agent"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Get the agent
        response = client.get(
            f"/v1/public/{project_id}/agents/{agent_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Verify all required fields (including agent_id for frontend integration)
        required_fields = {
            "id", "agent_id", "did", "role", "name", "description",
            "scope", "project_id", "created_at", "updated_at"
        }
        assert set(data.keys()) == required_fields

        # Verify field types
        assert isinstance(data["id"], str)
        assert isinstance(data["did"], str)
        assert isinstance(data["role"], str)
        assert isinstance(data["name"], str)
        assert isinstance(data["scope"], str)
        assert isinstance(data["project_id"], str)
        assert isinstance(data["created_at"], str)

    def test_get_agent_not_found(self, client, auth_headers_user1):
        """Test getting non-existent agent returns 404."""
        project_id = "proj_demo_u1_001"
        nonexistent_agent_id = "agent_nonexistent123"

        response = client.get(
            f"/v1/public/{project_id}/agents/{nonexistent_agent_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert nonexistent_agent_id in data["detail"]

    def test_get_agent_wrong_project(self, client, auth_headers_user1):
        """
        Test getting agent from wrong project returns 404.
        Agent exists but doesn't belong to the specified project.
        """
        # Create agent in first project
        create_response = client.post(
            "/v1/public/proj_demo_u1_001/agents",
            json={
                "did": "did:web:agent.example.com:wrong-project-test",
                "role": "researcher",
                "name": "Wrong Project Test Agent"
            },
            headers=auth_headers_user1
        )
        agent_id = create_response.json()["id"]

        # Try to get it from second project (wrong project)
        response = client.get(
            f"/v1/public/proj_demo_u1_002/agents/{agent_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data

    def test_get_agent_project_not_found(self, client, auth_headers_user1):
        """Test getting agent from non-existent project returns 404."""
        response = client.get(
            "/v1/public/nonexistent_project/agents/agent_123",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_get_agent_unauthorized_project(self, client, auth_headers_user1):
        """Test getting agent from another user's project returns 403."""
        # User 2's project
        project_id = "proj_demo_u2_001"

        response = client.get(
            f"/v1/public/{project_id}/agents/agent_123",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_get_agent_missing_api_key(self, client):
        """Test missing X-API-Key header returns 401."""
        project_id = "proj_demo_u1_001"
        agent_id = "agent_123"

        response = client.get(f"/v1/public/{project_id}/agents/{agent_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_get_agent_invalid_api_key(self, client, invalid_auth_headers):
        """Test invalid API key returns 401."""
        project_id = "proj_demo_u1_001"
        agent_id = "agent_123"

        response = client.get(
            f"/v1/public/{project_id}/agents/{agent_id}",
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"


class TestAgentsAPIIntegration:
    """Integration tests covering multiple operations together."""

    def test_full_agent_lifecycle(self, client, auth_headers_user1):
        """Test complete agent lifecycle: create, list, get."""
        project_id = "proj_demo_u1_001"

        # 1. List agents (should start empty or with existing agents)
        list_response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )
        initial_count = list_response.json()["total"]

        # 2. Create an agent
        create_response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:lifecycle-test",
                "role": "researcher",
                "name": "Lifecycle Test Agent",
                "description": "Full lifecycle test"
            },
            headers=auth_headers_user1
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        created_agent = create_response.json()
        agent_id = created_agent["id"]

        # 3. List agents (should have one more)
        list_response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        assert list_data["total"] == initial_count + 1

        # Verify our agent is in the list
        agent_ids = {agent["id"] for agent in list_data["agents"]}
        assert agent_id in agent_ids

        # 4. Get the specific agent
        get_response = client.get(
            f"/v1/public/{project_id}/agents/{agent_id}",
            headers=auth_headers_user1
        )
        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()

        # Verify data matches what we created
        assert get_data["id"] == created_agent["id"]
        assert get_data["did"] == created_agent["did"]
        assert get_data["role"] == created_agent["role"]
        assert get_data["name"] == created_agent["name"]

    def test_multiple_agents_different_roles(self, client, auth_headers_user1):
        """Test creating multiple agents with different roles and scopes."""
        project_id = "proj_demo_u1_001"

        agents_config = [
            {
                "did": "did:web:agent.example.com:multi-researcher",
                "role": "researcher",
                "name": "Multi Researcher Agent",
                "scope": "PROJECT"
            },
            {
                "did": "did:web:agent.example.com:multi-analyst",
                "role": "analyst",
                "name": "Multi Analyst Agent",
                "scope": "GLOBAL"
            },
            {
                "did": "did:web:agent.example.com:multi-executor",
                "role": "executor",
                "name": "Multi Executor Agent",
                "scope": "RESTRICTED"
            }
        ]

        created_agents = []
        for config in agents_config:
            response = client.post(
                f"/v1/public/{project_id}/agents",
                json=config,
                headers=auth_headers_user1
            )
            assert response.status_code == status.HTTP_201_CREATED
            created_agents.append(response.json())

        # List all agents
        list_response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()

        # Verify all created agents are present with correct details
        for created_agent in created_agents:
            matching_agent = next(
                (a for a in list_data["agents"] if a["id"] == created_agent["id"]),
                None
            )
            assert matching_agent is not None
            assert matching_agent["did"] == created_agent["did"]
            assert matching_agent["role"] == created_agent["role"]
            assert matching_agent["scope"] == created_agent["scope"]

    def test_user_isolation(self, client, auth_headers_user1, auth_headers_user2):
        """
        Test that users cannot access each other's agents.
        User isolation is enforced at project level.
        """
        # User 1 creates agent in their project
        response1 = client.post(
            "/v1/public/proj_demo_u1_001/agents",
            json={
                "did": "did:web:agent.example.com:user1-agent",
                "role": "researcher",
                "name": "User 1 Agent"
            },
            headers=auth_headers_user1
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # User 2 creates agent in their project
        response2 = client.post(
            "/v1/public/proj_demo_u2_001/agents",
            json={
                "did": "did:web:agent.example.com:user2-agent",
                "role": "analyst",
                "name": "User 2 Agent"
            },
            headers=auth_headers_user2
        )
        assert response2.status_code == status.HTTP_201_CREATED

        # User 1 cannot access User 2's project
        response = client.get(
            "/v1/public/proj_demo_u2_001/agents",
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # User 2 cannot access User 1's project
        response = client.get(
            "/v1/public/proj_demo_u1_001/agents",
            headers=auth_headers_user2
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_error_response_format_consistency(self, client, auth_headers_user1):
        """
        Test that all error responses follow the DX Contract format.
        All errors should return { detail, error_code }.
        """
        project_id = "proj_demo_u1_001"

        # 401 - Missing API key
        response = client.get(f"/v1/public/{project_id}/agents")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

        # 403 - Unauthorized project access
        response = client.get(
            "/v1/public/proj_demo_u2_001/agents",
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

        # 404 - Project not found
        response = client.get(
            "/v1/public/nonexistent_project/agents",
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

        # 404 - Agent not found
        response = client.get(
            f"/v1/public/{project_id}/agents/agent_nonexistent",
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data

        # 409 - Duplicate DID
        client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:duplicate-format-test",
                "role": "researcher",
                "name": "Test"
            },
            headers=auth_headers_user1
        )
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={
                "did": "did:web:agent.example.com:duplicate-format-test",
                "role": "researcher",
                "name": "Test"
            },
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "detail" in data

        # 422 - Validation error
        response = client.post(
            f"/v1/public/{project_id}/agents",
            json={"role": "researcher"},  # Missing required fields
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
