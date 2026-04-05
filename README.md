# Agent-402: Autonomous Fintech Agent Crew

**AINative Edition: CrewAI x X402 x ZeroDB x Hedera**

> **Status:** Production-ready for Consensus 2026
> **Goal:** Auditable, replayable, agent-native finance on Hedera Hashgraph

---

## What This Is

Agent-402 is a **production-quality infrastructure stack** for autonomous AI agents operating in regulated financial environments.

It proves — with real cryptography, real Hedera transactions, and real audit trails — that autonomous AI agents can:

- Discover and call financial services (X402 protocol, HCS-14 directory)
- Cryptographically sign requests (ECDSA/Ed25519, DID:Hedera)
- Hold verifiable on-chain identity (HTS NFT token class)
- Execute trustless USDC payments (Hedera Token Service, sub-3s finality)
- Persist decisions with tamper-evident memory (ZeroDB + HCS anchoring)
- Build reputation transparently (on-chain feedback, HCS topics)
- Replay workflows deterministically (ZeroDB + HCS history)

This is **not a toy demo**. It is production-ready infrastructure for regulated, agent-driven finance.

---

## Why This Exists

Most AI agent deployments today are:

- Stateless — no memory across runs
- Non-verifiable — no cryptographic proof of actions
- Impossible to audit or replay
- Unsafe for regulated domains (fintech, compliance, healthcare)

Agent-402 changes that by combining:

- **Signed requests** — X402 protocol with DID-based ECDSA/Ed25519 signing
- **Persistent, anchored memory** — ZeroDB vectors + Hedera HCS hash anchors
- **On-chain identity** — HTS NFT credentials per agent
- **Trustless payments** — USDC via HTS, no smart contract overhead
- **Deterministic replay** — reconstruct any run from ZeroDB + HCS logs

---

## Architecture

```
+────────────────────────────────────────────────────────────+
│                   CrewAI Agent Crew                        │
│  analyst · compliance_agent · transaction_agent            │
│  Capabilities: finance, KYT, X402, memory, identity        │
+──────────────────────┬─────────────────────────────────────+
                       │
                       ▼
+────────────────────────────────────────────────────────────+
│              Agent-402 FastAPI Backend                     │
│  /v1/agents  /v1/identity  /v1/hedera/payments             │
│  /v1/reputation  /v1/hcs  /v1/marketplace                  │
│  X402 Protocol: /.well-known/x402  /x402                   │
+─────────┬─────────────────┬──────────────┬─────────────────+
          │                 │              │
          ▼                 ▼              ▼
+─────────────+  +──────────────────+  +──────────────────+
│   ZeroDB    │  │     Hedera       │  │  Circle / USDC   │
│  Vectors    │  │  HCS topics      │  │  Gateway         │
│  Memory     │  │  HTS tokens      │  │  (fallback)      │
│  Ledgers    │  │  DID (did:hedera)│  +──────────────────+
│  Tables     │  │  HCS-10 / HCS-14 │
│  Audit      │  │  Mirror Node     │
+─────────────+  +──────────────────+
          │
          ▼
+──────────────────────────────────────────────────────────+
│                  AINative SDKs                           │
│  @ainative/react-sdk   @ainative/next-sdk                │
│  @ainative/svelte-sdk  @ainative/vue-sdk                 │
│  hedera-agent-kit plugin                                 │
│  agent402-sdk (Python)                                   │
+──────────────────────────────────────────────────────────+
          │
          ▼
+──────────────────────────────────────────────────────────+
│              Agent Marketplace                           │
│  HCS-14 directory  ·  HCS-10 messaging                  │
│  Reputation scores ·  Capability discovery              │
+──────────────────────────────────────────────────────────+
```

---

## Agent Roles

| Agent | Responsibility |
|-------|----------------|
| **Analyst Agent** | Evaluates market data, proposes transfers |
| **Compliance Agent** | Runs KYC/KYT checks, risk scoring |
| **Transaction Agent** | Signs and submits X402/HTS payment requests |

Each agent has:

- A W3C DID (did:hedera:testnet:...)
- An HTS NFT identity token
- A dedicated HCS reputation topic
- Persistent ZeroDB memory (vectors + structured records)
- Configurable spend limits with auto-settlement

---

## Core Technologies

| Technology | Role |
|------------|------|
| **CrewAI** | Multi-agent orchestration |
| **FastAPI** | X402 protocol server and REST API |
| **X402** | Cryptographically signed request protocol |
| **ZeroDB** | Persistent memory, vectors, ledgers, audit |
| **Hedera HCS** | Memory anchoring, reputation, HCS-10/14 messaging |
| **Hedera HTS** | USDC payments, agent identity NFTs |
| **Hedera DID** | W3C agent decentralised identifiers |
| **Circle USDC** | Payment gateway (Circle API fallback) |

