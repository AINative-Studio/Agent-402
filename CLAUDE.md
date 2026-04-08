# CLAUDE.md - Agent-402 (Autonomous Fintech Agent Crew)

## Project Overview

Agent-402 is an autonomous fintech agent system built with CrewAI, X402 protocol, ZeroDB, and AIKit. It demonstrates auditable, replayable, agent-native financial workflows where AI agents discover services, sign requests cryptographically, persist decisions, and produce audit-ready ledgers.

## Tech Stack

- **Language:** Python 3.x
- **Framework:** FastAPI (X402 protocol server)
- **Orchestration:** CrewAI (multi-agent)
- **Database:** ZeroDB (vectors, memory, ledgers, audit)
- **Protocol:** X402 (cryptographic request signing)
- **Blockchain:** Hedera (HCS-10, HTS, DID integration)
- **Payments:** Circle USDC (gateway integration)

## Development Practices

### TDD/BDD (Mandatory)

All code changes follow Red-Green-Refactor:
1. **Red:** Write failing tests first
2. **Green:** Minimal code to pass
3. **Refactor:** Improve with tests green

Minimum 80% test coverage. Tests must be actually executed with output included in PRs.

```bash
python3 -m pytest tests/ -v --cov --cov-report=term-missing
```

### Git Workflow

- Branch naming: `feature/{issue-id}-{slug}`, `bug/{issue-id}-{slug}`, `chore/{issue-id}-{slug}`
- Every commit references a GitHub issue (`Refs #123` or `Closes #123`)
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- **ZERO TOLERANCE:** No third-party AI attribution in commits/PRs/issues
- Use AINative branding: "Built by AINative Dev Team", "Built by Agent Swarm"

### Issue Tracking

- Create GitHub issue BEFORE writing any code
- Use issue templates: `[BUG]`, `[FEATURE]`, `[TEST]`, `[DOCS]`, `[REFACTOR]`
- Labels required: type, priority, status, component, effort
- Story points: Fibonacci (0, 1, 2, 3, 5, 8) - split stories >3 points

### File Placement Rules

- Documentation goes in `docs/` subdirectories, never in project root (except README.md and CLAUDE.md)
- Scripts go in `scripts/` directory
- No `.sh` files in `backend/` (except `start.sh`)

## Repository Structure

```
api/          - API definitions and contracts
app/          - Application entry points
backend/      - Backend service code
contracts/    - Smart contract definitions
docs/         - All documentation (api, reports, planning, etc.)
frontend/     - Frontend code
scripts/      - All utility and deployment scripts
tests/        - Test suites
```

## Key Commands

```bash
# Run smoke test
python tests/smoke_test.py

# Run full test suite
python3 -m pytest tests/ -v --cov --cov-report=term-missing

# Start X402 server
uvicorn server.main:app --reload

# Run demo
python scripts/run_demo.py
```

## Skills & Hooks

Skills are loaded from `.claude/skills/` (symlinked from core). Key skills:
- `mandatory-tdd` - TDD enforcement
- `git-workflow` - Git/PR standards
- `file-placement` - File organization rules
- `story-workflow` - Backlog management
- `code-quality` - Coding standards
- `delivery-checklist` - Pre-delivery verification

Git hooks installed in `.git/hooks/`:
- `pre-commit` - File placement validation
- `commit-msg` - Blocks third-party AI attribution

## Current Focus

Targeting **Consensus 2026** with Hedera integration across 5 sprints:
- Sprint 1: Agent SDK, Hedera Agent Kit Plugin, x402 on Hedera
- Sprint 2: Agent Identity (DID/HTS), Reputation system, Phase 2 payments
- Sprint 3: OpenConvAI (HCS-10), Memory Decay, OpenClaw agents
- Sprint 4: Marketplace, Real-Time Events, Threads, SDK Expansion, Billing, Trustless V1
- Sprint 5: Observability & Analytics — decision logging, anomaly detection, spend drift monitoring, webhooks, analytics dashboard, PRD acceptance tests
