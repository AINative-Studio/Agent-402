"""
FastAPI application entry point.
Implements ZeroDB-compliant API server per PRD and DX Contract.

DX Contract Section 7 (Error Semantics):
- All errors return { detail, error_code }
- Error codes are stable and documented
- Validation errors use HTTP 422

Epic 2, Issue 3: As a developer, all errors include a detail field.
Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND 404 errors.

404 Error Distinction:
- PATH_NOT_FOUND: The API endpoint/route doesn't exist (typo in URL)
- RESOURCE_NOT_FOUND: The endpoint exists but the resource doesn't
- Specific resource errors: PROJECT_NOT_FOUND, AGENT_NOT_FOUND, TABLE_NOT_FOUND

Reference: backend/app/schemas/errors.py for error response schemas.
"""
import os
import logging
from datetime import datetime
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.errors import APIError, format_error_response
from app.core.exceptions import ZeroDBException
from app.schemas.x402_protocol import X402ProtocolRequest, X402ProtocolResponse
from app.core.did_signer import DIDSigner, InvalidDIDError
from app.services.x402_service import x402_service

logger = logging.getLogger(__name__)
from app.core.middleware import (
    zerodb_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    internal_server_error_handler,
    DEFAULT_ERROR_DETAIL
)
from app.api.projects import router as projects_router
from app.api.auth import router as auth_router
# Issue #363: Zero-human provisioning
from app.api.provision import router as provision_router
# Use full embeddings API with generate, embed-and-store, and search endpoints
# Includes Issue #17 namespace scoping and Issue #23 search namespace parameter
from app.api.embeddings import router as embeddings_router
# Epic 4 Issue 16: Embed-and-store endpoint with texts field
from app.api.embeddings_embed_store import router as embed_store_router
from app.api.vectors import router as vectors_router
# Epic 8: Events API
from app.api.events import router as events_router
# Epic 12 Issue 3: Compliance events API
from app.api.compliance_events import router as compliance_events_router
# Epic 12 Issue 1: Agent profiles API
from app.api.agents import router as agents_router
# Epic 12 Issue 2: Agent memory persistence
from app.api.agent_memory import router as agent_memory_router
# Epic 12 Issue 4: X402 requests linked to agent + task
from app.api.x402_requests import router as x402_requests_router
# Epic 12 Issue 5: Agent run replay from ZeroDB records
from app.api.runs import router as runs_router
# Epic 7 Issue 1: Table creation with schema definitions
from app.api.tables import router as tables_router
# Epic 7 Issue 4: Row pagination and retrieval
from app.api.rows import router as rows_router
# Issues #119 + #122: X402 Payment Tracking and Agent Interactions
from app.api.agent_interactions import router as agent_interactions_router
# Issue #114: Circle Wallets and USDC Payments
from app.api.circle import router as circle_router
# Issue #156: Wallet status management API
from app.api.wallet_status import router as wallet_status_router
# Issue #187: Hedera USDC Payment Settlement via HTS
from app.api.hedera_payments import router as hedera_payments_router
# Issue #188: Hedera Agent Wallet Creation
from app.api.hedera_wallets import router as hedera_wallets_router
# Epic 17: Agent Identity on Hedera (created by parallel agent group)
try:
    from app.api.hedera_identity import router as hedera_identity_router
    _hedera_identity_router_available = True
except ImportError:
    hedera_identity_router = None
    _hedera_identity_router_available = False
# Epic 18: Reputation System on Hedera (created by parallel agent group)
try:
    from app.api.hedera_reputation import router as hedera_reputation_router
    _hedera_reputation_router_available = True
except ImportError:
    hedera_reputation_router = None
    _hedera_reputation_router_available = False
# Sprint 3 - Epic 19: HCS Anchoring
try:
    from app.api.hcs_anchoring import router as hcs_anchoring_router
except ImportError:
    hcs_anchoring_router = None
# Sprint 3 - Epic 20: OpenConvAI HCS-10
try:
    from app.api.openconvai import router as openconvai_router
except ImportError:
    openconvai_router = None
