# Tutorial 1: Identity & Memory

**Time:** ~50 minutes  
**Goal:** Create an agent with a Hedera identity and persistent, tamper-proof memory

## Prerequisites

Complete **[SETUP.md](../SETUP.md)** before starting this tutorial. You need:

- The backend server running on `http://localhost:8000`
- `WORKSHOP_MODE=true` in your `.env` (otherwise all API calls return 404)
- `WORKSHOP_DEFAULT_PROJECT_ID` set to your ZeroDB project ID
- ZeroDB credentials (`ZERODB_API_KEY`, `ZERODB_PROJECT_ID`) in your `.env`

**Quick check — run this before Step 1:**

```bash
curl http://localhost:8000/health
# → {"status": "healthy"}
```

If you see `Connection refused`, start the server first:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

> Every URL in this tutorial contains `{project_id}` — replace it with the value of
> `ZERODB_PROJECT_ID` from your `.env` file (e.g. `proj_workshop`).
> New to Hedera terms? See the [Glossary](../GLOSSARY.md).

---

## Step 1: Create Your Agent *(~5 min)*

Tell your AI:

> "Send a POST request to `http://localhost:8000/v1/public/{project_id}/agents` to create a new agent. Use these details: did is `did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK` (a placeholder — Step 4 will replace it with a real did:hedera), name is `my-consensus-agent`, role is `analyst`, scope is `PROJECT`, and description is `My first autonomous fintech agent on Hedera`. Replace `{project_id}` with my ZeroDB project ID."

**Required fields:**
- `did` — must be `did:key:z6Mk...` format (placeholder; replaced in Step 4)
- `name` — human-readable agent name
- `role` — valid values: `analyst` | `compliance` | `transaction` | `orchestrator`
- `scope` — valid values: `SYSTEM` | `PROJECT` | `RUN` (use `PROJECT` for this workshop)

**Optional:** `description` (max 1000 chars)

**Request body example:**
```json
{
  "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
  "name": "my-consensus-agent",
  "role": "analyst",
  "scope": "PROJECT",
  "description": "My first autonomous fintech agent on Hedera"
}
```

✅ **You should see:**
```json
{
  "id": "agent_abc123...",
  "agent_id": "agent_abc123...",
  "did": "did:key:z6Mk...",
  "name": "my-consensus-agent",
  "role": "analyst",
  "scope": "PROJECT",
  "description": "My first autonomous fintech agent on Hedera",
  "project_id": "proj_workshop",
  "created_at": "2026-04-17T...",
  "updated_at": "2026-04-17T..."
}
```

📌 **Save your `agent_id`** — you'll need it for every step after this.

**Verification:** `curl http://localhost:8000/v1/public/{project_id}/agents` shows your agent in the list.

---

## Step 2: Verify Your Agent Exists *(~2 min)*

Tell your AI:

> "GET my agent details from `http://localhost:8000/v1/public/{project_id}/agents/{agent_id}` — replace `{project_id}` with my ZeroDB project ID and `{agent_id}` with the ID from Step 1."

✅ **You should see:** Your agent's name, role, and DID in the response JSON.

---

## Step 3: Explore the Agent API *(~3 min)*

Tell your AI:

> "Show me all the endpoints available at `http://localhost:8000/docs` that have `/agents` in the path. What can I do with agents?"

This teaches you the API surface. Your AI will explain: create, list, get, update, delete — standard CRUD plus Hedera-specific identity operations.

---

## Step 4: Register Agent Identity on Hedera *(~7 min)*

Tell your AI:

> "Register my agent on Hedera using `POST http://localhost:8000/api/v1/hedera/identity/{agent_id}/register` — replace `{agent_id}` with the ID I saved in Step 1. Give it capabilities: `finance`, `compliance`, `payments`."

> 💡 **Your `agent_id` from Step 1 is reused here.** This endpoint *links* a Hedera identity to the agent you already created — Step 1 and Step 4 refer to the SAME agent record. The response will echo back the same `agent_id`.

