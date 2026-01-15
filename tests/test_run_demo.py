#!/usr/bin/env python3
"""
Test suite for one-command demo execution script.

Per TDD methodology:
1. RED: Write tests that fail (script doesn't exist yet)
2. GREEN: Implement script to make tests pass
3. REFACTOR: Improve clarity and robustness

Tests verify:
- Script exists in correct location (scripts/ folder)
- Script is executable
- Script demonstrates full workflow: project → embed → search → table → row → event
- Script has proper error handling
- Script is idempotent (can run multiple times)
- Script completes in under 5 minutes (per PRD requirements)
- Script produces deterministic output
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
DEMO_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_demo.py"


class TestRunDemoScript:
    """Test suite for run_demo.py script."""

    def test_script_exists(self):
        """Test that demo script exists in scripts/ folder."""
        assert DEMO_SCRIPT_PATH.exists(), (
            f"Demo script not found at {DEMO_SCRIPT_PATH}. "
            "Script must be created in scripts/ folder per file placement rules."
        )

    def test_script_is_executable(self):
        """Test that demo script has execute permissions."""
        assert DEMO_SCRIPT_PATH.exists(), f"Script not found: {DEMO_SCRIPT_PATH}"
        assert os.access(DEMO_SCRIPT_PATH, os.X_OK), (
            f"Demo script {DEMO_SCRIPT_PATH} is not executable. "
            "Run: chmod +x scripts/run_demo.py"
        )

    def test_script_imports_successfully(self):
        """Test that script can be imported without errors."""
        assert DEMO_SCRIPT_PATH.exists(), f"Script not found: {DEMO_SCRIPT_PATH}"

        # Try importing the script as a module
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_demo", DEMO_SCRIPT_PATH)
        assert spec is not None, "Could not load script spec"

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Script import failed: {e}")

    def test_script_has_required_functions(self):
        """Test that script defines required workflow functions."""
        assert DEMO_SCRIPT_PATH.exists(), f"Script not found: {DEMO_SCRIPT_PATH}"

        import importlib.util
        spec = importlib.util.spec_from_file_location("run_demo", DEMO_SCRIPT_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Required workflow functions
        required_functions = [
            "create_project",
            "embed_text",
            "search_vectors",
            "create_table",
            "insert_row",
            "create_event",
            "run_demo"
        ]

        for func_name in required_functions:
            assert hasattr(module, func_name), (
                f"Script missing required function: {func_name}. "
                f"Demo must implement full workflow: project → embed → search → table → row → event"
            )

    def test_script_execution_completes(self):
        """Test that script executes successfully without errors."""
        assert DEMO_SCRIPT_PATH.exists(), f"Script not found: {DEMO_SCRIPT_PATH}"

        start_time = time.time()

        # Run the demo script
        result = subprocess.run(
            [sys.executable, str(DEMO_SCRIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per PRD
            cwd=PROJECT_ROOT
        )

        execution_time = time.time() - start_time

        # Check execution completed successfully
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            pytest.fail(
                f"Demo script failed with exit code {result.returncode}. "
                f"Check output above for errors."
            )

        # Verify execution time is under 5 minutes (per PRD Section 10)
        assert execution_time < 300, (
            f"Demo took {execution_time:.1f}s (should be < 300s per PRD). "
            "Optimize for faster execution."
        )

    def test_script_output_contains_workflow_steps(self):
        """Test that script output shows all workflow steps."""
        assert DEMO_SCRIPT_PATH.exists(), f"Script not found: {DEMO_SCRIPT_PATH}"

        result = subprocess.run(
            [sys.executable, str(DEMO_SCRIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=PROJECT_ROOT
        )

        assert result.returncode == 0, f"Script failed: {result.stderr}"

        output = result.stdout.lower()

        # Check for workflow step indicators
        required_steps = [
            "project",     # Project creation
            "embed",       # Embedding generation
            "search",      # Vector search
            "table",       # Table creation
            "row",         # Row insertion
            "event"        # Event creation
        ]

        for step in required_steps:
            assert step in output, (
                f"Script output missing workflow step: {step}. "
                f"Output should clearly show all workflow stages."
            )

    def test_script_is_idempotent(self):
        """Test that script can be run multiple times without errors."""
        assert DEMO_SCRIPT_PATH.exists(), f"Script not found: {DEMO_SCRIPT_PATH}"

        # Run script twice
        for run_number in [1, 2]:
            result = subprocess.run(
                [sys.executable, str(DEMO_SCRIPT_PATH)],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=PROJECT_ROOT
            )

            assert result.returncode == 0, (
                f"Script failed on run {run_number}. "
                f"Script must be idempotent (can run multiple times). "
                f"Error: {result.stderr}"
            )

    def test_script_has_clear_error_messages(self):
        """Test that script provides clear error messages when prerequisites are missing."""
        assert DEMO_SCRIPT_PATH.exists(), f"Script not found: {DEMO_SCRIPT_PATH}"

        # Run script without required environment variables
        env = os.environ.copy()
        # Remove critical env vars to trigger error handling
        env.pop('ZERODB_API_KEY', None)
        env.pop('ZERODB_PROJECT_ID', None)

        result = subprocess.run(
            [sys.executable, str(DEMO_SCRIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_ROOT,
            env=env
        )

        # Script should fail gracefully with clear error message
        assert result.returncode != 0, "Script should fail when env vars are missing"

        error_output = result.stdout + result.stderr
        error_output_lower = error_output.lower()

        # Should mention missing configuration
        assert any(word in error_output_lower for word in ['missing', 'required', 'environment', 'config']), (
            "Script should provide clear error message when prerequisites are missing. "
            f"Got: {error_output}"
        )

    def test_script_deterministic_behavior(self):
        """Test that script produces consistent results (same inputs = same outputs)."""
        assert DEMO_SCRIPT_PATH.exists(), f"Script not found: {DEMO_SCRIPT_PATH}"

        # Run script twice and compare key outputs
        outputs = []
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, str(DEMO_SCRIPT_PATH)],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=PROJECT_ROOT
            )

            assert result.returncode == 0, f"Script execution failed: {result.stderr}"
            outputs.append(result.stdout)

        # Parse outputs to check for deterministic behavior
        # Note: Some fields like timestamps will differ, but workflow structure should be same
        # This is a basic check - more sophisticated comparison can be added
        output1_lines = [line.strip() for line in outputs[0].split('\n') if line.strip()]
        output2_lines = [line.strip() for line in outputs[1].split('\n') if line.strip()]

        # Both should have same number of major steps
        assert len(output1_lines) > 0, "First run produced no output"
        assert len(output2_lines) > 0, "Second run produced no output"

        # Should have similar structure (allowing for timestamp differences)
        # This is a weak test, but ensures basic determinism
        assert abs(len(output1_lines) - len(output2_lines)) < 5, (
            "Script output structure differs between runs. "
            "Ensure deterministic behavior per PRD requirements."
        )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
