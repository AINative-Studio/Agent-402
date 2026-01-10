# 📘 Product Requirements Document (PRD – MVP)

## Product Name

**Autonomous Fintech Agent Crew**
*(AINative Edition: CrewAI × X402 × ZeroDB × AIKit)*

---

## 1. Objective & Vision

The goal of this MVP is to demonstrate an **auditable, agent-native fintech workflow** using autonomous AI agents that can securely discover, authenticate, and interact with financial services via the **X402 protocol**.

This project showcases how **CrewAI-orchestrated agents**, combined with **cryptographically signed requests**, **persistent agent memory**, and **tool abstraction**, can form the foundation of a real-world, decentralized fintech agent system.

This MVP is intentionally scoped for:

* Hackathon demoability
* Technical credibility
* Clear extensibility into real fintech infrastructure

---

## 2. Problem Statement

Most AI agent demos today are:

* Stateless
* Non-verifiable
* Impossible to audit or replay
* Unsuitable for regulated domains like fintech

Without persistent memory, signed request ledgers, and compliance traceability, agent systems cannot realistically participate in financial workflows.

---

## 3. Solution Overview (MVP)

This MVP delivers:

* A **multi-agent CrewAI system** with defined roles
* A **FastAPI server implementing the X402 protocol**
* **DID-based request signing and verification**
* **Persistent agent memory and audit logs** via **ZeroDB**
* **Reusable, traceable agent tools** via **AIKit**

The result is a **provable, replayable, fintech-ready agent workflow**.

---

## 4. In-Scope (MVP Only)

### What Stays the Same (Core Design)

The following are intentionally **unchanged** to preserve scope and velocity:

* **CrewAI** agent orchestration
* **X402 Protocol** usage and semantics
* FastAPI server with:

  * `/.well-known/x402`
  * `/x402` signed POST endpoint
* DID + ECDSA signing flow
* Mock fintech simulation:

  * Market quote
  * Compliance check
  * Transaction execution
* Single-command demo execution

AINative **augments** this system — it does not replace or complicate it.

---

## 5. Agent Personas (MVP)

| Agent             | Role            | Responsibility                                   |
| ----------------- | --------------- | ------------------------------------------------ |
| Analyst Agent     | Market Analysis | Fetches mock market data and evaluates viability |
| Compliance Agent  | Risk & KYC      | Simulates KYC/KYT checks and risk scoring        |
| Transaction Agent | Execution       | Signs and submits X402 requests to server        |

Each agent has:

* A DID
* A defined task scope
* Access to shared AIKit tools
* Persistent memory in ZeroDB

---

## 6. ZeroDB Integration (Core MVP Upgrade)

### Purpose

ZeroDB transforms the project from a demo into a **fintech-credible backend** by providing:

* Persistent agent memory
* Signed request ledgers
* Compliance auditability
* Workflow replay

---

### ZeroDB Collections (Minimal MVP)

#### Agent Profiles

**Collection:** `agents`

Stores identity and role metadata.

#### Agent Memory

**Collection:** `agent_memory`

Stores:

* Past decisions
* Confidence scores
* Context summaries

Enables agents to improve decisions across runs.

---

#### Compliance Events

**Collection:** `compliance_events`

Stores:

* KYC/KYT results
* Risk scores
* Pass/fail outcomes

Supports audit and explainability.

---

#### X402 Request Ledger

**Collection:** `x402_requests`

Stores immutable records of:

* DID
* Signature
* Payload
* Verification result
* Timestamp

This ledger is critical for **non-repudiation** and demo credibility.

---

## 7. AIKit Integration (MVP Scope)

### Purpose

AIKit standardizes agent tooling and execution while keeping the system lightweight.

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

**Benefits:**

* Shared across all agents
* Automatically traced and logged
* Swappable backend (mock → real fintech API)
* Portable across CLI, server, or future UI

---

### Agent Scaffolding

* Agents are defined declaratively
* CrewAI consumes AIKit tools
* Future-ready for IDE, CLI, or web execution

---

## 8. System Architecture (MVP)

![Image](https://admin.bentoml.com/uploads/crewai_bentoml_diagram_b9a2e1246a.png)

![Image](https://cdn.prod.website-files.com/64b7ba4dc9375b7b74b2135e/685a9e61ef3301306098c846_1.webp)

![Image](https://www.falkordb.com/wp-content/uploads/elementor/thumbs/AI-Agents-Architecture-by-falkordb-qwm0qxz4ufo0rgq34ti2jh09fp4771feaxtkfmld3o.webp)

![Image](https://media.geeksforgeeks.org/wp-content/uploads/20250722125643748319/ai_agent_memory-.webp)

```
+------------------------------+
|        CrewAI Agents         |
|------------------------------|
| analyst                      |
| compliance_officer           |
| transaction_agent            |
|------------------------------|
| Tools                        |
| - AIKit X402 Tool            |
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
| agent_memory                 |
| compliance_events            |
| x402_requests (ledger)       |
| transactions                 |
+------------------------------+
```

---

## 9. Deliverables (MVP)

* ✅ CrewAI project with agents & tasks
* ✅ FastAPI X402 server
* ✅ ZeroDB schema with minimal collections
* ✅ AIKit `x402.request` tool
* ✅ One-command demo run
* ✅ Logs or screenshot showing:

  * Verified DID
  * Stored signed request
  * Replayable agent flow

---

## 10. Success Criteria

This MVP is successful if:

* Signed X402 requests are verified
* Agent decisions persist across runs
* Compliance results are auditable
* Full agent workflow can be replayed
* Demo runs cleanly in under 5 minutes

---

## 11. Strategic Positioning

This MVP demonstrates:

> **The first auditable, agent-native fintech workflow built on open protocols.**

It positions AINative as foundational infrastructure for:

* Autonomous finance
* Agent compliance
* Agent marketplaces
* Regulated AI systems

---

## 12. Build Guidance (Intentional Constraints)

* Do **not** overbuild
* Use **minimal ZeroDB collections**
* Implement **only one AIKit tool**
* Optimize for clarity, not completeness

---

### Final Framing (Judges & Investors)

> “We didn’t build a demo.
> We built the minimum viable foundation for agent-native finance.”

---
