#!/usr/bin/env python3
"""
Create Circle wallets for Agent-402 agents.

This script creates a Circle wallet set and individual wallets for the 3 agents:
- Analyst Agent (token_id: 0) - Analysis and research tasks
- Compliance Agent (token_id: 1) - Regulatory compliance verification
- Transaction Agent (token_id: 2) - Payment execution

Usage:
    python scripts/create_agent_wallets.py
    python scripts/create_agent_wallets.py --dry-run  # Preview only
    python scripts/create_agent_wallets.py --project-id proj_123  # Specify project

Environment Variables Required:
    CIRCLE_API_KEY - Circle API key
    CIRCLE_ENTITY_SECRET - Circle entity secret (32-byte hex string)
"""
import asyncio
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env
from app.services.circle_service import get_circle_service, CircleAPIError
from app.services.circle_wallet_service import CircleWalletService
from app.services.zerodb_client import get_zerodb_client

# Agent definitions from arc-testnet.json
# These are the 3 agents that need Circle wallets
AGENTS = [
    {
        "name": "Analyst Agent",
        "token_id": 0,
        "treasury_id": 1,
        "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
        "role": "analyst",
        "wallet_type": "analyst"
    },
    {
        "name": "Compliance Agent",
        "token_id": 1,
        "treasury_id": 2,
        "did": "did:key:z6Mki9E8kZT3ybvrYqVqJQrW9vHn6YuVjAVdHqzBGbYQk2Jp",
        "role": "compliance",
        "wallet_type": "compliance"
    },
    {
        "name": "Transaction Agent",
        "token_id": 2,
        "treasury_id": 3,
        "did": "did:key:z6MkkKQ3EbHjE4VPZqL6LS2b4kXy7nZvJqW9vHn6YuVjAVdH",
        "role": "transaction",
        "wallet_type": "transaction"
    }
]

# Default project ID for agent wallets
DEFAULT_PROJECT_ID = "agent402_platform"


async def create_agent_wallets(
    project_id: str,
    dry_run: bool = False,
    output_file: str = None
) -> dict:
    """
    Create Circle wallets for all Agent-402 agents.

    Args:
        project_id: Project identifier for wallet grouping
        dry_run: If True, only preview what would be created
        output_file: Optional path to save wallet configuration

    Returns:
        Dictionary containing created wallet information
    """
    print("=" * 60)
    print("Agent-402 Circle Wallet Creation")
    print("=" * 60)
    print(f"\nProject ID: {project_id}")
    print(f"Blockchain: ARC-TESTNET")
    print(f"Dry Run: {dry_run}")

    # Initialize services
    try:
        wallet_service = CircleWalletService()
        print("\nCircle service initialized successfully")
    except Exception as e:
        print(f"\nError initializing Circle service: {e}")
        print("Please set CIRCLE_API_KEY and CIRCLE_ENTITY_SECRET environment variables.")
        sys.exit(1)

    # Track results
    results = {
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "blockchain": "ARC-TESTNET",
        "wallet_set_id": None,
        "wallets": []
    }

    created_count = 0
    skipped_count = 0
    error_count = 0

    print("\n" + "-" * 60)
    print("Creating Agent Wallets")
    print("-" * 60)

    for agent in AGENTS:
        print(f"\n[{agent['name']}]")
        print(f"  DID: {agent['did']}")
        print(f"  Role: {agent['role']}")
        print(f"  Wallet Type: {agent['wallet_type']}")

        if dry_run:
            print(f"  [DRY-RUN] Would create wallet for {agent['name']}")
            results["wallets"].append({
                "agent_name": agent["name"],
                "agent_did": agent["did"],
                "wallet_type": agent["wallet_type"],
                "status": "dry_run"
            })
            created_count += 1
            continue

        try:
            # Create wallet for this agent
            wallet = await wallet_service.create_agent_wallet(
                project_id=project_id,
                agent_did=agent["did"],
                wallet_type=agent["wallet_type"],
                description=f"{agent['name']} wallet for USDC payments"
            )

            print(f"  [SUCCESS] Wallet created")
            print(f"    Wallet ID: {wallet['wallet_id']}")
            print(f"    Circle Wallet ID: {wallet['circle_wallet_id']}")
            print(f"    Blockchain Address: {wallet['blockchain_address']}")

            # Store wallet set ID from first wallet
            if not results["wallet_set_id"]:
                results["wallet_set_id"] = wallet.get("wallet_set_id")

            results["wallets"].append({
                "agent_name": agent["name"],
                "agent_did": agent["did"],
                "wallet_type": agent["wallet_type"],
                "wallet_id": wallet["wallet_id"],
                "circle_wallet_id": wallet["circle_wallet_id"],
                "blockchain_address": wallet["blockchain_address"],
                "blockchain": wallet.get("blockchain", "ARC-TESTNET"),
                "status": "active"
            })
            created_count += 1

        except Exception as e:
            error_message = str(e)
            if "DUPLICATE_WALLET" in error_message or "already exists" in error_message.lower():
                print(f"  [SKIP] Wallet already exists for this agent")
                skipped_count += 1
                results["wallets"].append({
                    "agent_name": agent["name"],
                    "agent_did": agent["did"],
                    "wallet_type": agent["wallet_type"],
                    "status": "already_exists"
                })
            else:
                print(f"  [ERROR] Failed to create wallet: {e}")
                error_count += 1
                results["wallets"].append({
                    "agent_name": agent["name"],
                    "agent_did": agent["did"],
                    "wallet_type": agent["wallet_type"],
                    "status": "error",
                    "error": error_message
                })

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    if dry_run:
        print(f"  Mode: DRY-RUN (no changes made)")
    print(f"  Wallets created: {created_count}")
    print(f"  Wallets skipped (already exist): {skipped_count}")
    print(f"  Errors: {error_count}")

    if results["wallet_set_id"]:
        print(f"\n  Wallet Set ID: {results['wallet_set_id']}")

    # Save results to file if specified
    if output_file and not dry_run:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n  Configuration saved to: {output_path}")

    # Print wallet addresses for funding
    if not dry_run and created_count > 0:
        print("\n" + "-" * 60)
        print("Wallet Addresses for Funding")
        print("-" * 60)
        print("\nTo fund these wallets with testnet USDC, use these addresses:")
        for wallet in results["wallets"]:
            if wallet.get("blockchain_address"):
                print(f"  {wallet['agent_name']}: {wallet['blockchain_address']}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Create Circle wallets for Agent-402 agents"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without making changes"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        default=DEFAULT_PROJECT_ID,
        help=f"Project ID for wallet grouping (default: {DEFAULT_PROJECT_ID})"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save wallet configuration JSON file"
    )
    args = parser.parse_args()

    asyncio.run(create_agent_wallets(
        project_id=args.project_id,
        dry_run=args.dry_run,
        output_file=args.output
    ))


if __name__ == "__main__":
    main()
