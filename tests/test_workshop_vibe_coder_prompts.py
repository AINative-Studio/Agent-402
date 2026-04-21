"""
Test suite for workshop E2E vibe-coder persona prompt purity.

Refs #342.

Per TDD methodology:
1. RED: Tests fail when any prompt_as_vibe_coder(...) call contains leaked
        API details (HTTP verbs, URL paths, snake_case field names).
2. GREEN: Prompts are rewritten in plain English; tests pass.
3. REFACTOR: Style-guide enforced via regex checks so future regressions
             are caught before merge.

The vibe-coder track is natural-language only — the AI assistant is
assumed to know which endpoint to call. Leaking POST /v1/public/... into
a vibe-coder prompt is a persona failure and is blocked here.

Built by AINative Dev Team
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Tuple

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_SCRIPT = REPO_ROOT / "scripts" / "workshop_e2e_test.py"


def _flatten_string(node: ast.AST) -> str:
    """Collapse a string/f-string/concat into a single inspectable string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: List[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append(f"{{{ast.unparse(value.value)}}}")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _flatten_string(node.left) + _flatten_string(node.right)
    return ast.unparse(node)


def _collect_vibe_coder_prompts() -> List[Tuple[int, str]]:
    """Return [(line_no, prompt_text), ...] for every prompt_as_vibe_coder call."""
    source = TARGET_SCRIPT.read_text()
    tree = ast.parse(source)
    prompts: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "prompt_as_vibe_coder":
            continue
        if not node.args:
            continue
        arg = node.args[0]
        # Adjacent string concatenation arrives as a single Constant post-parse
        # for plain strings, but f-strings and explicit BinOp need _flatten_string.
        prompt = _flatten_string(arg)
        prompts.append((node.lineno, prompt))
    return prompts


# Forbidden token patterns. Regex intentionally simple & explicit so the failure
# messages point right at the offending token.
HTTP_VERB_RE = re.compile(r"\b(POST|GET|PUT|DELETE|PATCH)\b")
URL_PATH_RE = re.compile(r"(/v1/public|/api/v1|/\.well-known|/anchor/|/hcs10/|/marketplace/)")
SNAKE_CASE_FIELD_RE = re.compile(
    r"\b(?:project_id|agent_id|memory_id|content_hash|submitter_did|wallet_id|token_id)\b"
)


class TestVibeCoderPrompts:
    """Every prompt_as_vibe_coder(...) must read like a non-technical user.

    BDD-style: each method name describes the invariant it verifies.
    """

    def test_it_finds_prompts_in_the_workshop_script(self):
        prompts = _collect_vibe_coder_prompts()
        assert prompts, (
            "Expected prompt_as_vibe_coder(...) calls in workshop_e2e_test.py "
            "but none were found. Did the file move?"
        )

    @pytest.mark.parametrize("line_no,prompt", _collect_vibe_coder_prompts())
    def test_it_contains_no_http_verbs(self, line_no: int, prompt: str):
        match = HTTP_VERB_RE.search(prompt)
        assert match is None, (
            f"workshop_e2e_test.py:{line_no} vibe-coder prompt leaks HTTP verb "
            f"'{match.group(0) if match else ''}': {prompt!r}"
        )

    @pytest.mark.parametrize("line_no,prompt", _collect_vibe_coder_prompts())
    def test_it_contains_no_url_paths(self, line_no: int, prompt: str):
        match = URL_PATH_RE.search(prompt)
        assert match is None, (
            f"workshop_e2e_test.py:{line_no} vibe-coder prompt leaks URL path "
            f"'{match.group(0) if match else ''}': {prompt!r}"
        )

    @pytest.mark.parametrize("line_no,prompt", _collect_vibe_coder_prompts())
    def test_it_contains_no_snake_case_field_names(self, line_no: int, prompt: str):
        match = SNAKE_CASE_FIELD_RE.search(prompt)
        assert match is None, (
            f"workshop_e2e_test.py:{line_no} vibe-coder prompt leaks snake_case field "
            f"'{match.group(0) if match else ''}': {prompt!r}"
        )