**Request body example:**
```json
{
  "capabilities": ["finance", "compliance", "payments"]
}
```

That's it — `name` and `role` are pulled from the agent you created in Step 1, so you don't need to repeat them.

✅ **You should see** (note the `agent_id` matches the one from Step 1):
```json
{
  "agent_id": "agent_abc123...",
  "token_id": "0.0.XXXXX",
  "serial_number": 1,
  "did": "did:hedera:testnet:agent_abc123..._pending",
  "status": "SUCCESS"
}
```

📌 **Save your `did`** — this is your agent's decentralized identity. It starts with `did:hedera:testnet:`.

**Verification:** Your agent now has an HTS NFT on Hedera testnet linked to the same `agent_id` you saw in Step 1. This NFT IS your agent's identity — portable, verifiable, revocable.

---

## Step 5: Resolve Your Agent's DID *(~3 min)*

Tell your AI:

> "Resolve my agent's DID using `GET http://localhost:8000/api/v1/hedera/identity/{agent_id}/did` — replace `{agent_id}` with the short ID from Step 1 (the `agt_...` format, NOT the `did:hedera:...` from Step 4)."

> 💡 **Which ID to use here?** Use the `agent_id` from Step 1 (the short `agent_abc123...` form), not the `agent_did` from Step 4. The path parameter `{agent_id}` means the ZeroDB agent ID, not the Hedera DID.

✅ **You should see:** A W3C DID Document with your agent's verification methods and service endpoints.

**What this means:** Any system in the world can verify your agent's identity by resolving this DID. No central authority needed.

---

## Step 6: Check Agent Capabilities *(~2 min)*

Tell your AI:

> "Get my agent's capabilities from `GET http://localhost:8000/api/v1/hedera/identity/{agent_id}/capabilities` — use my short `agent_id` from Step 1."

✅ **You should see:** The three capabilities you registered: `finance`, `compliance`, `payments`.

---

## Step 7: Store Your Agent's First Memory — Cognitive API *(~7 min)*

The cognitive API wraps raw storage with importance scoring, auto-categorization, and automatic HCS anchoring. One endpoint replaces the old CRUD + explicit-anchor dance.

Tell your AI:

> "Store a memory for my agent using `POST http://localhost:8000/v1/public/{project_id}/memory/remember`. The `agent_id` is `{agent_id}`, `content` is `'Evaluated market conditions: HBAR/USD stable at 0.08, low volatility. Recommendation: proceed with transaction.'`, and `memory_type` is `episodic`."

**Request body example:**
```json
{
  "agent_id": "{agent_id}",
  "content": "Evaluated market conditions: HBAR/USD stable at 0.08, low volatility. Recommendation: proceed with transaction.",
  "memory_type": "episodic"
}
```

**`memory_type` valid values:** `working` | `episodic` | `semantic` | `procedural`

**Optional fields:**
- `namespace` (default: `"default"`) — isolates memories by context
- `importance_hint` (0.0–1.0) — nudge the importance scorer
- `metadata` (object) — arbitrary key/value for your own use

✅ **You should see:**
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

📌 **Save your `memory_id`.**

**What this means:**
- `category` — auto-classified from your content (keywords like "evaluated" → `observation`). Valid category values: `decision` | `observation` | `knowledge` | `plan` | `interaction` | `error` | `other`.
- `importance` — a 0.0–1.0 score derived from memory type, content length, and any priority flags in metadata. Higher = more likely to surface in recall.
- `hcs_anchor_pending: false` — the memory's SHA-256 content hash was anchored to the Hedera Consensus Service **as part of the same call**. No separate anchor step needed.

---

## Step 8: Recall with Relevance + Recency *(~7 min)*

Tell your AI:

> "Recall memories for my agent using `POST http://localhost:8000/v1/public/{project_id}/memory/recall`. Use `agent_id` `{agent_id}` and `query` `'market conditions'`."

**Request body example:**
```json
{
  "agent_id": "{agent_id}",
  "query": "market conditions"
}
```

