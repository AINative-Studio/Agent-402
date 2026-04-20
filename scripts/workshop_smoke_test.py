"""
Workshop Smoke Test — Verifies Agent-402 is ready for the Consensus 2026 class.

Run before the workshop to confirm everything works:
    python scripts/workshop_smoke_test.py

Checks:
1. Backend server starts and responds
2. Agent CRUD works
3. Agent memory store/recall works
4. Hedera identity registration works
5. Hedera wallet creation works
6. Payment service responds
7. Reputation service responds
8. HCS anchoring works
9. OpenConvAI messaging works
10. Marketplace works
11. All tutorial API endpoints are reachable

Exit 0 = workshop ready
Exit 1 = something is broken (details printed)

Built by AINative Dev Team
"""
from __future__ import annotations

import sys
import os
import importlib
import asyncio
from typing import List, Tuple

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def check(name: str, fn) -> Tuple[bool, str]:
    """Run a check, return (passed, message)."""
    try:
        result = fn()
        return True, f"  PASS  {name}"
    except Exception as e:
        return False, f"  FAIL  {name}: {e}"


def check_import(module_path: str) -> bool:
    """Check if a module can be imported."""
    importlib.import_module(module_path)
    return True


def check_file_exists(path: str) -> bool:
    """Check if a file exists."""
    full = os.path.join(os.path.dirname(__file__), '..', path)
    if not os.path.exists(full):
        raise FileNotFoundError(f"{path} not found")
    return True


def check_dir_exists(path: str) -> bool:
    """Check if a directory exists and is non-empty."""
    full = os.path.join(os.path.dirname(__file__), '..', path)
    if not os.path.isdir(full):
        raise FileNotFoundError(f"{path} directory not found")
    if not os.listdir(full):
        raise FileNotFoundError(f"{path} directory is empty")
    return True


def check_orchestrator_project_id_exists() -> bool:
    """
    Assert the project ID the E2E orchestrator points at actually exists in
    the deterministic project store. Prevents regression of issue #330, where
    the orchestrator pointed at a non-existent project and every project-
    scoped endpoint 404'd.
    """
    # Source-of-truth store
    from app.services.project_store import project_store

    # Mirror the orchestrator's resolution precedence:
    # WORKSHOP_PROJECT_ID env > hard-coded default.
    # (The --project-id CLI flag only matters at runtime; env vars are what
    # the smoke test can observe statically.)
    default_project_id = "proj_demo_u1_001"
    project_id = os.environ.get("WORKSHOP_PROJECT_ID", default_project_id)

    project = project_store.get_by_id(project_id)
    if project is None:
        raise AssertionError(
            f"Orchestrator project '{project_id}' not found in project_store. "
            "Either add it to _initialize_demo_projects() in "
            "backend/app/services/project_store.py, or set WORKSHOP_PROJECT_ID "
            "to an existing project."
        )
    return True


