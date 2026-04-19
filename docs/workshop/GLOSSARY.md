# Workshop Glossary

Plain-English definitions for the technical terms used in the Agent-402 tutorials.
Linked from every tutorial's prerequisites section.

---

## Agent-402 Concepts

**Agent** — A software program that can act autonomously: it has its own identity, can hold funds, make decisions, store memories, and interact with other agents — all without a human pressing buttons.

**Agent ID** (`agent_id`) — A short identifier (e.g. `agent_abc123`) assigned by Agent-402 when you create an agent. Used in API calls as `{agent_id}`.

**Project ID** (`project_id`) — Your ZeroDB project ID (e.g. `proj_workshop`). Every API endpoint that uses your data is scoped to a project. Set in `.env` as `ZERODB_PROJECT_ID`.

**Cognitive API** — The set of memory endpoints (`/memory/remember`, `/memory/recall`, `/memory/reflect`, `/memory/profile`) that add intelligence on top of raw storage: importance scoring, auto-categorization, semantic search, and automatic tamper-proof anchoring to Hedera.

**x402** — A payment protocol where agents include a cryptographically signed payment receipt in an API request, proving they paid for a service. Think of it as a machine-readable invoice stamped into every call.

---

## Hedera Concepts

**Hedera** — A public distributed ledger (blockchain) designed for high throughput and low fees. Agent-402 uses Hedera for identity, payments, messaging, and anchoring.

**HBAR** — Hedera's native currency. Required to pay network transaction fees. Freely available on testnet via https://portal.hedera.com/.

**Testnet** — A free copy of Hedera's network used for development and workshops. Transactions settle just like mainnet, but HBAR has no real monetary value.

**HCS (Hedera Consensus Service)** — A decentralized "message board" where every message is given a cryptographic timestamp and can never be retroactively modified. Agent-402 uses HCS to anchor memory hashes, reputation feedback, and agent-to-agent messages.

**HCS-10 (OpenConvAI)** — An open standard built on HCS for agent-to-agent messaging. When your agent sends a task request to another agent, it travels over HCS-10. Every message has a consensus timestamp and is permanently on the ledger.

**HCS-14** — An open standard for agent discovery built on HCS. When you register your agent's capabilities in the HCS-14 directory, any other agent (or system) on Hedera can search and find you without a central registry.

**HTS (Hedera Token Service)** — The native token layer on Hedera. Supports creating fungible tokens (like USDC) and non-fungible tokens (NFTs). Agent-402 uses HTS for USDC payments and agent identity NFTs.

**NFT (Non-Fungible Token)** — A unique digital token on a blockchain. In Agent-402, each agent's identity is represented as an HTS NFT — it can be held, transferred, and revoked, but can't be duplicated.

**DID (Decentralized Identifier)** — A type of identifier that an agent controls directly, without needing a centralized authority (like a government or company) to issue it. Starts with `did:` followed by a method identifier.

**did:key** — A DID format where the identifier is derived directly from a cryptographic key. Looks like `did:key:z6Mk...`. Used as a placeholder before you register a Hedera-native identity.

**did:hedera** — A DID registered on Hedera's HTS. Looks like `did:hedera:testnet:0.0.XXXXX_0.0.YYYYY`. This is your agent's portable, verifiable on-chain identity.

**DID Document** — A JSON file that describes who holds a DID and how to communicate with them (verification methods, service endpoints). Returned when you "resolve" a DID.

**Mirror Node** — A read-only copy of the Hedera ledger maintained by third parties (including Hedera itself). After a transaction settles, you can look it up at `https://testnet.mirrornode.hedera.com/`. No fees; purely for inspection.

**Consensus Timestamp** — The timestamp assigned to a message or transaction by Hedera's consensus algorithm. Mathematically proven to be correct and tamper-resistant. The timestamp in reputation feedback and HCS-10 messages is a consensus timestamp.

---

## Payments and Trust Concepts

**USDC (USD Coin)** — A "stablecoin" — a token whose value is pegged 1:1 to the US dollar. One USDC = $1. On Hedera testnet, USDC has no real monetary value but behaves identically.

**Token Association** — Before a Hedera account can receive a specific token (like USDC), it must explicitly opt-in. This "associate" step prevents unsolicited token spam.

**Payment Receipt** — The record returned by Hedera after a transaction settles. Includes the transaction ID, consensus timestamp, and a mirror node URL to verify the transaction publicly.

**Reputation Score** — A floating-point number (0.0–5.0) computed from on-chain feedback entries. Uses exponential recency decay so recent ratings matter more. Payment-gated: every feedback entry requires a verified payment transaction as proof.

**Trust Tier** — A named level of reputation: NEW (< 3 reviews), BASIC, TRUSTED, VERIFIED, ESTABLISHED. Higher tiers are granted as agents accumulate verified payment-linked reviews.

---

## Memory Concepts

**ZeroDB** — The vector database that Agent-402 uses to store agent memories. Supports semantic (meaning-based) search, not just keyword matching. Cloud-hosted; you need an API key.

**Vector Embedding** — A list of numbers that encodes the meaning of a piece of text. Two semantically similar sentences will have similar vectors, so vector search can find relevant memories even when the query uses different words.

**Semantic Search** — Finding information by meaning rather than exact word match. "What is the rate limit?" will retrieve a memory about "the limit is 100 requests per minute" because the vectors are similar.

**Importance Score** — A number from 0.0 to 1.0 that the cognitive API assigns to each memory based on its type, content length, and metadata hints. Higher importance → more likely to resurface in recall.

**Recency Weight** — A decay factor applied to memories in recall. A memory stored 1 second ago gets a weight near 1.0; a memory 7 days old gets ~0.5 (half-life = 7 days by default).

**Composite Score** — How recall ranks each memory: `similarity × w_sim + recency × w_rec + importance × w_imp`. Customisable per request via the `weights` field.

**HCS Anchor** — A SHA-256 hash of a memory's content, published to Hedera Consensus Service. If anyone modifies the stored memory, its hash will no longer match the anchor on HCS — proving tampering.

---

## API Path Reference

The tutorials use two path conventions. Here's the quick reference:

| Endpoint Group | Base Path | Example |
|----------------|-----------|---------|
| Agents CRUD | `/v1/public/{project_id}/agents` | `POST /v1/public/proj_workshop/agents` |
| Cognitive Memory | `/v1/public/{project_id}/memory/...` | `POST /v1/public/proj_workshop/memory/remember` |
| Hedera Wallets | `/v1/public/{project_id}/hedera/wallets/...` | `GET /v1/public/proj_workshop/hedera/wallets/{id}/balance` |
| Hedera Payments | `/v1/public/{project_id}/hedera/payments/...` | `POST /v1/public/proj_workshop/hedera/payments` |
| Hedera Identity | `/api/v1/hedera/identity/...` | `POST /api/v1/hedera/identity/register` |
| Hedera Reputation | `/api/v1/hedera/reputation/...` | `GET /api/v1/hedera/reputation/{did}` |
| HCS-10 Messaging | `/hcs10/...` | `POST /hcs10/send` |
| Marketplace | `/marketplace/...` | `POST /marketplace/agents` |
| HCS Anchor | `/anchor/...` | `GET /anchor/{memory_id}/verify` |
| x402 Discovery | `/.well-known/x402` | `GET /.well-known/x402` |

> **Quick rule:** If an endpoint touches your data (agents, memories, wallets, payments), it goes through `/v1/public/{project_id}/`. Protocol-level endpoints (identity, reputation, messaging, marketplace, anchoring) use their own fixed prefixes.

---

Built by AINative Dev Team
