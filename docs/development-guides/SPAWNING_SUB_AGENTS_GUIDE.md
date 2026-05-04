# Spawning Sub-Agent Tasks — Developer Guide

## Problem

When the main session spawns sub-agents via `mcp__ccd_session__spawn_task`, the Task tool, or similar mechanisms, the sub-agent reads the project context file on start but does NOT automatically receive:

- The Cody persona and identity rules (`.ainative/CODY.md`)
- The Red → Green → Refactor 3-commit cadence (`.ainative/RULES.MD`, section 12)
- The PR evidence requirement (`.claude/skills/mandatory-tdd/SKILL.md`)

**Observed result (PRs #349, #350, #351):** sub-agents mix test + implementation into single commits, skip refactor commits, and omit test output from PR descriptions.

## Solution: Always Prepend the Preamble

Every sub-agent task prompt MUST start with this block:

```
## AINative Cody Task Preamble
Read and follow `.ainative/SPAWN_TASK_PREAMBLE.md` before any action.
You are Cody. Red → Green → Refactor. PR evidence mandatory.
```

The full boilerplate lives in `.ainative/SPAWN_TASK_PREAMBLE.md` (9 sections).

## Example: Spawning a Compliant Sub-Agent

```python
task_prompt = """
## AINative Cody Task Preamble
Read and follow `.ainative/SPAWN_TASK_PREAMBLE.md` before any action.
You are Cody. Red → Green → Refactor. PR evidence mandatory.

---

## Task: Fix ZeroDB mock mode short-circuit — Refs #345

The `query_rows` call in mock mode hits the network instead of
returning fixture data. Fix it so that when ZERODB_MOCK_MODE=true,
the endpoint returns mock fixtures without making any HTTP calls.

## Acceptance Criteria
- [ ] `ZERODB_MOCK_MODE=true` returns fixture data
- [ ] No HTTP calls made in mock mode (verify with spy)
- [ ] Tests follow `class Describe* / def it_*` style
- [ ] Three commits: test: → fix: → refactor:
- [ ] Coverage >= 80% with actual pytest output in PR
"""
```

## Expected Commit Sequence

```
test: red tests for ZeroDB mock mode short-circuit — Refs #345
fix: short-circuit query_rows when ZERODB_MOCK_MODE=true — Refs #345
refactor: extract mock_fixture_response helper — Refs #345
```

## PR Evidence Block (Required)

The spawned agent MUST include this in the PR description:

```
## Test Execution Evidence

### Command Run:
`python3 -m pytest tests/test_zerodb_mock.py -v --cov=app.services.zerodb --cov-report=term-missing`

### Output:
test_returns_fixture_data_in_mock_mode PASSED              [ 25%]
test_no_http_calls_in_mock_mode PASSED                     [ 50%]
test_real_mode_still_hits_network PASSED                   [ 75%]
test_env_var_toggle_works PASSED                           [100%]
==================== 4 passed in 0.31s ====================

### Coverage Report:
app/services/zerodb.py    87    11    87%
```

## Enforcement

- **Parent session:** always prepend the preamble when spawning.
- **Sub-agent:** read `.ainative/SPAWN_TASK_PREAMBLE.md` as the first action.
- **PR review:** any PR from a spawned agent missing 3-commit cadence or test evidence is returned for correction.

## References

- Full boilerplate: `.ainative/SPAWN_TASK_PREAMBLE.md`
- Rules reference: `.ainative/RULES.MD` section 12
- TDD skill: `.claude/skills/mandatory-tdd/SKILL.md`
- Issue: [#353](https://github.com/AINative-Studio/Agent-402/issues/353)
