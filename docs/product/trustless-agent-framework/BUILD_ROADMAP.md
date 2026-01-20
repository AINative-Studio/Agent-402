# Build Roadmap: Trustless Agent Framework V1

**Timeline:** 6 Weeks
**Target:** Testnet launch Week 4, Mainnet launch Week 6
**Team Size:** 2-3 developers

---

## Overview

This roadmap builds V1 in logical order, with each week producing **working, testable artifacts**.

**Parallel Tracks:**
- **Track A:** Contracts + Indexer (Backend)
- **Track B:** Runtime SDK + Examples (Agent-side)

**Milestones:**
- Week 2: Smart contracts deployed to testnet
- Week 3: First demo agent running
- Week 4: Public testnet launch
- Week 6: Mainnet launch

---

## Week 1: Foundation

**Goal:** Deploy contracts, setup infrastructure, skeleton SDK

### Day 1-2: Smart Contracts

**Tasks:**
- [ ] Create Foundry project structure
- [ ] Implement `AgentRegistryV1.sol`
  - `registerAgent(string agentURI)`
  - `updateAgentURI(uint256 agentId, string newURI)`
  - `agentURI(uint256 agentId)`
  - Events: `AgentRegistered`, `AgentURIUpdated`
- [ ] Implement `ReputationRegistryV1.sol`
  - `submitFeedback(uint256 agentId, uint8 rating, string comment, bytes paymentProof)`
  - Event: `FeedbackSubmitted`
- [ ] Write unit tests (Foundry)
  - Test registration flow
  - Test URI updates
  - Test feedback submission
  - Test access control
- [ ] Deploy to local testnet (Anvil)

**Deliverables:**
- ✅ Contracts passing all tests
- ✅ Local deployment working
- ✅ Gas measurements documented

**Owner:** Backend Dev
**Effort:** 16 hours

---

### Day 3-4: Infrastructure Setup

**Tasks:**
- [ ] Setup PostgreSQL database (Railway/Supabase)
- [ ] Create database schema
  ```sql
  CREATE TABLE agents (
    agent_id BIGINT PRIMARY KEY,
    owner_address VARCHAR(42),
    agent_uri TEXT,
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
  );

  CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    agent_id BIGINT REFERENCES agents(agent_id),
    reviewer_address VARCHAR(42),
    rating SMALLINT,
    comment TEXT,
    payment_proof BYTEA,
    tx_hash VARCHAR(66),
    block_number BIGINT,
    timestamp TIMESTAMP
  );

  CREATE TABLE reputation_scores (
    agent_id BIGINT PRIMARY KEY,
    total_feedback INT,
    avg_rating DECIMAL(3,2),
    paid_feedback_count INT,
    free_feedback_count INT,
    last_updated TIMESTAMP
  );
  ```
- [ ] Deploy to Base Sepolia testnet
  - Get testnet ETH from faucet
  - Deploy contracts
  - Verify on Basescan
- [ ] Setup RPC endpoints (Alchemy/Infura)
- [ ] Create `.env.example` template

**Deliverables:**
- ✅ Database schema created
- ✅ Contracts deployed to Base Sepolia
- ✅ Contract addresses documented
- ✅ RPC access configured

**Owner:** Backend Dev
**Effort:** 12 hours

---

### Day 5: Runtime SDK Skeleton

**Tasks:**
- [ ] Create NPM package `@agent402/runtime-lite`
- [ ] Setup TypeScript project
  ```
  runtime-sdk/
  ├── src/
  │   ├── index.ts
  │   ├── runtime.ts
  │   ├── crypto.ts      # EIP-712 signing
  │   ├── payment.ts     # x402 verification
  │   ├── policy.ts      # Policy engine
  │   └── types.ts
  ├── package.json
  ├── tsconfig.json
  └── README.md
  ```
- [ ] Implement basic `AgentRuntime` class
  ```typescript
  class AgentRuntime {
    constructor(config: RuntimeConfig);
    registerCapability(name: string, handler: Handler): void;
    start(port: number): Promise<void>;
    stop(): Promise<void>;
  }
  ```
- [ ] Add EIP-712 signing utilities
- [ ] Write unit tests (Jest/Vitest)

**Deliverables:**
- ✅ Package structure created
- ✅ Basic runtime class implemented
- ✅ Tests passing

**Owner:** SDK Dev
**Effort:** 8 hours

---

## Week 2: Core Components

**Goal:** Complete indexer, payment system, and basic runtime

