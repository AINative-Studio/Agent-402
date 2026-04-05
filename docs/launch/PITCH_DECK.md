# Agent-402 — Pitch Deck
## HederaCon / Consensus 2026

**Auditable · Replayable · Agent-Native Finance on Hedera**

Built by AINative Studio

---

## Slide 1 — The Problem

### AI Agents Today Are Broken for Regulated Domains

| Gap | Reality |
|-----|---------|
| Stateless | Agents have no persistent memory across runs |
| Unverifiable | No cryptographic proof of what an agent did or why |
| Non-repudiable | Actions cannot be audited or attributed |
| Financially blind | Agents cannot safely move money without human-in-the-loop |
| Unsafe for compliance | No audit trail for KYC/KYT, no replay capability |

**Result:** AI agents are locked out of fintech, DeFi, and regulated enterprise workflows.

> "You cannot put an AI agent in a compliance workflow you cannot audit."
> — Every regulated entity evaluating autonomous AI

---

## Slide 2 — The Solution

### Agent-402: The Infrastructure Layer for Trusted Autonomous Finance

Agent-402 provides everything a regulated AI agent needs to operate with full accountability:

- **HCS-anchored memory** — every decision is hash-anchored to Hedera Consensus Service
- **On-chain identity** — agents hold Hedera DID + HTS NFT credentials
- **Trustless payments** — USDC via HTS, X402-signed, sub-3 second finality
- **Reputation system** — on-chain feedback with exponential recency decay
- **Deterministic replay** — any run can be reconstructed from ZeroDB + HCS logs

One SDK. One runtime. Full auditability.

---

## Slide 3 — Architecture

```
+───────────────────────────────────────────────────────+
│                   CrewAI Agent Crew                   │
│  analyst · compliance_agent · transaction_agent       │
│  Capabilities: finance, KYT, X402, memory, identity   │
+────────────────────┬──────────────────────────────────+
                     │
                     ▼
+────────────────────────────────────────────────────────+
│              Agent-402 FastAPI Backend                 │
│  /v1/agents  /v1/identity  /v1/hedera/payments         │
│  /v1/reputation  /v1/hcs  /v1/marketplace              │
│  X402 Protocol: /.well-known/x402  /x402               │
+──────┬─────────────┬──────────────┬─────────────────────+
       │             │              │
       ▼             ▼              ▼
+──────────+  +──────────────+  +──────────────────────+
│ ZeroDB   │  │    Hedera    │  │  Circle / USDC        │
│ Vectors  │  │  HCS topics  │  │  Gateway (fallback)   │
│ Memory   │  │  HTS tokens  │  +──────────────────────+
│ Ledgers  │  │  DID / HCS-10│
│ Tables   │  │  Reputation  │
+──────────+  +──────────────+
       │
       ▼
+──────────────────────────────────────────────────────+
│            AINative SDKs                             │
│  @ainative/react-sdk  @ainative/next-sdk              │
│  @ainative/svelte-sdk  @ainative/vue-sdk              │
│  hedera-agent-kit plugin                             │
+──────────────────────────────────────────────────────+
```

**Key integration points:**
- Hedera HCS (Consensus Service) — memory anchoring, reputation, HCS-10 discovery
- Hedera HTS (Token Service) — USDC payments, agent identity NFTs
- Hedera DID — W3C-compliant decentralised identifiers for agents
- ZeroDB — vector memory, audit ledgers, agent profiles, immutable records

---

## Slide 4 — Key Features

### What Makes Agent-402 Different

**1. HCS-Anchored Memory**
Every agent decision is persisted in ZeroDB and its SHA-256 hash is submitted to a Hedera HCS topic. Tamper-evident by construction. Mirror node URL included for independent verification.

**2. On-Chain Identity**
Each agent mints an HTS NFT token class on creation. The token encodes agent capabilities, role, and DID. Transferable, revocable, verifiable — the agent passport for the autonomous economy.

**3. Reputation System**
Feedback submitted to per-agent HCS topics. Score calculated with exponential recency decay (half-life: 30 days). Trust tiers: NEW → BASIC → TRUSTED → VERIFIED → ESTABLISHED.

