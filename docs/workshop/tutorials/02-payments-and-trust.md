# Tutorial 2: Payments & Trust

**Time:** ~50 minutes
**Goal:** Execute USDC payments on Hedera and build an on-chain reputation

**Prerequisite:** Completed Tutorial 1 (you have an agent_id and agent_did)

---

## Step 1: Create an Agent Wallet

Tell your AI:

> "Create a Hedera wallet for my agent using POST http://localhost:8000/api/v1/hedera/wallets. My agent_id is {agent_id}."

**Expected response:**
```json
{
  "account_id": "0.0.XXXXX",
  "agent_id": "agent_abc123...",
  "status": "created"
}
```

**Save your `account_id`.**

**What this means:** Your agent now has its own Hedera account. It can hold HBAR and USDC independently of your operator account.

---

## Step 2: Associate USDC Token

Before your agent can receive USDC, its account must be associated with the USDC token. Tell your AI:

> "Associate the USDC token with my agent's wallet using POST http://localhost:8000/api/v1/hedera/wallets/{account_id}/associate-usdc."

**Verification:** The response confirms token association.

**Why this step exists:** On Hedera, accounts must explicitly opt-in to receive specific tokens. This is a security feature — no one can send you tokens you didn't agree to hold.

---

## Step 3: Check Balance

Tell your AI:

> "Check my agent's balance using GET http://localhost:8000/api/v1/hedera/wallets/{account_id}/balance."

**Expected response:**
```json
{
  "account_id": "0.0.XXXXX",
  "hbar_balance": "10.0",
  "usdc_balance": "0.0"
}
```

---

## Step 4: Execute a USDC Payment

Now the core of x402 — your agent pays for a service. Tell your AI:

> "Execute a USDC payment from my agent using POST http://localhost:8000/api/v1/hedera/payments. Transfer 1,000,000 USDC units (1 USDC) from my agent's account to account 0.0.22222. Set agent_id to my {agent_id}, task_id to 'workshop-task-1', and memo to 'workshop payment for data analysis'."

**Required fields:** `agent_id`, `amount` (in USDC smallest units — 1 USDC = 1,000,000), `recipient`, `task_id`. Optional: `from_account`, `memo` (max 100 chars).

**Expected response:**
```json
{
  "payment_id": "pay_abc123...",
  "transaction_id": "0.0.XXXXX@1234567890.000000001",
  "status": "SUCCESS",
  "agent_id": "agent_abc123...",
  "amount": 1000000,
  "recipient": "0.0.22222",
  "task_id": "workshop-task-1",
  "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1/transactions/..."
}
```

**Save your `transaction_id`.**

---

## Step 5: Verify the Payment Receipt

Tell your AI:

> "Verify my payment receipt using GET http://localhost:8000/api/v1/hedera/payments/{transaction_id}/verify."

**Expected response:**
```json
{
  "verified": true,
  "transaction_status": "SUCCESS",
  "consensus_timestamp": "2026-05-05T...",
  "mirror_node_url": "https://testnet.mirrornode.hedera.com/..."
}
```

**Verification:** Open the `mirror_node_url` in your browser. You'll see the actual Hedera transaction.

**What this means:** The payment is settled in under 3 seconds, verified by Hedera consensus, and independently auditable on the public ledger. No intermediary. No trust required.

---

## Step 6: Explore the x402 Discovery Endpoint

Tell your AI:

> "GET http://localhost:8000/.well-known/x402 — what does this tell us?"

**Expected response:** The x402 protocol metadata including Hedera network, USDC token ID, supported DIDs, and signature methods.

**What this means:** Any agent in the world can discover this server's payment capabilities by hitting this standard endpoint. It's how agents find and pay each other.

---

## Step 7: Submit Reputation Feedback

Now let's build trust. You'll submit feedback for another agent (or your own for testing). Tell your AI:

> "Submit reputation feedback using POST http://localhost:8000/api/v1/hedera/reputation/{agent_did}/feedback. Rate the agent 5 stars, comment 'Excellent analysis, fast settlement', with payment_proof_tx set to my transaction_id from Step 4, task_id 'workshop-task-1', and submitter_did set to my own agent_did."

**Expected response:**
```json
{
  "sequence_number": 1,
  "status": "submitted",
  "consensus_timestamp": "2026-05-05T..."
}
```

**What this means:** This feedback is anchored to Hedera Consensus Service. It can't be edited or deleted — it's permanent, timestamped, and tied to a real payment.

---

## Step 8: Submit More Feedback (Different Ratings)

Tell your AI:

> "Submit two more feedback entries for the same agent: one with rating 4 and comment 'Good but slightly slow', and one with rating 5 and comment 'Perfect execution'. Use different task_ids."

---

## Step 9: Check Reputation Score

Tell your AI:

> "Get the reputation score for agent {agent_did} using GET http://localhost:8000/api/v1/hedera/reputation/{agent_did}."

**Expected response:**
```json
{
  "agent_did": "did:hedera:testnet:...",
  "score": 4.67,
  "total_reviews": 3,
  "trust_tier": 0,
  "tier_name": "NEW",
  "last_updated": "2026-05-05T..."
}
```

**What this means:** The score uses exponential recency decay — recent feedback matters more. Trust tiers progress as the agent builds history:
- **0 (NEW):** < 3 reviews
- **1 (BASIC):** score < 2.0 or < 10 reviews
- **2 (TRUSTED):** score >= 2.0 and >= 10 reviews
- **3 (VERIFIED):** score >= 3.5 and >= 25 reviews
- **4 (ESTABLISHED):** score >= 4.0 and >= 50 reviews

---

## Step 10: View Feedback History

Tell your AI:

> "Get all feedback for agent {agent_did} using GET http://localhost:8000/api/v1/hedera/reputation/{agent_did}/feedback."

**Verification:** You see all 3 feedback entries with their consensus timestamps.

---

## Step 11: See Ranked Agents

Tell your AI:

> "Get all agents ranked by reputation using GET http://localhost:8000/api/v1/hedera/reputation/ranked."

**What this means:** When your agent needs to delegate work, it can choose partners based on on-chain trust scores. No fake reviews possible — every rating requires a verified payment proof.

---

## Hour 2 Complete!

You now have:
- An agent with a Hedera wallet holding HBAR
- A verified USDC payment on the Hedera public ledger
- Reputation feedback anchored to HCS (permanent, tamper-proof)
- A trust score calculated with recency-weighted decay

**What you built matters:** Payment-gated reputation is how you prevent fake reviews in an autonomous agent economy. Every rating costs real money and is linked to a real transaction. Your agent's trust is earned, not gamed.

---

## Next: [Tutorial 3: Discovery & Marketplace](03-discovery-and-marketplace.md)
