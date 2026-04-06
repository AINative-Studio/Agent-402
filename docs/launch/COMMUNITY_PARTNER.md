# Hedera Community Partner Application

**Organisation:** AINative Studio
**Application Type:** Hedera Ecosystem Community Partner
**Date:** April 2026

Built by AINative Dev Team
Refs #252

---

## 1. Organisation Information

**Name:** AINative Studio

**Description:**
AINative Studio is a developer-first AI infrastructure company building the tooling, SDKs, and runtime environments for the autonomous agent economy. We build open-source infrastructure that enables AI agents to operate in regulated, accountable, and financially-capable environments.

**Website:** https://ainative.studio

**GitHub:** https://github.com/ainative

**Primary Contact:** AINative Dev Team — hello@ainative.studio

**Location:** Remote / Distributed

---

## 2. Contribution to the Hedera Ecosystem

### What We Have Built on Hedera

AINative Studio has built the first production-ready multi-agent finance infrastructure stack on Hedera, covering every major Hedera service:

| Hedera Service | AINative Contribution |
|---------------|----------------------|
| **HCS (Consensus Service)** | Memory anchoring, reputation feedback ledgers, HCS-10 agent messaging, HCS-14 directory protocol |
| **HTS (Token Service)** | USDC payment infrastructure (sub-3s finality), agent identity NFT token classes |
| **DID (did:hedera)** | W3C DID integration for agent identity, Ed25519 signature verification |
| **Mirror Node** | Transaction receipt verification, HCS topic message retrieval, audit trail reconstruction |

### Open Source Repositories

- **Agent-402** — full Hedera agent finance backend (FastAPI, Python)
  - `HederaWalletService` — account creation, USDC token association
  - `HederaPaymentService` — HTS USDC transfers, X402 protocol integration
  - `HederaIdentityService` — HTS NFT identity, AAP capability mapping
  - `HederaReputationService` — HCS-anchored feedback and score calculation
  - `HCSAnchoringService` — SHA-256 memory integrity anchoring to HCS topics
  - `HCS14DirectoryService` — HCS-14 agent discovery and registration
  - `OpenConvAI` coordination, messaging, and audit services (HCS-10)

- **hedera-agent-kit plugin** — TypeScript plugin for Node.js AI agent frameworks
- **AINative SDKs** — React, Next.js, Svelte, Vue SDKs with Hedera identity support

### Reference Implementations

1. **5-Minute Demo** (`scripts/demo_consensus_2026.py`) — end-to-end Hedera agent workflow
2. **Integration Tests** (`backend/app/tests/test_hedera_integration_e2e.py`) — comprehensive mocked E2E test suite
3. **X402 on Hedera** — signed payment requests with Hedera DID verification

---

## 3. Community Engagement Plan

### Developer Education

**Documentation contributions:**
- Hedera developer portal: agent infrastructure quickstart guide
- HCS-10 messaging implementation guide with Agent-402 as reference
- HTS identity patterns for AI agents (W3C DID + NFT approach)
- X402 protocol integration guide for Hedera payments

**Video content:**
- 5-minute demo video: "AI Agent Makes a Payment on Hedera" (Consensus 2026)
- Tutorial series: "Building Agent-Native Finance on Hedera" (3 parts)
- Live coding stream: "From Zero to Hedera Agent in 30 Minutes"

**Workshops:**
- Consensus 2026 developer workshop: "Agent-402 Hands-On Lab"
- HederaCon lightning talk: "The Autonomous Agent Economy on Hedera"
- Monthly community calls: Hedera agent infrastructure updates

### Open Source Engagement

**Contributions:**
- Hedera SDK Python — issue reports, documentation PRs, example improvements
- HCS-10 specification — reference implementation and edge case documentation
- Hedera community forum — regular posts on agent infrastructure patterns

**Events:**
- Hackathon sponsorship / mentorship (Hedera x AI category)
- ETH Denver, TOKEN2049: Hedera agent infrastructure presentations
- Consensus 2026: live demo booth

### Developer Support

- GitHub Discussions on Agent-402 repo for community Q&A
- Discord channel: #agent402 in the AINative community server
- Office hours (bi-weekly, open to all developers)
- Issue tracking public — all bugs and feature requests visible

---

## 4. Developer Resources Provided

### SDKs

| Package | Language | Status |
|---------|----------|--------|
| `@ainative/react-sdk` | TypeScript/React | Production |
| `@ainative/next-sdk` | TypeScript/Next.js | Production |
| `@ainative/svelte-sdk` | TypeScript/Svelte | Production |
| `@ainative/vue-sdk` | TypeScript/Vue 3 | Production |
| `hedera-agent-kit` | TypeScript/Node.js | Beta |
| `agent402-sdk` | Python | In development |

### Documentation

All documentation is open source and available at:

- `docs/launch/PITCH_DECK.md` — architecture overview and key features
- `docs/launch/GRANT_APPLICATION.md` — detailed technical approach
- `docs/api/` — full REST API specification
- `docs/development-guides/` — developer guides for Hedera integration
- `docs/sdk/` — SDK quickstart and API reference

### Plugins

- **hedera-agent-kit** — drop-in plugin for CrewAI, LangGraph, and AutoGen agents to interact with Hedera HCS, HTS, and DID
- **ZeroDB MCP tools** — 76+ MCP tools for agent memory and vector search
- **OpenClaw integration** — multi-agent swarm orchestration with Hedera identity

---

## 5. Why AINative Studio Should Be a Hedera Community Partner

### Alignment with Hedera's Mission

Hedera's mission is to build a fair, trustworthy internet. AINative Studio's mission is to make AI agents trustworthy and accountable. The overlap is exact: we are building the accountability infrastructure for AI on top of Hedera's trust infrastructure.

### Demonstrated Commitment

We have shipped four sprints of production-quality Hedera integration — not a demo, not a proof of concept. Real services, real tests (200+), real architecture. We are committed to Hedera as the foundational trust layer for Agent-402.

### Ecosystem Multiplier Effect

Every developer who uses Agent-402 is a developer using Hedera. Every agent deployed with Agent-402 is an agent generating HCS, HTS, and DID transactions on Hedera. Our growth is Hedera's growth.

### New Developer Category

AI developers do not typically know Hedera. Agent-402 and our SDKs are the bridge between the AI developer community (Python/TypeScript, CrewAI/LangGraph) and the Hedera ecosystem. We bring a new, large, and rapidly growing developer population to Hedera.

---

## 6. Partnership Requests

As a Hedera Community Partner, AINative Studio requests:

- **Technical access:** Mirror node API access for production verification workloads
- **Co-marketing:** Joint announcement at Consensus 2026
- **Documentation:** Featured placement in Hedera developer portal (agent use case section)
- **Feedback:** Early access to Hedera SDK updates relevant to agent infrastructure
- **Community:** Invitation to Hedera ecosystem partner Slack/Discord channels

---

## 7. Commitment

AINative Studio commits to:

- Maintaining Agent-402 as an open-source, actively developed project
- Contributing documentation improvements to the Hedera developer portal (minimum 2 per quarter)
- Presenting at least one Hedera community event per quarter
- Providing prompt, accurate responses to community questions about Hedera integration
- Following Hedera's community guidelines and code of conduct
- Notifying the Hedera foundation of any security issues found in Hedera SDKs before public disclosure

---

*AINative Studio · April 2026 · Built by AINative Dev Team*