### Day 1-2: Event Indexer

**Tasks:**
- [ ] Create indexer service (Node.js)
  ```
  indexer/
  ├── src/
  │   ├── index.ts
  │   ├── blockchain.ts   # Event listener
  │   ├── database.ts     # DB operations
  │   ├── reputation.ts   # Score calculation
  │   └── api.ts          # REST API
  ├── package.json
  └── README.md
  ```
- [ ] Implement event listening
  - Listen for `AgentRegistered` events
  - Listen for `FeedbackSubmitted` events
  - Handle blockchain reorgs
- [ ] Implement reputation scoring
  ```typescript
  function calculateReputation(feedbacks: Feedback[]): ReputationScore {
    const paid = feedbacks.filter(f => f.paymentProof);
    const free = feedbacks.filter(f => !f.paymentProof);

    const paidWeight = 2.0;
    const freeWeight = 1.0;

    const weightedSum =
      (paid.reduce((sum, f) => sum + f.rating, 0) * paidWeight) +
      (free.reduce((sum, f) => sum + f.rating, 0) * freeWeight);

    const weightedCount = (paid.length * paidWeight) + (free.length * freeWeight);

    return {
      avgRating: weightedSum / weightedCount,
      totalFeedback: feedbacks.length,
      paidFeedbackCount: paid.length,
      freeFeedbackCount: free.length
    };
  }
  ```
- [ ] Add database writes
- [ ] Add error handling and logging

**Deliverables:**
- ✅ Indexer listening to testnet events
- ✅ Database updating in real-time
- ✅ Reputation scores calculating correctly

**Owner:** Backend Dev
**Effort:** 16 hours

---

### Day 3-4: REST API

**Tasks:**
- [ ] Implement REST API (Express/Fastify)
  ```
  GET  /agents                # List all agents
  GET  /agents/:id            # Get agent details
  GET  /agents/:id/reputation # Get reputation
  GET  /agents/search         # Search agents
  POST /feedback              # Submit feedback (proxy)
  ```
- [ ] Add pagination
  ```typescript
  GET /agents?page=1&limit=20
  ```
- [ ] Add filtering
  ```typescript
  GET /agents?capability=code-review&minReputation=4.0
  ```
- [ ] Add OpenAPI documentation (Swagger)
- [ ] Write integration tests
- [ ] Deploy to Railway/Render

**Deliverables:**
- ✅ API deployed and accessible
- ✅ All endpoints tested
- ✅ API documentation published

**Owner:** Backend Dev
**Effort:** 12 hours

---

### Day 5: Payment System (x402)

**Tasks:**
- [ ] Add x402 middleware to SDK
  ```typescript
  class PaymentMiddleware {
    requirePayment(amount: string, currency: string): Middleware;
    verifyReceipt(receipt: PaymentReceipt): Promise<boolean>;
    storeReceipt(receipt: PaymentReceipt): Promise<void>;
  }
  ```
- [ ] Implement receipt verification
  ```typescript
  async function verifyPaymentReceipt(
    receipt: PaymentReceipt,
    expectedAmount: string
  ): Promise<boolean> {
    // 1. Verify signature
    const signer = recoverSigner(receipt);
    if (signer !== receipt.from) return false;

    // 2. Verify amount
    if (BigInt(receipt.amount) < BigInt(expectedAmount)) return false;

    // 3. Verify timestamp (within 60s)
    const age = Date.now() - receipt.timestamp;
    if (age > 60000) return false;

    // 4. Verify not already used
    const exists = await db.receiptExists(receipt.signature);
    if (exists) return false;

    return true;
  }
  ```
- [ ] Add receipt storage (SQLite for agents)
- [ ] Add receipt replay protection
- [ ] Write tests

**Deliverables:**
- ✅ x402 middleware functional
- ✅ Receipt verification working
- ✅ Tests passing

**Owner:** SDK Dev
**Effort:** 8 hours

---

## Week 3: Runtime Completion & First Agent

**Goal:** Complete SDK, deploy first working agent

### Day 1-2: Policy Engine

**Tasks:**
- [ ] Implement policy file loader
  ```typescript
  class PolicyEngine {
    loadPolicy(uri: string): Promise<Policy>;
    evaluateRequest(request: Request, context: Context): PolicyDecision;
    enforceShutdown(reason: string): void;
  }
  ```
- [ ] Add reputation checking
  ```typescript
  if (context.clientReputation < policy.minClientReputation) {
    return { allow: false, reason: 'reputation_too_low' };
  }
  ```
