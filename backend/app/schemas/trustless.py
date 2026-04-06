"""
Trustless runtime API schemas.

Issue #235: Agent Runtime with x402 Service Advertising.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServicePricing(BaseModel):
    """Pricing configuration for a registered service."""

    price_per_call: float = Field(ge=0.0, description="Price in USDC per call")
    currency: str = Field(default="USDC")


class RegisterServiceRequest(BaseModel):
    """Request body for registering an advertised service."""

    agent_did: str
    service_description: str
    pricing: ServicePricing
    x402_endpoint: str = Field(description="Endpoint that accepts x402 payment headers")
    capabilities: List[str] = Field(default_factory=list)


class ServiceRegistryEntry(BaseModel):
    """A service registered in the trustless registry."""

    service_id: str
    agent_did: str
    service_description: str
    pricing: Dict[str, Any]
    x402_endpoint: str
    capabilities: List[str]
    registered_at: str


class DiscoverServicesRequest(BaseModel):
    """Request body for discovering services by capability."""

    capability: str
    max_price: Optional[float] = Field(None, ge=0.0)


class ExecuteServiceCallRequest(BaseModel):
    """Request body for invoking a service via x402."""

    caller_did: str
    service_id: str
    payload: Dict[str, Any]


class ServiceCallReceipt(BaseModel):
    """Receipt returned after a service call is executed."""

    receipt_id: str
    service_id: str
    caller_did: str
    agent_did: str
    payment_tx: str
    result: Dict[str, Any]
    executed_at: str
