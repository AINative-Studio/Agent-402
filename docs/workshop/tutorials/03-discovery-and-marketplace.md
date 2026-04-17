# Tutorial 3: Discovery & Marketplace

**Time:** ~50 minutes
**Goal:** Publish your agent, discover others, and coordinate a multi-agent workflow

**Prerequisite:** Completed Tutorials 1 & 2 (you have agent_id, agent_did, and a payment history)

---

## Step 1: Register in HCS-14 Directory

The HCS-14 standard is how Hedera agents advertise themselves for discovery. Tell your AI:

> "Register my agent in the HCS-14 directory using POST http://localhost:8000/api/v1/hedera/identity/directory/register. My agent_did is {agent_did}, capabilities are ['finance', 'compliance', 'payments'], role is 'analyst', and reputation_score is 0."

**Required fields:** `agent_did`, `capabilities` (list of strings), `role`, `reputation_score` (>= 0).

**Expected response:**
```json
{
  "status": "SUCCESS",
  "transaction_id": "0.0.XXXXX@...",
  "did": "did:hedera:testnet:...",
  "directory_topic": "0.0.XXXXX"
}
```

**What this means:** Your agent is now discoverable by any system that queries the HCS-14 directory on Hedera. This is decentralized agent discovery — no central registry.

---

## Step 2: Search the Directory

Tell your AI:

> "Search the HCS-14 directory for agents with capability 'finance' using POST http://localhost:8000/api/v1/hedera/identity/directory/search."

**Expected response:** A list of agents registered with the 'finance' capability — including yours!

---

## Step 3: Discover by Role

Tell your AI:

> "Search the directory for agents with role 'analyst'. Then search for role 'compliance'."

This shows how agents can find each other by function, not just by name.

---

## Step 4: Send an HCS-10 Message

HCS-10 (OpenConvAI) is the protocol for agent-to-agent messaging on Hedera. Tell your AI:

> "Send a message to another agent using POST http://localhost:8000/api/v1/hcs10/send. My sender_did is {my_agent_did}, recipient_did is {another_agent_did}, message_type is 'task_request', and payload is 'Please analyze HBAR/USD market conditions and report back'. Create a conversation_id like 'workshop-conv-1'."

**Expected response:**
```json
{
  "message_id": "msg_...",
  "conversation_id": "workshop-conv-1",
  "consensus_timestamp": "2026-05-05T...",
  "status": "sent"
}
```

**What this means:** This message is on the Hedera Consensus Service. It has a guaranteed ordering, timestamp, and cannot be retroactively modified.

---

## Step 5: Check for Messages

Tell your AI:

> "Check for messages addressed to my agent using GET http://localhost:8000/api/v1/hcs10/messages/{my_agent_did}."

If another workshop attendee sent you a message, it'll appear here.

---

## Step 6: View the Audit Trail

Tell your AI:

> "Get the audit trail for my conversation using GET http://localhost:8000/api/v1/hcs10/audit/{conversation_id}."

**What this means:** Every agent-to-agent interaction is logged with consensus timestamps. This audit trail is admissible — it's anchored to Hedera, not stored in someone's private database.

---

## Step 7: Publish to the Marketplace

Tell your AI:

> "Publish my agent to the marketplace using POST http://localhost:8000/api/v1/marketplace/agents. Use agent_id {agent_id}, category 'finance', description 'Autonomous fintech analyst specializing in market evaluation and compliance verification on Hedera', and pricing 'pay-per-task'."

**Expected response:**
```json
{
  "listing_id": "listing_...",
  "status": "published",
  "agent_id": "agent_...",
  "category": "finance"
}
```

---

## Step 8: Browse the Marketplace

Tell your AI:

> "Browse the agent marketplace using GET http://localhost:8000/api/v1/marketplace/browse. Filter by category 'finance'."

You should see your agent and potentially other workshop attendees' agents.

---

## Step 9: Search the Marketplace

Tell your AI:

> "Search the marketplace for agents that can do 'compliance verification' using POST http://localhost:8000/api/v1/marketplace/search."

---

## Step 10: The Full Agent Lifecycle

Let's bring it all together. Tell your AI:

> "I want to execute a complete agent workflow. Help me:
> 1. Search the marketplace for a 'finance' agent
> 2. Check its reputation score
> 3. Send it a task request via HCS-10
> 4. Execute a USDC payment for the service
> 5. Verify the payment receipt on the mirror node
> 6. Submit reputation feedback
> 7. Anchor the entire interaction to HCS"

Your AI will orchestrate all of these API calls in sequence. Watch the output — this is an autonomous agent economy in action.

---

## Workshop Complete!

You now have a fully operational agent with:

| Capability | What You Built | Why It Matters |
|-----------|----------------|----------------|
| **Identity** | HTS NFT + did:hedera DID | Portable, verifiable, revocable credentials |
| **Memory** | ZeroDB vectors + HCS anchors | Persistent decisions with tamper-proof audit |
| **Payments** | USDC via HTS, sub-3s settlement | Real financial transactions, no smart contract overhead |
| **Reputation** | HCS-anchored, payment-gated feedback | Trust scores that can't be faked |
| **Discovery** | HCS-14 directory + HCS-10 messaging | Decentralized agent-to-agent coordination |
| **Marketplace** | Publish, browse, search agents | Open economy for agent services |

---

## What's Next?

### Keep Building (After the Workshop)

Tell your AI:

> "I want to build a [describe your use case] using Agent-402. I have the server running at localhost:8000. Help me design the agent workflow."

Ideas:
- **DeFi portfolio manager** — agent monitors positions, rebalances, logs all decisions
- **Compliance bot** — agent reviews transactions, flags risks, anchors findings to HCS
- **Multi-agent research team** — analyst + fact-checker + writer, coordinating via HCS-10
- **Autonomous grant writer** — agent discovers grant opportunities, drafts applications, submits

### Use the SDKs

Instead of raw API calls, use the SDKs for cleaner code:

**TypeScript:** `npm install @ainative/agent-sdk`
**Python:** `pip install ainative-agent`

See `docs/sdk/typescript-quickstart.md` and `docs/sdk/python-quickstart.md`.

### Join the Community

- **Proof of Fiesta** — 7 PM tonight, same venue! Tacos, tequila, and the builders you just coded with.
- **AINative Studio** — ainative.studio
- **GitHub** — github.com/AINative-Studio/Agent-402

---

## Thank You

You just vibe coded a trustless AI agent on Hedera in three hours. Not bad for a Monday afternoon in Miami.
