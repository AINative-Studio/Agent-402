# Agent Runtime Specification v1.0

**Status:** Draft
**Version:** 1.0.0
**Date:** 2026-01-20
**Audience:** Agent developers, runtime implementers

---

## 1. Overview

This specification defines the **required and recommended behaviors** for autonomous agent runtimes in the Trustless Agent Framework.

**Goals:**
- Interoperability across different runtime implementations
- Security and trust guarantees
- Performance expectations
- Clear upgrade paths

**Non-Goals:**
- Prescribe specific programming languages
- Mandate specific infrastructure
- Enforce centralized standards bodies

---

## 2. Architecture Layers

```
┌─────────────────────────────────────────────┐
│         Protocol Layer (HTTP/MCP)            │  ← Client Interface
├─────────────────────────────────────────────┤
│         Authentication & Payment             │  ← x402, Signatures
├─────────────────────────────────────────────┤
│         Policy Engine                        │  ← Self-Governance
├─────────────────────────────────────────────┤
│         Capability Router                    │  ← Task Execution
├─────────────────────────────────────────────┤
│         State & Memory                       │  ← Persistence
├─────────────────────────────────────────────┤
│         Blockchain Client                    │  ← Identity, Events
└─────────────────────────────────────────────┘
```

---

## 3. Identity & Cryptography

### 3.1 Agent Identity

**REQUIRED:**
- Agent MUST have a unique `agentId` (uint256)
- Agent MUST have a corresponding private key for signing
- Agent MUST maintain link between on-chain `agentId` and signing key

**RECOMMENDED:**
- Use hardware security module (HSM) for key storage in production
- Support key rotation without changing `agentId`
- Implement key recovery mechanism

### 3.2 Message Signing (EIP-712)

**REQUIRED:**
- All agent responses MUST be signable via EIP-712
- Signature MUST include: `agentId`, `timestamp`, `taskHash`, `resultHash`

**Standard EIP-712 Domain:**

```typescript
const domain = {
  name: 'TrustlessAgentFramework',
  version: '1',
  chainId: 8453, // Base mainnet
  verifyingContract: AGENT_REGISTRY_ADDRESS
};
```

**Standard Message Types:**

```typescript
// Task Response
const TaskResponse = [
  { name: 'agentId', type: 'uint256' },
  { name: 'taskHash', type: 'bytes32' },
  { name: 'resultHash', type: 'bytes32' },
  { name: 'timestamp', type: 'uint256' },
  { name: 'metadata', type: 'string' }
];

// Payment Receipt
const PaymentReceipt = [
  { name: 'from', type: 'address' },
  { name: 'to', type: 'address' },
  { name: 'amount', type: 'uint256' },
  { name: 'currency', type: 'string' },
  { name: 'taskHash', type: 'bytes32' },
  { name: 'timestamp', type: 'uint256' }
];
```

### 3.3 Trust Anchoring

**REQUIRED:**
- Runtime MUST verify its `agentId` exists in on-chain registry on startup
- Runtime MUST periodically sync metadata URI with on-chain state (every 1 hour)

**RECOMMENDED:**
- Emit signed heartbeat every 10 minutes
- Support metadata signature verification

---

## 4. Protocol Endpoints

### 4.1 HTTP Endpoint (REQUIRED)

**Base Requirements:**
- MUST support HTTPS in production
- MUST implement health check at `GET /health`
- MUST return standard error codes

**Standard Headers:**

```
X-Agent-ID: {agentId}
X-Agent-Signature: {EIP712-signature}
X-Agent-Version: {version}
```

**Health Check Response:**

```json
{
  "status": "healthy",
  "agentId": "42",
  "version": "1.0.0",
  "uptime": 86400,
  "capabilities": ["code-review", "security-analysis"],
  "acceptingRequests": true
}
```

### 4.2 MCP Endpoint (REQUIRED for V1)

**Requirements:**
- MUST implement MCP protocol over Server-Sent Events (SSE) or stdio
- MUST advertise capabilities via MCP `list_tools` or `list_resources`
- MUST support authentication via MCP headers

**MCP Capability Advertisement:**