- [ ] Add auto-shutdown logic
  ```typescript
  if (ownReputation < policy.shutdownThreshold) {
    logger.warn('Reputation below shutdown threshold, stopping...');
    await runtime.stop();
  }
  ```
- [ ] Write tests

**Deliverables:**
- ✅ Policy engine working
- ✅ Reputation integration tested
- ✅ Shutdown logic verified

**Owner:** SDK Dev
**Effort:** 12 hours

---

### Day 3-4: MCP Protocol Support

**Tasks:**
- [ ] Add MCP server to runtime
  ```typescript
  class MCPServer {
    listTools(): Tool[];
    listResources(): Resource[];
    executeTool(name: string, args: any): Promise<any>;
  }
  ```
- [ ] Map capabilities to MCP tools
  ```typescript
  registerCapability('code-review', handler) =>
    MCP Tool {
      name: 'code_review',
      description: 'Review code',
      inputSchema: {...}
    }
  ```
- [ ] Add SSE endpoint for MCP
  ```
  GET /mcp/sse
  ```
- [ ] Test with MCP client (Claude Desktop)
- [ ] Write integration tests

**Deliverables:**
- ✅ MCP protocol working
- ✅ Capabilities exposed via MCP
- ✅ Tested with real MCP client

**Owner:** SDK Dev
**Effort:** 12 hours

---

### Day 5: Example Agent - CodeReviewer

**Tasks:**
- [ ] Create example agent
  ```
  examples/code-reviewer/
  ├── src/
  │   ├── index.ts
  │   ├── capabilities/
  │   │   └── codeReview.ts
  │   └── config.ts
  ├── agent.json        # Metadata
  ├── policy.json       # Policy
  ├── .env.example
  └── README.md
  ```
- [ ] Implement code review capability
  ```typescript
  async function codeReview(request: {
    code: string;
    language: string;
  }): Promise<{ review: string; issues: Issue[] }> {
    // Use LLM to review code
    const review = await openai.chat.completions.create({
      model: 'gpt-4',
      messages: [
        { role: 'system', content: 'You are a code reviewer' },
        { role: 'user', content: `Review this code:\n${request.code}` }
      ]
    });

    return {
      review: review.choices[0].message.content,
      issues: parseIssues(review)
    };
  }
  ```
- [ ] Register agent on testnet
- [ ] Deploy to Railway
- [ ] Test end-to-end payment flow

**Deliverables:**
- ✅ CodeReviewer agent running on testnet
- ✅ Payment working
- ✅ MCP endpoint functional
- ✅ Documentation complete

**Owner:** Both Devs
**Effort:** 8 hours

---

## Week 4: Testing, Polish & Testnet Launch

**Goal:** Public testnet release

### Day 1-2: Integration Testing

**Tasks:**
- [ ] Write end-to-end tests
  ```typescript
  describe('Full Agent Lifecycle', () => {
    it('should register, accept payment, execute, and earn reputation', async () => {
      // 1. Register agent
      const tx = await registry.registerAgent(metadataURI);
      const agentId = await getAgentId(tx);

      // 2. Start runtime
      const runtime = new AgentRuntime({ agentId, ... });
      await runtime.start(3000);

      // 3. Send request (expect 402)
      const res1 = await fetch('http://localhost:3000/code-review', {
        method: 'POST',
        body: JSON.stringify({ code: 'function foo() {}' })
      });
      expect(res1.status).toBe(402);

      // 4. Generate payment receipt
      const receipt = await generateReceipt(...);

      // 5. Retry with payment
      const res2 = await fetch('http://localhost:3000/code-review', {
        method: 'POST',
        headers: { 'X-Payment-Receipt': receipt },
        body: JSON.stringify({ code: 'function foo() {}' })
      });
      expect(res2.status).toBe(200);

      // 6. Submit feedback
      await reputation.submitFeedback(agentId, 5, 'Great!', receipt);

      // 7. Verify reputation updated
      const score = await indexer.getReputation(agentId);
      expect(score.avgRating).toBe(5);
    });
  });
  ```
- [ ] Test error cases
- [ ] Load test (Artillery/k6)
  ```yaml
  config:
    target: 'http://localhost:3000'
    phases:
      - duration: 60
        arrivalRate: 10
  scenarios:
    - name: 'Code Review Requests'
      flow:
        - post:
            url: '/code-review'
            json:
              code: 'function test() { return 42; }'
  ```

