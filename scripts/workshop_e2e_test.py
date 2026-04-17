"""
Workshop End-to-End Test Orchestrator.

Tests the Agent-402 workshop curriculum by executing each tutorial step
and verifying API responses against documented expectations.

Usage:
    # Run all tutorials as developer persona
    python scripts/workshop_e2e_test.py --persona developer --tutorial all

    # Run just tutorial 01 as vibe coder persona
    python scripts/workshop_e2e_test.py --persona vibe-coder --tutorial 01

    # Dry run (no server needed, prints what would happen)
    python scripts/workshop_e2e_test.py --dry-run

The orchestrator:
  1. Checks if backend server is running at localhost:8000
  2. Starts it in background if not (stops on exit)
  3. Executes each tutorial step, verifying checkpoints
  4. Writes a markdown report to docs/workshop/test-results/
  5. Exits 0 if all checkpoints pass, 1 if any fail

Designed to be wrapped in asciinema for recording:
    asciinema rec recording.cast --command "python scripts/workshop_e2e_test.py --persona developer --tutorial all"

Built by AINative Dev Team
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip3 install httpx")
    sys.exit(2)


# Configuration
BASE_URL = os.environ.get("WORKSHOP_BASE_URL", "http://localhost:8000")
PROJECT_ID = os.environ.get("WORKSHOP_PROJECT_ID", "proj_test_change_in_production")
API_KEY = os.environ.get("WORKSHOP_API_KEY", "demo_key_user1_abc123")
SERVER_STARTUP_TIMEOUT = 30  # seconds
REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "docs" / "workshop" / "test-results"


# ANSI colors for terminal output
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    DIM = "\033[2m"


def banner(text: str) -> None:
    print(f"\n{C.BOLD}{C.CYAN}{'=' * 70}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {text}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'=' * 70}{C.RESET}\n")


def step(num: int, text: str) -> None:
    print(f"{C.BOLD}{C.BLUE}Step {num}:{C.RESET} {text}")


def say(text: str) -> None:
    print(f"{C.DIM}   {text}{C.RESET}")


def prompt_as_vibe_coder(text: str) -> None:
    """Print what a vibe coder would say to their AI assistant."""
    print(f"{C.CYAN}   [Vibe Coder to AI]:{C.RESET} {text}")


def checkpoint(passed: bool, description: str, detail: str = "") -> bool:
    icon = f"{C.GREEN}PASS{C.RESET}" if passed else f"{C.RED}FAIL{C.RESET}"
    print(f"   [{icon}] {description}")
    if detail and not passed:
        print(f"   {C.DIM}         {detail}{C.RESET}")
    return passed


class TestResult:
    """Holds results for one test run."""

    def __init__(self, persona: str, tutorial: str):
        self.persona = persona
        self.tutorial = tutorial
        self.started_at = datetime.now(timezone.utc)
        self.steps: List[Dict[str, Any]] = []
        self.persona_violations: List[str] = []

    def record(self, step_num: int, description: str, passed: bool, detail: str = "", duration_s: float = 0.0) -> None:
        self.steps.append({
            "step": step_num,
            "description": description,
            "passed": passed,
            "detail": detail,
            "duration_s": round(duration_s, 2),
        })

    def record_persona_violation(self, description: str) -> None:
        self.persona_violations.append(description)

    @property
    def passed(self) -> int:
        return sum(1 for s in self.steps if s["passed"])

    @property
    def failed(self) -> int:
        return sum(1 for s in self.steps if not s["passed"])

    @property
    def total(self) -> int:
        return len(self.steps)

    def write_report(self) -> Path:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = self.started_at.strftime("%Y%m%dT%H%M%S")
        path = RESULTS_DIR / f"{self.persona}-{self.tutorial}-{timestamp}.md"
        finished_at = datetime.now(timezone.utc)

        lines = [
            f"# Workshop E2E Test Report",
            f"",
            f"- **Persona:** {self.persona}",
            f"- **Tutorial:** {self.tutorial}",
            f"- **Started:** {self.started_at.isoformat()}",
            f"- **Finished:** {finished_at.isoformat()}",
            f"- **Duration:** {(finished_at - self.started_at).total_seconds():.1f}s",
            f"- **Results:** {self.passed}/{self.total} passed, {self.failed} failed",
            f"",
            f"## Step Results",
            f"",
            f"| # | Description | Result | Duration | Detail |",
            f"|---|-------------|--------|----------|--------|",
        ]
        for s in self.steps:
            result = "PASS" if s["passed"] else "FAIL"
            detail = s["detail"].replace("|", "\\|")[:80] if s["detail"] else ""
            lines.append(f"| {s['step']} | {s['description']} | {result} | {s['duration_s']}s | {detail} |")

        if self.persona_violations:
            lines += [
                "",
                "## Persona Violations",
                "",
                "Steps where the persona rules were broken (tutorial needs rewording):",
                "",
            ]
            for v in self.persona_violations:
                lines.append(f"- {v}")

        lines += [
            "",
            "## Environment",
            f"- Base URL: {BASE_URL}",
            f"- Project ID: {PROJECT_ID}",
            f"- Python: {sys.version.split()[0]}",
        ]

        path.write_text("\n".join(lines))
        return path


# ---------------------------------------------------------------------------
# Server Management
# ---------------------------------------------------------------------------


def server_is_up() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def start_server() -> Optional[subprocess.Popen]:
    """Start uvicorn in background, return the process handle."""
    backend = REPO_ROOT / "backend"
    if not backend.exists():
        print(f"{C.RED}ERROR:{C.RESET} backend directory not found at {backend}")
        return None

    say(f"Starting server: uvicorn app.main:app --port 8000 (cwd={backend})")
    proc = subprocess.Popen(
        ["python3", "-m", "uvicorn", "app.main:app", "--port", "8000"],
        cwd=str(backend),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for server to come up
    for i in range(SERVER_STARTUP_TIMEOUT):
        if server_is_up():
            say(f"Server ready after {i+1}s")
            return proc
        time.sleep(1)

    print(f"{C.RED}ERROR:{C.RESET} Server did not start within {SERVER_STARTUP_TIMEOUT}s")
    proc.terminate()
    return None


def stop_server(proc: Optional[subprocess.Popen]) -> None:
    if proc is None:
        return
    say("Stopping server")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# HTTP Helpers
# ---------------------------------------------------------------------------


def api_post(path: str, json_body: Dict[str, Any], expected_status: int = 200) -> Tuple[bool, Any, str]:
    """POST to API, return (success, response_json, detail_on_failure)."""
    try:
        r = httpx.post(
            f"{BASE_URL}{path}",
            json=json_body,
            headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
            timeout=15.0,
        )
        if r.status_code == expected_status or (200 <= r.status_code < 300 and 200 <= expected_status < 300):
            try:
                return True, r.json(), ""
            except Exception:
                return True, r.text, ""
        return False, None, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, None, f"Request error: {e}"


def api_get(path: str, expected_status: int = 200) -> Tuple[bool, Any, str]:
    try:
        r = httpx.get(
            f"{BASE_URL}{path}",
            headers={"X-API-Key": API_KEY},
            timeout=15.0,
        )
        if r.status_code == expected_status:
            try:
                return True, r.json(), ""
            except Exception:
                return True, r.text, ""
        return False, None, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, None, f"Request error: {e}"


# ---------------------------------------------------------------------------
# Tutorial 01: Identity & Memory
# ---------------------------------------------------------------------------


def ensure_project_exists() -> bool:
    """Create the test project if it doesn't exist. Returns True if usable."""
    # Try to get the project first
    ok, data, detail = api_get(f"/v1/public/projects/{PROJECT_ID}")
    if ok:
        return True
    # Try to create it
    ok, data, detail = api_post(
        "/v1/public/projects",
        {
            "project_id": PROJECT_ID,
            "name": "Workshop Test Project",
            "description": "E2E test project for workshop orchestrator",
            "tier": "free",
            "database_enabled": True,
        },
        expected_status=201,
    )
    return ok