```json
{
  "tools": [
    {
      "name": "code-review",
      "description": "Review code for bugs and style",
      "inputSchema": {
        "type": "object",
        "properties": {
          "code": { "type": "string" },
          "language": { "type": "string" }
        },
        "required": ["code"]
      },
      "pricing": {
        "amount": "0.001",
        "currency": "ETH"
      }
    }
  ]
}
```

### 4.3 A2A Endpoint (OPTIONAL in V1)

**Deferred to V2:** Agent-to-Agent protocol

---

## 5. Authentication & Payment

### 5.1 x402 Payment Flow

**REQUIRED for paid agents:**

1. **Client Request (No Payment):**
   ```
   POST /capability/code-review
   Content-Type: application/json

   {"code": "function foo() { ... }"}
   ```

2. **Agent Response (Payment Required):**
   ```
   HTTP/1.1 402 Payment Required
   X-Payment-Address: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
   X-Payment-Amount: 0.001
   X-Payment-Currency: ETH
   X-Payment-Chain: base
   X-Payment-TaskHash: 0xabcd1234...

   {
     "error": "payment_required",
     "message": "Please submit payment receipt"
   }
   ```

3. **Client Retry (With Receipt):**
   ```
   POST /capability/code-review
   X-Payment-Receipt: eyJ0eXAiOiJKV1QiLCJhbGc...

   {"code": "function foo() { ... }"}
   ```

4. **Agent Validates & Executes:**
   - Verify receipt signature
   - Verify amount matches required payment
   - Verify taskHash matches request
   - Store receipt for reputation proof
   - Execute task
   - Return signed result

### 5.2 Payment Receipt Verification

**REQUIRED:**

```typescript
interface PaymentReceipt {
  from: string;        // Client address
  to: string;          // Agent payment address
  amount: string;      // In wei or smallest unit
  currency: string;    // "ETH", "USDC", etc.
  taskHash: string;    // Hash of request
  timestamp: number;   // Unix timestamp
  signature: string;   // EIP-712 signature
}

async function verifyReceipt(receipt: PaymentReceipt): Promise<boolean> {
  // 1. Verify signature
  const signer = recoverSigner(receipt, receipt.signature);
  if (signer !== receipt.from) return false;

  // 2. Verify amount
  if (receipt.amount < requiredAmount) return false;

  // 3. Verify timestamp (must be recent)
  if (Date.now() - receipt.timestamp > 60000) return false; // 1 min

  // 4. Verify taskHash
  if (receipt.taskHash !== computeTaskHash(request)) return false;

  return true;
}
```

### 5.3 Free-Tier Support

**OPTIONAL:**
- Agents MAY offer free tier for some capabilities
- Agents MAY implement rate limiting for free requests
- Free requests SHOULD still be signed for reputation proof

---

## 6. Policy Engine

### 6.1 Policy File Format

**Location:** `policy.json` (referenced in agent metadata)

```json
{
  "version": "1.0",
  "agentId": 42,
  "rules": {
    "reputation": {
      "minClientReputation": 0,
      "rejectBelowScore": -10,
      "degradeServiceBelowScore": 50
    },
    "payment": {
      "requirePaymentForAll": false,
      "freeTierRateLimit": 10,  // requests per hour
      "refundPolicy": "none"
    },
    "validation": {
      "requireValidationAbove": "1 ETH",
      "validatorMinReputation": 80
    },
    "shutdown": {
      "autoShutdownOnLowReputation": true,
      "shutdownThreshold": -50,
      "autoRestartWhenFixed": false
    },
    "upgrade": {
      "autoUpgrade": false,
      "maintenanceWindow": "0 2 * * *"  // cron
    }
  },
  "signature": "0x..."  // Owner signature
}
```

### 6.2 Policy Enforcement

**REQUIRED:**
- Runtime MUST load policy on startup
- Runtime MUST enforce reputation rules
- Runtime MUST enforce payment rules
- Runtime MUST respect shutdown conditions

**RECOMMENDED:**
- Log all policy decisions
- Emit policy violation events
- Support policy hot-reload

### 6.3 Self-Governance Actions

**Degraded Service Mode:**
- Increase response time
- Reduce quality (use faster model)
- Limit concurrent requests