---

## Hedera Integration

### HCS-Anchored Memory

Every agent decision is persisted in ZeroDB and its SHA-256 content hash is submitted to a Hedera Consensus Service topic. This provides:

- Tamper-evidence: any mutation of stored data is detectable
- Non-repudiation: sequence number + consensus timestamp are immutable
- Independent verification: mirror node URL included in every anchor receipt

```python
from app.services.hcs_anchoring_service import HCSAnchoringService

service = HCSAnchoringService()
anchor = await service.anchor_memory(
    memory_id="mem-001",
    content_hash=sha256(content),
    agent_id="agent-001",
    namespace="production",
)
# anchor["sequence_number"] — verifiable on mirror node
```

### On-Chain Agent Identity

Each agent mints an HTS NFT token class on creation. The token encodes the agent's DID, capabilities, and role. Identity is portable, verifiable, and revocable.

```python
from app.services.hedera_identity_service import HederaIdentityService

service = HederaIdentityService()
result = await service.create_agent_token_class(
    agent_id="agent-001",
    agent_name="Analyst Agent",
    capabilities=["finance", "compliance"],
)
# result["token_id"] — Hedera HTS token ID
```

### USDC Payments via HTS

Native HTS token transfers provide sub-3 second finality without smart contract overhead. Every payment is linked to agent_id, task_id, and run_id for full audit trail.

```python
from app.services.hedera_payment_service import HederaPaymentService

service = HederaPaymentService()
result = await service.transfer_usdc(
    from_account="0.0.11111",
    to_account="0.0.22222",
    amount=1_000_000,   # 1.00 USDC (6 decimal places)
    memo="task completion payment",
)
# result["transaction_id"] — verifiable on mirror node
```

### Reputation System

On-chain feedback with exponential recency decay. Trust tiers progress from NEW to ESTABLISHED as an agent completes verified tasks.

```python
from app.services.hedera_reputation_service import HederaReputationService

service = HederaReputationService()

# Submit feedback (stored on HCS topic)
await service.submit_feedback(
    agent_did="did:hedera:testnet:0.0.12345",
    rating=5,
    comment="excellent task completion",
    task_id="task-001",
    submitter_did="did:hedera:testnet:0.0.99999",
    payment_proof_tx="0.0.12345@1712000001.000000001",
)

# Calculate score with recency decay
score = await service.calculate_reputation_score(
    agent_did="did:hedera:testnet:0.0.12345"
)
# score["score"] 0.0-5.0, score["trust_tier"] 0-4
```

### Agent Discovery (HCS-14)

Agents register in an HCS-14 directory topic. Discovery queries replay topic history to build the current registry.

```python
from app.services.hcs14_directory_service import HCS14DirectoryService

service = HCS14DirectoryService()
result = await service.query_directory(capability="finance")
# result["agents"] — list of registered agents matching filter
```

---

## SDKs

| Package | Language | Description |
|---------|----------|-------------|
| `@ainative/react-sdk` | TypeScript/React | AI chat and agent UI components |
| `@ainative/next-sdk` | TypeScript/Next.js | Server-side agent integration |
| `@ainative/svelte-sdk` | TypeScript/Svelte | Svelte agent components |
| `@ainative/vue-sdk` | TypeScript/Vue 3 | Vue agent composables |
| `hedera-agent-kit` | TypeScript | Hedera HCS/HTS plugin for AI frameworks |

See `packages/` directory and `docs/sdk/` for quickstart guides.

---

## Repo Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers (agents, hedera, payments, etc.)
│   │   ├── core/             # Config, errors, middleware, DID signer
│   │   ├── models/           # SQLAlchemy / Pydantic models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic (Hedera, ZeroDB, Circle, etc.)
│   │   ├── tests/            # 200+ unit and integration tests
│   │   └── main.py           # FastAPI application entry point
│   └── requirements.txt
│
├── packages/
│   ├── react-sdk/            # @ainative/react-sdk
│   ├── next-sdk/             # @ainative/next-sdk
│   ├── svelte-sdk/           # @ainative/svelte-sdk
│   └── vue-sdk/              # @ainative/vue-sdk
│
├── scripts/
│   ├── demo_consensus_2026.py   # 5-minute live demo (Issue #249)
│   └── run_demo.py              # Legacy demo runner
│
├── docs/
│   ├── launch/
│   │   ├── PITCH_DECK.md         # HederaCon / Consensus 2026 pitch
│   │   ├── GRANT_APPLICATION.md  # Hedera HBAR Foundation grant
│   │   └── COMMUNITY_PARTNER.md  # Hedera ecosystem partner application
│   ├── api/                  # API specifications
│   ├── development-guides/   # Developer guides (identity, reputation, SDK)
│   ├── sdk/                  # SDK quickstart guides
│   └── testing/              # Test strategy and coverage reports
│
├── frontend/                 # Frontend application
├── contracts/                # Smart contract definitions
├── tests/                    # Smoke tests
├── .env.example
├── README.md
└── requirements.txt
```

---

## Quick Start

### Prerequisites

- Python 3.9+
- Hedera testnet account (free at portal.hedera.com)
- ZeroDB API key (free at ainative.studio)

### 1. Clone and install

```bash
git clone https://github.com/ainative/agent-402.git
cd agent-402
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# ZeroDB configuration
ZERODB_API_KEY=your_zerodb_api_key
ZERODB_PROJECT_ID=your_project_id
BASE_URL=https://api.ainative.studio/v1/public

