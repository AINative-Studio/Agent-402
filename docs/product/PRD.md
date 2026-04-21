# 📘 Product Requirements Document (PRD – MVP)

## Product Name

**Autonomous Fintech Agent Crew**
**(AINative Edition: CrewAI × X402 × ZeroDB × AIKit)**

---

## 1. Objective & Vision

The goal of this MVP is to demonstrate an **auditable, agent-native fintech workflow** using autonomous AI agents that can securely discover, authenticate, and interact with financial services via the **X402 protocol**.

This project proves that **CrewAI-orchestrated agents**, combined with **cryptographically signed requests**, **persistent agent memory**, and **standardized tool abstraction**, can form the foundation of a **real-world, decentralized fintech agent system**.

This MVP is intentionally scoped for:

* Hackathon demoability
* Technical credibility
* Reproducibility and auditability
* Clear extensibility into real fintech infrastructure

---

## 2. Problem Statement

Most AI agent demos today are:

* Stateless
* Non-verifiable
* Impossible to audit or replay
* Unsuitable for regulated domains like fintech

Without **persistent memory**, **signed request ledgers**, and **compliance traceability**, agent systems cannot realistically participate in financial workflows.

This MVP addresses that gap directly.

---

## 3. Solution Overview (MVP)

This MVP delivers:

* A **multi-agent CrewAI system** running locally
* A **FastAPI server** implementing the X402 protocol
* **DID-based request signing and verification**
* **Persistent agent memory and audit logs** via ZeroDB
* **Reusable, traceable agent tools** via AIKit
* **Replayable agent workflows**

The result is a **provable, inspectable, fintech-ready agent workflow**.

---

## 4. In-Scope (MVP Only)

### What Stays the Same (Core Design)

The following elements are intentionally unchanged to preserve scope and velocity:

* CrewAI agent orchestration (open-source, local runtime)
* X402 protocol usage and semantics
* FastAPI server exposing:

  * `/.well-known/x402`
  * `/x402` signed POST endpoint
* DID + ECDSA signing flow
* Mock fintech simulation:

  * Market quote
  * Compliance check
  * Transaction execution
* Single-command demo execution

**AINative augments this system — it does not replace or complicate it.**

---

## 5. Agent Personas (MVP)

| Agent             | Role            | Responsibility                                   |
| ----------------- | --------------- | ------------------------------------------------ |
| Analyst Agent     | Market Analysis | Fetches mock market data and evaluates viability |
| Compliance Agent  | Risk & KYC      | Simulates KYC/KYT checks and risk scoring        |
| Transaction Agent | Execution       | Signs and submits X402 requests to the server    |

Each agent has:

* A DID
* A clearly defined task scope
* Access to shared AIKit tools
* **Persistent memory stored in ZeroDB**
* **Local CrewAI execution for reproducibility**

---

## 6. CrewAI Runtime Integration (Explicit MVP Requirement)

### Local-First Execution

CrewAI **must run locally** as part of the MVP. This ensures:

* Deterministic demos
* Reproducible workflows
* Debuggable agent behavior
* CI-compatible testing

CrewAI is treated as a **runtime dependency**, not a hosted service.

### CrewAI Responsibilities

* Agent orchestration
* Task sequencing
* Tool invocation
* Passing structured outputs to ZeroDB

---

## 7. ZeroDB Integration (Core MVP Upgrade)

### Purpose

ZeroDB transforms the project from a demo into a **fintech-credible backend** by providing:

* Persistent agent memory
* Signed request ledgers
* Compliance auditability
* Workflow replay
* Deterministic observability

---

### ZeroDB Collections (Minimal MVP)

#### 1. Agent Profiles

**Collection:** `agents`

Stores:

* Agent ID
* DID
* Role
* Creation metadata

---

#### 2. Agent Memory

**Collection:** `agent_memory`

Stores:

* Agent ID
* Task ID
* Input summary
* Output summary
* Confidence / rationale
* Timestamp

Enables:

* Cross-run memory
* Decision improvement
* Replay

---

#### 3. Compliance Events

**Collection:** `compliance_events`

Stores:

* Agent ID
* Subject
* Risk score
* Pass / fail
* Reason
* Timestamp

