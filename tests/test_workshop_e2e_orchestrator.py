"""
Unit tests for the workshop E2E test orchestrator.

Covers the two fixes from #329 and #330:
1. ensure_project_exists() verifies the configured project via
   GET /v1/public/projects (it never tries to POST a new project, since
   Agent-402 exposes no runtime project-creation endpoint).
2. The orchestrator resolves PROJECT_ID with precedence
   --project-id > WORKSHOP_PROJECT_ID env > DEFAULT_PROJECT_ID.
3. The default is a project that actually exists in the deterministic
   project_store (regression guard for #330).
4. Tutorial 02 calls the Hedera wallet endpoints (not Circle) and does
   not pass the invalid wallet_type "EOA" (regression guard for #329).

These tests were written RED-first:
- #330 tests fail on the pre-fix default "proj_test_change_in_production"
  because it is not in project_store and ensure_project_exists() was
  attempting a POST to a nonexistent create endpoint.
- #329 tests fail on the pre-fix run_tutorial_02 source because it
  contained hits against `/circle/wallets` with `wallet_type: "EOA"`.

Built by AINative Dev Team
Refs #329 #330
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ORCHESTRATOR_PATH = PROJECT_ROOT / "scripts" / "workshop_e2e_test.py"


def _load_orchestrator():
    """Import scripts/workshop_e2e_test.py as a module."""
    spec = importlib.util.spec_from_file_location(
        "workshop_e2e_test", ORCHESTRATOR_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["workshop_e2e_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def orchestrator():
    """Fresh import of the orchestrator module per test."""
    # Ensure we get a fresh module so monkey-patching PROJECT_ID doesn't leak.
    sys.modules.pop("workshop_e2e_test", None)
    return _load_orchestrator()


class DescribeDefaultProjectId:
    """
    Regression guard for #330: the default project ID must exist in the
    deterministic project_store. Any future rename in project_store.py
    without updating the orchestrator will fail this test.
    """

    def it_points_at_an_existing_deterministic_project(self, orchestrator):
        # Late import so backend path setup above applies.
        sys.path.insert(
            0, str(PROJECT_ROOT / "backend")
        )
        from app.services.project_store import project_store

        assert project_store.get_by_id(orchestrator.DEFAULT_PROJECT_ID) is not None, (
            f"DEFAULT_PROJECT_ID '{orchestrator.DEFAULT_PROJECT_ID}' is not in "
            "project_store. Pre-fix this pointed at "
            "'proj_test_change_in_production', which did not exist and caused "
            "every project-scoped endpoint to 404."
        )

    def it_is_not_the_broken_pre_fix_default(self, orchestrator):
        assert orchestrator.DEFAULT_PROJECT_ID != "proj_test_change_in_production"


class DescribeEnsureProjectExists:
    """Tests for ensure_project_exists(): list-and-verify, never create."""

    def it_returns_true_when_project_is_in_list(self, orchestrator):
        def fake_api_get(path, expected_status=200):
            assert path == "/v1/public/projects"
            return (
                True,
                {
                    "projects": [
                        {"id": "proj_demo_u1_001", "name": "x"},
                        {"id": "proj_demo_u1_002", "name": "y"},
                    ],
                    "total": 2,
                },
                "",
            )

        with patch.object(orchestrator, "api_get", side_effect=fake_api_get):
            orchestrator.PROJECT_ID = "proj_demo_u1_001"
            ok, detail = orchestrator.ensure_project_exists()
        assert ok is True
        assert detail == ""

    def it_returns_false_with_helpful_detail_when_project_missing(
        self, orchestrator
    ):
        def fake_api_get(path, expected_status=200):
            return (
                True,
                {"projects": [{"id": "proj_demo_u1_001"}], "total": 1},
                "",
            )

        with patch.object(orchestrator, "api_get", side_effect=fake_api_get):
            orchestrator.PROJECT_ID = "proj_does_not_exist"
            ok, detail = orchestrator.ensure_project_exists()

        assert ok is False
        assert "proj_does_not_exist" in detail
        assert "Visible projects" in detail
        assert "--project-id" in detail or "WORKSHOP_PROJECT_ID" in detail

    def it_returns_false_when_list_endpoint_fails(self, orchestrator):
        with patch.object(
            orchestrator,
            "api_get",
            return_value=(False, None, "HTTP 500: oh no"),
        ):
            ok, detail = orchestrator.ensure_project_exists()
        assert ok is False
        assert "Could not list projects" in detail

    def it_does_not_attempt_to_create_projects(self, orchestrator):
        """Pre-fix ensure_project_exists() POSTed to /v1/public/projects,
        which does not exist in Agent-402. Guard against that regression."""
        call_log = []

        def fake_api_get(path, expected_status=200):
            call_log.append(("GET", path))
            return True, {"projects": [], "total": 0}, ""

        def fake_api_post(path, body, expected_status=201):
            call_log.append(("POST", path))
            return True, {}, ""

        with patch.object(orchestrator, "api_get", side_effect=fake_api_get), \
             patch.object(orchestrator, "api_post", side_effect=fake_api_post):
            orchestrator.ensure_project_exists()

        assert ("POST", "/v1/public/projects") not in call_log
        assert all(verb == "GET" for verb, _ in call_log)


class DescribeProjectIdCliAndEnv:
    """
    Resolution precedence: --project-id > WORKSHOP_PROJECT_ID env > default.
    These tests verify the module picks up the env var at import time and
    that main() overrides it when the CLI flag is supplied.
    """

    def it_uses_env_override_at_module_load(self):
        sys.modules.pop("workshop_e2e_test", None)
        with patch.dict(os.environ, {"WORKSHOP_PROJECT_ID": "proj_demo_u1_002"}):
            mod = _load_orchestrator()
        assert mod.PROJECT_ID == "proj_demo_u1_002"
        assert mod.DEFAULT_PROJECT_ID == "proj_demo_u1_001"

    def it_falls_back_to_default_when_env_unset(self):
        sys.modules.pop("workshop_e2e_test", None)
        env = {k: v for k, v in os.environ.items() if k != "WORKSHOP_PROJECT_ID"}
        with patch.dict(os.environ, env, clear=True):
            mod = _load_orchestrator()
        assert mod.PROJECT_ID == mod.DEFAULT_PROJECT_ID == "proj_demo_u1_001"

    def it_exposes_project_id_cli_flag(self, orchestrator):
        source = ORCHESTRATOR_PATH.read_text()
        # Minimal structural check — the flag must be wired into argparse.
        assert '"--project-id"' in source
        assert "WORKSHOP_PROJECT_ID" in source


class DescribeTutorial02UsesHedera:
    """
    Regression guard for #329: Tutorial 02 content teaches Hedera wallets,
    so the orchestrator must test Hedera wallets (not Circle), and must
    never use the invalid wallet_type "EOA".
    """

    def it_hits_hedera_wallet_endpoint_in_tutorial_02(self):
        source = ORCHESTRATOR_PATH.read_text()
        # Find the run_tutorial_02 body.
        start = source.index("def run_tutorial_02")
        end = source.index("def run_tutorial_03")
        t02 = source[start:end]

        assert "/hedera/wallets" in t02, (
            "run_tutorial_02 must POST to /v1/public/{project_id}/hedera/wallets; "
            "Tutorial 02 teaches Hedera wallets."
        )
        assert "associate-usdc" in t02
        assert "/hedera/payments" in t02
        assert "/verify" in t02

    def it_does_not_use_invalid_circle_eoa_wallet_type(self):
        source = ORCHESTRATOR_PATH.read_text()
        start = source.index("def run_tutorial_02")
        end = source.index("def run_tutorial_03")
        t02 = source[start:end]

        assert '"EOA"' not in t02 and "'EOA'" not in t02, (
            "Tutorial 02 must not submit wallet_type=EOA; the Circle schema "
            "(backend/app/schemas/circle.py) enumerates analyst|compliance|"
            "transaction and will return HTTP 422."
        )

    def it_does_not_call_circle_wallets_in_tutorial_02(self):
        source = ORCHESTRATOR_PATH.read_text()
        start = source.index("def run_tutorial_02")
        end = source.index("def run_tutorial_03")
        t02 = source[start:end]

        assert "/circle/wallets" not in t02, (
            "Circle wallet coverage must not live in Tutorial 02 — Tutorial 02 "
            "teaches Hedera. Circle coverage belongs in a future Tutorial 04."
        )


class DescribeSmokeTestRegressionGuard:
    """
    The smoke test must fail fast when the orchestrator's project ID is
    missing from project_store. This is the belt-and-braces check for #330.
    """

    def it_asserts_project_id_exists_in_store(self):
        backend_path = PROJECT_ROOT / "backend"
        sys.path.insert(0, str(backend_path))
        spec = importlib.util.spec_from_file_location(
            "workshop_smoke_test",
            str(PROJECT_ROOT / "scripts" / "workshop_smoke_test.py"),
        )
        assert spec is not None and spec.loader is not None
        smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(smoke)

        assert smoke.check_orchestrator_project_id_exists() is True

    def it_raises_for_unknown_project_id(self):
        backend_path = PROJECT_ROOT / "backend"
        sys.path.insert(0, str(backend_path))
        spec = importlib.util.spec_from_file_location(
            "workshop_smoke_test",
            str(PROJECT_ROOT / "scripts" / "workshop_smoke_test.py"),
        )
        assert spec is not None and spec.loader is not None
        smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(smoke)

        with patch.dict(
            os.environ, {"WORKSHOP_PROJECT_ID": "proj_does_not_exist"}
        ):
            with pytest.raises(AssertionError) as exc:
                smoke.check_orchestrator_project_id_exists()
        assert "proj_does_not_exist" in str(exc.value)
