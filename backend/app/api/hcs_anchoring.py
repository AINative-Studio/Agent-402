"""
HCS Anchoring API endpoints (Issues #200, #201, #202, #203).

Provides tamper-proof HCS anchoring for:
  POST /anchor/memory          — anchor a memory content hash (Issue #200)
  POST /anchor/compliance      — anchor a compliance event hash (Issue #201)
  GET  /anchor/{memory_id}/verify — verify memory integrity (Issue #202)
  POST /anchor/consolidation   — anchor a consolidation output hash (Issue #203)

Note: This router is NOT registered in main.py per task instructions.
      Include it manually in any FastAPI app where it is needed.

Built by AINative Dev Team
Refs #200, #201, #202, #203
"""
from __future__ import annotations

from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.schemas.hcs_anchoring import (
    AnchorMemoryRequest,
    AnchorComplianceRequest,
    AnchorConsolidationRequest,
    MemoryAnchorResponse,
    ComplianceAnchorResponse,
    MemoryIntegrityResult,
    ConsolidationAnchor,
)
from app.services.hcs_anchoring_service import (
    HCSAnchoringService,
    HCSAnchoringError,
    get_hcs_anchoring_service,
)

router = APIRouter(
    prefix="",
    tags=["hcs-anchoring"],
)


# ---------------------------------------------------------------------------
# Issue #200 — POST /anchor/memory
# ---------------------------------------------------------------------------

@router.post(
    "/anchor/memory",
    response_model=MemoryAnchorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Anchor memory content hash to HCS",
    description="""
    Submit the SHA-256 hash of a memory's content to Hedera Consensus Service (HCS).

    The hash is permanently recorded on-chain so that the memory's integrity
    can be verified at any future point using GET /anchor/{memory_id}/verify.

    **Issue #200:** Memory Operations Anchor to HCS
    """,
    responses={
        201: {"description": "Memory successfully anchored", "model": MemoryAnchorResponse},
        422: {"description": "Validation error"},
        502: {"description": "HCS submission failed"},
    },
)
async def post_anchor_memory(
    request: AnchorMemoryRequest,
    service: HCSAnchoringService = Depends(get_hcs_anchoring_service),
) -> MemoryAnchorResponse:
    """
    Anchor a memory content hash to HCS.

    Args:
        request: AnchorMemoryRequest with memory_id, content_hash, agent_id, namespace.
        service: Injected HCSAnchoringService.

    Returns:
        MemoryAnchorResponse with memory_id, sequence_number, timestamp.

    Raises:
        502 Bad Gateway: when HCS submission fails.
    """
    try:
        result = await service.anchor_memory(
            memory_id=request.memory_id,
            content_hash=request.content_hash,
            agent_id=request.agent_id,
            namespace=request.namespace,
        )
        return MemoryAnchorResponse(**result)
    except HCSAnchoringError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc), "error_code": "HCS_ANCHOR_ERROR"},
        )


# ---------------------------------------------------------------------------
# Issue #201 — POST /anchor/compliance
# ---------------------------------------------------------------------------

@router.post(
    "/anchor/compliance",
    response_model=ComplianceAnchorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Anchor compliance event hash to HCS",
    description="""
    Submit a compliance event's hash to Hedera Consensus Service (HCS).

    A deterministic SHA-256 hash is computed from the event fields and
    recorded immutably on HCS to serve as a tamper-proof compliance audit trail.

    **Issue #201:** Compliance Events on HCS
    """,
    responses={
        201: {
            "description": "Compliance event successfully anchored",
            "model": ComplianceAnchorResponse,
        },
        422: {"description": "Validation error"},
        502: {"description": "HCS submission failed"},
    },
)
async def post_anchor_compliance(
    request: AnchorComplianceRequest,
    service: HCSAnchoringService = Depends(get_hcs_anchoring_service),
) -> ComplianceAnchorResponse:
    """
    Anchor a compliance event to HCS.

    Args:
        request: AnchorComplianceRequest with event_id, event_type, classification,
                 risk_score, agent_id.
        service: Injected HCSAnchoringService.

    Returns:
        ComplianceAnchorResponse with event_id, sequence_number, timestamp.

    Raises:
        502 Bad Gateway: when HCS submission fails.
    """
    try:
        result = await service.anchor_compliance_event(
            event_id=request.event_id,
            event_type=request.event_type,
            classification=request.classification,
            risk_score=request.risk_score,
            agent_id=request.agent_id,
        )
        return ComplianceAnchorResponse(**result)
    except HCSAnchoringError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc), "error_code": "HCS_ANCHOR_ERROR"},
        )


