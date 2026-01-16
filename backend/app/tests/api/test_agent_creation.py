"""
Test agent creation endpoint with DID and role validation.
Epic 12, Issue 61: CrewAI agent profile creation with strict validation.

Test coverage:
- DID format validation (did:key:z6Mk...)
- Role enum validation (analyst, compliance, transaction, orchestrator)
- Scope enum validation (SYSTEM, PROJECT, RUN) with RUN default
- Required fields validation
- Agent creation success cases
"""
import pytest
from datetime import datetime


@pytest.fixture
def test_project_id():
    """Test project ID for agent creation tests."""
    return "proj_demo_u1_001"


class TestAgentCreationDIDValidation:
    """Test DID format validation per Issue #61."""

    def test_create_agent_with_valid_did_key_format(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation with valid did:key:z6Mk... format."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "analyst",
            "name": "Test Analyst Agent",
            "description": "Test agent for validation"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        data = response.json()
        assert data["did"] == payload["did"]
        assert data["role"] == payload["role"]
        assert data["name"] == payload["name"]
        assert data["scope"] == "RUN"  # Default scope per Issue #61
        assert "agent_id" in data
        assert "created_at" in data

    def test_create_agent_with_invalid_did_format_missing_prefix(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation fails with invalid DID format (missing did:key:)."""
        payload = {
            "did": "z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "analyst",
            "name": "Test Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "DID" in data["detail"] or "did" in data["detail"]

    def test_create_agent_with_invalid_did_format_wrong_method(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation fails with wrong DID method (not did:key:)."""
        payload = {
            "did": "did:web:example.com",
            "role": "analyst",
            "name": "Test Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "did:key" in data["detail"].lower() or "format" in data["detail"].lower()

    def test_create_agent_with_invalid_did_missing_z6mk(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation fails when DID doesn't start with z6Mk."""
        payload = {
            "did": "did:key:abc123",
            "role": "analyst",
            "name": "Test Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAgentCreationRoleValidation:
    """Test role enum validation per Issue #61."""

    def test_create_agent_with_valid_analyst_role(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation with valid 'analyst' role."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "analyst",
            "name": "Analyst Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        assert response.json()["role"] == "analyst"

    def test_create_agent_with_valid_compliance_role(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation with valid 'compliance' role."""
        payload = {
            "did": "did:key:z6MkuYx9bQhpVHKFaQGZpN5JMn7L6KePqT3rHbXzGaT5PQvN",
            "role": "compliance",
            "name": "Compliance Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        assert response.json()["role"] == "compliance"

    def test_create_agent_with_valid_transaction_role(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation with valid 'transaction' role."""
        payload = {
            "did": "did:key:z6MkoWx7Y8pQmRnK9NwT4vHbXfGaL5MePzT2qJbXuGfT6RsP",
            "role": "transaction",
            "name": "Transaction Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        assert response.json()["role"] == "transaction"

    def test_create_agent_with_valid_orchestrator_role(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation with valid 'orchestrator' role."""
        payload = {
            "did": "did:key:z6MkpWx9Y7qRmTnL8OxV5wJcYgHbM6NfQzU3rKcXvHgU7TsR",
            "role": "orchestrator",
            "name": "Orchestrator Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        assert response.json()["role"] == "orchestrator"

    def test_create_agent_with_invalid_role(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation fails with invalid role."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "invalid_role",
            "name": "Test Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAgentCreationScopeValidation:
    """Test scope enum validation per Issue #61."""


    def test_create_agent_with_default_run_scope(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation defaults to RUN scope when not specified."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "analyst",
            "name": "Default Scope Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        assert response.json()["scope"] == "RUN"


    def test_create_agent_with_explicit_run_scope(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation with explicit RUN scope."""
        payload = {
            "did": "did:key:z6MkuYx9bQhpVHKFaQGZpN5JMn7L6KePqT3rHbXzGaT5PQvN",
            "role": "analyst",
            "name": "Run Scope Agent",
            "scope": "RUN"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        assert response.json()["scope"] == "RUN"


    def test_create_agent_with_project_scope(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation with PROJECT scope."""
        payload = {
            "did": "did:key:z6MkoWx7Y8pQmRnK9NwT4vHbXfGaL5MePzT2qJbXuGfT6RsP",
            "role": "compliance",
            "name": "Project Scope Agent",
            "scope": "PROJECT"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        assert response.json()["scope"] == "PROJECT"


    def test_create_agent_with_system_scope(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation with SYSTEM scope."""
        payload = {
            "did": "did:key:z6MkpWx9Y7qRmTnL8OxV5wJcYgHbM6NfQzU3rKcXvHgU7TsR",
            "role": "orchestrator",
            "name": "System Scope Agent",
            "scope": "SYSTEM"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        assert response.json()["scope"] == "SYSTEM"


    def test_create_agent_with_invalid_scope(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation fails with invalid scope."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "analyst",
            "name": "Invalid Scope Agent",
            "scope": "INVALID"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422


class TestAgentCreationRequiredFields:
    """Test required fields validation."""


    def test_create_agent_missing_did(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation fails without DID."""
        payload = {
            "role": "analyst",
            "name": "No DID Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


    def test_create_agent_missing_role(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation fails without role."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "name": "No Role Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422


    def test_create_agent_missing_name(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation fails without name."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "analyst"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422


    def test_create_agent_with_all_required_fields(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation succeeds with all required fields."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "analyst",
            "name": "Complete Agent"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        data = response.json()
        assert data["did"] == payload["did"]
        assert data["role"] == payload["role"]
        assert data["name"] == payload["name"]
        assert data["project_id"] == test_project_id


class TestAgentCreationOptionalFields:
    """Test optional fields handling."""


    def test_create_agent_with_description(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation with optional description field."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "analyst",
            "name": "Agent with Description",
            "description": "This is a test agent with a description"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        assert response.json()["description"] == payload["description"]


    def test_create_agent_without_description(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation without description field."""
        payload = {
            "did": "did:key:z6MkuYx9bQhpVHKFaQGZpN5JMn7L6KePqT3rHbXzGaT5PQvN",
            "role": "compliance",
            "name": "Agent without Description"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        data = response.json()
        # Description can be None or empty string
        assert data.get("description") is None or data.get("description") == ""


class TestAgentCreationResponse:
    """Test response structure and fields."""


    def test_create_agent_response_includes_all_fields(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent creation response includes all expected fields."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "analyst",
            "name": "Complete Response Agent",
            "description": "Test description",
            "scope": "PROJECT"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        data = response.json()

        # Verify all expected fields are present
        assert "agent_id" in data
        assert "id" in data
        assert "did" in data
        assert "role" in data
        assert "name" in data
        assert "description" in data
        assert "scope" in data
        assert "project_id" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Verify values match request
        assert data["did"] == payload["did"]
        assert data["role"] == payload["role"]
        assert data["name"] == payload["name"]
        assert data["description"] == payload["description"]
        assert data["scope"] == payload["scope"]
        assert data["project_id"] == test_project_id


    def test_create_agent_response_agent_id_format(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test agent_id has correct format."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "orchestrator",
            "name": "Agent ID Format Test"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        data = response.json()
        assert data["agent_id"].startswith("agent_")
        assert len(data["agent_id"]) > 10


    def test_create_agent_response_timestamps_format(
        self, client, auth_headers_user1, test_project_id
    ):
        """Test created_at and updated_at have correct ISO format."""
        payload = {
            "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "role": "transaction",
            "name": "Timestamp Format Test"
        }

        response = client.post(
            f"/v1/public/{test_project_id}/agents",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        data = response.json()

        # Verify timestamps can be parsed as ISO format
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

        assert isinstance(created_at, datetime)
        assert isinstance(updated_at, datetime)