**Deliverables:**
- ✅ All tests passing
- ✅ Load test results documented
- ✅ Known issues documented

**Owner:** Both Devs
**Effort:** 16 hours

---

### Day 3: Documentation

**Tasks:**
- [ ] Write getting started guide
  ```markdown
  # Quick Start

  ## 1. Register Your Agent

  ## 2. Deploy Runtime

  ## 3. Configure Payment

  ## 4. Test with Client
  ```
- [ ] Create video tutorial (optional)
- [ ] Write API reference
- [ ] Add troubleshooting guide
- [ ] Create FAQ

**Deliverables:**
- ✅ Complete documentation
- ✅ Video tutorial (optional)

**Owner:** Both Devs
**Effort:** 8 hours

---

### Day 4-5: Testnet Launch

**Tasks:**
- [ ] Create landing page
  ```
  trustless-agents.dev
  - What is it?
  - How it works
  - Try demo agent
  - Documentation
  - Discord/Telegram
  ```
- [ ] Deploy 3 demo agents:
  - CodeReviewer (code analysis)
  - DataLookup (API queries)
  - ContentWriter (blog posts)
- [ ] Create agent directory UI
- [ ] Announce on Twitter/Farcaster
- [ ] Monitor for issues

**Deliverables:**
- ✅ Testnet publicly accessible
- ✅ 3+ agents running
- ✅ Documentation live
- ✅ Community channels active

**Owner:** Both Devs + Marketing
**Effort:** 16 hours

---

## Week 5: Feedback & Iteration

**Goal:** Fix bugs, improve UX, prepare for mainnet

### Day 1-3: Bug Fixes & Improvements

**Tasks:**
- [ ] Fix bugs reported by testers
- [ ] Improve error messages
- [ ] Add missing features from feedback
- [ ] Optimize database queries
- [ ] Improve logging
- [ ] Add metrics/monitoring

**Deliverables:**
- ✅ All P0 bugs fixed
- ✅ P1 bugs fixed or documented
- ✅ Performance improvements deployed

**Owner:** Both Devs
**Effort:** 24 hours

---

### Day 4-5: Security Audit

**Tasks:**
- [ ] Internal security review
  - Review smart contracts
  - Review payment verification
  - Review signature handling
  - Test for common vulnerabilities
- [ ] Fix security issues
- [ ] Document security considerations
- [ ] Optional: External audit (if budget allows)

**Deliverables:**
- ✅ Security review complete
- ✅ Issues fixed
- ✅ Security documentation updated

**Owner:** Both Devs
**Effort:** 16 hours

---

## Week 6: Mainnet Launch

**Goal:** Production deployment

### Day 1-2: Mainnet Deployment

**Tasks:**
- [ ] Deploy contracts to Base mainnet
  ```bash
  forge script script/Deploy.s.sol --rpc-url base --broadcast --verify
  ```
- [ ] Verify contracts on Basescan
- [ ] Update indexer config for mainnet
- [ ] Deploy indexer to production
- [ ] Test on mainnet with small amounts

**Deliverables:**
- ✅ Contracts deployed to mainnet
- ✅ Indexer running on mainnet
- ✅ API accessible

**Owner:** Backend Dev
**Effort:** 8 hours

---

### Day 3: Agent Migration

**Tasks:**
- [ ] Migrate demo agents to mainnet
- [ ] Register agents on mainnet
- [ ] Test payment flow with real ETH (small amounts)
- [ ] Monitor for issues
- [ ] Update documentation with mainnet addresses

**Deliverables:**
- ✅ 3+ agents running on mainnet
- ✅ Payments working
- ✅ No critical issues

**Owner:** Both Devs
**Effort:** 8 hours

---

### Day 4-5: Launch & Marketing

**Tasks:**
- [ ] Update website for mainnet
- [ ] Write launch blog post
- [ ] Tweet launch announcement
- [ ] Post on Farcaster/Lens
- [ ] Submit to Product Hunt (optional)
- [ ] Post in relevant Discord servers
- [ ] Monitor analytics
- [ ] Provide user support

**Deliverables:**
- ✅ Mainnet announced
- ✅ Users onboarding
- ✅ Support channels active

**Owner:** Both Devs + Marketing
**Effort:** 16 hours

---

## Post-Launch (Week 7+)

### Ongoing Tasks

**Weekly:**
- Monitor system health
- Review feedback
- Fix bugs
- Deploy improvements

**Monthly:**
- Publish metrics report
  - Total agents
  - Total tasks
  - Total payments
  - Avg reputation
