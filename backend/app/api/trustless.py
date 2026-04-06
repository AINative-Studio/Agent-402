"""
Trustless Runtime API router.
Exposes x402 service registry and execution endpoints.

Issue #235.

Built by AINative Dev Team
Refs #235
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.schemas.trustless import (
    DiscoverServicesRequest,
    ExecuteServiceCallRequest,
    RegisterServiceRequest,
    ServiceCallReceipt,
    ServiceRegistryEntry,
)
from app.services.trustless_runtime_service import (
    ServiceNotFoundError,
    trustless_runtime_service,
)

router = APIRouter(prefix="/trustless", tags=["trustless"])


@router.post("/services", response_model=Dict[str, Any], status_code=201)
async def register_service(body: RegisterServiceRequest) -> Dict[str, Any]:
    """Advertise an agent service in the trustless registry."""
    return await trustless_runtime_service.register_service(
        agent_did=body.agent_did,
        service_description=body.service_description,
        pricing=body.pricing.dict(),
        x402_endpoint=body.x402_endpoint,
        capabilities=body.capabilities,
    )


@router.get("/services", response_model=List[Dict[str, Any]])
async def get_registry() -> List[Dict[str, Any]]:
    """Return all advertised services."""
    return await trustless_runtime_service.get_service_registry()


@router.post("/discover", response_model=List[Dict[str, Any]])
async def discover_services(body: DiscoverServicesRequest) -> List[Dict[str, Any]]:
    """Discover services by capability and optional price ceiling."""
    return await trustless_runtime_service.discover_services(
        capability=body.capability,
        max_price=body.max_price,
    )


@router.post("/execute", response_model=Dict[str, Any], status_code=201)
async def execute_service_call(body: ExecuteServiceCallRequest) -> Dict[str, Any]:
    """Invoke a registered service with an x402 payment simulation."""
    try:
        return await trustless_runtime_service.execute_service_call(
            caller_did=body.caller_did,
            service_id=body.service_id,
            payload=body.payload,
        )
    except ServiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