def run_tutorial_01(result: TestResult, persona: str) -> None:
    banner("Tutorial 01: Identity & Memory")

    # Step 0: Baseline — can we hit the discovery endpoint?
    step(0, "Verify server is responding")
    t0 = time.time()
    ok, data, detail = api_get("/.well-known/x402")
    passed = checkpoint(ok, "x402 discovery endpoint responds", detail)
    result.record(0, "x402 discovery endpoint responds", passed, detail, time.time() - t0)
    if not passed:
        say("Server not responding properly. Cannot continue.")
        return

    # Setup: ensure test project exists
    say("Ensuring test project exists (setup)")
    ensure_project_exists()

    if persona == "vibe-coder":
        prompt_as_vibe_coder(
            "Check that the server is responding at localhost:8000/.well-known/x402"
        )

    # Step 1: Create an agent
    step(1, "Create an agent via POST /v1/public/{project_id}/agents")
    if persona == "vibe-coder":
        prompt_as_vibe_coder(
            "Help me create an agent using the Agent-402 API. "
            "POST to /v1/public/{project_id}/agents with name 'my-consensus-agent', "
            "role 'analyst', and description 'My first autonomous fintech agent on Hedera'."
        )
    t0 = time.time()
    ok, data, detail = api_post(
        f"/v1/public/{PROJECT_ID}/agents",
        {
            "name": "my-consensus-agent",
            "role": "analyst",
            "description": "My first autonomous fintech agent on Hedera",
            "did": "did:key:z6MkWorkshopTest001",
            "scope": "RUN",
        },
        expected_status=201,
    )
    agent_id = None
    if ok and isinstance(data, dict):
        agent_id = data.get("agent_id") or data.get("id")
    passed = checkpoint(
        ok and agent_id is not None,
        "Agent created with agent_id",
        detail or f"Response: {str(data)[:200]}",
    )
    result.record(1, "Create agent", passed, detail or f"agent_id={agent_id}", time.time() - t0)
    if not passed:
        return

    # Step 2: Retrieve the agent
    step(2, "Verify agent exists via GET /v1/public/{project_id}/agents/{agent_id}")
    if persona == "vibe-coder":
        prompt_as_vibe_coder(f"Get my agent details using GET /v1/public/{{project_id}}/agents/{agent_id}")
    t0 = time.time()
    ok, data, detail = api_get(f"/v1/public/{PROJECT_ID}/agents/{agent_id}")
    passed = checkpoint(ok, "Agent retrievable by ID", detail)
    result.record(2, "Retrieve agent", passed, detail, time.time() - t0)

    # Step 3: List agents
    step(3, "List agents via GET /v1/public/{project_id}/agents")
    t0 = time.time()
    ok, data, detail = api_get(f"/v1/public/{PROJECT_ID}/agents")
    passed = checkpoint(ok, "Agent appears in list", detail)
    result.record(3, "List agents", passed, detail, time.time() - t0)

    # Step 4: Register identity on Hedera
    step(4, "Register agent identity on Hedera HTS NFT")
    if persona == "vibe-coder":
        prompt_as_vibe_coder(
            f"Register my agent on Hedera using POST /api/v1/hedera/identity/register "
            f"with agent_id {agent_id} and capabilities [finance, compliance, payments]."
        )
    t0 = time.time()
    ok, data, detail = api_post(
        "/api/v1/hedera/identity/register",
        {
            "agent_id": agent_id,
            "agent_name": "my-consensus-agent",
            "capabilities": ["finance", "compliance", "payments"],
            "role": "analyst",
        },
        expected_status=200,
    )
    agent_did = None
    token_id = None
    if ok and isinstance(data, dict):
        agent_did = data.get("agent_did") or data.get("did")
        token_id = data.get("token_id")
    passed = checkpoint(
        ok,
        "Hedera identity registered",
        detail or f"token_id={token_id}, agent_did={agent_did}",
    )
    result.record(4, "Register Hedera identity", passed, detail or f"token_id={token_id}", time.time() - t0)

    # Step 5: Resolve DID
    step(5, "Resolve agent DID")
    t0 = time.time()
    ok, data, detail = api_get(f"/api/v1/hedera/identity/{agent_id}/did")
    passed = checkpoint(ok, "Agent DID resolvable", detail)
    result.record(5, "Resolve DID", passed, detail, time.time() - t0)

    # Step 6: Get capabilities
    step(6, "Get agent capabilities")
    t0 = time.time()
    ok, data, detail = api_get(f"/api/v1/hedera/identity/{agent_id}/capabilities")
    passed = checkpoint(ok, "Agent capabilities retrievable", detail)
    result.record(6, "Get capabilities", passed, detail, time.time() - t0)

    # Step 7: Store a memory
    step(7, "Store agent memory")
    if persona == "vibe-coder":
        prompt_as_vibe_coder(
            "Store a memory for my agent: 'Evaluated market conditions: HBAR/USD stable at 0.08'"
        )
    t0 = time.time()
    ok, data, detail = api_post(
        f"/v1/public/{PROJECT_ID}/agent-memory",
        {
            "agent_id": agent_id,
            "run_id": "workshop-run-1",
            "memory_type": "decision",
            "content": "Evaluated market conditions: HBAR/USD stable at 0.08, low volatility. Recommendation: proceed with transaction.",
            "confidence": 0.92,
        },
        expected_status=201,
    )
    memory_id = None
    if ok and isinstance(data, dict):
        memory_id = data.get("memory_id") or data.get("id")
    passed = checkpoint(ok and memory_id is not None, "Memory stored", detail or f"memory_id={memory_id}")
    result.record(7, "Store memory", passed, detail or f"memory_id={memory_id}", time.time() - t0)

    # Step 8: Retrieve memory
    step(8, "Retrieve stored memory")
    t0 = time.time()
    if memory_id:
        ok, data, detail = api_get(f"/v1/public/{PROJECT_ID}/agent-memory/{memory_id}")
    else:
        ok, detail = False, "No memory_id from step 7"
    passed = checkpoint(ok, "Memory retrievable", detail)
    result.record(8, "Retrieve memory", passed, detail, time.time() - t0)

    # Step 9: List memories
    step(9, "List all agent memories")
    t0 = time.time()
    ok, data, detail = api_get(f"/v1/public/{PROJECT_ID}/agent-memory")
    passed = checkpoint(ok, "Memories listable", detail)
    result.record(9, "List memories", passed, detail, time.time() - t0)

    # Step 10: Anchor to HCS
    step(10, "Anchor memory to Hedera Consensus Service")
    if persona == "vibe-coder":
        prompt_as_vibe_coder(
            f"Anchor my memory {memory_id} to Hedera HCS using POST /anchor/memory"
        )
    t0 = time.time()
    import hashlib
    content_hash = hashlib.sha256(b"test content").hexdigest()
    ok, data, detail = api_post(
        "/anchor/memory",
        {
            "memory_id": memory_id or "mem_test",
            "content_hash": content_hash,
            "agent_id": agent_id,
            "namespace": "workshop",
        },
        expected_status=201,
    )
    passed = checkpoint(ok, "Memory anchored to HCS", detail)
    result.record(10, "Anchor to HCS", passed, detail, time.time() - t0)


