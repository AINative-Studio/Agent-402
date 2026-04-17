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

## Step 7: Store Your Agent's First Memory — Cognitive API

The cognitive API wraps raw storage with importance scoring, auto-categorization, and automatic HCS anchoring. One endpoint replaces the old CRUD + explicit-anchor dance.

Tell your AI:

> "Store a memory for my agent using POST http://localhost:8000/api/v1/memory/remember. The agent_id is {agent_id}, content is 'Evaluated market conditions: HBAR/USD stable at 0.08, low volatility. Recommendation: proceed with transaction.', and memory_type is 'episodic'."

**Expected response:**
```json
{
  "memory_id": "mem_abc123...",
  "agent_id": "agent_abc123...",
  "content": "Evaluated market conditions: ...",
  "memory_type": "episodic",
  "category": "observation",
  "importance": 0.62,
  "namespace": "default",
  "timestamp": "2026-04-17T...",
  "hcs_anchor_pending": false
}
```

**Save your `memory_id`.**

**What this means:**
- `category` — the cognitive API classified your memory automatically (keywords like "evaluated" → `observation`).
- `importance` — a 0.0–1.0 score derived from memory type, content length, and any priority flags in metadata. Higher = more likely to resurface in recall.
- `hcs_anchor_pending: false` — the memory's SHA-256 content hash was anchored to the Hedera Consensus Service **as part of the same call**. No separate anchor step needed; if it were `true`, the anchor can be retried later (the memory itself is still durable).

---

## Step 8: Recall with Relevance + Recency

Tell your AI:

> "Recall memories for my agent using POST http://localhost:8000/api/v1/memory/recall. Use the query 'market conditions' and agent_id {agent_id}."

**Expected response:**
```json
{
  "memories": [
    {
      "memory_id": "mem_abc123...",
      "agent_id": "agent_abc123...",
      "content": "Evaluated market conditions: ...",
      "category": "observation",
      "memory_type": "episodic",
      "importance": 0.62,
      "similarity_score": 0.81,
      "recency_weight": 0.99,
      "composite_score": 0.73,
      "timestamp": "2026-04-17T..."
    }
  ],
  "query": "market conditions",
  "weights": {
    "similarity": 0.6,
    "recency": 0.3,
    "importance": 0.1,
    "half_life_days": 7.0
  }
}
```

**What this means:** Three signals combined into one ranking score:
- **similarity_score** — how close the memory is to your query (vector embedding cosine).
- **recency_weight** — exponential decay over age (`0.5 ** (age_days / 7)`). Recent memories surface first.
- **composite_score** — the weighted sum. Pass custom `weights` in the request body to reshape ranking (e.g. boost importance).

This is how agents "remember what matters" instead of drowning in every past observation.

---

## Step 9: Store More Memories, Then Reflect

Tell your AI:

> "Remember two more memories for my agent via POST http://localhost:8000/api/v1/memory/remember:
> (1) content 'KYC verification passed for counterparty 0.0.99999. Risk score: LOW.', memory_type 'episodic'.
> (2) content 'Approved 10 USDC transfer to 0.0.99999 based on positive market analysis.', memory_type 'episodic'."

Now recall by different queries to confirm semantic search still works:

> "Recall memories for 'compliance' — does it find the KYC memory?"
> "Recall memories for 'transfer approved' — does it find the transaction decision?"

Then try the synthesis endpoints:

> "Generate cognitive insights for my agent using POST http://localhost:8000/api/v1/memory/reflect with agent_id {agent_id}. Look at patterns and contradictions across my memories."

**Expected response:**
```json
{
  "agent_id": "agent_abc123...",
  "window_days": 30,
  "memory_count": 3,
  "patterns": [
    { "label": "observation", "count": 1, "category": "observation" },
    { "label": "decision",    "count": 2, "category": "decision"    }
  ],
  "contradictions": [],
  "gaps": [
    { "category": "plan", "description": "No memories of category 'plan' in the corpus" }
  ]
}
```

Finally, check the agent's cognitive profile:

> "Get the cognitive profile for my agent via GET http://localhost:8000/api/v1/memory/profile/{agent_id}."

**What this means:** `/reflect` gives you top patterns across a window, calls out contradictions (approve/reject on the same topic), and highlights gaps. `/profile/{agent_id}` surfaces the agent's topic distribution and expertise areas (`count × avg_importance`) — handy for routing work to the right agent.

---

## Step 10: Verify the HCS Anchor on the Public Ledger

`/memory/remember` anchors the memory's SHA-256 content hash to Hedera Consensus Service as part of the same call (`hcs_anchor_pending: false` in the response confirms it succeeded). Now verify the anchor is visible on the public ledger.

Tell your AI:

> "Fetch the HCS audit trail for memory {memory_id} via GET http://localhost:8000/api/v1/anchor/{memory_id}/verify. Return the HCS topic_id and sequence number."

**Expected response:**
```json
{
  "memory_id": "mem_abc123...",
  "content_hash": "sha256...",
  "verified": true,
  "sequence_number": 42,
  "topic_id": "0.0.XXXXX",
  "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1/topics/0.0.XXXXX/messages/42"
}
```

**Verification:** Open the `mirror_node_url` in your browser — you'll see the anchor record on the Hedera public ledger. If anyone modifies the stored memory, its SHA-256 will no longer match this anchor, which is how you prove tamper-evidence.

**What this means:** You didn't have to call an anchor endpoint yourself — the cognitive API did it automatically on write. Your agent's memory is **durable in ZeroDB and tamper-evident on Hedera** in a single operation. That's the full "remember with proof" flow regulated use cases require.

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