# Sprint 3 - Epic 21: Memory Decay
try:
    from app.api.memory_decay import router as memory_decay_router
except ImportError:
    memory_decay_router = None
# Sprint 3 - Epic 27: OpenClaw Agents
try:
    from app.api.openclaw_agents import router as openclaw_agents_router
except ImportError:
    openclaw_agents_router = None
# Sprint 4 - Epic 22: Real-Time Events
try:
    from app.api.websocket_events import router as websocket_events_router
    from app.api.sse_events import router as sse_events_router
except ImportError:
    websocket_events_router = sse_events_router = None
# Sprint 4 - Epic 24: Threads
try:
    from app.api.threads import router as threads_router
except ImportError:
    threads_router = None
# Sprint 4 - Epic 23: Marketplace
try:
    from app.api.marketplace import router as marketplace_router
except ImportError:
    marketplace_router = None
# Sprint 4 - Epic 28: Trustless V1
try:
    from app.api.trustless import router as trustless_router
except ImportError:
    trustless_router = None
# Sprint 4 - Epic 26: Billing
try:
    from app.api.billing import router as billing_router
except ImportError:
    billing_router = None
# Sprint 5 - Observability & Analytics
try:
    from app.api.analytics import router as analytics_router
except ImportError:
    analytics_router = None
try:
    from app.api.webhooks import router as webhooks_router
except ImportError:
    webhooks_router = None
# Post-Launch - Plugin System
try:
    from app.api.plugins import router as plugins_router
except ImportError:
    plugins_router = None
# Post-Launch - Hedera Audit
try:
    from app.api.hedera_audit import router as hedera_audit_router
except ImportError:
    hedera_audit_router = None
from app.middleware import APIKeyAuthMiddleware, ImmutableMiddleware
# Refs #285, #300: Workshop-mode path rewriter for flat /api/v1/* prefix
from app.middleware.workshop_prefix import WorkshopPrefixMiddleware


