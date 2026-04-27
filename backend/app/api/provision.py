"""
Zero-human provisioning API.

Exposes:
  POST /v1/public/provision   — wallet sig → API key (no auth required)
  POST /v1/public/keys        — create additional key (auth required)
  GET  /v1/public/capabilities — machine-readable capability manifest (public)

These endpoints enable fully autonomous agent onboarding:
  1. Agent signs a nonce with its wallet
  2. Calls /provision → receives an API key
  3. Uses that key for all subsequent calls

Refs AINative-Studio/Agent-402#363
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Request, status
from pydantic import BaseModel, Field
from typing import Optional

from app.core.errors import APIError, format_error_response
from app.services.provision_service import get_provision_service

router = APIRouter(prefix="/v1/public", tags=["provisioning"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ProvisionRequest(BaseModel):
    wallet_address: str = Field(..., description="EVM wallet address (0x...)")
    message: str = Field(..., description="Plaintext message that was signed")
    signature: str = Field(..., description="EIP-191 personal_sign signature")


class ProvisionResponse(BaseModel):
    api_key: str
    user_id: str
    wallet_address: str
    created_at: str
    capabilities_url: str


class CreateKeyRequest(BaseModel):
    name: Optional[str] = Field(None, description="Human-readable key label")


class CreateKeyResponse(BaseModel):
    api_key: str
    key_id: str
    user_id: str
    key_name: str
    created_at: str


# ---------------------------------------------------------------------------
# Capability manifest (static, config-driven)
# ---------------------------------------------------------------------------

CAPABILITIES = {
    "service": "Agent-402",
    "version": "1.0.0",
    "protocols": ["x402", "hedera-hcs10", "openconvai"],
    "auth": {
        "methods": ["X-API-Key", "Bearer JWT"],
        "provision_url": "/v1/public/provision",
        "keys_url": "/v1/public/keys",
    },
    "features": {
        "x402_signing": True,
        "hedera_payments": True,
        "circle_usdc": True,
        "agent_memory": True,
        "agent_runs": True,
        "embeddings": True,
        "compliance_events": True,
        "threads": True,
        "marketplace": True,
        "trustless_runtime": True,
        "did_identity": True,
        "reputation": True,
    },
    "models": {
        "embedding": [
            {"id": "BAAI/bge-small-en-v1.5", "dimensions": 384, "default": True},
            {"id": "BAAI/bge-base-en-v1.5", "dimensions": 768},
            {"id": "BAAI/bge-large-en-v1.5", "dimensions": 1024},
        ],
        "llm": [
            {"id": "gemini-1.5-flash", "provider": "google"},
            {"id": "gemini-pro", "provider": "google"},
        ],
    },
    "limits": {
        "max_embedding_batch": 100,
        "max_rows_per_query": 1000,
        "max_vector_search_results": 50,
    },
    "pricing": {
        "note": "Usage billed via AINative Studio credits",
        "pricing_url": "https://ainative.studio/pricing",
    },
    "discovery": {
        "openapi_url": "/openapi.json",
        "x402_url": "/.well-known/x402",
    },
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/provision",
    response_model=ProvisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Zero-human wallet provisioning",
    description="""
Provision an API key by proving ownership of an EVM wallet address.

No human dashboard interaction required — fully agent-native.

**Steps:**
1. Generate a message (e.g. `"Agent-402 provision {timestamp}"`)
2. Sign it with your wallet using EIP-191 `personal_sign`
3. POST `{ wallet_address, message, signature }` to this endpoint
4. Receive an API key immediately

Subsequent calls with the same wallet return the existing key (idempotent).
""",
)
async def provision(request: ProvisionRequest) -> ProvisionResponse:
    svc = get_provision_service()
    result = await svc.provision(
        wallet_address=request.wallet_address,
        message=request.message,
        signature=request.signature,
    )
    return ProvisionResponse(**result)


@router.post(
    "/keys",
    response_model=CreateKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create additional API key",
    description="""
Create an additional API key for the authenticated user.

Requires an existing valid API key (X-API-Key header) or Bearer JWT.
Useful for key rotation or scoping keys per agent/environment.
""",
)
async def create_key(
    request_body: CreateKeyRequest,
    http_request: Request,
) -> CreateKeyResponse:
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise APIError(status_code=401, error_code="UNAUTHORIZED", detail="Authentication required")

    svc = get_provision_service()
    result = await svc.create_key(
        user_id=user_id,
        key_name=request_body.name or "default",
    )
    return CreateKeyResponse(**result)


@router.get(
    "/capabilities",
    status_code=status.HTTP_200_OK,
    summary="Machine-readable capability manifest",
    description="""
Public endpoint. Returns a structured manifest of Agent-402's capabilities,
supported protocols, models, limits, and pricing.

Designed for agent-native service discovery — no auth required.
""",
)
async def capabilities():
    return CAPABILITIES
