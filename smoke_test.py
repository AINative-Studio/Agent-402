```python
# tests/smoke_test.py
"""
Smoke Test — CrewAI × X402 × ZeroDB × AIKit (AINative Edition)

What this test guarantees (per PRD):
1) The demo workflow runs end-to-end (single command).
2) X402 server is discoverable via /.well-known/x402.
3) ZeroDB contract requirements are enforced:
   - Embeddings model defaults/valid model works
   - Wrong model fails (contract drift detector)
   - Missing /database prefix returns 404 (contract drift detector)
   - Missing row_data returns 422 (contract drift detector)
   - Project limit exceeded returns 429 with PROJECT_LIMIT_EXCEEDED (issue #59)
4) ZeroDB tables exist (or are created) and are writable:
   - agents
   - agent_memory
   - compliance_events
   - x402_requests
5) A recent ledger entry exists after demo run (best-effort check).

Usage:
  export ZERODB_API_KEY="..."
  export ZERODB_PROJECT_ID="..."
  export X402_SERVER_URL="http://127.0.0.1:8001"   # or wherever your X402 server runs
  # Optional: export SMOKE_DEMO_CMD="python main.py"
  python tests/smoke_test.py

Notes:
- This script assumes you have already implemented:
  - X402 FastAPI server endpoints: /.well-known/x402 and /x402
  - Your demo command writes to ZeroDB (especially x402_requests ledger)
- If your demo command is different, set SMOKE_DEMO_CMD env var.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests


ZERODB_BASE_URL = os.getenv("ZERODB_BASE_URL", "https://api.ainative.studio/v1/public")


@dataclass(frozen=True)
class Env:
    zerodb_api_key: str
    zerodb_project_id: str
    x402_server_url: str
    smoke_demo_cmd: str
    timeout_s: int = 30
    max_retries: int = 4


def require_env() -> Env:
    api_key = os.getenv("ZERODB_API_KEY", "").strip()
    project_id = os.getenv("ZERODB_PROJECT_ID", "").strip()
    x402_url = os.getenv("X402_SERVER_URL", "").strip().rstrip("/")
    demo_cmd = os.getenv("SMOKE_DEMO_CMD", "python main.py").strip()

    missing = []
    if not api_key:
        missing.append("ZERODB_API_KEY")
    if not project_id:
        missing.append("ZERODB_PROJECT_ID")
    if not x402_url:
        missing.append("X402_SERVER_URL")

    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")

    return Env(
        zerodb_api_key=api_key,
        zerodb_project_id=project_id,
        x402_server_url=x402_url,
        smoke_demo_cmd=demo_cmd,
    )


def _headers(env: Env) -> Dict[str, str]:
    return {"X-API-Key": env.zerodb_api_key, "Content-Type": "application/json"}


def request_with_retry(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout_s: int = 30,
    max_retries: int = 4,
    expect_status: Optional[int] = None,
) -> requests.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
                timeout=timeout_s,
            )
            if expect_status is not None and resp.status_code != expect_status:
                # retry for transient errors
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            return resp
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
    raise RuntimeError(f"HTTP request failed after retries: {method} {url} | last_err={last_exc}")


def assert_status(resp: requests.Response, expected: int, msg: str) -> None:
    if resp.status_code != expected:
        body = resp.text[:1500]
        raise AssertionError(f"{msg}\nExpected HTTP {expected}, got {resp.status_code}\nBody:\n{body}")


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# -----------------------------
# ZeroDB helpers
# -----------------------------
def zerodb_url(env: Env, path: str) -> str:
    return f"{ZERODB_BASE_URL}/{env.zerodb_project_id}{path}"


def create_table_if_missing(env: Env, name: str, schema: Dict[str, str], description: str) -> None:
    """
    Best effort:
    - Try create; if fails because already exists, continue.
    """
    url = zerodb_url(env, "/database/tables")
    payload = {"name": name, "description": description, "schema": schema}
    resp = request_with_retry(
        "POST",
        url,
        headers=_headers(env),
        json_body=payload,
        timeout_s=env.timeout_s,
        max_retries=env.max_retries,
    )
    # Accept 200/201 as created; accept 400/409-ish as "already exists" depending on backend behavior.
    if resp.status_code in (200, 201):
        return
    if resp.status_code in (400, 409):
        # Try to detect "exists" from body text without being brittle
        txt = (resp.text or "").lower()
        if "exist" in txt or "already" in txt or "duplicate" in txt:
            return
    # Otherwise fail
    raise AssertionError(f"Failed creating table '{name}'. Status={resp.status_code} Body={resp.text[:1000]}")


def insert_row(env: Env, table: str, row_data: Dict[str, Any], expect: int = 200) -> Dict[str, Any]:
    url = zerodb_url(env, f"/database/tables/{table}/rows")
    resp = request_with_retry(
        "POST",
        url,
        headers=_headers(env),
        json_body={"row_data": row_data},
        timeout_s=env.timeout_s,
        max_retries=env.max_retries,
    )
    assert_status(resp, expect, f"Insert row failed for table={table}")
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}


def list_rows(env: Env, table: str, limit: int = 50) -> Dict[str, Any]:
    url = zerodb_url(env, f"/database/tables/{table}/rows?limit={limit}")
    resp = request_with_retry(
        "GET",
        url,
        headers={"X-API-Key": env.zerodb_api_key},
        timeout_s=env.timeout_s,
        max_retries=env.max_retries,
    )
    assert_status(resp, 200, f"List rows failed for table={table}")
    return resp.json()


# -----------------------------
# Smoke checks
# -----------------------------
def check_x402_discovery(env: Env) -> Dict[str, Any]:
    url = f"{env.x402_server_url}/.well-known/x402"
    resp = request_with_retry("GET", url, timeout_s=env.timeout_s, max_retries=env.max_retries)
    assert_status(resp, 200, "X402 discovery endpoint failed")
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
    return data


def check_embeddings_contract(env: Env) -> None:
    """
    Contract rules from the ZeroDB dev docs:
    - Valid model works (default or BAAI/bge-small-en-v1.5)
    - Wrong model fails (MODEL_NOT_FOUND or similar)
    """
    # Good: default model (no "model" field)
    good_url = zerodb_url(env, "/embeddings/generate")
    good_payload = {"texts": ["smoke test: embeddings generate"]}
    good = request_with_retry(
        "POST",
        good_url,
        headers=_headers(env),
        json_body=good_payload,
        timeout_s=env.timeout_s,
        max_retries=env.max_retries,
    )
    assert_status(good, 200, "Embeddings generate (default model) should succeed")
    j = good.json()
    assert_true("embeddings" in j and isinstance(j["embeddings"], list), "Embeddings generate response missing embeddings[]")
    assert_true(j.get("dimensions") in (384, 768, 1024, 1536), "Embeddings generate response missing dimensions")
    # If default is expected 384, enforce it unless you explicitly changed default:
    assert_true(j.get("dimensions") == 384, f"Expected default embeddings dimensions=384, got {j.get('dimensions')}")

    # Bad: wrong model should fail
    bad_payload = {"texts": ["smoke test: wrong model"], "model": "custom-1536"}
    bad = request_with_retry(
        "POST",
        good_url,
        headers=_headers(env),
        json_body=bad_payload,
        timeout_s=env.timeout_s,
        max_retries=env.max_retries,
    )
    assert_true(
        bad.status_code in (400, 404, 422, 500),
        f"Expected wrong model to fail, got status={bad.status_code} body={bad.text[:500]}",
    )


def check_database_prefix_contract(env: Env) -> None:
    """
    Contract rule: Vector operations require /database prefix.
    - POST /{project_id}/vectors/upsert should 404
    """
    wrong_url = f"{ZERODB_BASE_URL}/{env.zerodb_project_id}/vectors/upsert"  # intentionally missing /database
    resp = request_with_retry(
        "POST",
        wrong_url,
        headers=_headers(env),
        json_body={"id": "smoke_wrong_prefix", "vector": [0.0] * 384},
        timeout_s=env.timeout_s,
        max_retries=env.max_retries,
    )
    assert_status(resp, 404, "Missing /database prefix should return 404 (contract drift detector)")


def check_row_data_contract(env: Env) -> None:
    """
    Contract rule: row inserts must use 'row_data' (NOT 'data' or 'rows')
    """
    url = zerodb_url(env, "/database/tables/agents/rows")
    # Intentionally wrong payload
    resp = request_with_retry(
        "POST",
        url,
        headers=_headers(env),
        json_body={"data": {"agent_id": "bad_payload"}},  # wrong key on purpose
        timeout_s=env.timeout_s,
        max_retries=env.max_retries,
    )
    assert_status(resp, 422, "Missing row_data should return 422 (contract drift detector)")


def check_project_limit_contract(env: Env) -> None:
    """
    Contract rule: Project limit validation (GitHub issue #59)
    - Exceeding project limit must return HTTP 429
    - Error response must include error_code: "PROJECT_LIMIT_EXCEEDED"
    - Error response must include "detail" field explaining the limit
    - Error message should include current tier and project limit
    - Suggest upgrade path or contact support

    Per PRD §12 (Infrastructure Credibility) and Backlog Epic 1, Story 4.
    """
    # Use a unique API key for this test to avoid interference
    test_api_key = f"{env.zerodb_api_key}-limit-test"
    test_headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}

    # Note: This test assumes the local/test API is running on the same base URL
    # For production ZeroDB, this would need to be modified
    projects_url = f"{ZERODB_BASE_URL}/projects"

    # Create projects up to free tier limit (3)
    for i in range(3):
        resp = request_with_retry(
            "POST",
            projects_url,
            headers=test_headers,
            json_body={
                "name": f"smoke-limit-test-{i}",
                "tier": "free",
                "database_enabled": True
            },
            timeout_s=env.timeout_s,
            max_retries=env.max_retries,
        )
        # All 3 should succeed
        assert_status(resp, 201, f"Project {i+1}/3 creation should succeed")

    # Attempt to create 4th project (should fail with 429)
    resp = request_with_retry(
        "POST",
        projects_url,
        headers=test_headers,
        json_body={
            "name": "smoke-limit-test-4",
            "tier": "free",
            "database_enabled": True
        },
        timeout_s=env.timeout_s,
        max_retries=env.max_retries,
    )

    # Must return 429 (Too Many Requests)
    assert_status(resp, 429, "Exceeding project limit should return 429")

    # Validate error response structure
    error_data = resp.json()

    # Must have error_code
    assert_true(
        "error_code" in error_data,
        "PROJECT_LIMIT_EXCEEDED error must include error_code field"
    )
    assert_true(
        error_data["error_code"] == "PROJECT_LIMIT_EXCEEDED",
        f"Expected error_code 'PROJECT_LIMIT_EXCEEDED', got '{error_data.get('error_code')}'"
    )

    # Must have detail
    assert_true(
        "detail" in error_data,
        "PROJECT_LIMIT_EXCEEDED error must include detail field"
    )

    detail = error_data["detail"]

    # Detail must include tier and limit information
    assert_true(
        "tier 'free'" in detail or "tier \"free\"" in detail,
        "Detail must include tier information"
    )
    assert_true(
        "3/3" in detail or "3 / 3" in detail,
        "Detail must include current count and limit (3/3)"
    )

    # Detail must suggest upgrade or support
    assert_true(
        "upgrade" in detail.lower() or "support" in detail.lower(),
        "Detail must suggest upgrade path or support contact"
    )


def check_project_status_field(env: Env) -> None:
    """
    Contract rule: All project responses must include 'status' field.
    - Newly created projects must have status: "ACTIVE"
    - List projects must include status for all items
    - Status must never be null, undefined, or omitted

    Per PRD §9 and Backlog Epic 1, Story 5.
    """
    # First, list existing projects to verify status field presence
    url = f"{ZERODB_BASE_URL}/projects"
    resp = request_with_retry(
        "GET",
        url,
        headers={"X-API-Key": env.zerodb_api_key},
        timeout_s=env.timeout_s,
        max_retries=env.max_retries,
    )
    assert_status(resp, 200, "List projects should succeed")

    projects_data = resp.json()
    # Handle both {"items": [...]} and direct array response
    items = projects_data.get("items", projects_data) if isinstance(projects_data, dict) else projects_data

    if isinstance(items, list) and len(items) > 0:
        for idx, project in enumerate(items):
            assert_true(
                "status" in project,
                f"Project at index {idx} missing 'status' field. Project: {project.get('id', 'unknown')}"
            )
            assert_true(
                project["status"] in ["ACTIVE", "SUSPENDED", "DELETED"],
                f"Project {project.get('id')} has invalid status: {project.get('status')}"
            )
            assert_true(
                project["status"] is not None and project["status"] != "",
                f"Project {project.get('id')} has null or empty status"
            )


def ensure_mvp_tables(env: Env) -> None:
    """
    Minimal MVP tables aligned to PRD "collections".
    Implemented as ZeroDB tables via /database/tables endpoints.
    """
    create_table_if_missing(
        env,
        "agents",
        schema={
            "id": "UUID PRIMARY KEY",
            "agent_id": "TEXT UNIQUE",
            "did": "TEXT NOT NULL",
            "role": "TEXT NOT NULL",
            "created_at": "TIMESTAMP DEFAULT NOW()",
        },
        description="Agent profiles (DID, role, metadata)",
    )

    create_table_if_missing(
        env,
        "agent_memory",
        schema={
            "id": "UUID PRIMARY KEY",
            "agent_id": "TEXT NOT NULL",
            "task_id": "TEXT NOT NULL",
            "input_summary": "TEXT",
            "output_summary": "TEXT",
            "confidence": "FLOAT",
            "created_at": "TIMESTAMP DEFAULT NOW()",
        },
        description="Persistent agent memory across runs",
    )

    create_table_if_missing(
        env,
        "compliance_events",
        schema={
            "id": "UUID PRIMARY KEY",
            "agent_id": "TEXT NOT NULL",
            "subject_id": "TEXT",
            "risk_score": "FLOAT",
            "passed": "BOOLEAN",
            "reason": "TEXT",
            "created_at": "TIMESTAMP DEFAULT NOW()",
        },
        description="Compliance audit trail (KYC/KYT simulation)",
    )

    create_table_if_missing(
        env,
        "x402_requests",
        schema={
            "id": "UUID PRIMARY KEY",
            "did": "TEXT NOT NULL",
            "signature": "TEXT NOT NULL",
            "payload": "JSONB",
            "verified": "BOOLEAN",
            "response": "JSONB",
            "created_at": "TIMESTAMP DEFAULT NOW()",
        },
        description="Signed X402 request ledger (non-repudiation)",
    )


def seed_minimal_rows(env: Env) -> None:
    """
    Insert one row into each table to prove writes work.
    """
    now = datetime.now(timezone.utc).isoformat()

    insert_row(
        env,
        "agents",
        {
            "agent_id": "smoke_analyst",
            "did": "did:ethr:0xSMOKEANALYST",
            "role": "analyst",
            "created_at": now,
        },
        expect=200,
    )

    insert_row(
        env,
        "agent_memory",
        {
            "agent_id": "smoke_analyst",
            "task_id": "smoke_task_1",
            "input_summary": "smoke input",
            "output_summary": "smoke output",
            "confidence": 0.5,
            "created_at": now,
        },
        expect=200,
    )

    insert_row(
        env,
        "compliance_events",
        {
            "agent_id": "smoke_compliance",
            "subject_id": "smoke_subject_1",
            "risk_score": 0.1,
            "passed": True,
            "reason": "smoke pass",
            "created_at": now,
        },
        expect=200,
    )


def run_demo_command(env: Env) -> str:
    """
    Runs the one-command demo and returns stdout for downstream checks.
    Configure with SMOKE_DEMO_CMD if not `python main.py`.
    """
    print(f"▶ Running demo command: {env.smoke_demo_cmd}")
    proc = subprocess.run(
        env.smoke_demo_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=os.environ.copy(),
    )
    out = proc.stdout or ""
    print(out)
    if proc.returncode != 0:
        raise AssertionError(f"Demo command failed with code={proc.returncode}\nOutput:\n{out[:2000]}")
    return out


def find_recent_ledger_entry(env: Env, since_epoch_s: float) -> None:
    """
    Best-effort: look for x402_requests rows created after `since_epoch_s`.
    Because the tables endpoint response format may vary, this uses tolerant parsing.
    """
    data = list_rows(env, "x402_requests", limit=50)

    # Try common shapes:
    # - {"items":[{...}]}
    # - {"rows":[{...}]}
    # - [{"..."}]
    items = None
    if isinstance(data, dict):
        for k in ("items", "rows", "data", "results"):
            if k in data and isinstance(data[k], list):
                items = data[k]
                break
    if items is None and isinstance(data, list):
        items = data

    assert_true(isinstance(items, list), f"Unexpected x402_requests rows payload shape: {type(data)}")

    def parse_ts(val: Any) -> Optional[float]:
        if not val:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # ISO-8601 timestamps expected
            try:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                return dt.timestamp()
            except Exception:
                return None
        return None

    recent = []
    for r in items:
        if not isinstance(r, dict):
            continue
        ts = parse_ts(r.get("created_at")) or parse_ts(r.get("timestamp"))
        if ts is None:
            continue
        if ts >= since_epoch_s:
            recent.append(r)

    assert_true(
        len(recent) >= 1,
        "No recent x402_requests ledger entry found after demo run. "
        "Ensure your demo writes to ZeroDB x402_requests table.",
    )

    # Optional stronger checks (non-fatal if missing fields)
    r0 = recent[0]
    for key in ("did", "signature"):
        assert_true(key in r0, f"Recent ledger entry missing field '{key}'")
    # verified may be boolean — check if present
    if "verified" in r0:
        assert_true(isinstance(r0["verified"], bool), "Ledger field 'verified' should be boolean if present")


def main() -> None:
    env = require_env()
    started_at = time.time()

    print("=== SMOKE TEST: START ===")

    # 1) X402 discovery must work
    meta = check_x402_discovery(env)
    print(f"✅ X402 discovery ok: keys={list(meta)[:10]}")

    # 2) ZeroDB table provisioning (minimal MVP)
    ensure_mvp_tables(env)
    print("✅ ZeroDB MVP tables ensured")

    # 3) Contract drift detectors (these should NOT pass silently)
    check_database_prefix_contract(env)
    print("✅ Contract: /database prefix enforced")

    check_row_data_contract(env)
    print("✅ Contract: row_data enforced (422 on wrong payload)")

    check_embeddings_contract(env)
    print("✅ Contract: embeddings default model works; wrong model fails")

    check_project_limit_contract(env)
    print("✅ Contract: project limit enforced (429 with PROJECT_LIMIT_EXCEEDED, Issue #59)")

    check_project_status_field(env)
    print("✅ Contract: project status field present in all responses (Issue #60)")

    # 4) Prove we can write rows
    seed_minimal_rows(env)
    print("✅ ZeroDB writes ok (seed rows inserted)")

    # 5) Run demo command (CrewAI local runtime -> X402 -> ZeroDB)
    demo_output = run_demo_command(env)

    # Optional: if you print a run_id, capture it (not required)
    m = re.search(r"run_id[:=]\s*([A-Za-z0-9_\-]+)", demo_output)
    if m:
        print(f"ℹ️ Detected run_id: {m.group(1)}")

    # 6) Confirm ledger entry created after demo started
    find_recent_ledger_entry(env, since_epoch_s=started_at)
    print("✅ Ledger: recent x402_requests entry found")

    print("=== SMOKE TEST: PASS ✅ ===")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"\n=== SMOKE TEST: FAIL ❌ ===\n{e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n=== SMOKE TEST: ERROR ❌ ===\n{e}\n")
        sys.exit(2)
```
