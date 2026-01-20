# V1 Trustless Agent Lite - Minimal Viable Scope

**Version:** 1.0
**Target Timeline:** 4-6 weeks
**Goal:** Prove core value with minimal complexity

---

## Philosophy

> **Build the simplest system that proves agents can:**
> 1. Have verifiable identities
> 2. Earn reputation from real interactions
> 3. Get paid autonomously
> 4. Self-govern without DAOs

**Not in V1:** Validation system, multiple validators, complex governance, TEEs, zkML

---

## V1 Scope Summary

| Component               | V1 Scope                        | Deferred to V2                |
| ----------------------- | ------------------------------- | ----------------------------- |
| **Identity**            | Simple NFT registry + metadata  | Transfer, delegation, revocation |
| **Runtime**             | HTTP + MCP only                 | A2A protocol, multi-node      |
| **Reputation**          | Event logging + simple scoring  | Advanced weighting, spam detection |
| **Payments**            | x402 basic (off-chain only)     | On-chain commitments, escrow  |
| **Validation**          | ❌ Not in V1                    | All validation features       |
| **Indexers**            | Basic event indexer             | GraphQL, advanced analytics   |
| **Governance**          | Agent self-policy only          | Multi-agent coordination      |

---

## V1 User Journey

**The Story We're Proving:**

1. Alice creates an agent (CodeReviewer)
2. Alice registers agent identity on-chain (takes 1 min, costs $2)
3. Alice deploys agent runtime (takes 5 min)
4. Agent advertises: "Code review for 0.001 ETH per review"
5. Bob discovers CodeReviewer via simple directory
6. Bob sends code review request
7. Agent returns HTTP 402 with payment instructions
8. Bob pays 0.001 ETH (off-chain receipt)
9. Agent performs review and returns result
10. Bob submits reputation feedback (on-chain, $0.50)
11. Agent's reputation score updates (visible in < 1 min)
12. Carol sees high reputation score and also hires CodeReviewer

**Success Criteria:** This flow works end-to-end in < 30 minutes.

---

## V1 Component Details

### 1. Identity Registry (V1)

**Contract: `AgentRegistryV1.sol`**

```solidity
// Minimal interface
interface IAgentRegistryV1 {
    // Register new agent (mint NFT)
    function registerAgent(string memory agentURI) external returns (uint256 agentId);

    // Update agent metadata URI
    function updateAgentURI(uint256 agentId, string memory newURI) external;

    // Query agent URI
    function agentURI(uint256 agentId) external view returns (string memory);

    // Events
    event AgentRegistered(uint256 indexed agentId, address indexed owner, string agentURI);
    event AgentURIUpdated(uint256 indexed agentId, string newURI);
}
```

**Features:**
- ✅ Mint agent NFT with metadata URI
- ✅ Update URI (owner only)
- ✅ Query URI
- ✅ Transfer ownership (ERC-721 default)

**Deferred:**
- Multi-signature ownership
- Delegation to operators
- Revocation or suspension
- Batch registration

**Implementation:** ~200 lines, 2 days

---

### 2. Agent Metadata Schema (V1)

**File: `agent-metadata.schema.json`**

```json
{
  "agentId": "42",
  "name": "CodeReviewer",
  "description": "AI agent for code review",
  "version": "1.0.0",
  "owner": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
  "endpoints": {
    "http": "https://codereview-agent.example.com",
    "mcp": "https://codereview-agent.example.com/mcp"
  },
  "capabilities": ["code-review", "security-analysis"],
  "trustTiers": ["tier0", "tier1", "tier2"],
  "payment": {
    "x402Enabled": true,
    "pricing": {
      "code-review": "0.001 ETH",
      "security-analysis": "0.005 ETH"
    }
  },
  "policy": {
    "minReputationToAccept": 0,
    "autoShutdownOnLowReputation": false
  }
}
```

**Features:**
- ✅ Name, description, version
- ✅ HTTP and MCP endpoints
- ✅ x402 pricing
- ✅ Basic policy configuration

**Deferred:**
- Service level agreements (SLAs)
- Compliance certifications
- Multi-language support
- Rich media (logos, screenshots)

**Implementation:** Schema only, 1 day

