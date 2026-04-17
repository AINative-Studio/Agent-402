"""
Hedera Identity API endpoints.
Implements the Hedera-native agent identity system.

Issues #191, #192, #193, #194:
- POST /api/v1/hedera/identity/register — Register agent as HTS NFT
- GET  /api/v1/hedera/identity/{agent_id}/did — Resolve agent DID
- POST /api/v1/hedera/identity/directory/search — Query HCS-14 directory
- GET  /api/v1/hedera/identity/{agent_id}/capabilities — Get AAP capabilities
- PUT  /api/v1/hedera/identity/{agent_id}/capabilities — Update capabilities

NOTE: This router is NOT registered in main.py — another group handles that.

Built by AINative Dev Team
Refs #191, #192, #193, #194
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.hedera_identity import (
    AgentRegisterRequest,
    AgentRegisterResponse,
    CapabilitiesResponse,
    CapabilitiesUpdateRequest,
    DirectoryQueryResult,
    DirectoryRegisterRequest,
    DirectoryRegisterResponse,
    DirectorySearchRequest,
    DIDResolutionResult,
)
from app.services.hedera_identity_service import (
    HederaIdentityError,
    HederaIdentityService,
    get_hedera_identity_service,
)
from app.services.hedera_did_service import (
    HederaDIDError,
    HederaDIDNotFoundError,
    HederaDIDService,
    get_hedera_did_service,
)
from app.services.hcs14_directory_service import (
    HCS14DirectoryError,
    HCS14DirectoryService,
    get_hcs14_directory_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/hedera/identity",
    tags=["hedera-identity"],
)


# ---------------------------------------------------------------------------
# POST /api/v1/hedera/identity/register
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=AgentRegisterResponse,
    responses={
        201: {"description": "Agent registered as HTS NFT successfully"},
        400: {"description": "Validation error or invalid request"},
        422: {"description": "Request schema validation failed"},
        502: {"description": "Hedera network error"},
    },
    summary="Register agent as HTS NFT",
    description=(
        "Registers an agent identity as an HTS non-fungible token. "
        "Creates a new serial number under the specified token class "
        "with agent metadata encoded in the NFT. "
        "Refs #191, #194"
    ),
)
async def register_agent(
    request: AgentRegisterRequest,
    identity_service: HederaIdentityService = Depends(get_hedera_identity_service),
) -> AgentRegisterResponse:
    """Register a new agent as an HTS NFT."""
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"

        # Use provided token_id or generate a placeholder DID for the metadata
        token_id = request.token_id or "0.0.pending"
        did = f"did:hedera:testnet:{agent_id}_pending"

        metadata = {
            "name": request.name,
            "role": request.role,
            "did": did,
            "capabilities": request.capabilities,
            "created_at": timestamp,
            "status": "active",
        }

        result = await identity_service.mint_agent_nft(
            token_id=token_id,
            agent_metadata=metadata,
        )

        return AgentRegisterResponse(
            agent_id=agent_id,
            token_id=result["token_id"],
            serial_number=result["serial_number"],
            did=did,
            status=result["status"],
            transaction_id=result.get("transaction_id"),
        )
    except HederaIdentityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


# ---------------------------------------------------------------------------
# GET /api/v1/hedera/identity/{agent_id}/did
# ---------------------------------------------------------------------------


@router.get(
    "/{agent_id}/did",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "DID Document resolved successfully"},
        400: {"description": "Invalid DID format"},
        404: {"description": "Agent DID not found"},
        502: {"description": "Hedera network error"},
    },
    summary="Resolve agent DID",
    description=(
        "Resolves an agent's DID to its W3C-compliant DID Document. "
        "Requires the DID string as a query parameter. "
        "Refs #192"
    ),
)
async def get_agent_did(
    agent_id: str,
    did: Optional[str] = Query(
        default=None,
        description="DID string to resolve (did:hedera:testnet:...)"
    ),
    did_service: HederaDIDService = Depends(get_hedera_did_service),
) -> Dict[str, Any]:
    """Resolve agent DID to W3C DID Document."""
    try:
        # If no DID provided, construct a default DID from agent_id
        did_string = did or f"did:hedera:testnet:{agent_id}_0.0.1"

        result = await did_service.resolve_did(did_string=did_string)
        return result
    except HederaDIDNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except HederaDIDError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


# ---------------------------------------------------------------------------
# POST /api/v1/hedera/identity/directory/register (Refs #291)
# ---------------------------------------------------------------------------


@router.post(
    "/directory/register",
    status_code=status.HTTP_201_CREATED,
    response_model=DirectoryRegisterResponse,
    responses={
        201: {"description": "Agent registered in HCS-14 directory"},
        400: {"description": "Validation error (empty DID, negative reputation)"},
        422: {"description": "Request schema validation failed"},
        502: {"description": "Hedera network error"},
    },
    summary="Register agent in HCS-14 directory",
    description=(
        "Submits an HCS-14 `register` message for the given agent DID to the "
        "directory topic. The registered agent becomes discoverable via "
        "POST /directory/search. Refs #291."
    ),
)
async def register_in_directory(
    request: DirectoryRegisterRequest,
    directory_service: HCS14DirectoryService = Depends(get_hcs14_directory_service),
) -> DirectoryRegisterResponse:
    """Register an agent in the HCS-14 directory."""
    try:
        result = await directory_service.register_agent(
            agent_did=request.agent_did,
            capabilities=request.capabilities,
            role=request.role,
            reputation_score=request.reputation_score,
        )
    except HCS14DirectoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    return DirectoryRegisterResponse(
        status=result.get("status", "SUCCESS"),
        transaction_id=result.get("transaction_id"),
        did=result.get("did", request.agent_did),
        directory_topic=directory_service.directory_topic_id,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/hedera/identity/directory/search
# ---------------------------------------------------------------------------


@router.post(
    "/directory/search",
    status_code=status.HTTP_200_OK,
    response_model=DirectoryQueryResult,
    responses={
        200: {"description": "Directory query completed successfully"},
        400: {"description": "Invalid query parameters"},
        502: {"description": "Hedera network error"},
    },
    summary="Search HCS-14 agent directory",
    description=(
        "Queries the HCS-14 agent directory. "
        "Optionally filters by capability, role, and minimum reputation. "
        "Refs #193"
    ),
)
async def search_directory(
    request: DirectorySearchRequest,
    directory_service: HCS14DirectoryService = Depends(get_hcs14_directory_service),
) -> DirectoryQueryResult:
    """Query the HCS-14 agent directory with optional filters."""
    try:
        result = await directory_service.query_directory(
            capability=request.capability,
            role=request.role,
            min_reputation=request.min_reputation,
        )

        return DirectoryQueryResult(agents=result.get("agents", []))
    except HCS14DirectoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


# ---------------------------------------------------------------------------
# GET /api/v1/hedera/identity/{agent_id}/capabilities
# ---------------------------------------------------------------------------


@router.get(
    "/{agent_id}/capabilities",
    status_code=status.HTTP_200_OK,
    response_model=CapabilitiesResponse,
    responses={
        200: {"description": "AAP capabilities returned successfully"},
        400: {"description": "Invalid request"},
        404: {"description": "Agent NFT not found"},
        502: {"description": "Hedera network error"},
    },
    summary="Get agent AAP capabilities",
    description=(
        "Returns the AAP capability list decoded from the agent's NFT metadata. "
        "Requires token_id and serial_number as query parameters. "
        "Refs #194"
    ),
)
async def get_agent_capabilities(
    agent_id: str,
    token_id: str = Query(description="HTS token ID (e.g. 0.0.9999)"),
    serial_number: int = Query(description="NFT serial number"),
    identity_service: HederaIdentityService = Depends(get_hedera_identity_service),
) -> CapabilitiesResponse:
    """Get AAP capabilities for an agent from their HTS NFT metadata."""
    try:
        capabilities = await identity_service.get_agent_capabilities(
            token_id=token_id,
            serial_number=serial_number,
        )

        return CapabilitiesResponse(
            capabilities=capabilities,
            token_id=token_id,
            serial_number=serial_number,
        )
    except HederaIdentityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


# ---------------------------------------------------------------------------
# PUT /api/v1/hedera/identity/{agent_id}/capabilities
# ---------------------------------------------------------------------------


@router.put(
    "/{agent_id}/capabilities",
    status_code=status.HTTP_200_OK,
    response_model=CapabilitiesResponse,
    responses={
        200: {"description": "AAP capabilities updated successfully"},
        400: {"description": "Invalid capability name or request"},
        422: {"description": "Request schema validation failed"},
        502: {"description": "Hedera network error"},
    },
    summary="Update agent AAP capabilities",
    description=(
        "Updates the AAP capabilities encoded in the agent's HTS NFT metadata. "
        "All capability names must be from the defined AAP capability set. "
        "Refs #194"
    ),
)
async def update_agent_capabilities(
    agent_id: str,
    request: CapabilitiesUpdateRequest,
    identity_service: HederaIdentityService = Depends(get_hedera_identity_service),
) -> CapabilitiesResponse:
    """Update AAP capabilities for an agent."""
    try:
        result = await identity_service.map_aap_capabilities(
            token_id=request.token_id,
            serial_number=request.serial_number,
            capabilities=request.capabilities,
        )

        return CapabilitiesResponse(
            capabilities=result["capabilities"],
            token_id=result["token_id"],
            serial_number=result["serial_number"],
            status=result["status"],
        )
    except HederaIdentityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


# Note: exception handling is done inline within each endpoint handler.
# APIRouter does not support .exception_handler decorators — those are
# registered on the FastAPI app by the router-registering group.