**Optional `weights` field** — override the default ranking balance:
```json
{
  "agent_id": "{agent_id}",
  "query": "market conditions",
  "weights": {
    "similarity": 0.6,
    "recency": 0.3,
    "importance": 0.1,
    "half_life_days": 7.0
  }
}
```

✅ **You should see:**
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
- **composite_score** — the weighted sum. Pass custom `weights` to reshape ranking (e.g. boost importance over recency).

This is how agents "remember what matters" instead of drowning in every past observation.

---

## Step 9: Store More Memories, Then Reflect *(~10 min)*

Tell your AI:

> "Remember two more memories for my agent via `POST http://localhost:8000/v1/public/{project_id}/memory/remember`:
> 1. `content` = `'KYC verification passed for counterparty 0.0.99999. Risk score: LOW.'`, `memory_type` = `episodic`
> 2. `content` = `'Approved 10 USDC transfer to 0.0.99999 based on positive market analysis.'`, `memory_type` = `episodic`"

Now verify semantic search works across these memories:

> "Recall memories for `'compliance'` — does it find the KYC memory?"
> "Recall memories for `'transfer approved'` — does it find the transaction decision?"

Then run the synthesis endpoints:

> "Generate cognitive insights for my agent using `POST http://localhost:8000/v1/public/{project_id}/memory/reflect` with `agent_id` = `{agent_id}`."

**Request body example:**
```json
{
  "agent_id": "{agent_id}"
}
```

**Optional `window_days`** (default: 30) — how far back to look for patterns.

✅ **You should see:**
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

> "Get the cognitive profile for my agent via `GET http://localhost:8000/v1/public/{project_id}/memory/profile/{agent_id}`."

✅ **You should see:**
```json
{
  "agent_id": "agent_abc123...",
  "total_memories": 3,
  "memory_type_distribution": {
    "episodic": 3
  },
  "category_distribution": {
    "observation": 1,
    "decision": 2
  },
  "avg_importance": 0.58,
  "expertise_topics": ["market conditions", "compliance", "payments"]
}
```

**What this means:** `/reflect` identifies top patterns across a window, calls out contradictions (approve/reject on the same topic), and highlights gaps. `/profile/{agent_id}` surfaces the agent's topic distribution and expertise areas — handy for routing work to the right agent.

---

## Step 10: Verify the HCS Anchor on the Public Ledger *(~5 min)*

`/memory/remember` anchors the memory's SHA-256 content hash to Hedera Consensus Service as part of the same call (`hcs_anchor_pending: false` in the response confirms it succeeded). Now verify the anchor is visible on the public ledger.

Tell your AI:

> "Fetch the HCS audit trail for memory `{memory_id}` via `GET http://localhost:8000/anchor/{memory_id}/verify`. Return the HCS `topic_id` and `sequence_number`."

> ⚠️ **Note:** The anchor endpoint does **not** have an `/api/v1/` or `/v1/public/` prefix — use the path exactly as shown: `GET http://localhost:8000/anchor/{memory_id}/verify`.

✅ **You should see:**
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

**Verification:** Open the `mirror_node_url` in your browser — you'll see the anchor record on the Hedera public ledger. If anyone modifies the stored memory, its SHA-256 will no longer match this anchor, proving tamper-evidence.

**What this means:** You didn't have to call an anchor endpoint yourself — the cognitive API did it automatically on write. Your agent's memory is **durable in ZeroDB and tamper-evident on Hedera** in a single operation. That's the full "remember with proof" flow regulated use cases require.

---

## Hour 1 Complete!

You now have:
- An AI agent with a unique identity
- A Hedera-native DID (`did:hedera`) backed by an HTS NFT
- Persistent memories that survive across sessions
- At least one memory anchored to Hedera for tamper-proof audit

**What you built matters:** Regulated industries (finance, healthcare, legal) need exactly this: AI agents whose decisions are verifiable, auditable, and provably unmodified. You just built that foundation in under an hour, by talking to your AI assistant.

---

## Next: [Tutorial 2: Payments & Trust](02-payments-and-trust.md)
