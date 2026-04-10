# Agent 402 Workshop Curriculum

## Vibe Code a Trustless AI Agent on Hedera

- **Duration:** 3 hours (3:00 PM - 6:00 PM)
- **Format:** Hands-on, AI pair programming, no lectures
- **Audience:** Developers and vibe coders (non-technical welcome)

---

## Pre-Workshop Setup (10 minutes)

Attendees arrive with:
- Laptop (macOS, Linux, or Windows with WSL)
- AI coding assistant installed (Claude Code, Cursor, GitHub Copilot, etc.)
- Hedera testnet account (we help set up if needed)

Instructor walks through:
1. Clone the repo
2. Copy `.env.example` to `.env`
3. Start the backend server
4. Verify it's running at `http://localhost:8000/docs`

See: [VIBE_CODER_GUIDE.md](./VIBE_CODER_GUIDE.md) for detailed setup with AI prompts.

---

## Hour 1: Identity & Memory (3:00 - 4:00 PM)

### Learning Objectives
- Create an AI agent with a unique identity
- Register the agent on Hedera with an NFT identity
- Give the agent persistent memory that survives across sessions
- Anchor memories to Hedera Consensus Service for tamper-proof audit

### Activities

| Time | Activity | Tutorial Reference |
|------|----------|-------------------|
| 3:00-3:10 | Setup verification, introductions | VIBE_CODER_GUIDE.md |
| 3:10-3:25 | Create your first agent via API | Tutorial 01, Steps 1-3 |
| 3:25-3:40 | Register agent identity on Hedera (HTS NFT + DID) | Tutorial 01, Steps 4-6 |
| 3:40-3:55 | Store and recall agent memories | Tutorial 01, Steps 7-9 |
| 3:55-4:00 | Anchor a memory to HCS, verify on mirror node | Tutorial 01, Step 10 |

### Verification Checkpoint
By 4:00 PM, every attendee should have:
- An agent visible at `GET /api/v1/agents`
- A did:hedera identity resolvable via the identity API
- At least one memory stored and recalled
- One HCS anchor with a mirror node verification URL

### Key AI Prompts for This Hour
```
"Help me create an agent using the Agent-402 API at localhost:8000.
I need to POST to /api/v1/agents with a name, role, and DID."

"Now help me register this agent's identity on Hedera using the
identity API at /api/v1/hedera/identity/register"

"Store a memory for my agent using the agent memory API.
The content should be 'First decision: approved the transaction'."
```

---

## Hour 2: Payments & Trust (4:00 - 5:00 PM)

### Learning Objectives
- Execute a USDC payment on Hedera via x402 protocol
- Verify payment receipts on the Hedera mirror node
- Submit reputation feedback anchored to HCS
- See how reputation scores are calculated with recency decay

### Activities

| Time | Activity | Tutorial Reference |
|------|----------|-------------------|
| 4:00-4:15 | Create agent wallet, check USDC balance | Tutorial 02, Steps 1-3 |
| 4:15-4:30 | Execute x402 payment, verify receipt | Tutorial 02, Steps 4-6 |
| 4:30-4:45 | Submit reputation feedback for another attendee's agent | Tutorial 02, Steps 7-9 |
| 4:45-5:00 | Check reputation scores, explore trust tiers | Tutorial 02, Steps 10-11 |

### Verification Checkpoint
By 5:00 PM, every attendee should have:
- An agent wallet with a Hedera account
- At least one USDC payment executed (testnet)
- A payment receipt with a mirror node URL
- Reputation feedback submitted and a calculated trust score

### Key AI Prompts for This Hour
```
"Help me create a Hedera wallet for my agent using the
wallet API at /api/v1/hedera/wallets"

"Execute a USDC payment from my agent to account 0.0.XXXXX
using the payment API. Amount: 1 USDC."

"Submit reputation feedback for agent did:hedera:testnet:0.0.XXXXX
with rating 5 and comment 'excellent work'."
```

---

## Hour 3: Discovery & Marketplace (5:00 - 6:00 PM)

### Learning Objectives
- Register your agent in the HCS-14 directory for discovery
- Send messages to other agents via HCS-10 (OpenConvAI)
- Publish your agent to the marketplace
- Discover and interact with other workshop agents

### Activities

| Time | Activity | Tutorial Reference |
|------|----------|-------------------|
| 5:00-5:15 | Register agent in HCS-14 directory | Tutorial 03, Steps 1-3 |
| 5:15-5:30 | Send HCS-10 message to another attendee's agent | Tutorial 03, Steps 4-6 |
| 5:30-5:45 | Publish agent to marketplace, browse other agents | Tutorial 03, Steps 7-9 |
| 5:45-6:00 | Multi-agent demo: discover, negotiate, pay, rate | Tutorial 03, Step 10 |

### Verification Checkpoint
By 6:00 PM, every attendee should have:
- Agent discoverable in HCS-14 directory
- At least one HCS-10 message sent and received
- Agent published in the marketplace
- A complete agent lifecycle: identity -> memory -> payment -> reputation -> discovery

---

## Instructor Notes

### Pacing
- If the room is ahead, move to the next section early
- If someone is stuck, their AI assistant should be able to diagnose most issues
- The troubleshooting guide covers the top 10 common errors

### What Success Looks Like
- Attendees leave with a working agent on Hedera testnet
- They understand the architecture (agents, memory, payments, reputation, discovery)
- They've experienced vibe coding — describing what they want, letting AI write the code
- They know how to continue building after the workshop

### Materials
- Tutorial files: `docs/workshop/tutorials/01-*.md`, `02-*.md`, `03-*.md`
- Smoke test: `python scripts/workshop_smoke_test.py` (run before class to verify everything works)
- Vibe coder guide: `docs/workshop/VIBE_CODER_GUIDE.md`
- Troubleshooting: `docs/workshop/TROUBLESHOOTING.md`
