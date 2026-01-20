# Epics & User Stories: Trustless Agent Framework

**Version:** 1.0
**Date:** 2026-01-20
**Status:** Planning

---

## Epic Organization

Epics are organized by system component and sequenced for logical build order:

1. **Identity Registry** (Foundation)
2. **Agent Runtime Core** (Off-chain foundation)
3. **Reputation System** (Trust layer)
4. **Payment & Economic Layer** (x402 integration)
5. **Validation System** (High-trust operations)
6. **Indexers & Aggregators** (Discovery & analytics)

---

## EPIC 1: Agent Identity Registry

**Goal:** Provide globally unique, censorship-resistant identities for autonomous agents.

**Priority:** P0 (Critical Path)
**Estimated Effort:** 2-3 weeks
**Dependencies:** None

### User Stories

#### Story 1.1: Agent Registration

**As an** agent creator
**I want to** register a new agent with a unique identity
**So that** my agent can be discovered and verified globally

**Acceptance Criteria:**
- [ ] Can mint a new agent NFT (ERC-721) with unique `agentId`
- [ ] Can set `agentURI` pointing to off-chain registration metadata
- [ ] AgentURI resolves to valid JSON registration file
- [ ] Registration emits `AgentRegistered` event
- [ ] Gas cost < 100k gas per registration
- [ ] Transaction can be sponsored (gasless for agent creator)

**Technical Requirements:**
- Minimal ERC-721 contract (no unnecessary features)
- IPFS or HTTPS URI support
- Event indexing compatibility

---

#### Story 1.2: Agent Metadata Resolution

**As a** client application
**I want to** discover an agent's capabilities and endpoints
**So that** I can determine if the agent meets my needs

**Acceptance Criteria:**
- [ ] Can query `agentURI` for a given `agentId`
- [ ] Registration file follows standard schema
- [ ] Metadata includes: name, description, version, endpoints, trust tiers
- [ ] Metadata includes x402 payment support flag
- [ ] Can verify metadata integrity (optional signature)

**Technical Requirements:**
- JSON schema definition for agent registration
- Client SDK for metadata resolution
- Caching strategy for repeated lookups

---

#### Story 1.3: Agent Identity Updates

**As an** agent owner
**I want to** update my agent's metadata URI
**So that** I can migrate hosting or update capabilities

**Acceptance Criteria:**
- [ ] Only agent owner can update `agentURI`
- [ ] Update emits `AgentURIUpdated` event
- [ ] Historical URIs are traceable via events
- [ ] Gas cost < 50k per update

**Technical Requirements:**
- Owner-only access control
- Event logging for auditability

---

#### Story 1.4: Agent Discovery

**As a** developer
**I want to** search for agents by capability or domain
**So that** I can find suitable agents for my use case

**Acceptance Criteria:**
- [ ] Can query all registered agents (paginated)
- [ ] Can filter by metadata tags (off-chain indexer)
- [ ] Can search by name/description (off-chain indexer)
- [ ] Results include agentId and current URI

**Technical Requirements:**
- Graph indexer (The Graph or custom)
- REST/GraphQL API for discovery
- Metadata indexing pipeline

---

## EPIC 2: Agent Runtime Core

**Goal:** Enable agents to run autonomously with self-governance capabilities.

**Priority:** P0 (Critical Path)
**Estimated Effort:** 3-4 weeks
**Dependencies:** Epic 1

### User Stories

#### Story 2.1: Cryptographic Agent Identity

**As an** agent runtime
**I want to** sign messages with my cryptographic identity
**So that** I can prove authenticity of my actions

**Acceptance Criteria:**
- [ ] Agent has EIP-712 signing capability
- [ ] Can generate and store private key securely
- [ ] Can sign structured data (requests, responses, policies)
- [ ] Signatures can be verified against on-chain agentId

**Technical Requirements:**
- Key management system (local or HSM)
- EIP-712 signing library
- Key rotation support

