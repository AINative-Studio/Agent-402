"""
Agent-402 Polished Demo — Consensus 2026
Issue #249: Polished 5-Minute Demo

Orchestrates the full Agent-402 agent workflow:
  1. Create agent profile
  2. Register identity on Hedera (HTS NFT)
  3. Execute X402 payment via Hedera USDC
  4. Store memory in ZeroDB and anchor to HCS
  5. Submit reputation feedback to HCS topic
  6. Search agent marketplace (HCS-14 directory)

Works against Hedera testnet (configurable via env vars).
Graceful error handling with clear messages at every step.

Usage:
    python scripts/demo_consensus_2026.py

Environment variables:
    HEDERA_NETWORK          testnet (default) or mainnet
    HEDERA_OPERATOR_ID      Hedera account ID (e.g. 0.0.12345)
    HEDERA_OPERATOR_KEY     ED25519 private key (DER hex)
    ZERODB_API_KEY          ZeroDB API key
    ZERODB_PROJECT_ID       ZeroDB project ID
    DEMO_DRY_RUN            Set to "1" to skip real network calls

Built by AINative Dev Team
Refs #249
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# ---------------------------------------------------------------------------
# Console colour helpers — no third-party deps required
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"

_CYAN = "\033[96m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_MAGENTA = "\033[95m"
_BLUE = "\033[94m"
_WHITE = "\033[97m"


def _c(text: str, colour: str, bold: bool = False) -> str:
    prefix = _BOLD if bold else ""
    return f"{prefix}{colour}{text}{_RESET}"


def _header(title: str) -> None:
    width = 60
    print()
    print(_c("=" * width, _CYAN, bold=True))
    print(_c(f"  {title}", _WHITE, bold=True))
    print(_c("=" * width, _CYAN, bold=True))


def _step(number: int, description: str) -> None:
    print()
    print(_c(f"  Step {number}/6 — {description}", _YELLOW, bold=True))
    print(_c("  " + "-" * 50, _YELLOW))


def _ok(message: str) -> None:
    print(_c(f"    [OK] {message}", _GREEN))


def _info(message: str) -> None:
    print(_c(f"    ... {message}", _BLUE))


def _warn(message: str) -> None:
    print(_c(f"    [!] {message}", _MAGENTA))


def _fail(message: str) -> None:
    print(_c(f"    [ERROR] {message}", _RED, bold=True))


def _result(key: str, value: str) -> None:
    print(_c(f"        {key:<25} {value}", _WHITE))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEMO_DRY_RUN: bool = os.environ.get("DEMO_DRY_RUN", "0") == "1"
HEDERA_NETWORK: str = os.environ.get("HEDERA_NETWORK", "testnet")
HEDERA_OPERATOR_ID: str = os.environ.get("HEDERA_OPERATOR_ID", "")
HEDERA_OPERATOR_KEY: str = os.environ.get("HEDERA_OPERATOR_KEY", "")
ZERODB_API_KEY: str = os.environ.get("ZERODB_API_KEY", "")
ZERODB_PROJECT_ID: str = os.environ.get("ZERODB_PROJECT_ID", "")

# Demo identity constants
DEMO_AGENT_ID: str = "demo-agent-consensus-2026"
DEMO_AGENT_DID: str = "did:hedera:testnet:0.0.demo"
DEMO_RECIPIENT_ACCOUNT: str = "0.0.456789"
DEMO_DIRECTORY_TOPIC: str = "0.0.99001"


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------

async def _step1_create_agent(context: Dict[str, Any]) -> None:
    """
    Step 1: Create agent profile via the Agent-402 backend.

    In a live run this calls POST /v1/public/{project}/agents.
    In dry-run mode the call is simulated with a stub response.
    """
    _step(1, "Create Agent Profile")
    _info("Registering agent in ZeroDB agent table ...")

    if DEMO_DRY_RUN:
        _warn("DRY RUN — skipping real API call")
        context["agent_id"] = DEMO_AGENT_ID
        context["agent_did"] = DEMO_AGENT_DID
        _ok("Agent created (simulated)")
        _result("agent_id", DEMO_AGENT_ID)
        return

    try:
        import httpx

        api_base = os.environ.get("AGENT402_API_URL", "http://localhost:8000")
        payload = {
            "agent_id": DEMO_AGENT_ID,
            "name": "Consensus 2026 Demo Agent",
            "description": "Live Hedera finance agent demo — AINative Studio",
            "capabilities": ["finance", "compliance", "memory"],
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{api_base}/v1/public/{ZERODB_PROJECT_ID}/agents",
                json=payload,
                headers={"X-API-Key": ZERODB_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()

        context["agent_id"] = data.get("agent_id", DEMO_AGENT_ID)
        context["agent_did"] = data.get("did", DEMO_AGENT_DID)
        _ok("Agent profile created")
        _result("agent_id", context["agent_id"])
        _result("did", context["agent_did"])

    except Exception as exc:
        _fail(f"Agent creation failed: {exc}")
        _info("Continuing with fallback identity ...")
        context["agent_id"] = DEMO_AGENT_ID
        context["agent_did"] = DEMO_AGENT_DID


async def _step2_register_identity(context: Dict[str, Any]) -> None:
    """
    Step 2: Register agent identity on Hedera HTS (NFT token class).

    Calls HederaIdentityService.create_agent_token_class to mint an NFT
    representing the agent's on-chain identity.
    """
    _step(2, "Register Identity on Hedera (HTS NFT)")
    _info("Minting agent identity NFT on Hedera Token Service ...")

    if DEMO_DRY_RUN:
        _warn("DRY RUN — skipping Hedera call")
        context["identity_token_id"] = "0.0.55001"
        _ok("Identity token minted (simulated)")
        _result("token_id", "0.0.55001")
        return

    try:
        from app.services.hedera_identity_service import HederaIdentityService

        service = HederaIdentityService()
        result = await service.create_agent_token_class(
            agent_id=context["agent_id"],
            agent_name="Consensus 2026 Demo Agent",
            capabilities=["finance", "compliance", "memory"],
            memo="Agent-402 demo — AINative Studio",
        )

        context["identity_token_id"] = result.get("token_id", "")
        _ok("Identity NFT token class created on Hedera")
        _result("token_id", context["identity_token_id"])
        _result("transaction_id", result.get("transaction_id", ""))

    except Exception as exc:
        _fail(f"Identity registration failed: {exc}")
        _info("Continuing demo without on-chain identity ...")
        context["identity_token_id"] = ""


async def _step3_x402_payment(context: Dict[str, Any]) -> None:
    """
    Step 3: Execute X402 payment via Hedera USDC (HTS transfer).

    Demonstrates sub-3-second USDC settlement on Hedera testnet.
    """
    _step(3, "Execute X402 USDC Payment via Hedera HTS")
    _info("Initiating 1.00 USDC transfer on Hedera testnet ...")

    if DEMO_DRY_RUN:
        _warn("DRY RUN — skipping Hedera transfer")
        context["payment_tx_id"] = "0.0.77001@1712000001.000000002"
        _ok("USDC transfer executed (simulated)")
        _result("transaction_id", context["payment_tx_id"])
        _result("amount", "1.000000 USDC")
        _result("settlement", "< 3 seconds")
        return

    try:
        from app.services.hedera_payment_service import HederaPaymentService

        service = HederaPaymentService()
        result = await service.create_x402_payment(
            agent_id=context["agent_id"],
            amount=1_000_000,  # 1.00 USDC
            recipient=DEMO_RECIPIENT_ACCOUNT,
            task_id="demo-task-consensus-2026",
            memo="Agent-402 Consensus 2026 demo",
        )

        context["payment_tx_id"] = result.get("transaction_id", "")
        _ok("USDC payment executed on Hedera")
        _result("transaction_id", context["payment_tx_id"])
        _result("amount", f"{result.get('amount', 0) / 1_000_000:.6f} USDC")
        _result("status", result.get("status", "UNKNOWN"))

        # Verify receipt
        _info("Verifying settlement on mirror node ...")
        receipt = await service.verify_receipt_on_mirror_node(
            transaction_id=context["payment_tx_id"]
        )
        verified = receipt.get("verified", False)
        if verified:
            _ok("Payment verified on Hedera mirror node")
        else:
            _warn("Payment not yet confirmed — mirror node may be syncing")

    except Exception as exc:
        _fail(f"Payment failed: {exc}")
        _info("Continuing demo without live payment ...")
        context["payment_tx_id"] = ""


async def _step4_store_memory(context: Dict[str, Any]) -> None:
    """
    Step 4: Store agent decision memory in ZeroDB and anchor to Hedera HCS.

    Demonstrates tamper-proof memory via SHA-256 hash anchoring.
    """
    _step(4, "Store Memory in ZeroDB + Anchor to Hedera HCS")
    _info("Writing agent decision to ZeroDB ...")
    _info("Anchoring SHA-256 content hash to Hedera HCS ...")

    if DEMO_DRY_RUN:
        _warn("DRY RUN — skipping real memory write and HCS anchor")
        context["memory_sequence"] = 42
        _ok("Memory stored (simulated)")
        _ok("HCS anchor submitted (simulated)")
        _result("hcs_sequence", "42")
        _result("hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        return

    try:
        import hashlib
        from app.services.hcs_anchoring_service import HCSAnchoringService

        memory_content = (
            f"Agent {context['agent_id']} approved 1 USDC transfer to "
            f"{DEMO_RECIPIENT_ACCOUNT} at {datetime.now(timezone.utc).isoformat()}. "
            f"Payment tx: {context.get('payment_tx_id', 'N/A')}."
        )
        content_hash = hashlib.sha256(memory_content.encode()).hexdigest()

        anchor_service = HCSAnchoringService()
        anchor = await anchor_service.anchor_memory(
            memory_id=f"demo-mem-{int(datetime.now(timezone.utc).timestamp())}",
            content_hash=content_hash,
            agent_id=context["agent_id"],
            namespace="consensus-2026-demo",
        )

        context["memory_sequence"] = anchor.get("sequence_number", 0)
        _ok("Agent memory anchored to Hedera HCS")
        _result("hcs_sequence", str(context["memory_sequence"]))
        _result("hash (sha256)", content_hash[:32] + "...")

    except Exception as exc:
        _fail(f"Memory anchoring failed: {exc}")
        _info("Continuing demo without HCS anchor ...")
        context["memory_sequence"] = 0


async def _step5_reputation_feedback(context: Dict[str, Any]) -> None:
    """
    Step 5: Submit reputation feedback to HCS topic and calculate score.

    Demonstrates on-chain reputation with exponential recency decay.
    """
    _step(5, "Submit Reputation Feedback + Calculate Score")
    _info("Submitting feedback to Hedera HCS reputation topic ...")

    if DEMO_DRY_RUN:
        _warn("DRY RUN — skipping HCS feedback submission")
        context["reputation_score"] = 4.5
        context["trust_tier"] = 2
        _ok("Feedback submitted (simulated)")
        _ok("Reputation score calculated (simulated)")
        _result("score", "4.50")
        _result("trust_tier", "2 (TRUSTED)")
        return

    try:
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()

        feedback = await service.submit_feedback(
            agent_did=context.get("agent_did", DEMO_AGENT_DID),
            rating=5,
            comment="Demo: excellent task completion at Consensus 2026",
            payment_proof_tx=context.get("payment_tx_id", "demo-tx"),
            task_id="demo-task-consensus-2026",
            submitter_did="did:hedera:testnet:0.0.demo-auditor",
        )
        _ok("Feedback submitted to HCS reputation topic")
        _result("sequence_number", str(feedback.get("sequence_number", 0)))

        reputation = await service.calculate_reputation_score(
            agent_did=context.get("agent_did", DEMO_AGENT_DID)
        )
        context["reputation_score"] = reputation.get("score", 0.0)
        context["trust_tier"] = reputation.get("trust_tier", 0)

        tier_labels = {0: "NEW", 1: "BASIC", 2: "TRUSTED", 3: "VERIFIED", 4: "ESTABLISHED"}
        tier_label = tier_labels.get(context["trust_tier"], "UNKNOWN")
        _ok("Reputation score calculated")
        _result("score", f"{context['reputation_score']:.2f}")
        _result("trust_tier", f"{context['trust_tier']} ({tier_label})")
        _result("total_reviews", str(reputation.get("total_reviews", 0)))

    except Exception as exc:
        _fail(f"Reputation feedback failed: {exc}")
        _info("Continuing demo without live reputation data ...")
        context["reputation_score"] = 0.0
        context["trust_tier"] = 0


async def _step6_marketplace_search(context: Dict[str, Any]) -> None:
    """
    Step 6: Search agent marketplace via HCS-14 directory.

    Demonstrates agent discovery with capability and reputation filtering.
    """
    _step(6, "Search Agent Marketplace (HCS-14 Directory)")
    _info(f"Querying HCS-14 directory topic {DEMO_DIRECTORY_TOPIC} ...")
    _info("Filtering agents with capability='finance' ...")

    if DEMO_DRY_RUN:
        _warn("DRY RUN — skipping HCS-14 query")
        _ok("Marketplace search complete (simulated)")
        _result("agents found", "1")
        _result("top agent", "did:hedera:testnet:0.0.77001")
        _result("capability", "finance, compliance")
        return

    try:
        from app.services.hcs14_directory_service import HCS14DirectoryService

        service = HCS14DirectoryService(directory_topic_id=DEMO_DIRECTORY_TOPIC)
        result = await service.query_directory(capability="finance")
        agents = result.get("agents", [])

        _ok(f"Marketplace search returned {len(agents)} agent(s)")
        for idx, agent in enumerate(agents[:3], start=1):
            _result(f"agent #{idx} did", agent.get("did", "unknown"))
            _result(f"agent #{idx} capabilities", ", ".join(agent.get("capabilities", [])))
            _result(f"agent #{idx} reputation", str(agent.get("reputation", 0)))

        if not agents:
            _info("No agents registered yet — register first via /v1/agents/register")

    except Exception as exc:
        _fail(f"Marketplace search failed: {exc}")
        _info("HCS-14 directory may be empty or unreachable in this environment.")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _print_summary(context: Dict[str, Any], elapsed: float) -> None:
    _header("Demo Complete — Agent-402 Summary")
    print()
    print(_c("  Full Hedera Agent Workflow:", _WHITE, bold=True))
    print()
    _result("Agent ID", context.get("agent_id", "N/A"))
    _result("DID", context.get("agent_did", "N/A"))
    _result("Identity Token", context.get("identity_token_id", "N/A") or "not minted")
    _result("Payment TX", context.get("payment_tx_id", "N/A") or "not executed")
    _result("HCS Memory Sequence", str(context.get("memory_sequence", 0)))
    _result("Reputation Score", f"{context.get('reputation_score', 0.0):.2f}")
    _result("Trust Tier", str(context.get("trust_tier", 0)))
    print()
    print(_c(f"  Total elapsed: {elapsed:.1f}s", _CYAN))
    print()
    print(_c("  Powered by:", _WHITE, bold=True))
    print(_c("    CrewAI + X402 + ZeroDB + Hedera (HCS, HTS, DID)", _BLUE))
    print(_c("    Built by AINative Dev Team", _BLUE))
    print()
    if DEMO_DRY_RUN:
        print(_c("  NOTE: Demo ran in DRY RUN mode (DEMO_DRY_RUN=1).", _YELLOW))
        print(_c("        Set HEDERA_OPERATOR_ID, HEDERA_OPERATOR_KEY, and", _YELLOW))
        print(_c("        ZERODB_API_KEY env vars for live testnet execution.", _YELLOW))
        print()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_demo() -> None:
    """
    Orchestrate the full Agent-402 Consensus 2026 demo workflow.

    Runs all six steps against Hedera testnet (or in DRY RUN mode),
    with colourful step-by-step output and graceful error handling.
    """
    import time

    _header("Agent-402 — Consensus 2026 Live Demo")
    print()
    print(_c("  Autonomous Finance Agents on Hedera Hashgraph", _WHITE, bold=True))
    print(_c("  Auditable · Replayable · Agent-Native", _CYAN))
    print()

    if DEMO_DRY_RUN:
        print(_c("  Mode: DRY RUN (no real testnet calls)", _YELLOW, bold=True))
    else:
        print(_c(f"  Mode: LIVE ({HEDERA_NETWORK.upper()})", _GREEN, bold=True))
        if not HEDERA_OPERATOR_ID:
            print(_c("  WARNING: HEDERA_OPERATOR_ID not set — some steps may fail", _MAGENTA))
        if not ZERODB_API_KEY:
            print(_c("  WARNING: ZERODB_API_KEY not set — some steps may fail", _MAGENTA))

    context: Dict[str, Any] = {}
    start = time.monotonic()

    steps = [
        _step1_create_agent,
        _step2_register_identity,
        _step3_x402_payment,
        _step4_store_memory,
        _step5_reputation_feedback,
        _step6_marketplace_search,
    ]

    for step_fn in steps:
        try:
            await step_fn(context)
        except KeyboardInterrupt:
            print()
            print(_c("  Demo interrupted by user.", _RED, bold=True))
            sys.exit(0)
        except Exception as exc:
            _fail(f"Unexpected error in {step_fn.__name__}: {exc}")
            _info("Traceback:")
            traceback.print_exc()
            _info("Continuing to next step ...")

    elapsed = time.monotonic() - start
    _print_summary(context, elapsed)


if __name__ == "__main__":
    asyncio.run(run_demo())