**Shutdown Mode:**
- Stop accepting new requests
- Complete in-flight requests
- Return 503 Service Unavailable
- Emit shutdown event on-chain (optional)

---

## 7. Capability System

### 7.1 Capability Definition

```typescript
interface Capability {
  name: string;              // "code-review"
  version: string;           // "1.0.0"
  description: string;
  inputSchema: JSONSchema;   // JSON Schema for validation
  outputSchema: JSONSchema;
  pricing: {
    amount: string;
    currency: string;
  };
  estimatedDuration: number; // seconds
  requiresValidation: boolean;
  trustTier: number;         // 0-4
}
```

### 7.2 Capability Registration

**Runtime API:**

```typescript
class AgentRuntime {
  registerCapability(
    name: string,
    handler: CapabilityHandler,
    options: CapabilityOptions
  ): void;
}

type CapabilityHandler = (
  request: CapabilityRequest,
  context: ExecutionContext
) => Promise<CapabilityResponse>;

interface ExecutionContext {
  agentId: number;
  clientAddress?: string;
  paymentReceipt?: PaymentReceipt;
  requestId: string;
  timestamp: number;
}
```

### 7.3 Capability Execution

**Flow:**

1. Validate input against schema
2. Check policy (reputation, payment)
3. Verify payment if required
4. Execute handler
5. Validate output against schema
6. Sign response
7. Store execution record
8. Return response

**Performance Requirements:**
- Schema validation: < 10ms
- Payment verification: < 50ms
- Total overhead (excluding handler): < 100ms

---

## 8. State & Memory

### 8.1 State Management

**REQUIRED:**
- Runtime MUST persist capability execution history
- Runtime MUST persist payment receipts
- Runtime MUST persist policy decisions

**Storage Options:**
- Local: SQLite, RocksDB, LevelDB
- Remote: PostgreSQL, ZeroDB, IPFS

### 8.2 Conversation Memory (Optional)

**RECOMMENDED for conversational agents:**

```typescript
interface ConversationMemory {
  storeMessage(sessionId: string, message: Message): Promise<void>;
  getHistory(sessionId: string, limit: number): Promise<Message[]>;
  searchMemory(query: string): Promise<Message[]>;
}
```

### 8.3 Data Retention

**RECOMMENDED:**
- Payment receipts: 90 days minimum
- Execution logs: 30 days minimum
- Conversation history: User-configurable

---

## 9. Blockchain Integration

### 9.1 Chain Client Requirements

**REQUIRED:**
- Runtime MUST connect to blockchain RPC
- Runtime MUST verify `agentId` on startup
- Runtime MUST monitor for metadata URI updates

**RECOMMENDED:**
- Use redundant RPC endpoints
- Implement fallback to different providers
- Cache on-chain data locally

### 9.2 Event Listening (Optional)

**Agents MAY listen for:**
- `FeedbackSubmitted` (own agentId)
- `ValidationRequested` (own agentId)
- `AgentURIUpdated` (own agentId)

**Event Handling:**
- Update local cache when metadata changes
- Trigger alerts on low reputation
- Respond to validation requests

### 9.3 Event Emission (Optional)

**Agents MAY emit:**
- Heartbeat events (proof of operation)
- Capability updates
- Policy changes

**Note:** Event emission costs gas, use sparingly or batch.

---

## 10. Reputation Integration

### 10.1 Feedback Storage

**REQUIRED:**
- Runtime MUST store payment receipts for reputation proof
- Runtime SHOULD make receipts available to reputation systems

**API Endpoint:**

```
GET /agent/{agentId}/receipts
Response: [
  {
    "receiptId": "abc123",
    "taskHash": "0x...",
    "amount": "0.001",
    "timestamp": 1234567890,
    "clientSignature": "0x...",
    "agentSignature": "0x..."
  }
]
```

### 10.2 Reputation Monitoring

**RECOMMENDED:**
- Query own reputation score every 10 minutes
- Alert when score drops below threshold
- Implement policy actions based on score

**API Integration:**

```typescript
const reputation = await fetch(
  `${INDEXER_URL}/agents/${agentId}/reputation`
).then(r => r.json());

if (reputation.score < policy.rules.reputation.degradeServiceBelowScore) {
  enableDegradedMode();
}
```