---

#### Story 2.2: Self-Governance Policy Engine

**As an** agent
**I want to** enforce my own operational policies
**So that** I can self-govern without external control

**Acceptance Criteria:**
- [ ] Can load policy configuration file
- [ ] Policy defines: min reputation threshold, validation requirements, shutdown conditions
- [ ] Agent automatically enforces policy rules
- [ ] Policy violations trigger configurable actions (reject, degrade, shutdown)
- [ ] Policy file is signed and verifiable

**Technical Requirements:**
- Policy schema definition (JSON/YAML)
- Policy evaluation engine
- Event logging for policy decisions

---

#### Story 2.3: Agent Memory & State Management

**As an** agent
**I want to** persist my state and conversation history
**So that** I can maintain context across sessions

**Acceptance Criteria:**
- [ ] Can store and retrieve conversation history
- [ ] Can persist task state and progress
- [ ] Memory can be local or distributed (ZeroDB)
- [ ] Memory queries are fast (< 100ms p95)

**Technical Requirements:**
- Memory abstraction layer
- Local storage backend (SQLite/RocksDB)
- Optional remote backend integration (ZeroDB)

---

#### Story 2.4: Agent Endpoint Implementation

**As an** agent
**I want to** expose multiple protocol endpoints
**So that** I can communicate via MCP, A2A, and HTTP

**Acceptance Criteria:**
- [ ] Can serve MCP protocol over stdio/SSE
- [ ] Can serve A2A protocol over HTTP
- [ ] Can serve custom HTTP endpoints
- [ ] All endpoints share same authentication
- [ ] Endpoints can require x402 payment

**Technical Requirements:**
- Multi-protocol server framework
- Authentication middleware
- Payment middleware (x402)

---

#### Story 2.5: Agent Health & Monitoring

**As an** agent operator
**I want to** monitor my agent's health and performance
**So that** I can detect and resolve issues

**Acceptance Criteria:**
- [ ] Agent exposes health check endpoint
- [ ] Metrics include: uptime, request count, error rate, avg latency
- [ ] Can configure alerting thresholds
- [ ] Metrics can be exported (Prometheus format)

**Technical Requirements:**
- Health check endpoint
- Metrics collection
- Optional monitoring integration

---

## EPIC 3: Reputation System

**Goal:** Enable trustless reputation scoring backed by verifiable events.

**Priority:** P0 (Critical Path)
**Estimated Effort:** 2-3 weeks
**Dependencies:** Epic 1, Epic 2

### User Stories

#### Story 3.1: Submit Reputation Feedback

**As a** user of an agent
**I want to** submit feedback about my experience
**So that** others can evaluate the agent's trustworthiness

**Acceptance Criteria:**
- [ ] Can submit feedback with: rating, tags, comment, proof of payment (optional)
- [ ] Feedback is signed by reviewer
- [ ] Feedback emits `FeedbackSubmitted` event on-chain
- [ ] Gas cost < 50k per feedback
- [ ] Feedback can be batched (Merkle root commitment)

**Technical Requirements:**
- Reputation contract with event logging
- Batch commitment mechanism
- EIP-712 signature verification

---

#### Story 3.2: Query Agent Reputation

**As a** potential client
**I want to** view an agent's reputation score
**So that** I can decide whether to trust the agent

**Acceptance Criteria:**
- [ ] Can query aggregated reputation score
- [ ] Score includes: total feedback count, average rating, paid vs free feedback
- [ ] Can filter feedback by: time range, tag, payment proof
- [ ] Response time < 200ms

**Technical Requirements:**
- Off-chain reputation aggregator
- Indexer for feedback events
- REST API for queries

---

#### Story 3.3: Reputation Weighting by Economic Proof

**As a** reputation aggregator
**I want to** weight feedback based on payment receipts
**So that** paid interactions count more than unpaid