---

### 3. Agent Runtime SDK (V1)

**Package: `@agent402/runtime-lite`**

**Core Features:**
- ✅ HTTP server with x402 middleware
- ✅ MCP protocol support (stdio/SSE)
- ✅ EIP-712 signing
- ✅ Simple in-memory state
- ✅ Policy enforcement (basic)
- ✅ Health check endpoint

**API Example:**

```typescript
import { AgentRuntime } from '@agent402/runtime-lite';

const agent = new AgentRuntime({
  agentId: 42,
  privateKey: process.env.AGENT_PRIVATE_KEY,
  metadataURI: 'https://example.com/agent.json',
  x402: {
    enabled: true,
    paymentAddress: '0x...',
    pricing: {
      'code-review': '0.001'
    }
  }
});

// Define capability
agent.registerCapability('code-review', async (request, context) => {
  // Payment already verified by middleware
  const code = request.code;
  const review = await performCodeReview(code);
  return { review };
});

// Start server
await agent.start({ port: 3000 });
```

**Deferred:**
- Distributed state/memory
- Multi-node clustering
- Advanced policy DSL
- Built-in monitoring dashboards

**Implementation:** ~1000 lines, 1 week

---

### 4. Reputation System (V1)

**Contract: `ReputationRegistryV1.sol`**

```solidity
interface IReputationRegistryV1 {
    // Submit feedback
    function submitFeedback(
        uint256 agentId,
        uint8 rating,        // 1-5
        string memory comment,
        bytes memory paymentProof  // optional x402 receipt
    ) external;

    // Query feedback count
    function getFeedbackCount(uint256 agentId) external view returns (uint256);

    // Events
    event FeedbackSubmitted(
        uint256 indexed agentId,
        address indexed reviewer,
        uint8 rating,
        string comment,
        bytes paymentProof,
        uint256 timestamp
    );
}
```

**Off-Chain Aggregator:**
- Indexes FeedbackSubmitted events
- Computes simple average score
- Weights paid feedback 2x vs free
- REST API: `GET /agents/{id}/reputation`

**Deferred:**
- Complex weighting algorithms
- Spam detection
- Collusion detection
- Time-decay scoring
- Category-specific scores

**Implementation:** ~300 lines contract + 500 lines indexer, 1 week

---

### 5. Payment System (V1)

**x402 Implementation: Off-chain receipts only**

**Payment Flow:**

1. Agent returns `402 Payment Required`
   ```
   HTTP/1.1 402 Payment Required
   X-Payment-Address: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
   X-Payment-Amount: 0.001
   X-Payment-Currency: ETH
   X-Payment-Chain: base-sepolia
   ```

2. Client generates payment receipt (signed off-chain)
   ```json
   {
     "from": "0xClient...",
     "to": "0xAgent...",
     "amount": "0.001",
     "currency": "ETH",
     "timestamp": 1234567890,
     "taskHash": "0xabcd...",
     "signature": "0x..."
   }
   ```

3. Client retries with receipt
   ```
   POST /code-review
   X-Payment-Receipt: <base64-encoded-receipt>
   ```

4. Agent verifies signature and executes

**Features:**
- ✅ Off-chain receipts (no gas)
- ✅ Signature verification
- ✅ Receipt storage for reputation proof
- ✅ Simple payment address (no escrow)

**Deferred:**
- On-chain payment commitments
- Escrow for high-value tasks
- Multi-token support
- Refund mechanisms
- Payment splitting

**Implementation:** ~400 lines SDK, 3 days

---

### 6. Indexer & Discovery (V1)

**Service: `agent-indexer-v1`**

**Features:**
- ✅ Index AgentRegistered events
- ✅ Index FeedbackSubmitted events
- ✅ REST API for discovery
- ✅ Simple search (by name, capability)
- ✅ Reputation score calculation

**API Endpoints:**

```
GET  /agents                    # List all agents (paginated)
GET  /agents/{id}               # Get agent details
GET  /agents/{id}/reputation    # Get reputation score
GET  /agents/search?q=code      # Search agents
POST /agents/{id}/feedback      # Submit feedback (proxies to contract)
```

**Database:** PostgreSQL (simple schema)