# Hedera testnet configuration
HEDERA_NETWORK=testnet
HEDERA_OPERATOR_ID=0.0.YOUR_ACCOUNT_ID
HEDERA_OPERATOR_KEY=YOUR_PRIVATE_KEY_DER_HEX

# Circle (optional — for payment fallback)
CIRCLE_API_KEY=your_circle_api_key
```

Get your Hedera testnet credentials:
1. Create account at https://portal.hedera.com
2. Fund with testnet HBAR (faucet included in portal)
3. Copy account ID and private key to `.env`

> **SECURITY WARNING:** Never commit `.env` to version control. See [SECURITY.md](/docs/SECURITY_POLICY.md) for best practices.

### 3. Start the backend

```bash
cd backend
uvicorn app.main:app --reload
```

API available at http://localhost:8000
Documentation at http://localhost:8000/docs

### 4. Run the 5-minute demo

```bash
# Dry run (no real network calls — great for first look)
DEMO_DRY_RUN=1 python scripts/demo_consensus_2026.py

# Live testnet run (requires Hedera credentials)
python scripts/demo_consensus_2026.py
```

The demo executes the complete agent workflow:

1. Create agent profile in ZeroDB
2. Register identity on Hedera HTS (NFT token class)
3. Execute X402 USDC payment via HTS
4. Anchor agent memory to Hedera HCS
5. Submit and calculate reputation score
6. Search agent marketplace (HCS-14 directory)

### 5. Run the test suite

```bash
cd backend
python -m pytest app/tests/ -v --cov --cov-report=term-missing
```

200+ tests covering all services, API endpoints, and integrations.

---

## Deterministic Replay

Every agent action writes to ZeroDB with:

- `agent_id` — who acted
- `run_id` — which execution
- `inputs` + `outputs` — what was decided
- `timestamp` — when it happened
- `hcs_sequence_number` — on-chain anchor (tamper-evident)

Any run can be replayed **without re-executing agents**, proving:

- Auditability
- Non-repudiation
- Compliance traceability

---

## ZeroDB DX Contract

This project follows the **ZeroDB DX Contract**, which guarantees:

- Stable endpoints
- Default 384-dim embeddings
- Deterministic errors (`{ detail, error_code }` always)
- Immutable ledgers (append-only semantics enforced by middleware)
- Copy-paste-safe docs
- Consistent project `status: "ACTIVE"` field

See [DX-Contract.md](/docs/DX_CONTRACT.md) and [project-lifecycle.md](/docs/product/project-lifecycle.md).

---

## Security

### API Key Safety

**NEVER expose your ZeroDB or Hedera keys in:**
- Frontend JavaScript (React, Vue, Angular, Svelte)
- Mobile apps
- Public repositories
- Client-side environment variables

Use a backend proxy pattern:

```
[Client App] -> [Your Backend API] -> [ZeroDB / Hedera API]
     |               |                        |
  JWT Token     API Key (secure)        Validated Request
```

See [SECURITY_POLICY.md](/docs/SECURITY_POLICY.md) for complete guidance.

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [Pitch Deck](/docs/launch/PITCH_DECK.md) | HederaCon / Consensus 2026 architecture and value proposition |
| [Grant Application](/docs/launch/GRANT_APPLICATION.md) | Hedera HBAR Foundation grant application |
| [Community Partner](/docs/launch/COMMUNITY_PARTNER.md) | Hedera ecosystem partner application |
| [DX Contract](/docs/DX_CONTRACT.md) | API behaviour guarantees |
| [Security Policy](/docs/SECURITY_POLICY.md) | Key management and security practices |
| [API Spec](/docs/api/) | Full REST API specification |
| [SDK Quickstart](/docs/sdk/) | SDK quickstart guides |
| [Identity Guide](/docs/development-guides/) | Hedera DID and HTS identity implementation |
| [Documentation Index](/docs/DOCUMENTATION_INDEX.md) | Full docs directory listing |

---

## Support and Contact

- **AINative Studio** — https://ainative.studio
- **GitHub Issues** — bug reports and feature requests welcome
- **Demo questions** — find us at Consensus 2026

---

Built by AINative Dev Team