**Acceptance Criteria:**
- [ ] Can verify x402 payment receipt in feedback metadata
- [ ] Paid feedback has configurable weight multiplier
- [ ] Score calculation is transparent and reproducible
- [ ] Multiple weighting schemes can coexist

**Technical Requirements:**
- x402 receipt verification
- Configurable weighting algorithm
- Score calculation documentation

---

#### Story 3.4: Sybil Resistance

**As a** reputation system
**I want to** detect and filter spam feedback
**So that** scores reflect genuine interactions

**Acceptance Criteria:**
- [ ] Can identify feedback clusters from same source
- [ ] Can require minimum payment threshold for inclusion
- [ ] Can detect collusive patterns
- [ ] Spam detection is transparent and auditable

**Technical Requirements:**
- Graph analysis for collusion detection
- Configurable spam filters
- Public audit logs

---

#### Story 3.5: Reputation History & Auditability

**As an** auditor
**I want to** trace all feedback for an agent
**So that** I can verify reputation scores independently

**Acceptance Criteria:**
- [ ] Can retrieve all historical feedback events
- [ ] Events include: timestamp, reviewer, rating, payment proof
- [ ] Can replay score calculation from events
- [ ] Events are immutable and timestamped

**Technical Requirements:**
- Event indexer with historical queries
- Score calculation algorithm documentation
- Verification tooling

---

## EPIC 4: Payment & Economic Layer (x402)

**Goal:** Enable frictionless per-request payments for agent services.

**Priority:** P0 (Critical Path)
**Estimated Effort:** 2-3 weeks
**Dependencies:** Epic 2

### User Stories

#### Story 4.1: Agent Accepts x402 Payments

**As an** agent
**I want to** require payment before executing requests
**So that** I can monetize my services autonomously

**Acceptance Criteria:**
- [ ] Agent returns HTTP 402 when payment required
- [ ] 402 response includes payment instructions (amount, address, format)
- [ ] Agent validates payment receipt on retry
- [ ] Invalid payment receipts are rejected
- [ ] Valid receipts are stored for reputation proof

**Technical Requirements:**
- x402 middleware for HTTP endpoints
- Payment receipt verification
- Receipt storage (local or ZeroDB)

---

#### Story 4.2: Client Sends x402 Payment

**As a** client
**I want to** pay for agent services per-request
**So that** I can use paid agents without subscriptions

**Acceptance Criteria:**
- [ ] Receive 402 response with payment instructions
- [ ] Generate payment receipt (signed, timestamped)
- [ ] Retry request with receipt in header
- [ ] Request succeeds with valid receipt

**Technical Requirements:**
- Client SDK with x402 support
- Payment receipt generation
- Automatic retry logic

---

#### Story 4.3: Payment Receipt as Reputation Proof

**As an** agent
**I want to** link payment receipts to reputation feedback
**So that** paid interactions strengthen my trust score

**Acceptance Criteria:**
- [ ] Payment receipt can be referenced in feedback
- [ ] Receipt includes: amount, timestamp, task hash
- [ ] Receipt signature is verifiable
- [ ] Reputation system can weight by payment amount

**Technical Requirements:**
- Receipt schema with metadata
- Linking mechanism (receipt ID in feedback)
- Verification API

---

#### Story 4.4: Optional On-Chain Payment Commitment

**As an** agent
**I want to** optionally commit payment batches on-chain
**So that** high-value payments have stronger proof

**Acceptance Criteria:**
- [ ] Can batch payment receipts into Merkle tree
- [ ] Can commit Merkle root on-chain (low gas)
- [ ] Can prove individual receipt inclusion
- [ ] Commitment is optional per agent policy

**Technical Requirements:**
- Merkle tree implementation
- Batch commitment contract
- Inclusion proof verification

---

#### Story 4.5: Payment-Based Access Tiers

**As an** agent
**I want to** offer different capabilities at different price points
**So that** I can optimize revenue and access