# Create FastAPI application
app = FastAPI(
    title="ZeroDB Agent Finance API",
    description="Autonomous Fintech Agent Crew - AINative Edition",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Immutable Record middleware - enforces append-only semantics
# Per Epic 12 Issue 6 and PRD Section 10: Non-repudiation
# Must be added before authentication to reject mutations early
app.add_middleware(ImmutableMiddleware)

# API Key Authentication middleware - must be added before CORS
# Per Epic 2 Story 1: All /v1/public/* endpoints require X-API-Key
app.add_middleware(APIKeyAuthMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Workshop-mode path rewriter - must be outermost so downstream middleware
# (auth, immutable) see the rewritten /v1/public/... path. Gated by
# settings.workshop_mode so production is unaffected by default.
# Overrides are populated by B2 (#302) and B3 (#303) for non-conventional
# prefixes (hcs10, anchor, marketplace).
app.add_middleware(
    WorkshopPrefixMiddleware,
    enabled=settings.workshop_mode,
    default_project_id=settings.workshop_default_project_id,
    overrides={
        # B2 (#302): HCS anchoring is mounted at `/anchor/*`, not under
        # /v1/public/{project_id}/, so route it directly.
        "anchor/": "/anchor/",
        # B2 (#302, subsumes #295): HCS-10 (OpenConvAI) router lives at
        # `/hcs10/*` without a project prefix.
        "hcs10/": "/hcs10/",
        # B3 (#303): marketplace router is mounted at `/marketplace/*`
        # without a project prefix.
        "marketplace/": "/marketplace/",
    },
)


# Exception handlers - implement DX Contract error format
# Handlers are registered in order of specificity (most specific first)

# 1. Handle custom ZeroDB exceptions (from app.core.exceptions)
app.add_exception_handler(ZeroDBException, zerodb_exception_handler)

# 2. Handle custom API errors (from app.core.errors)
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """
    Handle custom API errors with consistent format.
    Per DX Contract: All errors return { detail, error_code }.
    Per Epic 2, Issue 3: All errors include a detail field.
    """
    # Ensure detail and error_code are never empty (defensive programming)
    detail = exc.detail if exc.detail else DEFAULT_ERROR_DETAIL
    error_code = exc.error_code if exc.error_code else "ERROR"

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(error_code, detail)
    )

# 3. Handle Pydantic validation errors (HTTP 422)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# 4. Handle FastAPI HTTPException
app.add_exception_handler(HTTPException, http_exception_handler)

# 5. Handle Starlette HTTPException (for cases not caught by FastAPI)
# Per Epic 9, Issue 42: All errors return { detail, error_code }
# Per Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND
@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle Starlette HTTPException with consistent error format.
    Per DX Contract: All errors return { detail, error_code }.
    Per Epic 9, Issue 42: All error responses include detail and error_code.
    Per Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND.

    404 Error Distinction:
    - PATH_NOT_FOUND: FastAPI/Starlette returns 404 for unknown routes
    - RESOURCE_NOT_FOUND: Custom exceptions return 404 for missing resources
    """
    from app.core.middleware import _derive_error_code_from_status, _is_route_not_found

    detail = str(exc.detail) if exc.detail else DEFAULT_ERROR_DETAIL

    # Epic 9 Issue 43: Detect route-not-found 404s
    if exc.status_code == 404 and _is_route_not_found(exc):
        error_code = "PATH_NOT_FOUND"
        detail = (
            f"Path '{request.url.path}' not found. "
            f"Check the API documentation for valid endpoints."
        )
    else:
        error_code = _derive_error_code_from_status(exc.status_code)

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(error_code, detail)
    )

# 6. Handle all other unexpected exceptions (catch-all)
app.add_exception_handler(Exception, internal_server_error_handler)


# X402 Protocol Discovery Endpoint - Issue #73
# Per PRD Section 9: Discovery endpoint for X402 protocol
# Must be BEFORE middleware registration to ensure public access
@app.get(
    "/.well-known/x402",
    tags=["x402"],
    summary="X402 Protocol Discovery",
    status_code=status.HTTP_200_OK,
    response_model=None
)
async def x402_discovery():
    """
    X402 Protocol Discovery Endpoint.

    Per PRD Section 9 (System Architecture):
    - Public discovery endpoint (no authentication required)
    - Returns X402 protocol metadata and capabilities
    - Enables agent-native service discovery

    This endpoint allows agents and clients to discover:
    - Protocol version
    - X402 endpoint location
    - Supported DID methods
    - Supported signature algorithms
    - Server information

    Returns:
        JSON object with X402 protocol metadata:
        - version: Protocol version (1.0)
        - endpoint: X402 signed request endpoint (/x402)
        - supported_dids: List of supported DID methods (["did:ethr"])
        - signature_methods: List of supported signature algorithms (["ECDSA"])
        - server_info: Server name and description
    """
    # Issue #190: include Hedera metadata while preserving all existing fields
    return {
        "version": "1.0",
        "endpoint": "/x402",
        "supported_dids": ["did:ethr", "did:hedera"],
        "signature_methods": ["ECDSA", "Ed25519"],
        "server_info": {
            "name": "ZeroDB Agent Finance API",
            "description": "Autonomous Fintech Agent Crew - AINative Edition"
        },
        "hedera": {
            "network": os.environ.get("HEDERA_NETWORK", "testnet"),
            "usdc_token_id": "0.0.456858",
            "operator_account_id": os.environ.get("HEDERA_OPERATOR_ID", ""),
            "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1"
        }
    }


# X402 Protocol Signed POST Endpoint - Issue #77
# Per PRD Section 9: X402 signed POST endpoint at root path
# Must be BEFORE middleware registration to ensure public access (no X-API-Key)
@app.post(
    "/x402",
    tags=["x402"],
    summary="X402 Protocol Signed POST Endpoint",
    status_code=status.HTTP_200_OK,
    response_model=None,
    responses={
        200: {
            "description": "Request received and logged successfully",
            "content": {
                "application/json": {
                    "example": {
                        "request_id": "x402_req_a1b2c3d4e5f6g7h8",
                        "status": "received",
                        "timestamp": "2026-01-14T12:34:56.789Z"
                    }
                }
            }
        },
        401: {
            "description": "Invalid signature or DID format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid signature: signature verification failed",
                        "error_code": "UNAUTHORIZED"
                    }
                }
            }
        },
        422: {
            "description": "Invalid payload format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "payload"],
                                "msg": "Payload cannot be empty",
                                "type": "value_error"
                            }
                        ],
                        "error_code": "VALIDATION_ERROR"
                    }
                }
            }
        }
    }
)
async def x402_signed_request(request: Request):
    """
    X402 Protocol Signed POST Endpoint.

    Per PRD Section 9 (System Architecture):
    - Root-level /x402 endpoint for signed X402 protocol requests
    - Public endpoint (no X-API-Key authentication required)
    - Uses DID-based signature verification for authentication
    - Logs all requests to x402_requests collection for audit trail

    Per Issue #77 Acceptance Criteria:
    - Accept X402 protocol request format (did, signature, payload)
    - Verify signature using DID signing service
    - Return 200 on success with request_id
    - Return 401 for invalid signatures
    - Return 422 for invalid payload format
    - Log to x402_requests collection
    - Endpoint must NOT require X-API-Key (public protocol endpoint)

    Security:
    - DID-based authentication via ECDSA signatures
    - Signature verification against payload hash
    - Non-repudiation through cryptographic signatures
    - All requests logged for audit trail

    Request Format:
        {
            "did": "did:ethr:0xabc123def456...",
            "signature": "0x8f3e9a7c2b1d4e6f...",
            "payload": {
                "action": "transfer",
                "amount": 1000,
                "currency": "USD",
                "recipient": "did:ethr:0xdef789...",
                "timestamp": "2026-01-14T12:00:00Z"
            }
        }

    Response Format:
        {
            "request_id": "x402_req_a1b2c3d4e5f6g7h8",
            "status": "received",
            "timestamp": "2026-01-14T12:34:56.789Z"
        }

    Raises:
        HTTPException 401: Invalid signature or DID format
        HTTPException 422: Invalid payload format

    Security Notes:
        - Uses ECDSA SECP256k1 signature verification
        - Constant-time signature comparison (via hmac.compare_digest)
        - SHA256 payload hashing with deterministic JSON serialization
        - No private keys logged or exposed
        - All requests logged for audit trail
        - Rate limiting TODO (max 100 req/min per DID)
    """
    # Parse and validate request body
    try:
        body = await request.json()
        x402_request = X402ProtocolRequest(**body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid request format: {str(e)}"
        )

    # Verify signature before processing request
    try:
        is_valid = DIDSigner.verify_signature(
            payload=x402_request.payload,
            signature_hex=x402_request.signature,
            did=x402_request.did
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature: signature verification failed"
            )

    except InvalidDIDError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid DID format: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        # Catch any other verification errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Signature verification error: {str(e)}"
        )

    # Generate request ID and timestamp
    request_id = x402_service.generate_request_id()
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Store request in x402_requests collection
    # Create a minimal record for protocol-level requests
    # These differ from /v1/public/{project_id}/x402-requests which require project context
    try:
        # For protocol-level requests, we use a special "protocol" project_id
        await x402_service.create_request(
            project_id="x402_protocol",
            agent_id=x402_request.did,
            task_id="x402_protocol_request",
            run_id=request_id,
            request_payload=x402_request.payload,
            signature=x402_request.signature,
            metadata={
                "source": "x402_protocol_endpoint",
                "signature_verified": True
            }
        )
    except Exception as e:
        # Log error but don't fail the request
        # The signature verification already succeeded
        # This is a best-effort logging mechanism
        logger.error(
            f"Failed to store X402 protocol request: {e}",
            extra={
                "request_id": request_id,
                "did": x402_request.did,
                "error": str(e)
            }
        )

    # Return success response
    return X402ProtocolResponse(
        request_id=request_id,
        status="received",
        timestamp=timestamp
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    status_code=status.HTTP_200_OK
)
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "ZeroDB Agent Finance API",
        "version": "1.0.0"
    }


# Include routers
app.include_router(auth_router)
app.include_router(provision_router)  # Issue #363: zero-human provisioning
app.include_router(projects_router)
# Issue #79: embeddings_router must come first to handle single 'text' field properly
# embeddings_router handles single text (text field), embed_store_router handles batch (documents field)
app.include_router(embeddings_router)
app.include_router(embed_store_router)
app.include_router(vectors_router)
app.include_router(events_router)
app.include_router(compliance_events_router)
app.include_router(agents_router)
app.include_router(agent_memory_router)
# Epic 34 (#292 S0): ZeroMemory Cognitive API — 4 endpoints live in the
# `app.api.cognitive` package, aggregated under one router.
try:
    from app.api.cognitive_memory import router as cognitive_memory_router
    app.include_router(cognitive_memory_router)
except ImportError:
    cognitive_memory_router = None
app.include_router(x402_requests_router)
app.include_router(runs_router)
app.include_router(tables_router)
app.include_router(rows_router)
# Issues #119 + #122: X402 Payment Tracking and Agent Interactions
app.include_router(agent_interactions_router)
# Issue #114: Circle Wallets and USDC Payments
app.include_router(circle_router)
# Issue #156: Wallet status management API
app.include_router(wallet_status_router)
# Issue #187: Hedera USDC Payment Settlement via HTS
app.include_router(hedera_payments_router)
# Issue #188: Hedera Agent Wallet Creation
app.include_router(hedera_wallets_router)
# Epic 17: Agent Identity on Hedera (registered when module is available)
if _hedera_identity_router_available and hedera_identity_router is not None:
    app.include_router(hedera_identity_router)
# Epic 18: Reputation System on Hedera (registered when module is available)
if _hedera_reputation_router_available and hedera_reputation_router is not None:
    app.include_router(hedera_reputation_router)
# Sprint 3 - Epic 19: HCS Anchoring (registered when module is available)
if hcs_anchoring_router is not None:
    app.include_router(hcs_anchoring_router)
# Sprint 3 - Epic 20: OpenConvAI HCS-10 (registered when module is available)
if openconvai_router is not None:
    app.include_router(openconvai_router)
# Sprint 3 - Epic 21: Memory Decay (registered when module is available)
if memory_decay_router is not None:
    app.include_router(memory_decay_router)
# Sprint 3 - Epic 27: OpenClaw Agents (registered when module is available)
if openclaw_agents_router is not None:
    app.include_router(openclaw_agents_router)
# Sprint 4 - Epic 22: Real-Time Events (registered when modules are available)
if websocket_events_router is not None:
    app.include_router(websocket_events_router)
if sse_events_router is not None:
    app.include_router(sse_events_router)
# Sprint 4 - Epic 24: Threads (registered when module is available)
if threads_router is not None:
    app.include_router(threads_router)
# Sprint 4 - Epic 23: Marketplace (registered when module is available)
if marketplace_router is not None:
    app.include_router(marketplace_router)
# Sprint 4 - Epic 28: Trustless V1 (registered when module is available)
if trustless_router is not None:
    app.include_router(trustless_router)
# Sprint 4 - Epic 26: Billing (registered when module is available)
if billing_router is not None:
    app.include_router(billing_router)
# Sprint 5 - Observability & Analytics (registered when modules are available)
if analytics_router is not None:
    app.include_router(analytics_router)
if webhooks_router is not None:
    app.include_router(webhooks_router)
# Post-Launch - Plugin System (registered when module is available)
if plugins_router is not None:
    app.include_router(plugins_router)
# Post-Launch - Hedera Audit (registered when module is available)
if hedera_audit_router is not None:
    app.include_router(hedera_audit_router)


# Root endpoint
@app.get(
    "/",
    tags=["root"],
    summary="API information"
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ZeroDB Agent Finance API",
        "version": "1.0.0",
        "description": "Autonomous Fintech Agent Crew - AINative Edition",
        "docs_url": "/docs",
        "health_url": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
