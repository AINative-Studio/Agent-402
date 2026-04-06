"""
Trustless Runtime Service.
Handles x402 service advertising, discovery, invocation, and receipts.

Issue #235: Agent Runtime with x402 Service Advertising.

Built by AINative Dev Team
Refs #235
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.errors import APIError
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

SERVICE_REGISTRY_TABLE = "service_registry"
SERVICE_RECEIPTS_TABLE = "service_receipts"


class ServiceNotFoundError(APIError):
    """Raised when a registered service cannot be found."""

    def __init__(self, service_id: str):
        super().__init__(
            status_code=404,
            error_code="SERVICE_NOT_FOUND",
            detail=f"Service not found: {service_id}",
        )


class TrustlessRuntimeService:
    """
    Manages the trustless agent service registry and x402-signed invocations.

    Provides:
    - Service registration with x402 endpoint advertising
    - Capability-based discovery with price filtering
    - x402-signed service execution with receipt generation
    - Full registry enumeration
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        """Lazy-init ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    async def register_service(
        self,
        agent_did: str,
        service_description: str,
        pricing: Dict[str, Any],
        x402_endpoint: str,
        capabilities: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Advertise an agent service in the trustless registry.

        Args:
            agent_did: Provider agent DID
            service_description: Human-readable service description
            pricing: Pricing dict (price_per_call, currency, etc.)
            x402_endpoint: URL that accepts x402 payment headers
            capabilities: Optional list of capability tags

        Returns:
            Registry entry dict with service_id
        """
        service_id = f"svc_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        row = {
            "service_id": service_id,
            "agent_did": agent_did,
            "service_description": service_description,
            "pricing": pricing,
            "x402_endpoint": x402_endpoint,
            "capabilities": capabilities or [],
            "active": True,
            "registered_at": now,
        }

        await self.client.insert_row(SERVICE_REGISTRY_TABLE, row)
        logger.info(f"Registered service: {service_id} for agent {agent_did}")
        return self._entry_from_row(row)

    async def discover_services(
        self,
        capability: str,
        max_price: Optional[float],
    ) -> List[Dict[str, Any]]:
        """
        Find services that offer a given capability within a price ceiling.

        Args:
            capability: Capability string to search for
            max_price: Optional maximum price_per_call (inclusive)

        Returns:
            List of matching registry entry dicts
        """
        result = await self.client.query_rows(
            SERVICE_REGISTRY_TABLE,
            filter={"active": True},
            limit=10_000,
        )
        rows = result.get("rows", [])

        def _matches(row: Dict[str, Any]) -> bool:
            caps = row.get("capabilities") or []
            if capability not in caps:
                return False
            if max_price is not None:
                price = (row.get("pricing") or {}).get("price_per_call", 0.0)
                if price > max_price:
                    return False
            return True

        matched = [r for r in rows if _matches(r)]
        return [self._entry_from_row(r) for r in matched]

    async def execute_service_call(
        self,
        caller_did: str,
        service_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Invoke a registered service with an x402-signed payment.

        Args:
            caller_did: Calling agent's DID
            service_id: Target service ID
            payload: Request payload

        Returns:
            Receipt dict with receipt_id, payment_tx, result, executed_at

        Raises:
            ServiceNotFoundError: If service_id does not exist
        """
        result = await self.client.query_rows(
            SERVICE_REGISTRY_TABLE,
            filter={"service_id": service_id, "active": True},
            limit=1,
        )
        rows = result.get("rows", [])
        if not rows:
            raise ServiceNotFoundError(service_id)

        service_row = rows[0]
        receipt_id = f"rcpt_{uuid.uuid4().hex[:16]}"
        payment_tx = f"tx_{uuid.uuid4().hex[:20]}"
        now = datetime.now(timezone.utc).isoformat()

        # Simulated execution result (in production: HTTP call to x402_endpoint)
        execution_result = {
            "status": "success",
            "payload_echo": payload,
        }

        receipt_row = {
            "receipt_id": receipt_id,
            "service_id": service_id,
            "caller_did": caller_did,
            "agent_did": service_row.get("agent_did"),
            "payment_tx": payment_tx,
            "result": execution_result,
            "executed_at": now,
        }

        await self.client.insert_row(SERVICE_RECEIPTS_TABLE, receipt_row)
        logger.info(
            f"Executed service call: service={service_id}, caller={caller_did}, "
            f"receipt={receipt_id}"
        )
        return receipt_row

    async def get_service_registry(self) -> List[Dict[str, Any]]:
        """
        Return all advertised services.

        Returns:
            List of all active registry entry dicts
        """
        result = await self.client.query_rows(
            SERVICE_REGISTRY_TABLE,
            filter={"active": True},
            limit=10_000,
        )
        rows = result.get("rows", [])
        return [self._entry_from_row(r) for r in rows]

    def _entry_from_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a raw ZeroDB row to a clean registry entry dict."""
        return {
            "service_id": row.get("service_id"),
            "agent_did": row.get("agent_did"),
            "service_description": row.get("service_description", ""),
            "pricing": row.get("pricing") or {},
            "x402_endpoint": row.get("x402_endpoint", ""),
            "capabilities": row.get("capabilities") or [],
            "registered_at": row.get("registered_at", ""),
        }


trustless_runtime_service = TrustlessRuntimeService()
