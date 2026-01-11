#!/usr/bin/env python3
"""
Initialize Agent402 ZeroDB database schema.

Creates all required tables for the Agent402 backend:
- runs: Workflow execution records
- agents: Agent definitions with DIDs
- x402_requests: Cryptographically signed requests
- compliance_events: Risk assessment and audit logs
- agent_memory: Agent memory entries for persistence

Usage:
    python scripts/init_database.py
    python scripts/init_database.py --dry-run  # Preview only
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env
from app.services.zerodb_client import ZeroDBClient


# Agent402 Database Schema
AGENT402_TABLES = [
    {
        "table_name": "runs",
        "schema_definition": {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "run_id", "type": "text"},
                {"name": "project_id", "type": "text"},
                {"name": "status", "type": "text"},
                {"name": "started_at", "type": "timestamp"},
                {"name": "completed_at", "type": "timestamp"},
                {"name": "duration_ms", "type": "integer"},
                {"name": "workflow_type", "type": "text"},
                {"name": "config", "type": "jsonb"},
                {"name": "result", "type": "jsonb"},
                {"name": "error", "type": "text"},
                {"name": "created_at", "type": "timestamp"},
                {"name": "updated_at", "type": "timestamp"}
            ]
        }
    },
    {
        "table_name": "agents",
        "schema_definition": {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "agent_id", "type": "text"},
                {"name": "project_id", "type": "text"},
                {"name": "name", "type": "text"},
                {"name": "role", "type": "text"},
                {"name": "did", "type": "text"},
                {"name": "public_key", "type": "text"},
                {"name": "status", "type": "text"},
                {"name": "config", "type": "jsonb"},
                {"name": "created_at", "type": "timestamp"},
                {"name": "updated_at", "type": "timestamp"}
            ]
        }
    },
    {
        "table_name": "x402_requests",
        "schema_definition": {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "request_id", "type": "text"},
                {"name": "run_id", "type": "text"},
                {"name": "project_id", "type": "text"},
                {"name": "agent_id", "type": "text"},
                {"name": "method", "type": "text"},
                {"name": "url", "type": "text"},
                {"name": "headers", "type": "jsonb"},
                {"name": "body", "type": "jsonb"},
                {"name": "signature", "type": "text"},
                {"name": "signature_algorithm", "type": "text"},
                {"name": "verification_status", "type": "text"},
                {"name": "timestamp", "type": "timestamp"},
                {"name": "created_at", "type": "timestamp"}
            ]
        }
    },
    {
        "table_name": "compliance_events",
        "schema_definition": {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "event_id", "type": "text"},
                {"name": "run_id", "type": "text"},
                {"name": "project_id", "type": "text"},
                {"name": "agent_id", "type": "text"},
                {"name": "event_type", "type": "text"},
                {"name": "action", "type": "text"},
                {"name": "risk_score", "type": "integer"},
                {"name": "risk_level", "type": "text"},
                {"name": "passed", "type": "boolean"},
                {"name": "details", "type": "jsonb"},
                {"name": "timestamp", "type": "timestamp"},
                {"name": "created_at", "type": "timestamp"}
            ]
        }
    },
    {
        "table_name": "agent_memory",
        "schema_definition": {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "memory_id", "type": "text"},
                {"name": "run_id", "type": "text"},
                {"name": "project_id", "type": "text"},
                {"name": "agent_id", "type": "text"},
                {"name": "memory_type", "type": "text"},
                {"name": "content", "type": "text"},
                {"name": "embedding_id", "type": "text"},
                {"name": "metadata", "type": "jsonb"},
                {"name": "created_at", "type": "timestamp"},
                {"name": "updated_at", "type": "timestamp"}
            ]
        }
    },
    {
        "table_name": "events",
        "schema_definition": {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "event_id", "type": "text"},
                {"name": "project_id", "type": "text"},
                {"name": "event_type", "type": "text"},
                {"name": "source", "type": "text"},
                {"name": "correlation_id", "type": "text"},
                {"name": "data", "type": "jsonb"},
                {"name": "timestamp", "type": "timestamp"},
                {"name": "created_at", "type": "timestamp"}
            ]
        }
    }
]


async def init_database(dry_run: bool = False) -> None:
    """
    Initialize the Agent402 database schema.

    Args:
        dry_run: If True, only preview what would be created
    """
    print("=" * 60)
    print("Agent402 ZeroDB Database Initialization")
    print("=" * 60)

    # Initialize client
    try:
        client = ZeroDBClient()
        print(f"\nProject ID: {client.project_id}")
        print(f"Base URL: {client.base_url}")
    except ValueError as e:
        print(f"\nError: {e}")
        print("Please set ZERODB_API_KEY and ZERODB_PROJECT_ID environment variables.")
        sys.exit(1)

    # Get current database status
    print("\nChecking database status...")
    try:
        status = await client.get_database_status()
        print(f"  Database enabled: {status.get('database_enabled')}")
        print(f"  Vector dimensions: {status.get('vector_dimensions')}")
        usage = status.get('usage', {})
        print(f"  Current tables: {usage.get('tables_count', 0)}")
        print(f"  Current vectors: {usage.get('vectors_count', 0)}")
    except Exception as e:
        print(f"  Error checking status: {e}")
        sys.exit(1)

    # List existing tables
    print("\nListing existing tables...")
    try:
        tables_response = await client.list_tables()
        existing_tables = {t.get('table_name') for t in tables_response.get('data', [])}
        print(f"  Found {len(existing_tables)} existing tables")
        for table_name in existing_tables:
            print(f"    - {table_name}")
    except Exception as e:
        print(f"  Error listing tables: {e}")
        existing_tables = set()

    # Create tables
    print("\n" + "-" * 60)
    print("Creating Agent402 Tables")
    print("-" * 60)

    created_count = 0
    skipped_count = 0
    error_count = 0

    for table_def in AGENT402_TABLES:
        table_name = table_def["table_name"]

        if table_name in existing_tables:
            print(f"\n[SKIP] Table '{table_name}' already exists")
            skipped_count += 1
            continue

        if dry_run:
            print(f"\n[DRY-RUN] Would create table '{table_name}'")
            columns = table_def["schema_definition"]["columns"]
            for col in columns:
                pk = " (PK)" if col.get("primary_key") else ""
                print(f"    - {col['name']}: {col['type']}{pk}")
            created_count += 1
            continue

        print(f"\n[CREATE] Creating table '{table_name}'...")
        try:
            result = await client.create_table(
                table_name=table_name,
                schema_definition=table_def["schema_definition"]
            )
            print(f"  Success: Table '{table_name}' created")
            created_count += 1
        except Exception as e:
            print(f"  Error: {e}")
            error_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    if dry_run:
        print(f"  Mode: DRY-RUN (no changes made)")
    print(f"  Tables created: {created_count}")
    print(f"  Tables skipped (already exist): {skipped_count}")
    print(f"  Errors: {error_count}")

    if not dry_run and created_count > 0:
        print("\nDatabase initialization complete!")
        print("You can now start the backend server.")


def main():
    parser = argparse.ArgumentParser(
        description="Initialize Agent402 ZeroDB database schema"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without making changes"
    )
    args = parser.parse_args()

    asyncio.run(init_database(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