**4. Trustless X402 Payments**
Agents initiate cryptographically signed USDC transfers via HTS. Sub-3 second finality. Every payment linked to agent_id, task_id, and run_id for full audit trail.

**5. Trustless Runtime**
Deterministic replay from ZeroDB + HCS history. Any run can be reconstructed without re-executing the agent. Non-repudiation via ECDSA/Ed25519 signatures.

---

## Slide 5 — Demo Highlights (5 Minutes)

### Live Workflow at Consensus 2026

Run: `python scripts/demo_consensus_2026.py`

| Step | Action | Hedera Feature |
|------|--------|----------------|
| 1 | Create agent profile | ZeroDB agent table |
| 2 | Register identity | HTS NFT token class |
| 3 | Execute X402 payment (1 USDC) | HTS USDC transfer |
| 4 | Anchor memory to blockchain | HCS topic message |
| 5 | Submit + calculate reputation | HCS feedback + decay score |
| 6 | Search agent marketplace | HCS-14 directory query |

**What the audience sees:**
- Coloured step-by-step console output
- Real Hedera transaction IDs (testnet)
- Sub-3 second payment confirmation
- Mirror node URLs for independent verification
- Reputation score with trust tier

---

## Slide 6 — Market Opportunity

### The Autonomous Agent Economy is Coming

| Segment | Use Case | Pain Point We Solve |
|---------|----------|---------------------|
| **Fintech / Neobanks** | Autonomous compliance agents | No audit trail, no replay |
| **DeFi protocols** | On-chain agent governance | No identity, no accountability |
| **Enterprise AI** | Regulated workflow automation | Cannot prove what AI did |
| **Hedera ecosystem** | Agent-native dApps | No agent SDK for HCS/HTS |
| **Compliance tech** | Automated KYT/AML monitoring | No cryptographic attestation |

**Total Addressable Market:**
- Enterprise AI automation: $50B+ by 2027
- Compliance tech: $35B+ by 2027
- Agent-native finance: emerging category, first-mover advantage

**Hedera advantage:** Sub-3 second finality, predictable fee structure, enterprise governance — the only L1 suitable for regulated agent workflows.

---

## Slide 7 — Team

### AINative Studio

A team of engineers, protocol designers, and AI practitioners building the infrastructure layer for the autonomous agent economy.

**Expertise:**
- Multi-agent system design (CrewAI, LangGraph)
- Hedera SDK integration (HCS, HTS, DID)
- ZeroDB / vector database architecture
- X402 protocol and cryptographic request signing
- Fintech compliance and audit systems

**What we have shipped:**
- Agent-402 backend (Python / FastAPI) — 4 sprints, 200+ tests
- ZeroDB integration (vectors, memory, ledgers, tables)
- Full Hedera integration: wallets, payments, identity, reputation, HCS anchoring
- AINative SDK packages (React, Next.js, Svelte, Vue)
- OpenConvAI HCS-10 agent coordination protocol

---

## Slide 8 — The Ask

### Hedera Grant + Ecosystem Partnership

**Grant Request:**
- Hedera HBAR Foundation development grant
- Scope: production hardening, mainnet deployment, compliance pilot
- Deliverable: first production-ready agent finance infrastructure on Hedera

**Ecosystem Partnership:**
- Co-marketing for Consensus 2026 launch
- Hedera developer documentation feature (agent SDK guide)
- Access to Hedera enterprise customer introductions (compliance / fintech)
- Mirror node access for production verification workloads

**What Hedera Gets:**
- First production multi-agent finance stack on Hedera
- Reference implementation for HCS-10, HTS identity, X402 on Hedera
- Open-source SDK contribution to the Hedera ecosystem
- Live Consensus 2026 demo showcasing Hedera's speed and finality

---

## Contact

**AINative Studio**
Website: https://ainative.studio
GitHub: https://github.com/ainative
Demo: `python scripts/demo_consensus_2026.py`

Built by AINative Dev Team
Refs #250