**Deferred:**
- GraphQL API
- Advanced filtering
- Real-time subscriptions
- Analytics dashboards
- Historical trending

**Implementation:** ~800 lines, 4 days

---

## V1 Infrastructure

### Deployment Stack

- **Blockchain:** Base Sepolia (testnet) → Base (mainnet)
- **Contracts:** Foundry for development
- **Indexer:** Node.js + PostgreSQL
- **Runtime SDK:** TypeScript/Node.js
- **Hosting:** Railway (indexer + sample agents)
- **Metadata:** IPFS (Pinata) or HTTPS

### Gas Budget (Per Transaction)

| Operation        | Estimated Gas | Cost @ 0.5 gwei |
| ---------------- | ------------- | --------------- |
| Register Agent   | 80,000        | $0.04           |
| Update URI       | 40,000        | $0.02           |
| Submit Feedback  | 60,000        | $0.03           |
| **Total (full lifecycle)** | **180,000** | **$0.09** |

*Assumes Base L2 pricing. Even cheaper on actual deployment.*

---

## V1 Security Model

### Threat Mitigation

| Threat            | V1 Mitigation                      | V2 Enhancement        |
| ----------------- | ---------------------------------- | --------------------- |
| Sybil attacks     | Payment-weighted reputation        | Economic staking      |
| Fake agents       | On-chain identity + metadata sig   | Validator verification |
| Spam feedback     | Gas cost + payment weighting       | Spam detection ML     |
| Payment fraud     | Signature verification             | On-chain commitments  |
| Agent downtime    | No mitigation                      | SLA enforcement       |

### Known Limitations

- **No dispute resolution:** V1 is caveat emptor
- **No refunds:** Payments are final
- **No validation:** Trust based on reputation only
- **Limited spam protection:** Gas cost is only barrier

**Acceptable for V1:** Focus on low-stakes tasks (code review, data lookup, content generation)

---

## V1 Success Metrics

### Week 4 (Testnet Launch)

- [ ] 5+ agents registered
- [ ] 50+ tasks completed
- [ ] 20+ reputation feedbacks submitted
- [ ] Average task latency < 2s
- [ ] Zero critical bugs

### Week 6 (Mainnet Launch)

- [ ] 20+ agents registered
- [ ] 200+ tasks completed
- [ ] 100+ feedbacks
- [ ] At least 3 different agent types (code, data, content)
- [ ] Public demo available

---

## What We're Proving

**V1 demonstrates:**

1. ✅ Agents can have **trustless identities** (no centralized registry)
2. ✅ Agents can **earn reputation** from real users
3. ✅ Agents can **get paid autonomously** (no accounts, no billing)
4. ✅ **Zero governance overhead** (no DAOs, no votes)
5. ✅ **Near-zero gas costs** (< $0.10 per agent lifecycle)
6. ✅ Works **today** with existing tools (MCP, x402)

**V1 defers:**
- High-stakes validation
- Complex governance
- Advanced economics
- Enterprise features

---

## V1 Build Order (Next Section)

See `BUILD_ROADMAP.md` for week-by-week implementation plan.

---

## V2 Preview (Post-V1)

After V1 validates core concepts, V2 adds:

- **Validation System:** For high-value tasks
- **Advanced Reputation:** Spam detection, time-decay, categories
- **On-Chain Payment Commitments:** For disputes
- **A2A Protocol:** Agent-to-agent communication
- **Multi-Agent Workflows:** Agents composing agents
- **Governance Tools:** For high-stakes scenarios

---

## Decision Log

| Decision                  | Rationale                                    |
| ------------------------- | -------------------------------------------- |
| No validation in V1       | Adds 2+ weeks, not needed for low-stakes     |
| Off-chain payments only   | Zero gas, simpler, proves economic model     |
| Base L2 deployment        | Cheap gas, EVM compatible, growing ecosystem |
| PostgreSQL over Graph     | Faster development, easier ops               |
| HTTP + MCP only           | A2A can wait, these cover 90% of use cases   |
| Simple reputation (avg)   | Proves concept, can iterate on algorithm     |

---

## Next: Build Roadmap

Proceed to `BUILD_ROADMAP.md` for detailed week-by-week implementation plan.
