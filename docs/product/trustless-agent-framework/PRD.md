# PRD: Trustless Autonomous Agent Framework (ERC-8004 + x402)

**Status:** Planning
**Audience:** Engineering, Protocol, Agent Runtime, Infra
**Primary Goal:** Enable lightweight, gas-minimal, trustable, self-governing autonomous agents anchored to blockchain trust primitives but operating off-chain.

---

## 1. Problem Statement

AI agents today suffer from three fundamental trust problems:

1. **No portable identity** – agents cannot be reliably discovered or verified across organizations.
2. **No credible reputation** – feedback is centralized, spoofable, or siloed.
3. **No economic trust** – agents cannot safely pay or get paid autonomously without accounts, subscriptions, or custom integrations.

Existing agent protocols (MCP, A2A) solve *communication*, but **not trust**.

Blockchain can solve trust — but **direct on-chain execution is too expensive, slow, and complex** for agent systems.

---

## 2. Product Vision

Build a **Trustless Agent Framework** where:

* Agents are **discoverable, verifiable, and reputation-scored**
* Trust is **anchored on-chain** but **enforced off-chain**
* Payments are **frictionless, per-request, and autonomous**
* Gas usage is **near zero**
* Agents are **self-governing**, not DAO-governed
* The system works for **low-risk and high-risk tasks** via progressive trust

> Ethereum is used as a **court record**, not a runtime.

---

## 3. Core Design Principles

1. **On-chain minimalism**
   Blockchain stores *identity pointers, events, and hashes only*.

2. **Off-chain intelligence**
   Agents run, reason, learn, and govern themselves off-chain.

3. **Gasless by default**
   End users never pay gas. Agents only write checkpoints.

4. **Trust via verifiability, not belief**
   Every trust signal can be independently verified.

5. **No governance theater**
   No DAOs, no voting tokens, no human-in-the-loop unless required.

---

## 4. System Overview

### High-Level Components

1. **Identity Registry (On-Chain)**
2. **Reputation Registry (On-Chain, Event-Driven)**
3. **Validation Registry (On-Chain, Event-Driven)**
4. **Agent Runtime (Off-Chain)**
5. **Payment & Economic Layer (x402, Off-Chain HTTP)**
6. **Indexers & Reputation Aggregators (Off-Chain)**

---

## 5. Agent Identity (ERC-8004 Based)

### Purpose

Provide each agent with a **globally unique, censorship-resistant identity**.

### Requirements

* Each agent has:
  * A unique `agentId` (ERC-721 token)
  * A resolvable `agentURI`
* `agentURI` points to an **Agent Registration File** (JSON)
* The registration file advertises:
  * Agent name, description
  * Supported endpoints (MCP, A2A, HTTP)
  * Supported trust models
  * Whether x402 payments are supported

### Non-Goals

* No on-chain storage of agent logic
* No on-chain execution of agent tasks

---

## 6. Agent Runtime (Off-Chain)

Each agent runs as an autonomous service with:

* A cryptographic identity (EIP-712 signer)
* Local or distributed memory
* A policy engine for self-governance
* Access to blockchain indexers
* Optional validator integrations

### Self-Governance Policy

Each agent maintains a signed policy file defining:

* Minimum acceptable reputation
* Validator requirements for high-risk tasks
* Auto-shutdown or self-degradation rules
* Upgrade and recovery behavior

The agent enforces this policy itself.

---

## 7. Reputation System

### Purpose

Allow anyone to evaluate agents while preventing spam and Sybil attacks.

### On-Chain Responsibilities

* Store immutable feedback events
* Never compute scores or rankings
* Allow filtering by reviewer, tag, endpoint

### Off-Chain Responsibilities

* Aggregate feedback
* Weight feedback by economic proof
* Detect spam and collusion
* Publish derived reputation scores

### Key Insight

> Reputation is **public data**, but **interpretation is competitive**.

---

## 8. Payments & Economic Trust (x402 Integration)

### Why x402 Is Used

x402 enables:

* Per-request payments
* Agent-to-agent commerce
* No accounts or subscriptions
* Native fit for HTTP-based agents

### How x402 Is Used

* Agents return **HTTP 402** when payment is required
* Client retries with a valid payment receipt
* Agent executes the task

### Critical Design Choice

**Payments are NOT written on-chain by default.**

Instead:

* Payment receipts are stored off-chain
* Receipts are referenced in reputation feedback
* Optional batch commitments (Merkle roots) can be written on-chain

### Why This Matters

* Economic proof becomes a **trust signal**
* Paid interactions are harder to fake
* Reputation backed by payment is stronger

---

## 9. Reputation + Payment Coupling

### Trust Model

Feedback may optionally include:

* Proof of payment
* Task metadata
* Capability used
* Outcome

Reputation aggregators may:

* Weight paid feedback higher
* Ignore unpaid feedback entirely
* Create "economically trusted" scores

This avoids staking, slashing, or DAOs.

---

## 10. Validation System

### Purpose

Enable independent verification for high-risk tasks.

### Validation Types

* Re-execution by staked validators
* TEE attestations
* zkML proofs
* Human or institutional judges (optional)

### On-Chain Role

* Record validation requests
* Record validation responses
* Timestamp outcomes

### Off-Chain Role

* Perform actual validation
* Store proofs
* Handle incentives and penalties

---

## 11. Progressive Trust Tiers

| Tier   | Requirements         | Example Use          |
| ------ | -------------------- | -------------------- |
| Tier 0 | Identity only        | Discovery            |
| Tier 1 | Reputation           | Content, data lookup |
| Tier 2 | Reputation + Payment | APIs, tools          |
| Tier 3 | Validation           | Financial actions    |
| Tier 4 | zk/TEE               | Medical, legal       |

Agents declare which tiers they support.

---

## 12. Gas & Cost Strategy

### Requirements

* No per-interaction gas
* No end-user wallets required
* Rare on-chain writes only

### Techniques

* Sponsored transactions
* Batched reputation commits
* Event-only registries
* Optional L2 deployment

---

## 13. Security & Threat Model

### Known Risks

* Sybil attacks
* Fake agents
* Collusive feedback

### Mitigations

* Economic proof via x402
* Validator diversity
* Public auditability
* Agent self-shutdown policies

---

## 14. Non-Goals (Explicit)

* No agent logic on Ethereum
* No DAO governance
* No universal scoring algorithm
* No forced monetization
* No requirement to use x402 for all agents

---

## 15. Success Criteria

The system is successful if:

* Agents can autonomously buy and sell services
* Trust can be evaluated without prior relationships
* Gas costs are negligible
* Multiple reputation systems can coexist
* Agents can self-govern without human intervention

---

## 16. Deliverables for Engineering

This PRD should translate into:

* Protocol contracts (minimal)
* Agent runtime SDK
* x402 integration module
* Indexer & reputation services
* Validator interfaces
* Example agent implementations

---

## 17. Summary (The Essence)

> **Agents live off-chain.**
>
> **Truth lives on-chain.**
>
> **Payments create trust without governance.**
>
> **Reputation emerges, it is not dictated.**

---

## Next Steps

Recommended follow-up deliverables:

* Convert this into **Epics + User Stories**
* Produce a **v1 "Trustless Agent Lite" scope**
* Define a **reference agent runtime spec**
* Create a **build order roadmap (Week 1 → Week 6)**