Supports:

* Audit
* Explainability
* Regulated workflows

---

#### 4. X402 Request Ledger

**Collection:** `x402_requests`

Stores immutable records of:

* DID
* Signature
* Payload
* Verification result
* Server response
* Timestamp

This ledger provides **non-repudiation** and is central to demo credibility.

---

## 8. AIKit Integration (MVP Scope)

### Purpose

AIKit standardizes agent tooling while keeping the system lightweight and portable.

---

### AIKit Tool: `x402.request`

The custom X402 request logic is wrapped as an **AIKit Tool Primitive**:

```text
AIKit.Tool(
  name = "x402.request",
  schema = { did, signature, payload },
  runtime = "fastapi"
)
```

### Benefits

* Shared across all agents
* Automatically traced and logged
* Backend-swappable (mock → real fintech API)
* Portable across CLI, server, or future UI

---

### Agent Scaffolding

* Agents are defined declaratively
* CrewAI consumes AIKit tools
* Future-ready for IDE, CLI, or web execution

---

## 9. System Architecture (MVP)

```
+------------------------------+
|        CrewAI Agents         |
|------------------------------|
| analyst                      |
| compliance_agent             |
| transaction_agent            |
|------------------------------|
| Tools                        |
| - AIKit x402.request         |
| - Market Data Tool           |
+--------------+---------------+
               |
               v
+------------------------------+
|     X402 FastAPI Server      |
|------------------------------|
| /.well-known/x402            |
| /x402 (signed POST)          |
|                              |
| Signature Verification       |
| Payload Validation           |
+--------------+---------------+
               |
               v
+------------------------------+
|           ZeroDB             |
|------------------------------|
| agents                       |
| agent_memory                 |
| compliance_events            |
| x402_requests (ledger)       |
+------------------------------+
```

---

## 10. Deliverables (MVP)

* ✅ CrewAI project with agents & tasks (local runtime)
* ✅ FastAPI X402 server
* ✅ ZeroDB schema with minimal collections
* ✅ AIKit `x402.request` tool
* ✅ One-command demo run
* ✅ Logs or screenshot showing:

  * Verified DID
  * Stored signed request
  * Replayable agent workflow

---

## 11. Testing & Verification (MVP)

### Exact Smoke Test (Required)

A single script must:

1. Run the full agent workflow
2. Persist memory to ZeroDB
3. Verify X402 signature
4. Write to the request ledger
5. Replay the workflow deterministically

If documented behavior changes, the smoke test **must fail**.

---

## 12. Success Criteria

This MVP is successful if:

* Signed X402 requests are verified
* Agent decisions persist across runs
* Compliance results are auditable
* Full agent workflow can be replayed
* Demo runs cleanly in under 5 minutes
* Behavior matches documented defaults exactly

---

## 13. Strategic Positioning

This MVP demonstrates:

> **The first auditable, agent-native fintech workflow built on open protocols.**

It positions AINative as foundational infrastructure for:

* Autonomous finance
* Agent compliance
* Agent marketplaces
* Regulated AI systems

---

## 14. Build Guidance (Intentional Constraints)

* Do not overbuild
* Use minimal ZeroDB collections
* Implement only one AIKit tool
* Optimize for clarity, not completeness
* Treat documentation as a contract

---

## 15. Workshop Curriculum Readiness (Consensus 2026)

Agent-402 ships with a workshop curriculum targeting **Consensus 2026**. The curriculum is a first-class deliverable of the MVP and is subject to the same acceptance-criteria discipline as the code.

### 15.1 Scope

Three 50-minute tutorials, each runnable against `localhost:8000` in the workshop's default mock mode:

1. `docs/workshop/tutorials/01-identity-and-memory.md` — agent creation, Hedera identity (HTS NFT + did:hedera), cognitive memory (remember/recall/reflect), HCS anchor
2. `docs/workshop/tutorials/02-payments-and-trust.md` — Hedera wallets, USDC association, USDC payments, payment verification, reputation feedback
3. `docs/workshop/tutorials/03-discovery-and-marketplace.md` — HCS-14 directory, HCS-10 messaging, marketplace publish/browse/search

