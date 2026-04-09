# Tutorial 1: Identity & Memory

**Time:** ~50 minutes
**Goal:** Create an agent with a Hedera identity and persistent, tamper-proof memory

---

## Step 1: Create Your Agent

Tell your AI:

> "Send a POST request to http://localhost:8000/api/v1/agents to create a new agent. Use these details: name is 'my-consensus-agent', role is 'analyst', and description is 'My first autonomous fintech agent on Hedera'."

**Expected response:**
```json
{
  "agent_id": "agent_abc123...",
  "name": "my-consensus-agent",
  "role": "analyst",
  "did": "did:ethr:0x...",
  "status": "active"
}
```

**Save your `agent_id`** — you'll need it for every step after this.

**Verification:** `curl http://localhost:8000/api/v1/agents` shows your agent in the list.

---

## Step 2: Verify Your Agent Exists

Tell your AI:

> "GET my agent details from http://localhost:8000/api/v1/agents/{agent_id} — replace {agent_id} with the ID from Step 1."

**Verification:** You see your agent's name, role, and DID.

---

## Step 3: Explore the Agent API

Tell your AI:

> "Show me all the endpoints available at http://localhost:8000/docs that start with /api/v1/agents. What can I do with agents?"

This teaches you the API surface. Your AI will explain: create, list, get, update, delete — standard CRUD plus Hedera-specific identity operations.

---

## Step 4: Register Agent Identity on Hedera

Tell your AI:

> "Register my agent on Hedera using POST http://localhost:8000/api/v1/hedera/identity/register. My agent_id is {agent_id}. Give it capabilities: finance, compliance, payments."

**Expected response:**
```json
{
  "token_id": "0.0.XXXXX",
  "serial_number": 1,
  "agent_did": "did:hedera:testnet:0.0.XXXXX_0.0.YYYYY",
  "status": "registered"
}
```

**Save your `agent_did`** — this is your agent's decentralized identity.

**Verification:** Your agent now has an HTS NFT on Hedera testnet. This NFT IS your agent's identity — portable, verifiable, revocable.

---

## Step 5: Resolve Your Agent's DID

Tell your AI:

> "Resolve my agent's DID using GET http://localhost:8000/api/v1/hedera/identity/{agent_id}/did"

**Expected response:** A W3C DID Document with your agent's verification methods and service endpoints.

**What this means:** Any system in the world can verify your agent's identity by resolving this DID. No central authority needed.

---

## Step 6: Check Agent Capabilities

Tell your AI:

> "Get my agent's capabilities from GET http://localhost:8000/api/v1/hedera/identity/{agent_id}/capabilities"

**Expected response:** The capabilities you registered (finance, compliance, payments).

---

## Step 7: Store Your Agent's First Memory

Tell your AI:

> "Store a memory for my agent using POST http://localhost:8000/api/v1/agent-memory. The agent_id is {agent_id}, run_id is 'workshop-run-1', memory_type is 'decision', content is 'Evaluated market conditions: HBAR/USD stable at 0.08, low volatility. Recommendation: proceed with transaction.', and confidence is 0.92."

**Expected response:**
```json
{
  "memory_id": "mem_abc123...",
  "status": "stored"
}
```

**Save your `memory_id`.**

**What this means:** Your agent now has a persistent decision record. It can recall this across sessions, runs, and even server restarts.

---

## Step 8: Recall the Memory

Tell your AI:

> "Search my agent's memories using POST http://localhost:8000/api/v1/agent-memory/search. Use the query 'market conditions' and agent_id {agent_id}."

**Expected response:** Your stored memory should appear as the top result with a relevance score.

**What this means:** Semantic search — your agent can find relevant memories by meaning, not just exact text match. This is powered by vector embeddings in ZeroDB.

---

## Step 9: Store More Memories

Tell your AI:

> "Store two more memories for my agent: (1) A compliance check: 'KYC verification passed for counterparty 0.0.99999. Risk score: LOW.' with confidence 0.98. (2) A transaction decision: 'Approved 10 USDC transfer to 0.0.99999 based on positive market analysis and clean compliance.' with confidence 0.95."

Now try recalling:

> "Search memories for 'compliance' — does it find the KYC memory?"
> "Search memories for 'transfer approved' — does it find the transaction decision?"

---

## Step 10: Anchor a Memory to Hedera

This is the key innovation. Tell your AI:

> "Anchor my agent's memory to Hedera Consensus Service using POST http://localhost:8000/api/v1/anchor/memory. Provide the memory_id from Step 7, a content_hash (SHA-256 of the memory content), agent_id, and namespace 'workshop'."

**Expected response:**
```json
{
  "sequence_number": 42,
  "topic_id": "0.0.XXXXX",
  "content_hash": "sha256...",
  "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1/..."
}
```

**Verification:** Open the `mirror_node_url` in your browser. You'll see the anchor record on the Hedera public ledger.

**What this means:** This memory is now tamper-evident. If anyone changes the stored memory, the hash won't match the HCS anchor. Your agent's decisions are provably unmodified — critical for compliance, audit, and trust.

---

## Hour 1 Complete!

You now have:
- An AI agent with a unique identity
- A Hedera-native DID (did:hedera) backed by an HTS NFT
- Persistent memories that survive across sessions
- At least one memory anchored to Hedera for tamper-proof audit

**What you built matters:** This isn't a toy. Regulated industries (finance, healthcare, legal) need exactly this: AI agents whose decisions are verifiable, auditable, and provably unmodified. You just built that foundation in under an hour, by talking to your AI assistant.

---

## Next: [Tutorial 2: Payments & Trust](02-payments-and-trust.md)