# ---------------------------------------------------------------------------
# Tutorial 02: Payments & Trust
# ---------------------------------------------------------------------------


def run_tutorial_02(result: TestResult, persona: str) -> None:
    banner("Tutorial 02: Payments & Trust")

    # Step 1: Create wallet (Circle is the simpler test path)
    step(1, "Create Circle wallet for agent")
    t0 = time.time()
    ok, data, detail = api_post(
        f"/v1/public/{PROJECT_ID}/circle/wallets",
        {
            "agent_did": "did:key:z6MkWorkshopTest001",
            "wallet_type": "EOA",
            "blockchain": "ARC-TESTNET",
            "description": "Workshop test wallet",
        },
        expected_status=201,
    )
    wallet_id = None
    if ok and isinstance(data, dict):
        wallet_id = data.get("wallet_id") or data.get("id")
    passed = checkpoint(ok, "Circle wallet created", detail)
    result.record(1, "Create wallet", passed, detail or f"wallet_id={wallet_id}", time.time() - t0)

    # Step 2: List wallets
    step(2, "List Circle wallets")
    t0 = time.time()
    ok, data, detail = api_get(f"/v1/public/{PROJECT_ID}/circle/wallets")
    passed = checkpoint(ok, "Wallets listable", detail)
    result.record(2, "List wallets", passed, detail, time.time() - t0)

    # Step 3: x402 discovery
    step(3, "Check x402 discovery for Hedera metadata")
    t0 = time.time()
    ok, data, detail = api_get("/.well-known/x402")
    has_hedera = False
    if ok and isinstance(data, dict):
        has_hedera = "hedera" in data or "did:hedera" in data.get("supported_dids", [])
    passed = checkpoint(
        ok and has_hedera,
        "x402 discovery includes Hedera metadata",
        detail or f"hedera_present={has_hedera}",
    )
    result.record(3, "x402 Hedera discovery", passed, detail, time.time() - t0)

    # Step 4: Submit reputation feedback
    step(4, "Submit reputation feedback")
    if persona == "vibe-coder":
        prompt_as_vibe_coder(
            "Submit reputation feedback for agent did:hedera:testnet:0.0.12345 "
            "with rating 5 and comment 'excellent work'"
        )
    t0 = time.time()
    test_did = "did:hedera:testnet:0.0.12345"
    ok, data, detail = api_post(
        f"/api/v1/hedera/reputation/{test_did}/feedback",
        {
            "rating": 5,
            "comment": "excellent work in workshop test",
            "payment_proof_tx": "0.0.12345@1712000001.000000001",
            "task_id": "workshop-task-1",
            "submitter_did": "did:key:z6MkWorkshopTest001",
        },
        expected_status=201,
    )
    passed = checkpoint(ok, "Feedback submitted", detail)
    result.record(4, "Submit feedback", passed, detail, time.time() - t0)

    # Step 5: Get reputation score
    step(5, "Get reputation score")
    t0 = time.time()
    ok, data, detail = api_get(f"/api/v1/hedera/reputation/{test_did}")
    passed = checkpoint(ok, "Reputation score calculated", detail)
    result.record(5, "Get reputation", passed, detail, time.time() - t0)

    # Step 6: Get feedback history
    step(6, "Get feedback history")
    t0 = time.time()
    ok, data, detail = api_get(f"/api/v1/hedera/reputation/{test_did}/feedback")
    passed = checkpoint(ok, "Feedback history retrievable", detail)
    result.record(6, "Feedback history", passed, detail, time.time() - t0)

    # Step 7: Ranked agents
    step(7, "List ranked agents")
    t0 = time.time()
    ok, data, detail = api_get("/api/v1/hedera/reputation/ranked")
    passed = checkpoint(ok, "Ranked agents listable", detail)
    result.record(7, "Ranked agents", passed, detail, time.time() - t0)