# ---------------------------------------------------------------------------
# Issue #202 — GET /anchor/{memory_id}/verify
# ---------------------------------------------------------------------------

@router.get(
    "/anchor/{memory_id}/verify",
    response_model=MemoryIntegrityResult,
    status_code=status.HTTP_200_OK,
    summary="Verify memory integrity against HCS anchor",
    description="""
    Compare the SHA-256 hash of the supplied *current_content* against
    the hash recorded on HCS when the memory was first anchored.

    **Returns:**
    - ``verified: true``  + ``match: true`` — content is unmodified.
    - ``verified: false`` + ``match: false`` — content has been tampered with.
    - ``verified: false`` + ``reason: "no_anchor_found"`` — memory was never anchored.

    **Issue #202:** Memory Integrity Verification
    """,
    responses={
        200: {"description": "Verification result", "model": MemoryIntegrityResult},
        422: {"description": "Missing current_content query parameter"},
    },
)
async def get_anchor_verify(
    memory_id: str,
    current_content: str = Query(
        ...,
        description="Current content of the memory to verify against the HCS anchor",
    ),
    service: HCSAnchoringService = Depends(get_hcs_anchoring_service),
) -> MemoryIntegrityResult:
    """
    Verify memory integrity against the HCS anchor.

    Args:
        memory_id:       Path parameter — memory to verify.
        current_content: Query parameter — current content string.
        service:         Injected HCSAnchoringService.

    Returns:
        MemoryIntegrityResult with verification outcome.
    """
    result = await service.verify_memory_integrity(
        memory_id=memory_id,
        current_content=current_content,
    )
    return MemoryIntegrityResult(**result)


# ---------------------------------------------------------------------------
# Issue #203 — POST /anchor/consolidation
# ---------------------------------------------------------------------------

@router.post(
    "/anchor/consolidation",
    response_model=ConsolidationAnchor,
    status_code=status.HTTP_201_CREATED,
    summary="Anchor consolidation synthesis output to HCS",
    description="""
    Anchor a NousCoder synthesis / consolidation output to HCS.

    Records the synthesis hash, the source memory IDs, and the model used
    so that the full provenance of the synthesis can be verified on-chain.

    **Issue #203:** Consolidation Output Anchoring
    """,
    responses={
        201: {
            "description": "Consolidation successfully anchored",
            "model": ConsolidationAnchor,
        },
        422: {"description": "Validation error"},
        502: {"description": "HCS submission failed"},
    },
)
async def post_anchor_consolidation(
    request: AnchorConsolidationRequest,
    service: HCSAnchoringService = Depends(get_hcs_anchoring_service),
) -> ConsolidationAnchor:
    """
    Anchor a consolidation output to HCS.

    Args:
        request: AnchorConsolidationRequest with consolidation_id, synthesis_hash,
                 source_memory_ids, model_used.
        service: Injected HCSAnchoringService.

    Returns:
        ConsolidationAnchor with consolidation_id, sequence_number, timestamp.

    Raises:
        502 Bad Gateway: when HCS submission fails.
    """
    try:
        result = await service.anchor_consolidation(
            consolidation_id=request.consolidation_id,
            synthesis_hash=request.synthesis_hash,
            source_memory_ids=request.source_memory_ids,
            model_used=request.model_used,
        )
        return ConsolidationAnchor(**result)
    except HCSAnchoringError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc), "error_code": "HCS_ANCHOR_ERROR"},
        )
