"""
Test X402Service Dependency Injection.

Tests that X402Service properly accepts and uses an injected ZeroDB client.
This test ensures that the service can be instantiated with a mock client
for testing purposes, fixing Issue #78.

Per TDD methodology:
1. RED: Test fails initially because X402Service doesn't accept client parameter
2. GREEN: Fix X402Service to accept client parameter
3. REFACTOR: Ensure consistency across all services
"""
import pytest
from app.services.x402_service import X402Service, X402RequestStatus
from app.tests.fixtures.zerodb_mock import MockZeroDBClient


class TestX402ServiceDependencyInjection:
    """
    Test suite for X402Service dependency injection.

    Validates that services can be instantiated with mock clients
    and that the injected client is used for all operations.
    """

    @pytest.mark.asyncio
    async def test_x402_service_accepts_client_parameter(self, mock_zerodb_client):
        """
        Test that X402Service constructor accepts an optional client parameter.

        This is the RED test that will fail initially because X402Service.__init__
        doesn't accept a client parameter, while all other services do.

        Expected behavior:
        - X402Service should accept client=None in constructor
        - When client is provided, it should be used instead of get_zerodb_client()
        """
        # Arrange: Create a fresh mock client
        custom_client = MockZeroDBClient()
        custom_client.reset()

        # Act: Instantiate service with custom client
        # This will FAIL initially because X402Service.__init__() doesn't accept client
        service = X402Service(client=custom_client)

        # Assert: Service should use the injected client
        assert service._client is custom_client
        assert service.client is custom_client

    @pytest.mark.asyncio
    async def test_x402_service_uses_injected_client_for_operations(self, mock_zerodb_client):
        """
        Test that X402Service uses the injected client for database operations.

        Validates that when a custom client is provided, all database operations
        use that client instead of calling get_zerodb_client().
        """
        # Arrange: Create service with custom client
        custom_client = MockZeroDBClient()
        custom_client.reset()
        service = X402Service(client=custom_client)

        # Act: Create an X402 request
        request = await service.create_request(
            project_id="test_project",
            agent_id="agent_001",
            task_id="task_001",
            run_id="run_001",
            request_payload={"method": "POST", "url": "https://api.example.com/payment"},
            signature="test_signature_123"
        )

        # Assert: The custom client should have been used
        assert custom_client.get_call_count("insert_row") == 1
        assert len(custom_client.get_table_data("x402_requests")) == 1

        # Verify the request was created correctly
        assert request["request_id"] is not None
        assert request["project_id"] == "test_project"
        assert request["agent_id"] == "agent_001"

    @pytest.mark.asyncio
    async def test_x402_service_lazy_initialization_without_client(self):
        """
        Test that X402Service can be instantiated without a client parameter.

        When no client is provided, the service should lazily initialize
        the client on first use via get_zerodb_client().
        """
        # Arrange & Act: Create service without client
        service = X402Service()

        # Assert: Client should be None initially
        assert service._client is None

        # Act: Access the client property (triggers lazy initialization)
        client = service.client

        # Assert: Client should now be initialized
        assert client is not None

    @pytest.mark.asyncio
    async def test_x402_service_consistency_with_other_services(self, mock_zerodb_client):
        """
        Test that X402Service follows the same dependency injection pattern as other services.

        All services (AgentMemoryService, AgentService, ComplianceService, EventService)
        should follow the same pattern:
        1. Accept optional client parameter in __init__
        2. Store in self._client
        3. Provide lazy initialization via @property client
        """
        from app.services.agent_memory_service import AgentMemoryService
        from app.services.agent_service import AgentService
        from app.services.compliance_service import ComplianceService
        from app.services.event_service import EventService
        from app.services.x402_service import X402Service

        # Arrange: Create custom client
        custom_client = MockZeroDBClient()
        custom_client.reset()

        # Act: Instantiate all services with custom client
        services = [
            AgentMemoryService(client=custom_client),
            AgentService(client=custom_client),
            ComplianceService(client=custom_client),
            EventService(client=custom_client),
            X402Service(client=custom_client)  # Will FAIL initially
        ]

        # Assert: All services should use the injected client
        for service in services:
            assert hasattr(service, '_client'), f"{service.__class__.__name__} missing _client attribute"
            assert service._client is custom_client, f"{service.__class__.__name__} not using injected client"
            assert hasattr(service, 'client'), f"{service.__class__.__name__} missing client property"
            assert service.client is custom_client, f"{service.__class__.__name__}.client property not returning injected client"

    @pytest.mark.asyncio
    async def test_x402_service_get_request_uses_injected_client(self, mock_zerodb_client):
        """
        Test that get_request method uses the injected client.

        Ensures that all methods in X402Service use the injected client
        instead of calling get_zerodb_client() directly.
        """
        # Arrange: Create service with custom client
        custom_client = MockZeroDBClient()
        custom_client.reset()
        service = X402Service(client=custom_client)

        # Insert a test request directly into the mock
        await custom_client.insert_row("x402_requests", {
            "request_id": "x402_req_test123",
            "project_id": "test_project",
            "agent_id": "agent_001",
            "run_id": "run_001",
            "method": "POST",
            "url": "https://api.example.com/payment",
            "body": {
                "task_id": "task_001",
                "payload": {"amount": 100},
                "linked_memory_ids": [],
                "linked_compliance_ids": []
            },
            "signature": "test_sig",
            "verification_status": "PENDING",
            "timestamp": "2024-01-01T00:00:00.000Z"
        })

        # Act: Retrieve the request
        request = await service.get_request("test_project", "x402_req_test123")

        # Assert: The custom client should have been used
        assert custom_client.get_call_count("query_rows") >= 1
        assert request["request_id"] == "x402_req_test123"

    @pytest.mark.asyncio
    async def test_x402_service_list_requests_uses_injected_client(self, mock_zerodb_client):
        """
        Test that list_requests method uses the injected client.
        """
        # Arrange: Create service with custom client
        custom_client = MockZeroDBClient()
        custom_client.reset()
        service = X402Service(client=custom_client)

        # Insert test requests
        for i in range(3):
            await custom_client.insert_row("x402_requests", {
                "request_id": f"x402_req_test{i}",
                "project_id": "test_project",
                "agent_id": "agent_001",
                "run_id": "run_001",
                "method": "POST",
                "url": "https://api.example.com/payment",
                "body": {
                    "task_id": "task_001",
                    "payload": {},
                    "linked_memory_ids": [],
                    "linked_compliance_ids": []
                },
                "signature": "test_sig",
                "verification_status": "PENDING",
                "timestamp": "2024-01-01T00:00:00.000Z"
            })

        # Act: List requests
        requests, total = await service.list_requests("test_project")

        # Assert: The custom client should have been used
        assert custom_client.get_call_count("query_rows") >= 1
        assert len(requests) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_x402_service_update_status_uses_injected_client(self, mock_zerodb_client):
        """
        Test that update_request_status method uses the injected client.
        """
        # Arrange: Create service with custom client
        custom_client = MockZeroDBClient()
        custom_client.reset()
        service = X402Service(client=custom_client)

        # Insert a test request
        await custom_client.insert_row("x402_requests", {
            "request_id": "x402_req_test123",
            "project_id": "test_project",
            "agent_id": "agent_001",
            "run_id": "run_001",
            "method": "POST",
            "url": "https://api.example.com/payment",
            "body": {
                "task_id": "task_001",
                "payload": {},
                "linked_memory_ids": [],
                "linked_compliance_ids": []
            },
            "signature": "test_sig",
            "verification_status": "PENDING",
            "timestamp": "2024-01-01T00:00:00.000Z"
        })

        # Act: Update status
        updated = await service.update_request_status(
            "test_project",
            "x402_req_test123",
            X402RequestStatus.APPROVED
        )

        # Assert: The custom client should have been used for query and update
        assert custom_client.get_call_count("query_rows") >= 1
        assert custom_client.get_call_count("update_row") == 1
        assert updated["status"] == "APPROVED"