Supporting materials:
- `docs/workshop/VIBE_CODER_GUIDE.md` — prerequisites, setup, AI-assistant patterns
- `docs/workshop/GLOSSARY.md` — plain-English definitions of all Hedera/Agent-402 terminology
- `docs/workshop/TROUBLESHOOTING.md` — common errors and recovery
- `scripts/workshop_e2e_test.py` — automated checkpoint orchestrator
- `scripts/workshop_smoke_test.py` — pre-workshop sanity check

### 15.2 Personas (binding)

- **Developer** — may run commands, inspect files, debug. Expected to complete all 3 tutorials in 90 minutes.
- **Vibe Coder** — natural-language prompts to an AI assistant only; MUST NOT write code, edit files, or run bash directly. Expected to complete all 3 tutorials in 120 minutes.

A tutorial step that forces a vibe coder to break persona (write code, edit files, run bash) is a **curriculum defect** and MUST be rewritten.

### 15.3 Acceptance Criteria

- [ ] `python3 scripts/workshop_e2e_test.py --persona developer --tutorial all` exits 0 with **≥ 95%** of checkpoints passing
- [ ] `python3 scripts/workshop_e2e_test.py --persona vibe-coder --tutorial all` matches the developer checkpoint count
- [ ] No tutorial step requires a vibe-coder to write or edit code (persona integrity)
- [ ] All tutorial steps return HTTP 2xx in mock mode — no ZeroDB or Hedera credentials required for the happy path
- [ ] `GET /.well-known/x402` includes Hedera metadata (usdc_token_id, mirror_node_url, supported_dids)
- [ ] `GET /anchor/{memory_id}/verify` returns accurate results — `verified: true` only when the anchor matches; `verified: false` for unknown or fabricated transaction_ids (no false positives)
- [ ] Each tutorial opens with a prerequisites block linking to `VIBE_CODER_GUIDE.md` and `GLOSSARY.md`
- [ ] Each step includes: a natural-language vibe-coder prompt, an expected JSON response block, a ✅ self-verification callout
- [ ] All documented API paths match registered FastAPI routes (enforced by the orchestrator's checkpoints and by `scripts/workshop_smoke_test.py`)

### 15.4 Recordings

- [ ] `asciinema` cast of developer run, total wall time ≤ 10 minutes
- [ ] `asciinema` cast of vibe-coder run, total wall time ≤ 12 minutes
- [ ] Both casts uploaded to asciinema.org with URLs in the top-level README and Luma event page
- [ ] At least one 2×-speed `agg`-rendered GIF ≤ 5 minutes embedded on the Luma event page

### 15.5 Regression Guards

- [ ] `scripts/workshop_smoke_test.py` exits 0 before every release tagged `consensus-2026-*`
- [ ] CI runs `scripts/workshop_e2e_test.py --persona developer --tutorial all` on every PR that changes `backend/app/`, `docs/workshop/`, or `scripts/workshop_*`
- [ ] Root `pytest.ini` preserves AINative BDD collection (`Describe*` classes, `it_*` functions) so workshop test suites collect
- [ ] New Hedera/ZeroDB client code paths MUST include regression tests against the checkpoints in 15.3
- [ ] Any PR that adds, renames, or removes an API route touched by the tutorials MUST update the corresponding tutorial step in the same PR

### 15.6 Change-Control

Any change that risks a §15.3 acceptance criterion — regardless of intent — requires:

1. The PR body references PRD §15.3 and calls out which criterion is affected
2. A before/after run of `scripts/workshop_e2e_test.py --persona developer --tutorial all` pasted in the PR body
3. If a checkpoint regresses: either the regression is fixed in the same PR, or a follow-up `bug/` issue is filed and linked **before merge**

### 15.7 Current State (as of 2026-04-20)

Live workshop status is tracked in `docs/workshop/test-results/CURRICULUM_WALKTHROUGH_20260419.md` and in open issues labelled with `epic-10` or `epic-15`. Baseline at this PRD version: **24/28 checkpoints passing (86%)**. Open issues to close before Consensus 2026: #337, #342, #346, #347, #348, #353, #356.

---

## Final Framing (Judges & Investors)

> **“We didn’t build a demo.
> We built the minimum viable foundation for agent-native finance.”**

---