**Acceptance Criteria:**
- [ ] Can define pricing per capability/endpoint
- [ ] Payment receipt includes capability identifier
- [ ] Agent enforces tier-based access control
- [ ] Pricing is advertised in agent metadata

**Technical Requirements:**
- Pricing configuration schema
- Tier-based middleware
- Price discovery mechanism

---

## EPIC 5: Validation System

**Goal:** Enable independent verification for high-risk agent tasks.

**Priority:** P1 (Important)
**Estimated Effort:** 3-4 weeks
**Dependencies:** Epic 1, Epic 2, Epic 3

### User Stories

#### Story 5.1: Request Task Validation

**As an** agent
**I want to** request independent validation for high-risk tasks
**So that** clients can trust critical operations

**Acceptance Criteria:**
- [ ] Can submit validation request with: task hash, result hash, validator requirements
- [ ] Request emits `ValidationRequested` event
- [ ] Validators can claim validation tasks
- [ ] Gas cost < 100k per request

**Technical Requirements:**
- Validation registry contract
- Task claim mechanism
- Event indexing

---

#### Story 5.2: Validator Performs Verification

**As a** validator
**I want to** re-execute agent tasks to verify correctness
**So that** I can earn validation fees

**Acceptance Criteria:**
- [ ] Can retrieve task specification from validation request
- [ ] Can re-execute task in isolated environment
- [ ] Can submit validation result (pass/fail + proof)
- [ ] Result emits `ValidationCompleted` event

**Technical Requirements:**
- Validator runtime environment
- Result submission API
- Proof format specification

---

#### Story 5.3: Client Requires Validation

**As a** client
**I want to** require validation for high-value tasks
**So that** I can trust the agent's output

**Acceptance Criteria:**
- [ ] Can specify validation requirement in request
- [ ] Agent automatically requests validation
- [ ] Client receives notification when validation completes
- [ ] Can retrieve validation proof

**Technical Requirements:**
- Validation requirement protocol
- Notification mechanism (webhook/polling)
- Proof retrieval API

---

#### Story 5.4: Multiple Validation Types

**As a** system
**I want to** support different validation methods
**So that** appropriate verification is used per task type

**Acceptance Criteria:**
- [ ] Support re-execution validation
- [ ] Support TEE attestation (optional)
- [ ] Support zkML proof (optional)
- [ ] Support human review (optional)
- [ ] Validation type specified in request

**Technical Requirements:**
- Pluggable validator interfaces
- Type-specific verification logic
- Proof format per type

---

#### Story 5.5: Validation Reputation

**As a** client
**I want to** view validator reputation
**So that** I can select trustworthy validators

**Acceptance Criteria:**
- [ ] Validators have reputation scores
- [ ] Scores based on: accuracy, response time, stake
- [ ] Failed validations reduce validator score
- [ ] Clients can filter validators by min score

**Technical Requirements:**
- Validator reputation system
- Slashing mechanism for failures
- Validator discovery API

---

## EPIC 6: Indexers & Aggregators

**Goal:** Enable fast discovery and analytics for the agent ecosystem.

**Priority:** P1 (Important)
**Estimated Effort:** 2-3 weeks
**Dependencies:** Epic 1, Epic 3

### User Stories

#### Story 6.1: Real-Time Event Indexing

**As an** indexer
**I want to** capture all on-chain events in real-time
**So that** I can provide up-to-date data to clients

**Acceptance Criteria:**
- [ ] Index all AgentRegistered events
- [ ] Index all FeedbackSubmitted events
- [ ] Index all ValidationCompleted events
- [ ] Indexing latency < 10 seconds
- [ ] Support historical event replay

**Technical Requirements:**
- Blockchain event listener
- Database for indexed data
- Reorg handling

---

#### Story 6.2: Agent Discovery API

**As a** developer
**I want to** search and filter agents via API
**So that** I can build agent marketplaces and directories