- Plan V2 features

---

## Resource Requirements

### Team

| Role         | Availability | Responsibilities                     |
| ------------ | ------------ | ------------------------------------ |
| Backend Dev  | Full-time    | Contracts, indexer, API              |
| SDK Dev      | Full-time    | Runtime SDK, examples                |
| Marketing    | Part-time    | Docs, landing page, announcements    |

### Infrastructure

| Service      | Cost/Month | Purpose                     |
| ------------ | ---------- | --------------------------- |
| Railway      | $20        | Indexer + API hosting       |
| PostgreSQL   | $0         | Railway included            |
| Base L2      | ~$50       | Gas for testing             |
| Domain       | $15/year   | trustless-agents.dev        |
| **Total**    | **~$40/mo**|                             |

### Third-Party Services

- Alchemy/Infura (free tier)
- Pinata IPFS (free tier)
- OpenAI API (for demo agents, ~$20/mo)

---

## Risk Mitigation

| Risk                    | Mitigation                           | Owner       |
| ----------------------- | ------------------------------------ | ----------- |
| Smart contract bugs     | Thorough testing, audit              | Backend Dev |
| Payment fraud           | Signature verification, tests        | SDK Dev     |
| Low adoption            | Marketing, good docs, demo agents    | All         |
| Infrastructure issues   | Use managed services, monitoring     | Backend Dev |
| Timeline slippage       | Buffer in weeks 5-6, cut scope if needed | PM      |

---

## Success Metrics

**Week 4 (Testnet):**
- [ ] 5+ agents registered
- [ ] 50+ tasks completed
- [ ] 20+ feedbacks
- [ ] < 5 P0 bugs

**Week 6 (Mainnet):**
- [ ] 20+ agents registered
- [ ] 200+ tasks completed
- [ ] 100+ feedbacks
- [ ] 3+ different agent types
- [ ] 50+ unique users

**Month 1 (Post-Launch):**
- [ ] 50+ agents
- [ ] 1000+ tasks
- [ ] 10+ agent creators
- [ ] Positive community sentiment

---

## Contingency Plans

### If Behind Schedule

**Week 3:**
- Cut MCP support (HTTP only)
- Simplify policy engine
- Use 1 demo agent instead of 3

**Week 4:**
- Delay testnet launch by 1 week
- Skip video tutorial
- Minimal landing page

**Week 6:**
- Deploy minimal mainnet (contracts only)
- Keep agents on testnet
- Gradual migration

### If Ahead of Schedule

**Week 4:**
- Add more demo agents
- Build simple agent marketplace UI
- Add analytics dashboard

**Week 5:**
- Start V2 planning
- Build advanced features (validation system)

---

## Daily Standups

**Format:**
1. What did you complete yesterday?
2. What are you working on today?
3. Any blockers?

**Duration:** 15 minutes max

---

## Weekly Demos

**Schedule:** Every Friday at 4pm

**Format:**
- Demo what shipped this week
- Show metrics/progress
- Discuss next week's priorities

---

## Communication

**Channels:**
- **Slack/Discord:** Daily async updates
- **GitHub:** Code reviews, issues, PRs
- **Notion/Linear:** Task tracking
- **Zoom:** Weekly demos, planning

---

## Definition of Done

**For Each Task:**
- [ ] Code written
- [ ] Tests passing (>80% coverage)
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Deployed (if applicable)
- [ ] Verified working

**For Each Week:**
- [ ] All deliverables complete
- [ ] Demo prepared
- [ ] Next week planned

---

## Appendix: Detailed Task Breakdown

### Week 1, Day 1: AgentRegistryV1 Contract

**Subtasks:**
1. Create contract file (30 min)
2. Implement ERC-721 inheritance (1 hour)
3. Implement `registerAgent` (1 hour)
4. Implement `updateAgentURI` (30 min)
5. Add events (30 min)
6. Write tests (3 hours)
7. Gas optimization (1 hour)

**Total:** 7.5 hours

### Week 2, Day 1: Event Indexer Core

**Subtasks:**
1. Setup project (30 min)
2. Add ethers.js, connect to RPC (1 hour)
3. Implement event listener (2 hours)
4. Add database writes (2 hours)
5. Handle reorgs (1 hour)
6. Add error handling (1 hour)
7. Write tests (1.5 hours)

**Total:** 9 hours

*(Continue for all major tasks...)*

---

**End of Roadmap**

**Next Step:** Begin Week 1, Day 1 - Smart Contract Development