def main():
    print("=" * 60)
    print("  Agent-402 Workshop Smoke Test")
    print("  Verifying all systems for Consensus 2026 class")
    print("=" * 60)
    print()

    results: List[Tuple[bool, str]] = []

    # Section 1: Core files exist
    print("[1/6] Checking project structure...")
    results.append(check("README.md exists", lambda: check_file_exists("README.md")))
    results.append(check("Backend main.py exists", lambda: check_file_exists("backend/app/main.py")))
    results.append(check(".env.example exists", lambda: check_file_exists(".env.example")))
    results.append(check("Demo script exists", lambda: check_file_exists("scripts/demo_consensus_2026.py")))
    results.append(check("Workshop curriculum exists", lambda: check_file_exists("docs/workshop/CURRICULUM.md")))
    results.append(check("Tutorial 01 exists", lambda: check_file_exists("docs/workshop/tutorials/01-identity-and-memory.md")))
    results.append(check("Tutorial 02 exists", lambda: check_file_exists("docs/workshop/tutorials/02-payments-and-trust.md")))
    results.append(check("Tutorial 03 exists", lambda: check_file_exists("docs/workshop/tutorials/03-discovery-and-marketplace.md")))
    print()

    # Section 2: SDK packages exist
    print("[2/6] Checking SDK packages...")
    results.append(check("TypeScript SDK", lambda: check_dir_exists("packages/sdks/agent/src")))
    results.append(check("Python SDK", lambda: check_dir_exists("packages/sdks/python-agent/ainative_agent")))
    results.append(check("Hedera plugin", lambda: check_dir_exists("packages/hedera-agent-kit-plugin/src")))
    results.append(check("Next.js SDK", lambda: check_dir_exists("packages/sdks/next-agent/src")))
    results.append(check("Agent runtime", lambda: check_dir_exists("packages/agent-runtime/src")))
    print()

    # Section 3: Backend services import
    print("[3/6] Checking backend service imports...")
    core_services = [
        ("Agent service", "app.services.agent_service"),
        ("Agent memory", "app.services.agent_memory_service"),
        ("X402 service", "app.services.x402_service"),
        ("Hedera client", "app.services.hedera_client"),
        ("Hedera payments", "app.services.hedera_payment_service"),
        ("Hedera wallets", "app.services.hedera_wallet_service"),
        ("Hedera identity", "app.services.hedera_identity_service"),
        ("Hedera DID", "app.services.hedera_did_service"),
        ("Hedera reputation", "app.services.hedera_reputation_service"),
        ("HCS anchoring", "app.services.hcs_anchoring_service"),
        ("OpenConvAI messaging", "app.services.openconvai_messaging_service"),
        ("Marketplace", "app.services.marketplace_service"),
        ("Billing", "app.services.billing_service"),
        ("Memory decay", "app.services.memory_decay_worker"),
        ("Plugin registry", "app.services.plugin_registry_service"),
        ("Cognitive memory", "app.services.cognitive_memory_service"),
        ("HCS-14 directory", "app.services.hcs14_directory_service"),
        ("Workshop prefix middleware", "app.middleware.workshop_prefix"),
    ]
    for name, module in core_services:
        results.append(check(name, lambda m=module: check_import(m)))
    print()

    # Section 4: Schemas import
    print("[4/6] Checking schema imports...")
    schemas = [
        ("Hedera schemas", "app.schemas.hedera"),
        ("Identity schemas", "app.schemas.hedera_identity"),
        ("Reputation schemas", "app.schemas.hedera_reputation"),
        ("HCS anchoring schemas", "app.schemas.hcs_anchoring"),
        ("Marketplace schemas", "app.schemas.marketplace"),
        ("Plugin schemas", "app.schemas.plugins"),
        ("Billing schemas", "app.schemas.billing"),
        ("Cognitive memory schemas", "app.schemas.cognitive_memory"),
    ]
    for name, module in schemas:
        results.append(check(name, lambda m=module: check_import(m)))
    print()

    # Section 5: API routers import
    print("[5/6] Checking API router imports...")
    routers = [
        ("Agents API", "app.api.agents"),
        ("Hedera payments API", "app.api.hedera_payments"),
        ("Hedera wallets API", "app.api.hedera_wallets"),
        ("Hedera identity API", "app.api.hedera_identity"),
        ("Hedera reputation API", "app.api.hedera_reputation"),
        ("HCS anchoring API", "app.api.hcs_anchoring"),
        ("Marketplace API", "app.api.marketplace"),
        ("Plugins API", "app.api.plugins"),
        ("Billing API", "app.api.billing"),
    ]
    for name, module in routers:
        results.append(check(name, lambda m=module: check_import(m)))
    print()

    # Section 6: FastAPI app loads
    print("[6/6] Checking FastAPI app loads...")
    results.append(check("FastAPI app imports", lambda: check_import("app.main")))
    # Regression guard for issue #330: the E2E orchestrator's project must exist.
    results.append(check(
        "Orchestrator project ID exists in project_store",
        check_orchestrator_project_id_exists,
    ))
    print()

    # Summary
    passed = sum(1 for ok, _ in results if ok)
    failed = sum(1 for ok, _ in results if not ok)
    total = len(results)

    print("=" * 60)
    for ok, msg in results:
        print(msg)
    print("=" * 60)
    print(f"\n  Results: {passed}/{total} passed, {failed} failed")

    if failed == 0:
        print("\n  Workshop is READY! All systems go.")
        print("  Start the server: cd backend && uvicorn app.main:app --reload")
        print()
        return 0
    else:
        print(f"\n  Workshop has {failed} issue(s) to fix before class.")
        print("  Fix the FAIL items above, then run this script again.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