**Acceptance Criteria:**
- [ ] REST/GraphQL API for agent search
- [ ] Filter by: capability tags, trust tier, reputation score
- [ ] Pagination support
- [ ] Response time < 200ms
- [ ] OpenAPI specification available

**Technical Requirements:**
- API server
- Query optimization
- API documentation

---

#### Story 6.3: Reputation Analytics

**As an** analyst
**I want to** view ecosystem-wide reputation trends
**So that** I can understand agent quality over time

**Acceptance Criteria:**
- [ ] Dashboard showing: total agents, total feedback, avg scores
- [ ] Time-series charts for reputation trends
- [ ] Breakdown by agent category
- [ ] Export data as CSV/JSON

**Technical Requirements:**
- Analytics database (time-series)
- Dashboard UI (optional)
- Data export API

---

#### Story 6.4: Payment Flow Analytics

**As a** platform operator
**I want to** track payment volume and patterns
**So that** I can understand economic activity

**Acceptance Criteria:**
- [ ] Track total payment volume (if on-chain)
- [ ] Track payment frequency
- [ ] Identify top-earning agents
- [ ] Identify most active clients

**Technical Requirements:**
- Payment event indexing
- Aggregation queries
- Privacy considerations (optional anonymization)

---

#### Story 6.5: Competitive Reputation Systems

**As a** reputation provider
**I want to** build my own scoring algorithm
**So that** I can differentiate my service

**Acceptance Criteria:**
- [ ] Can access all raw feedback events via API
- [ ] Can compute custom scores independently
- [ ] Can publish scores via standard format
- [ ] Multiple systems can coexist

**Technical Requirements:**
- Public event data API
- Score publication schema
- Registry of reputation providers

---

## Cross-Epic Stories

### Story X.1: End-to-End Agent Lifecycle

**As an** agent creator
**I want to** deploy a complete agent from registration to earning
**So that** I can participate in the ecosystem

**Acceptance Criteria:**
- [ ] Register agent identity
- [ ] Deploy agent runtime
- [ ] Configure x402 payment
- [ ] Receive first paid request
- [ ] Earn first reputation feedback
- [ ] Complete end-to-end in < 1 hour

**Technical Requirements:**
- Complete documentation
- Quick-start guide
- Sample agent implementation

---

### Story X.2: Progressive Trust Demo

**As a** developer
**I want to** see agents operating at different trust tiers
**So that** I understand the trust model

**Acceptance Criteria:**
- [ ] Demo agent at Tier 0 (identity only)
- [ ] Demo agent at Tier 2 (reputation + payment)
- [ ] Demo agent at Tier 3 (validation required)
- [ ] Clear documentation of tier differences

**Technical Requirements:**
- Sample implementations per tier
- Tutorial documentation
- Video walkthrough (optional)

---

## Story Estimation Guide

- **Small (1-2 days):** Single contract function, simple API endpoint
- **Medium (3-5 days):** Full contract, complex API, client SDK feature
- **Large (1-2 weeks):** Multiple contracts, full subsystem, runtime feature

---

## Success Metrics

Track these metrics to measure epic success:

**Epic 1 - Identity:**
- Agents registered
- Registration gas cost
- Metadata resolution success rate

**Epic 2 - Runtime:**
- Agent uptime
- Request latency
- Policy enforcement rate

**Epic 3 - Reputation:**
- Feedback submissions
- Score calculation time
- Spam detection accuracy

**Epic 4 - Payments:**
- Payment success rate
- Payment verification time
- Revenue per agent

**Epic 5 - Validation:**
- Validation requests
- Validator accuracy
- Validation turnaround time

**Epic 6 - Indexers:**
- Indexing latency
- API response time
- Query accuracy

---

## Next Steps

After reviewing these epics and stories:

1. Prioritize stories within each epic
2. Assign stories to sprints
3. Define technical spikes for unknowns
4. Create detailed task breakdowns
5. Begin implementation with Epic 1
