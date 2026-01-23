"""
Integration test fixtures for Phase 2 demo flow.

Provides mocks for external services:
- Circle API responses
- Gemini API responses
- ZeroDB test project setup
- Arc testnet connection mocks

Issues #124 and #127: Backend Integration Tests.
"""
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from app.tests.fixtures.zerodb_mock import MockZeroDBClient


# Sample DIDs for test agents
ANALYST_AGENT_DID = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnAnalyst"
COMPLIANCE_AGENT_DID = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnCompliance"
TRANSACTION_AGENT_DID = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnTransaction"


class MockCircleService:
    """
    Mock Circle API service for integration testing.

    Simulates Circle API responses for wallet and transfer operations.
    """

    def __init__(self):
        self.wallets: Dict[str, Dict[str, Any]] = {}
        self.transfers: Dict[str, Dict[str, Any]] = {}
        self.balances: Dict[str, str] = {}
        self._call_history: List[Dict[str, Any]] = []

    def reset(self):
        """Reset all mock data."""
        self.wallets.clear()
        self.transfers.clear()
        self.balances.clear()
        self._call_history.clear()

    def _track_call(self, method: str, **kwargs):
        """Track method calls for verification."""
        self._call_history.append({
            "method": method,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs
        })

    async def create_wallet(
        self,
        idempotency_key: str,
        blockchain: str = "ETH-SEPOLIA",
        wallet_set_id: str = None
    ) -> Dict[str, Any]:
        """Create a mock Circle wallet."""
        self._track_call("create_wallet", idempotency_key=idempotency_key)

        wallet_id = f"circle_wlt_{uuid.uuid4().hex[:12]}"
        address = f"0x{uuid.uuid4().hex}"

        wallet_data = {
            "walletId": wallet_id,
            "entityId": f"entity_{uuid.uuid4().hex[:8]}",
            "blockchain": blockchain,
            "address": address,
            "state": "LIVE",
            "createDate": datetime.now(timezone.utc).isoformat()
        }

        self.wallets[wallet_id] = wallet_data
        self.balances[wallet_id] = "1000.00"

        return {"data": wallet_data}

    async def get_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """Get mock wallet by ID."""
        self._track_call("get_wallet", wallet_id=wallet_id)

        if wallet_id in self.wallets:
            return {"data": self.wallets[wallet_id]}

        from app.services.circle_service import WalletNotFoundError
        raise WalletNotFoundError(wallet_id)

    async def get_wallet_balance(self, wallet_id: str) -> Dict[str, Any]:
        """Get mock wallet balance."""
        self._track_call("get_wallet_balance", wallet_id=wallet_id)

        amount = self.balances.get(wallet_id, "0.00")
        return {
            "amount": amount,
            "currency": "USDC"
        }

    async def create_transfer(
        self,
        source_wallet_id: str,
        destination_wallet_id: str,
        amount: str,
        idempotency_key: str,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """Create a mock USDC transfer."""
        self._track_call(
            "create_transfer",
            source=source_wallet_id,
            destination=destination_wallet_id,
            amount=amount
        )

        transfer_id = f"circle_xfr_{uuid.uuid4().hex[:12]}"

        transfer_data = {
            "transferId": transfer_id,
            "source": {"type": "wallet", "id": source_wallet_id},
            "destination": {"type": "wallet", "id": destination_wallet_id},
            "amount": {"amount": amount, "currency": currency},
            "status": "pending",
            "createDate": datetime.now(timezone.utc).isoformat()
        }

        self.transfers[transfer_id] = transfer_data

        return {"data": transfer_data}

    async def get_transfer(self, transfer_id: str) -> Dict[str, Any]:
        """Get mock transfer by ID."""
        self._track_call("get_transfer", transfer_id=transfer_id)

        if transfer_id in self.transfers:
            transfer = self.transfers[transfer_id].copy()
            transfer["status"] = "complete"
            transfer["transactionHash"] = f"0x{uuid.uuid4().hex}"
            return {"data": transfer}

        from app.services.circle_service import TransferNotFoundError
        raise TransferNotFoundError(transfer_id)

    def set_balance(self, wallet_id: str, amount: str):
        """Set wallet balance for testing."""
        self.balances[wallet_id] = amount

    def get_call_count(self, method: str) -> int:
        """Get number of times a method was called."""
        return sum(1 for call in self._call_history if call["method"] == method)


class MockGeminiService:
    """
    Mock Gemini AI service for integration testing.

    Simulates Gemini API responses for different agent types.
    """

    def __init__(self):
        self._responses: Dict[str, str] = {}
        self._call_history: List[Dict[str, Any]] = []
        self._rate_limit_count = 0
        self._max_rate_limit_retries = 0

    def reset(self):
        """Reset all mock data."""
        self._responses.clear()
        self._call_history.clear()
        self._rate_limit_count = 0
        self._max_rate_limit_retries = 0

    def _track_call(self, method: str, **kwargs):
        """Track method calls for verification."""
        self._call_history.append({
            "method": method,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs
        })

    def set_response(self, agent_type: str, response: str):
        """Set a canned response for an agent type."""
        self._responses[agent_type] = response

    def set_rate_limit_behavior(self, fail_count: int):
        """Configure rate limit simulation."""
        self._max_rate_limit_retries = fail_count
        self._rate_limit_count = 0

    def get_model_for_agent(self, agent_type: str) -> str:
        """Get model for agent type."""
        model_map = {
            "analyst": "gemini-pro",
            "compliance": "gemini-pro",
            "transaction": "gemini-1.5-flash"
        }
        return model_map.get(agent_type, "gemini-pro")

    async def generate(
        self,
        prompt: str,
        model: str = None,
        system_instruction: str = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Generate mock response."""
        self._track_call("generate", prompt=prompt[:100], model=model)

        return {
            "text": "Mock Gemini response for testing",
            "model": model or "gemini-pro",
            "latency_ms": 150
        }

    async def generate_for_agent(
        self,
        agent_type: str,
        prompt: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate mock response for a specific agent type."""
        self._track_call("generate_for_agent", agent_type=agent_type)

        model = self.get_model_for_agent(agent_type)

        if agent_type in self._responses:
            text = self._responses[agent_type]
        elif agent_type == "analyst":
            text = '{"market_data": {"price": 1.0, "volume": 1000000}, "recommendation": "proceed"}'
        elif agent_type == "compliance":
            text = '{"approved": true, "risk_score": 0.15, "checks_passed": ["aml", "kyc", "sanctions"]}'
        elif agent_type == "transaction":
            text = '{"action": "execute", "transaction_id": "tx_mock_123", "status": "success"}'
        else:
            text = '{"status": "completed"}'

        return {
            "text": text,
            "model": model,
            "latency_ms": 200
        }

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate with function calling support."""
        self._track_call("generate_with_tools", prompt=prompt[:100])

        prompt_lower = prompt.lower()

        # Check for transfer first (more specific than wallet)
        if "transfer" in prompt_lower or "usdc" in prompt_lower:
            return {
                "function_call": {
                    "name": "transfer_usdc",
                    "args": {
                        "source_wallet_id": "wallet_123",
                        "destination_wallet_id": "wallet_456",
                        "amount": "100.00"
                    }
                }
            }
        # Check for balance before wallet (balance is more specific)
        elif "balance" in prompt_lower or "check" in prompt_lower:
            return {
                "function_call": {
                    "name": "get_wallet_balance",
                    "args": {"wallet_id": "wallet_123"}
                }
            }
        # Wallet creation is the catch-all for wallet-related prompts
        elif "wallet" in prompt_lower or "create" in prompt_lower:
            return {
                "function_call": {
                    "name": "create_wallet",
                    "args": {"blockchain": "ETH-SEPOLIA"}
                }
            }

        return {"text": "No matching function", "function_call": None}

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate structured JSON response."""
        self._track_call("generate_structured", prompt=prompt[:100])

        return {
            "text": '{"status": "approved", "risk_score": 0.2}',
            "parsed": {"status": "approved", "risk_score": 0.2},
            "model": "gemini-pro",
            "latency_ms": 180
        }

    def convert_tools_to_gemini_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to Gemini format (pass-through for mock)."""
        return tools

    def get_call_count(self, method: str) -> int:
        """Get number of times a method was called."""
        return sum(1 for call in self._call_history if call["method"] == method)


class MockArcBlockchainService:
    """
    Mock Arc blockchain service for integration testing.

    Simulates Arc testnet interactions for agent registration and reputation.
    """

    def __init__(self):
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.reputation_scores: Dict[str, int] = {}
        self.transactions: List[Dict[str, Any]] = []
        self._call_history: List[Dict[str, Any]] = []

    def reset(self):
        """Reset all mock data."""
        self.registered_agents.clear()
        self.reputation_scores.clear()
        self.transactions.clear()
        self._call_history.clear()

    def _track_call(self, method: str, **kwargs):
        """Track method calls for verification."""
        self._call_history.append({
            "method": method,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs
        })

    async def register_agent(
        self,
        agent_did: str,
        wallet_address: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Register an agent on Arc blockchain."""
        self._track_call("register_agent", agent_did=agent_did)

        tx_hash = f"0x{uuid.uuid4().hex}"

        agent_data = {
            "did": agent_did,
            "wallet_address": wallet_address,
            "metadata": metadata or {},
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "tx_hash": tx_hash
        }

        self.registered_agents[agent_did] = agent_data
        self.reputation_scores[agent_did] = 100  # Initial reputation

        self.transactions.append({
            "type": "agent_registration",
            "tx_hash": tx_hash,
            "data": agent_data
        })

        return {
            "success": True,
            "tx_hash": tx_hash,
            "agent_data": agent_data
        }

    async def update_reputation(
        self,
        agent_did: str,
        delta: int,
        reason: str = None
    ) -> Dict[str, Any]:
        """Update agent reputation score."""
        self._track_call("update_reputation", agent_did=agent_did, delta=delta)

        if agent_did not in self.registered_agents:
            return {"success": False, "error": "Agent not registered"}

        old_score = self.reputation_scores.get(agent_did, 100)
        new_score = max(0, min(200, old_score + delta))
        self.reputation_scores[agent_did] = new_score

        tx_hash = f"0x{uuid.uuid4().hex}"

        self.transactions.append({
            "type": "reputation_update",
            "tx_hash": tx_hash,
            "data": {
                "agent_did": agent_did,
                "old_score": old_score,
                "new_score": new_score,
                "delta": delta,
                "reason": reason
            }
        })

        return {
            "success": True,
            "tx_hash": tx_hash,
            "old_score": old_score,
            "new_score": new_score
        }

    async def get_agent_reputation(self, agent_did: str) -> Dict[str, Any]:
        """Get agent reputation score."""
        self._track_call("get_agent_reputation", agent_did=agent_did)

        if agent_did not in self.registered_agents:
            return {"success": False, "error": "Agent not registered"}

        return {
            "success": True,
            "agent_did": agent_did,
            "reputation_score": self.reputation_scores.get(agent_did, 0)
        }

    async def verify_payment(
        self,
        transaction_hash: str,
        expected_amount: str
    ) -> Dict[str, Any]:
        """Verify a payment transaction on Arc blockchain."""
        self._track_call("verify_payment", tx_hash=transaction_hash)

        return {
            "success": True,
            "tx_hash": transaction_hash,
            "verified": True,
            "amount": expected_amount,
            "confirmed_at": datetime.now(timezone.utc).isoformat()
        }

    def get_call_count(self, method: str) -> int:
        """Get number of times a method was called."""
        return sum(1 for call in self._call_history if call["method"] == method)


@pytest.fixture
def mock_zerodb_client():
    """
    Provide a fresh MockZeroDBClient instance.

    The client is reset before each test to ensure isolation.
    """
    client = MockZeroDBClient()
    client.reset()
    return client


@pytest.fixture
def mock_circle_service():
    """Provide a fresh MockCircleService instance."""
    service = MockCircleService()
    return service


@pytest.fixture
def mock_gemini_service():
    """Provide a fresh MockGeminiService instance."""
    service = MockGeminiService()
    return service


@pytest.fixture
def mock_arc_service():
    """Provide a fresh MockArcBlockchainService instance."""
    service = MockArcBlockchainService()
    return service


@pytest.fixture
def test_project_id():
    """Provide a test project ID."""
    return f"proj_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_run_id():
    """Provide a test run ID."""
    return f"run_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_agent_dids():
    """Provide sample agent DIDs for testing."""
    return {
        "analyst": ANALYST_AGENT_DID,
        "compliance": COMPLIANCE_AGENT_DID,
        "transaction": TRANSACTION_AGENT_DID
    }


@pytest.fixture
def circle_tools():
    """Define Circle tool schemas for Gemini function calling."""
    return [
        {
            "name": "create_wallet",
            "description": "Create a new Circle wallet",
            "parameters": {
                "type": "object",
                "properties": {
                    "blockchain": {
                        "type": "string",
                        "description": "Target blockchain"
                    }
                }
            }
        },
        {
            "name": "transfer_usdc",
            "description": "Transfer USDC between wallets",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_wallet_id": {"type": "string"},
                    "destination_wallet_id": {"type": "string"},
                    "amount": {"type": "string"}
                },
                "required": ["source_wallet_id", "destination_wallet_id", "amount"]
            }
        },
        {
            "name": "get_wallet_balance",
            "description": "Get USDC balance for a wallet",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_id": {"type": "string"}
                },
                "required": ["wallet_id"]
            }
        }
    ]


@pytest.fixture
def integration_services(
    mock_zerodb_client,
    mock_circle_service,
    mock_gemini_service,
    mock_arc_service
):
    """
    Provide all mock services bundled together.

    Returns a dict with all mock services for easy access.
    """
    return {
        "zerodb": mock_zerodb_client,
        "circle": mock_circle_service,
        "gemini": mock_gemini_service,
        "arc": mock_arc_service
    }