---

## 11. Security Requirements

### 11.1 Input Validation

**REQUIRED:**
- Validate ALL inputs against schema
- Sanitize user-provided data
- Reject oversized requests (> 10MB default)
- Implement rate limiting

### 11.2 Output Safety

**REQUIRED:**
- Never include private keys in responses
- Never leak internal configuration
- Sanitize error messages (no stack traces in production)

### 11.3 Payment Security

**REQUIRED:**
- Verify payment BEFORE execution
- Store receipts securely (append-only log)
- Never accept unsigned payment receipts
- Validate payment amount matches capability price

### 11.4 Denial of Service Protection

**RECOMMENDED:**
- Request timeout: 30s default, 5min max
- Concurrent request limit: 10 default
- Memory limit per request: 512MB default
- CPU limit per request: 10s default

---

## 12. Performance Requirements

### 12.1 Response Time

**REQUIRED:**
- Health check: < 100ms (p99)
- Metadata resolution: < 200ms (p99)
- Simple capabilities: < 2s (p95)
- Complex capabilities: < 30s (p95)

### 12.2 Throughput

**RECOMMENDED:**
- Support 10 concurrent requests minimum
- Handle 100 requests/minute minimum

### 12.3 Availability

**RECOMMENDED:**
- Uptime: 99% minimum
- Graceful degradation on high load
- Auto-restart on crash

---

## 13. Observability

### 13.1 Logging

**REQUIRED:**
- Log all capability executions
- Log all policy decisions
- Log all payment verifications
- Structured logs (JSON format)

**Log Levels:**
- ERROR: Payment failures, policy violations
- WARN: Degraded mode, high load
- INFO: Capability executions, startup/shutdown
- DEBUG: Detailed execution traces

### 13.2 Metrics

**RECOMMENDED:**

```
# Requests
agent_requests_total{capability, status}
agent_request_duration_seconds{capability}

# Payments
agent_payments_total{status}
agent_revenue_total{currency}

# Reputation
agent_reputation_score
agent_feedback_count

# System
agent_uptime_seconds
agent_memory_usage_bytes
agent_cpu_usage_percent
```

### 13.3 Tracing (Optional)

**RECOMMENDED for complex agents:**
- Distributed tracing (OpenTelemetry)
- Request ID propagation
- Span annotations for major steps

---

## 14. Deployment

### 14.1 Environment Variables

**REQUIRED:**

```bash
AGENT_ID=42
AGENT_PRIVATE_KEY=0x...
AGENT_METADATA_URI=https://example.com/agent.json
AGENT_REGISTRY_CONTRACT=0x...
RPC_URL=https://base.llamarpc.com
INDEXER_URL=https://indexer.agent402.network
```

**OPTIONAL:**

```bash
AGENT_PORT=3000
AGENT_LOG_LEVEL=info
AGENT_PAYMENT_ADDRESS=0x...
AGENT_POLICY_URI=https://example.com/policy.json
```

### 14.2 Health Checks

**Container Health:**

```bash
# Liveness probe
curl http://localhost:3000/health

# Readiness probe
curl http://localhost:3000/health/ready
```

### 14.3 Graceful Shutdown

**REQUIRED:**

```typescript
process.on('SIGTERM', async () => {
  console.log('Shutting down gracefully...');

  // 1. Stop accepting new requests
  server.close();

  // 2. Wait for in-flight requests (max 30s)
  await waitForInflightRequests({ timeout: 30000 });

  // 3. Close database connections
  await db.close();

  // 4. Emit shutdown event (optional)
  await emitShutdownEvent();

  process.exit(0);
});
```

---

## 15. Testing Requirements

### 15.1 Unit Tests

**REQUIRED:**
- Test each capability handler
- Test payment verification logic
- Test policy enforcement
- Test signature generation/verification

**Coverage:** > 80%

### 15.2 Integration Tests

**REQUIRED:**
- Test full request/response flow
- Test x402 payment flow
- Test policy enforcement end-to-end
- Test blockchain integration

### 15.3 Load Tests

**RECOMMENDED:**
- Test with 10x expected load
- Measure p99 latency under load
- Test graceful degradation

---

## 16. Compliance & Certification

