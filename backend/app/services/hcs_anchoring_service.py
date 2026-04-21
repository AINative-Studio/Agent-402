"""
HCS Anchoring Service — tamper-proof anchoring for memory operations,
compliance events, integrity verification, and consolidation outputs.

Submits SHA-256 content hashes to an HCS topic so that any future
mutation of stored data can be detected cryptographically.

Issues:
  #200 — Memory Operations Anchor to HCS
  #201 — Compliance Events on HCS
  #202 — Memory Integrity Verification
  #203 — Consolidation Output Anchoring

Built by AINative Dev Team
Refs #200, #201, #202, #203
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from app.services.hedera_client import get_hedera_client

logger = logging.getLogger(__name__)

# Default HCS topic used when no env var or constructor arg is supplied.
# Overridable via HEDERA_ANCHOR_TOPIC_ID.
DEFAULT_ANCHOR_TOPIC_ID = "0.0.800001"


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class HCSAnchoringError(Exception):
    """
    Raised when an HCS anchoring or retrieval operation fails.

    Wraps lower-level network / client errors so callers have a single
    exception type to catch.
    """

    def __init__(self, message: str, original: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.original = original


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _sha256_hex(data: str) -> str:
    """Return the SHA-256 hex digest of *data*."""
    return hashlib.sha256(data.encode()).hexdigest()


def _build_compliance_event_hash(
    event_id: str,
    event_type: str,
    classification: str,
    risk_score: float,
    agent_id: str,
) -> str:
    """
    Build a deterministic SHA-256 hash of the compliance event fields.

    The hash is computed over a canonical JSON representation of the event
    fields, sorted by key so the result is stable regardless of insertion order.
    """
    canonical = json.dumps(
        {
            "agent_id": agent_id,
            "classification": classification,
            "event_id": event_id,
            "event_type": event_type,
            "risk_score": risk_score,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_hex(canonical)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class HCSAnchoringService:
    """
    Service for anchoring agent operations to Hedera Consensus Service (HCS).

    Provides tamper-proof audit trail capabilities by submitting SHA-256 hashes
    of memory content, compliance events, and synthesis outputs to an HCS topic.
    Anchored hashes can be retrieved from the mirror node for later integrity
    verification.

    All public methods are async-safe and designed for use inside FastAPI
    request handlers or background tasks.

    Dependency Injection:
        Pass a pre-configured *hcs_client* during construction for testing.
        In production the lazy property uses `get_hedera_client()`.
    """

    def __init__(
        self,
        hcs_client: Optional[Any] = None,
        anchor_topic_id: Optional[str] = None,
    ):
        """
        Initialise the anchoring service.

        Args:
            hcs_client: Optional HCS client instance. When None the service
                        creates one lazily via ``get_hedera_client()``.
            anchor_topic_id: HCS topic ID to anchor messages to. When None,
                        resolves from ``HEDERA_ANCHOR_TOPIC_ID`` env var, or
                        ``DEFAULT_ANCHOR_TOPIC_ID`` as a final fallback.
        """
        self._hcs_client = hcs_client
        self._anchor_topic_id = (
            anchor_topic_id
            or os.getenv("HEDERA_ANCHOR_TOPIC_ID")
            or DEFAULT_ANCHOR_TOPIC_ID
        )

    # ------------------------------------------------------------------
    # Internal: lazy client access
    # ------------------------------------------------------------------

    @property
    def hcs_client(self) -> Any:
        """Lazy-initialised HCS client."""
        if self._hcs_client is None:
            self._hcs_client = get_hedera_client()
        return self._hcs_client

    # ------------------------------------------------------------------
    # Internal: submit helper
    # ------------------------------------------------------------------

    async def _submit_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit *message* to the HCS topic and return the raw HCS response.

        Args:
            message: Dict that will be JSON-serialised before submission.

        Returns:
            Raw dict returned by the HCS client (contains ``sequence_number``).

        Raises:
            HCSAnchoringError: When the HCS client raises any exception.
        """
        try:
            return await self.hcs_client.submit_hcs_message(
                topic_id=self._anchor_topic_id,
                message=message,
            )
        except HCSAnchoringError:
            raise
        except Exception as exc:
            logger.error("HCS message submission failed: %s", exc)
            raise HCSAnchoringError(
                f"Failed to submit HCS message: {exc}", original=exc
            ) from exc

    # ------------------------------------------------------------------
    # Issue #200 — Memory Operations Anchor
    # ------------------------------------------------------------------

    async def anchor_memory(
        self,
        memory_id: str,
        content_hash: str,
        agent_id: str,
        namespace: str,
    ) -> Dict[str, Any]:
        """
        Submit a memory content hash to HCS.

        Constructs and submits an HCS message of type ``memory_anchor`` that
        permanently records the SHA-256 hash of the memory's content on the
        Hedera Consensus Service.

        Args:
            memory_id:    Unique memory identifier (e.g. ``mem_abc123``).
            content_hash: SHA-256 hex digest of the memory content.
            agent_id:     Agent that owns the memory.
            namespace:    Isolation namespace for multi-agent setups.

        Returns:
            Dict containing ``memory_id``, ``sequence_number``, ``timestamp``.

        Raises:
            HCSAnchoringError: When the HCS submission fails.
        """
        timestamp = _utc_now_iso()
        message: Dict[str, Any] = {
            "type": "memory_anchor",
            "memory_id": memory_id,
            "content_hash": content_hash,
            "agent_id": agent_id,
            "namespace": namespace,
            "timestamp": timestamp,
        }

        logger.info(
            "Anchoring memory %s for agent %s to HCS", memory_id, agent_id
        )

        hcs_response = await self._submit_message(message)
        sequence_number = hcs_response.get("sequence_number", 0)

        logger.info(
            "Memory %s anchored at HCS sequence %d", memory_id, sequence_number
        )

        return {
            "memory_id": memory_id,
            "sequence_number": sequence_number,
            "timestamp": timestamp,
        }

    async def get_anchor(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a memory anchor record from the HCS mirror node.

        Args:
            memory_id: Memory identifier to look up.

        Returns:
            Anchor record dict when found, or ``None`` if no anchor exists.
        """
        try:
            result = await self.hcs_client.get_hcs_message(memory_id)
            return result
        except Exception as exc:
            logger.warning("Failed to retrieve HCS anchor for %s: %s", memory_id, exc)
            return None

    # ------------------------------------------------------------------
    # Issue #201 — Compliance Events on HCS
    # ------------------------------------------------------------------

    async def anchor_compliance_event(
        self,
        event_id: str,
        event_type: str,
        classification: str,
        risk_score: float,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        Submit a compliance event hash to HCS.

        Constructs and submits an HCS message of type ``compliance_anchor``.
        A deterministic ``event_hash`` is computed from the event fields so
        the anchor is replayable / verifiable independently.

        Args:
            event_id:       Unique compliance event identifier.
            event_type:     Type of compliance check (KYC_CHECK, KYT_CHECK, …).
            classification: Outcome classification (PASS, FAIL, PENDING, …).
            risk_score:     Risk score in range [0.0, 1.0].
            agent_id:       Agent that produced the compliance event.

        Returns:
            Dict containing ``event_id``, ``sequence_number``, ``timestamp``.

        Raises:
            HCSAnchoringError: When the HCS submission fails.
        """
        timestamp = _utc_now_iso()
        event_hash = _build_compliance_event_hash(
            event_id=event_id,
            event_type=event_type,
            classification=classification,
            risk_score=risk_score,
            agent_id=agent_id,
        )

        message: Dict[str, Any] = {
            "type": "compliance_anchor",
            "event_id": event_id,
            "event_hash": event_hash,
            "event_type": event_type,
            "classification": classification,
            "risk_score": risk_score,
            "agent_id": agent_id,
            "timestamp": timestamp,
        }

        logger.info(
            "Anchoring compliance event %s (type=%s) for agent %s",
            event_id, event_type, agent_id,
        )

        hcs_response = await self._submit_message(message)
        sequence_number = hcs_response.get("sequence_number", 0)

        logger.info(
            "Compliance event %s anchored at HCS sequence %d",
            event_id, sequence_number,
        )

        return {
            "event_id": event_id,
            "sequence_number": sequence_number,
            "timestamp": timestamp,
        }

    # ------------------------------------------------------------------
    # Issue #202 — Memory Integrity Verification
    # ------------------------------------------------------------------

    async def verify_memory_integrity(
        self,
        memory_id: str,
        current_content: str,
    ) -> Dict[str, Any]:
        """
        Verify the integrity of a memory by comparing its current content hash
        against the hash stored on HCS at anchor time.

        Args:
            memory_id:       Memory identifier to verify.
            current_content: The current content of the memory.

        Returns:
            When anchor exists:
                ``{verified, match, anchor_hash, current_hash, anchor_timestamp}``
            When no anchor found:
                ``{verified: False, reason: "no_anchor_found"}``
        """
        anchor = await self.get_anchor(memory_id)

        if anchor is None:
            logger.warning(
                "No HCS anchor found for memory %s — integrity unverifiable",
                memory_id,
            )
            return {"verified": False, "reason": "no_anchor_found"}

        anchor_hash: str = anchor["content_hash"]
        current_hash: str = _sha256_hex(current_content)
        match: bool = anchor_hash == current_hash

        logger.info(
            "Integrity check for memory %s: match=%s", memory_id, match
        )

        return {
            "verified": match,
            "match": match,
            "anchor_hash": anchor_hash,
            "current_hash": current_hash,
            "anchor_timestamp": anchor.get("timestamp"),
        }

    # ------------------------------------------------------------------
    # Issue #203 — Consolidation Output Anchoring
    # ------------------------------------------------------------------

    async def anchor_consolidation(
        self,
        consolidation_id: str,
        synthesis_hash: str,
        source_memory_ids: List[str],
        model_used: str,
    ) -> Dict[str, Any]:
        """
        Anchor a NousCoder synthesis / consolidation output to HCS.

        Records the synthesis hash alongside the source memory IDs and the
        model that produced the output, enabling full provenance tracing.

        Args:
            consolidation_id:  Unique consolidation identifier.
            synthesis_hash:    SHA-256 hex digest of the synthesised output.
            source_memory_ids: List of source memory IDs used in synthesis.
            model_used:        Model name (e.g. ``nous-codestral-22b``).

        Returns:
            Dict containing ``consolidation_id``, ``sequence_number``, ``timestamp``.

        Raises:
            HCSAnchoringError: When the HCS submission fails.
        """
        timestamp = _utc_now_iso()
        message: Dict[str, Any] = {
            "type": "consolidation_anchor",
            "consolidation_id": consolidation_id,
            "synthesis_hash": synthesis_hash,
            "source_memory_ids": source_memory_ids,
            "model_used": model_used,
            "timestamp": timestamp,
        }

        logger.info(
            "Anchoring consolidation %s (model=%s, sources=%d) to HCS",
            consolidation_id, model_used, len(source_memory_ids),
        )

        hcs_response = await self._submit_message(message)
        sequence_number = hcs_response.get("sequence_number", 0)

        logger.info(
            "Consolidation %s anchored at HCS sequence %d",
            consolidation_id, sequence_number,
        )

        return {
            "consolidation_id": consolidation_id,
            "sequence_number": sequence_number,
            "timestamp": timestamp,
        }


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_hcs_anchoring_service: Optional[HCSAnchoringService] = None


def get_hcs_anchoring_service() -> HCSAnchoringService:
    """
    Return the shared HCSAnchoringService singleton.

    In tests, replace this function via ``unittest.mock.patch`` to inject
    a mock service instance.
    """
    global _hcs_anchoring_service
    if _hcs_anchoring_service is None:
        _hcs_anchoring_service = HCSAnchoringService()
    return _hcs_anchoring_service