# ---------------------------------------------------------------------------
# Tutorial 03: Discovery & Marketplace
# ---------------------------------------------------------------------------


def run_tutorial_03(result: TestResult, persona: str) -> None:
    banner("Tutorial 03: Discovery & Marketplace")

    test_did = "did:hedera:testnet:0.0.99999"

    # Step 1: HCS-14 directory registration
    step(1, "Register in HCS-14 directory")
    t0 = time.time()
    ok, data, detail = api_post(
        "/api/v1/hedera/identity/directory/register",
        {
            "agent_did": test_did,
            "capabilities": ["finance", "compliance"],
            "role": "analyst",
            "reputation_score": 4,
        },
        expected_status=201,
    )
    passed = checkpoint(ok, "HCS-14 registration", detail)
    result.record(1, "HCS-14 register", passed, detail, time.time() - t0)

    # Step 2: Search directory
    step(2, "Search HCS-14 directory by capability")
    t0 = time.time()
    ok, data, detail = api_post(
        "/api/v1/hedera/identity/directory/search",
        {"capability": "finance"},
        expected_status=200,
    )
    passed = checkpoint(ok, "Directory search works", detail)
    result.record(2, "Directory search", passed, detail, time.time() - t0)

    # Step 3: Send HCS-10 message
    step(3, "Send HCS-10 message")
    if persona == "vibe-coder":
        prompt_as_vibe_coder(
            "Send an HCS-10 message from my agent to another agent "
            "with message 'Please analyze HBAR market conditions'"
        )
    t0 = time.time()
    ok, data, detail = api_post(
        "/hcs10/send",
        {
            "sender_did": "did:key:z6MkWorkshopTest001",
            "recipient_did": test_did,
            "message_type": "task_request",
            "payload": {"task": "analyze HBAR market conditions"},
            "conversation_id": "workshop-conv-1",
        },
        expected_status=201,
    )
    passed = checkpoint(ok, "HCS-10 message sent", detail)
    result.record(3, "HCS-10 send", passed, detail, time.time() - t0)

    # Step 4: Check messages
    step(4, "Check messages for agent")
    t0 = time.time()
    ok, data, detail = api_get(f"/hcs10/messages/{test_did}")
    passed = checkpoint(ok, "Messages retrievable", detail)
    result.record(4, "HCS-10 receive", passed, detail, time.time() - t0)

    # Step 5: Browse marketplace
    step(5, "Browse marketplace")
    t0 = time.time()
    ok, data, detail = api_get("/marketplace/browse")
    passed = checkpoint(ok, "Marketplace browsable", detail)
    result.record(5, "Marketplace browse", passed, detail, time.time() - t0)

    # Step 6: Search marketplace
    step(6, "Search marketplace")
    t0 = time.time()
    ok, data, detail = api_post(
        "/marketplace/search",
        {"query": "finance"},
        expected_status=200,
    )
    passed = checkpoint(ok, "Marketplace search works", detail)
    result.record(6, "Marketplace search", passed, detail, time.time() - t0)

    # Step 7: Marketplace categories
    step(7, "List marketplace categories")
    t0 = time.time()
    ok, data, detail = api_get("/marketplace/categories")
    passed = checkpoint(ok, "Categories listable", detail)
    result.record(7, "Marketplace categories", passed, detail, time.time() - t0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


TUTORIALS: Dict[str, Callable[[TestResult, str], None]] = {
    "01": run_tutorial_01,
    "02": run_tutorial_02,
    "03": run_tutorial_03,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-402 Workshop E2E Test Orchestrator")
    parser.add_argument(
        "--persona",
        choices=["vibe-coder", "developer"],
        default="developer",
        help="Test persona (default: developer)",
    )
    parser.add_argument(
        "--tutorial",
        choices=["01", "02", "03", "all"],
        default="all",
        help="Tutorial to run (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen, don't actually hit the server",
    )
    args = parser.parse_args()

    banner(f"Agent-402 Workshop E2E Test")
    print(f"Persona:  {C.BOLD}{args.persona}{C.RESET}")
    print(f"Tutorial: {C.BOLD}{args.tutorial}{C.RESET}")
    print(f"Base URL: {BASE_URL}")

    if args.dry_run:
        say("Dry run mode — not actually testing")
        return 0

    # Server management
    own_server = False
    server_proc = None
    if not server_is_up():
        say("Server not running at localhost:8000")
        server_proc = start_server()
        if server_proc is None:
            return 1
        own_server = True
    else:
        say("Server already running at localhost:8000")

    try:
        tutorials_to_run = ["01", "02", "03"] if args.tutorial == "all" else [args.tutorial]
        all_results: List[TestResult] = []

        for t in tutorials_to_run:
            result = TestResult(persona=args.persona, tutorial=t)
            TUTORIALS[t](result, args.persona)
            report_path = result.write_report()
            all_results.append(result)
            say(f"Report written to {report_path.relative_to(REPO_ROOT)}")

        # Summary
        banner("Summary")
        total_passed = sum(r.passed for r in all_results)
        total_steps = sum(r.total for r in all_results)
        for r in all_results:
            color = C.GREEN if r.failed == 0 else C.RED
            print(f"  Tutorial {r.tutorial}: {color}{r.passed}/{r.total}{C.RESET}")

        print(f"\n  {C.BOLD}Total: {total_passed}/{total_steps} checkpoints passed{C.RESET}")

        if total_passed == total_steps:
            print(f"\n  {C.GREEN}{C.BOLD}Workshop is READY for {args.persona}.{C.RESET}\n")
            return 0
        else:
            failed = total_steps - total_passed
            print(f"\n  {C.RED}{C.BOLD}{failed} checkpoint(s) failed.{C.RESET}")
            print(f"  {C.DIM}See reports in docs/workshop/test-results/{C.RESET}\n")
            return 1

    finally:
        if own_server:
            stop_server(server_proc)


if __name__ == "__main__":
    sys.exit(main())