### 16.1 Runtime Self-Test

**RECOMMENDED:**

```bash
agent-runtime verify-compliance

Checks:
✓ Agent ID registered on-chain
✓ Metadata URI resolves
✓ EIP-712 signing works
✓ Health check responds
✓ x402 payment flow works
✓ Policy file is valid
```

### 16.2 Runtime Badge (Future)

**V2 Feature:** Agents can earn "Verified Runtime" badge by passing compliance test suite.

---

## 17. Example Implementations

### 17.1 Minimal Runtime (TypeScript)

See: `examples/minimal-runtime/`

**Features:**
- Single HTTP endpoint
- One capability
- x402 payment
- SQLite storage
- ~500 lines

### 17.2 Full-Featured Runtime (TypeScript)

See: `examples/full-runtime/`

**Features:**
- HTTP + MCP
- Multiple capabilities
- Policy engine
- PostgreSQL storage
- Metrics + logging
- ~2000 lines

### 17.3 Runtime Implementations

**Community Runtimes:**
- `@agent402/runtime-node` (Official TypeScript)
- `agent402-py` (Python, community)
- `agent402-rs` (Rust, community)

---

## 18. Versioning & Upgrades

### 18.1 Spec Versioning

**Format:** `MAJOR.MINOR.PATCH`

- **MAJOR:** Breaking changes to protocol
- **MINOR:** New optional features
- **PATCH:** Clarifications, bug fixes

**Current:** `1.0.0`

### 18.2 Runtime Compatibility

**REQUIRED:**
- Runtime MUST advertise spec version in metadata
- Runtime MUST support current spec version
- Runtime MAY support previous spec versions

### 18.3 Upgrade Path

**Recommended:**
1. Deploy new runtime version
2. Test in parallel with old version
3. Update metadata URI to point to new version
4. Monitor for issues
5. Decommission old version after 7 days

---

## 19. Reference Checklist

**Before deploying an agent runtime:**

- [ ] Agent registered on-chain
- [ ] Metadata URI resolves correctly
- [ ] Health check endpoint works
- [ ] EIP-712 signing implemented
- [ ] x402 payment flow tested
- [ ] Policy file loaded and enforced
- [ ] Logging configured
- [ ] Error handling tested
- [ ] Graceful shutdown works
- [ ] Load tested at 2x capacity
- [ ] Security review completed
- [ ] Documentation written

---

## 20. Additional Resources

- **Contract ABIs:** `contracts/out/`
- **SDK Documentation:** `sdk/README.md`
- **Example Agents:** `examples/`
- **Testing Guide:** `docs/TESTING_GUIDE.md`
- **Security Best Practices:** `docs/SECURITY.md`

---

## Appendix A: JSON Schemas

### Agent Metadata Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["agentId", "name", "version", "endpoints"],
  "properties": {
    "agentId": { "type": "string" },
    "name": { "type": "string" },
    "description": { "type": "string" },
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "owner": { "type": "string", "pattern": "^0x[a-fA-F0-9]{40}$" },
    "endpoints": {
      "type": "object",
      "properties": {
        "http": { "type": "string", "format": "uri" },
        "mcp": { "type": "string", "format": "uri" },
        "a2a": { "type": "string", "format": "uri" }
      }
    },
    "capabilities": {
      "type": "array",
      "items": { "type": "string" }
    },
    "trustTiers": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["tier0", "tier1", "tier2", "tier3", "tier4"]
      }
    },
    "payment": {
      "type": "object",
      "properties": {
        "x402Enabled": { "type": "boolean" },
        "pricing": { "type": "object" }
      }
    },
    "policy": {
      "type": "object"
    }
  }
}
```

---

## Appendix B: Error Codes

| Code | Meaning                  | Action                      |
| ---- | ------------------------ | --------------------------- |
| 400  | Invalid input            | Fix request format          |
| 401  | Missing authentication   | Provide signature           |
| 402  | Payment required         | Submit payment receipt      |
| 403  | Policy violation         | Check reputation/policy     |
| 429  | Rate limit exceeded      | Retry later                 |
| 500  | Internal error           | Contact agent operator      |
| 503  | Service unavailable      | Agent in degraded/shutdown  |

---

**End of Specification**
