# Agent 402 Codebase Analysis: Payment, Transaction, and Control Systems

## Executive Summary

The Agent 402 platform implements a comprehensive agent hiring and payment system with multi-layered financial controls, audit trails, and compliance mechanisms. The architecture combines blockchain-based payments (USDC via Circle), DIDs for agent identity, and policy enforcement through compliance agents.

---

## 1. CURRENT PAYMENT/TRANSACTION CAPABILITIES

### 1.1 X402 Protocol - Payment Authorization Framework
**File**: `/Users/aideveloper/Agent-402/backend/app/schemas/x402_protocol.py`
**File**: `/Users/aideveloper/Agent-402/backend/app/services/x402_service.py`

**Core Capabilities**:
- Root-level `/x402` POST endpoint accepts DID-signed payment requests
- Payload format: `{did, signature, payload}`
- Cryptographic signature verification for non-repudiation
- Public endpoint (no X-API-Key required for discovery)

**Request Payload Structure**:
```json
{
  "did": "did:ethr:0xabc123...",
  "signature": "0x8f3e9a7c2b1d4e6f5a8c9b0e3d7f1a4c...",
  "payload": {
    "type": "payment_authorization",
    "amount": "100.00",
    "currency": "USD",
    "recipient": "did:ethr:0xdef789...",
    "memo": "Payment for task completion",
    "timestamp": "2026-01-11T12:34:56.789Z"
  }
}
```

**Current Status**: Request validation and logging implemented. Cryptographic verification (Issue #75) is TODO.

### 1.2 Circle Gateway Integration - Gasless Payments
**File**: `/Users/aideveloper/Agent-402/backend/app/services/gateway_service.py`
**File**: `/Users/aideveloper/Agent-402/backend/app/api/gateway.py`

**Capabilities**:
- Gasless payment verification via Circle x402 Batching SDK
- X-Payment-Signature header validation
- Payment signature replay protection via nonce validation
- 5-minute signature expiration timeout
- Batched settlement to Arc Testnet AgentTreasury contract
- Amount validation before accepting payment

**Gateway Flow**:
1. User deposits USDC to Gateway (one-time setup)
2. User signs payment intent (gasless, no gas fees)
3. Backend verifies X-Payment-Signature header
4. Gateway batches payments and settles periodically (~10 min)

**Payment Endpoints**:
- `POST /v1/public/gateway/{project_id}/hire-agent` - Hire agent with gasless payment
- `POST /v1/public/gateway/deposit` - Get deposit instructions

### 1.3 USDC Transfer Management
**File**: `/Users/aideveloper/Agent-402/backend/app/services/circle_wallet_service.py`

**Wallet Management**:
- Create agent wallets via Circle API
- Support for 3 wallet types per agent: analyst, compliance, transaction
- Wallet linking to agent DIDs
- Blockchain address management (ETH-SEPOLIA)
- Balance tracking and updates

**Transfer Operations**:
- Initiate USDC transfers between wallets
- Transfer status tracking (pending, complete)
- Transaction hash tracking
- Support for linked X402 requests
- Idempotency keys for duplicate prevention

**Transfer Data Captured**:
```python
{
    "transfer_id": "transfer_abc123",
    "source_wallet_id": "wallet_src",
    "destination_wallet_id": "wallet_dst",
    "amount": "10.50",
    "currency": "USD",
    "status": "complete",
    "transaction_hash": "0x...",
    "x402_request_id": "x402_req_abc123",
    "created_at": "2026-01-23T12:00:00Z",
    "completed_at": "2026-01-23T12:00:05Z"
}
```

### 1.4 Payment Receipt System
**File**: `/Users/aideveloper/Agent-402/backend/app/services/x402_payment_tracker.py`
**File**: `/Users/aideveloper/Agent-402/backend/app/schemas/payment_tracking.py`

**Receipt Tracking**:
- Payment receipts stored with full traceability
- Linked to X402 requests for audit trail
- USDC transaction hash storage
- Arc contract payment ID linkage
- Treasury ID tracking (source and destination)

**Payment Status Lifecycle**:
- `PENDING`: Payment initiated, awaiting confirmation
- `CONFIRMED`: Payment confirmed on-chain
- `FAILED`: Payment failed
- `REFUNDED`: Payment was refunded

**Receipt Data**:
```python
{
    "receipt_id": "pay_rcpt_a1b2c3d4",
    "x402_request_id": "x402_req_abc123",
    "from_agent_id": "agent_001",
    "to_agent_id": "agent_002",
    "amount_usdc": "1.500000",  # 6 decimals preserved
    "purpose": "x402-api-call",
    "status": "confirmed",
    "transaction_hash": "0xabc123...",
    "arc_payment_id": 42,
    "treasury_from_id": 1,
    "treasury_to_id": 2,
    "created_at": "2026-01-23T12:00:00Z",
    "confirmed_at": "2026-01-23T12:00:05Z"
}
```

---

## 2. AGENT WALLET IMPLEMENTATION

### 2.1 Agent Identity & DID System
**File**: `/Users/aideveloper/Agent-402/backend/app/models/agent.py`
**File**: `/Users/aideveloper/Agent-402/backend/app/schemas/agents.py`

**DID Format**:
- Required format: `did:key:z6Mk...`
- Validation: Must start with `did:key:z6Mk` and be minimum 10 chars
- Example: `did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK`

**Agent Attributes**:
```python
{
    "id": "agent_abc123def456",
    "did": "did:key:z6MkhaXgBZ...",
    "role": "analyst|compliance|transaction|orchestrator",
    "name": "Research Agent Alpha",
    "description": "Specialized agent for financial research",
    "scope": "SYSTEM|PROJECT|RUN",
    "project_id": "proj_xyz789",
    "created_at": "2026-01-23T12:00:00Z",
    "updated_at": "2026-01-23T12:00:00Z"
}
```

### 2.2 Circle Wallet Integration
**File**: `/Users/aideveloper/Agent-402/backend/app/services/circle_wallet_service.py`

**Wallet Lifecycle**:
1. Create wallet via Circle API (blockchain: ETH-SEPOLIA)
2. Store wallet metadata in ZeroDB with agent DID linkage
3. Track wallet blockchain address
4. Monitor USDC balance

**Wallet Metadata**:
```python
{
    "wallet_id": "wallet_abc123",
    "circle_wallet_id": "circle_id_123",
    "agent_did": "did:key:z6Mk...",
    "wallet_type": "analyst|compliance|transaction",
    "status": "active",
    "blockchain_address": "0x1234567890abcdef...",
    "blockchain": "ETH-SEPOLIA",
    "balance": "0.00",
    "description": "Analyst wallet for agent xyz",
    "created_at": "2026-01-23T12:00:00Z"
}
```

**Features**:
- Duplicate wallet prevention (one per type per agent)
- Automatic balance fetching from Circle
- Idempotency keys for fault tolerance
- Multi-wallet support per agent

---

## 3. POLICY & CONTROL MECHANISMS

### 3.1 Authentication & Authorization
**File**: `/Users/aideveloper/Agent-402/backend/app/core/auth.py`
**File**: `/Users/aideveloper/Agent-402/backend/app/core/ainative_auth.py`
**File**: `/Users/aideveloper/Agent-402/backend/app/middleware/api_key_auth.py`

**Dual Authentication Modes**:
1. **X-API-Key**: Static API key authentication (per user)
2. **JWT Bearer Token**: Supports AINative Studio tokens + local JWT

**API Key Validation**:
- All missing/invalid/malformed keys return 401 INVALID_API_KEY
- Minimum length: 10 characters
- Valid chars: alphanumeric, underscore, hyphen
- Expired key prefix: `expired_*`

**JWT Token Support**:
- AINative validation via `https://api.ainative.studio/v1/public/auth/me`
- Local JWT decoding fallback
- Token cache with 5-minute TTL
- Token expiration detection

**Authorization Points**:
- All `/v1/public/*` endpoints require authentication
- Exempt paths: health, docs, login, x402 discovery, public model listing
- Middleware validates before route handler execution

### 3.2 Compliance Events & Audit Trail
**File**: `/Users/aideveloper/Agent-402/backend/app/services/compliance_service.py`
**File**: `/Users/aideveloper/Agent-402/backend/app/schemas/compliance_events.py`

**Compliance Event Types**:
- `KYC_CHECK`: Know Your Customer verification
- `KYT_CHECK`: Know Your Transaction analysis
- `RISK_ASSESSMENT`: Risk scoring and assessment
- `COMPLIANCE_DECISION`: Final compliance decisions
- `AUDIT_LOG`: Audit trail entries

**Compliance Outcomes**:
- `PASS`: Compliance check passed
- `FAIL`: Compliance check failed
- `PENDING`: Awaiting further review
- `ESCALATED`: Escalated for manual review
- `ERROR`: Error during processing

**Event Data**:
```python
{
    "event_id": "evt_abc123def456",
    "project_id": "proj_xyz789",
    "agent_id": "compliance_agent_001",
    "event_type": "KYC_CHECK",
    "outcome": "PASS",
    "risk_score": 0.15,  # 0.0-1.0 float
    "details": {
        "customer_id": "cust_12345",
        "verification_method": "document",
        "confidence_score": 0.95
    },
    "run_id": "run_abc123",
    "timestamp": "2026-01-10T12:34:56.789Z"
}
```

**Risk Level Calculation**:
- 0.0-0.25: LOW
- 0.25-0.5: MEDIUM
- 0.5-0.75: HIGH
- 0.75-1.0: CRITICAL

### 3.3 Signature Verification (DID Signing)
**File**: `/Users/aideveloper/Agent-402/backend/app/api/x402_requests.py` (calls DIDSigner)

**Signature Verification Process**:
1. Extract signature from X402 request
2. Verify ECDSA signature against agent DID
3. Reject invalid signatures with 401 Unauthorized
4. Add `signature_verified` metadata to request

**Error Handling**:
- Invalid signature: HTTP 401 "Invalid signature: signature verification failed"
- Invalid DID format: HTTP 401 "Invalid DID format"
- Verification errors: HTTP 401 "Signature verification error"

---

## 4. AUDIT TRAIL & LOGGING

### 4.1 X402 Request Linkage
**File**: `/Users/aideveloper/Agent-402/backend/app/services/x402_service.py`

**Audit Trail Components**:
- **Agent Linkage**: Every X402 request linked to originating agent_id
- **Task Linkage**: Every X402 request linked to task_id that produced it
- **Run Context**: Execution context captured via run_id
- **Memory Links**: Optional links to agent_memory records (decision context)
- **Compliance Links**: Optional links to compliance_events records

**X402 Request Structure**:
```python
{
    "request_id": "x402_req_abc123",
    "project_id": "proj_xyz",
    "agent_id": "agent_001",
    "task_id": "task_payment_001",
    "run_id": "run_2026_01_10_001",
    "request_payload": {
        "type": "payment_authorization",
        "amount": "100.00",
        "method": "POST",
        "url": "/api/payment"
    },
    "signature": "0xsig123...",
    "status": "PENDING|APPROVED|REJECTED|EXPIRED|COMPLETED",
    "timestamp": "2026-01-10T12:34:56.789Z",
    "linked_memory_ids": ["mem_abc123", "mem_def456"],
    "linked_compliance_ids": ["comp_evt_001"],
    "metadata": {
        "priority": "high",
        "source": "payment_agent",
        "signature_verified": true
    }
}
```

**Query Capabilities**:
- List requests by agent_id
- List requests by task_id
- List requests by run_id
- Filter by status
- Pagination support (limit/offset)

### 4.2 Payment Receipt Audit
**File**: `/Users/aideveloper/Agent-402/backend/app/services/x402_payment_tracker.py`

**Full Transaction Traceability**:
- Receipt ID uniquely identifies payment
- X402 request ID links to authorization
- From/To agent IDs document flow
- Blockchain transaction hash captured
- Arc contract payment ID stored
- Treasury IDs tracked

**Operational Timeline**:
- `created_at`: When payment receipt generated
- `confirmed_at`: When payment confirmed on-chain
- Status transitions: pending → confirmed → settled

### 4.3 Compliance Event Storage
**File**: `/Users/aideveloper/Agent-402/backend/app/services/compliance_service.py`

**Event Persistence**:
- Deterministic event IDs (format: `evt_{uuid}`)
- Project-level organization
- Full auditability with timestamps
- Agent identification
- Filterable by type, outcome, risk range, time

**Statistics & Analytics**:
- Project event count
- Events grouped by type
- Events grouped by outcome
- Average risk score calculation

---

## 5. SPEND MANAGEMENT FEATURES

### 5.1 Payment Amount Validation
**File**: `/Users/aideveloper/Agent-402/backend/app/services/gateway_service.py`

**Validation Rules**:
- Base rate: $10 per task
- Complexity multiplier: 1.0 + (description_length - 100) / 1000
- Formula: `amount = base_rate * complexity_multiplier`

**Example Calculations**:
- 100 char description: $10.00
- 1100 char description: $11.00
- 2100 char description: $12.00

**Payment Verification Steps**:
1. Calculate required amount
2. Check for X-Payment-Signature header (402 if missing)
3. Validate payment amount meets requirement (402 if insufficient)
4. Verify signature with Circle Gateway API (401 if invalid)

### 5.2 Wallet Balance Management
**File**: `/Users/aideveloper/Agent-402/backend/app/services/circle_wallet_service.py`

**Balance Operations**:
- Real-time balance fetching from Circle API
- Balance updates on transfer completion
- Insufficient funds detection
- Multi-wallet balance tracking per agent

**Transfer Initiation**:
```python
async def initiate_transfer(
    project_id: str,
    source_wallet_id: str,
    destination_wallet_id: str,
    amount: str,
    x402_request_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
)
```

### 5.3 Receipt Generation
**File**: `/Users/aideveloper/Agent-402/backend/app/services/circle_wallet_service.py`

**Automatic Receipt Creation**:
```python
{
    "receipt_id": "receipt_abc123",
    "transfer_id": "transfer_xyz",
    "project_id": "proj_123",
    "x402_request_id": "x402_req_abc",
    "source_agent_did": "did:key:z6Mk...",
    "destination_agent_did": "did:key:z6Mk...",
    "amount": "10.50",
    "currency": "USD",
    "status": "complete",
    "transaction_hash": "0x...",
    "blockchain": "ETH-SEPOLIA",
    "created_at": "2026-01-23T12:00:00Z"
}
```

---

## 6. AGENT IDENTITY & AUTHENTICATION

### 6.1 DID-Based Identity
**File**: `/Users/aideveloper/Agent-402/backend/app/models/agent.py`

**DID Properties**:
- Decentralized identifier per agent
- Cryptographic key material embedded
- Enables signature verification
- Links agent to wallet
- Non-fungible (one DID per agent)

**DID Format Validation**:
```python
def validate_did_format(cls, v: str) -> str:
    # Must start with "did:key:"
    # Must have "z6Mk" key identifier
    # Minimum length 10 characters after prefix
```

### 6.2 Agent Role-Based Access
**File**: `/Users/aideveloper/Agent-402/backend/app/schemas/agents.py`

**Agent Roles**:
- `ANALYST`: Research and data gathering
- `COMPLIANCE`: Compliance checking and risk assessment
- `TRANSACTION`: Execute payments and transfers
- `ORCHESTRATOR`: Coordinate between agents

**Scope Levels**:
- `SYSTEM`: System-wide scope across all projects
- `PROJECT`: Limited to single project
- `RUN`: Limited to single agent run (default)

### 6.3 API Key Management
**File**: `/Users/aideveloper/Agent-402/backend/app/core/config.py` (settings)

**Key Mapping**:
- User ID ← → API Key (1-to-1 mapping)
- Keys stored in configuration
- Validation: minimum 10 chars, alphanumeric + underscore/hyphen
- Per-user keys enable user isolation

---

## 7. REAL-TIME ENFORCEMENT CAPABILITIES

### 7.1 Immediate Request Validation
**Request Level**:
- X402 signature validation happens before processing
- Payment signature verification required before task creation
- Request payload validation (non-empty, valid format)

**Response Level**:
- Validation errors return immediately (401/402)
- No state changes on invalid requests
- Clear error messages for debugging

### 7.2 Payment Guard Rails
**Pre-Payment Checks**:
1. X-Payment-Signature header presence (402 if missing)
2. Payment amount sufficiency (402 if insufficient)
3. Signature validity (401 if invalid)
4. Nonce/replay protection via Gateway

**Post-Payment Tracking**:
- Status transitions monitored
- Transaction hash validation
- Confirmation tracking

### 7.3 Compliance Enforcement
**Automatic Compliance**:
- Events created for every significant action
- Risk scoring on all transactions
- Outcome classification (PASS/FAIL/ESCALATED)
- Event linkage to causative request

**Real-time Filtering**:
- Risk score thresholds
- Event type filtering
- Outcome-based routing

---

## 8. DEVELOPER APIs & INTEGRATION POINTS

### 8.1 X402 Request API
**Endpoint**: `POST /v1/public/{project_id}/x402-requests`

**Request**:
```json
{
    "agent_id": "did:ethr:0xabc123...",
    "task_id": "task_payment_001",
    "run_id": "run_2026_01_10_001",
    "request_payload": {
        "type": "payment_authorization",
        "amount": "100.00",
        "currency": "USD",
        "recipient": "did:ethr:0xdef789..."
    },
    "signature": "0xsig123...",
    "status": "PENDING",
    "linked_memory_ids": ["mem_abc123"],
    "linked_compliance_ids": ["comp_evt_001"],
    "metadata": {"priority": "high"}
}
```

**Response**:
```json
{
    "request_id": "x402_req_abc123",
    "project_id": "proj_xyz",
    "agent_id": "did:ethr:0xabc123...",
    "task_id": "task_payment_001",
    "run_id": "run_2026_01_10_001",
    "status": "PENDING",
    "timestamp": "2026-01-10T12:34:56.789Z"
}
```

### 8.2 Payment Receipt API
**Create Receipt**:
```
POST /v1/public/{project_id}/payment-receipts
```

**List Receipts**:
```
GET /v1/public/{project_id}/payment-receipts?
  from_agent_id=agent_001&
  to_agent_id=agent_002&
  status=confirmed&
  limit=100&offset=0
```

**Update Status**:
```
PATCH /v1/public/{project_id}/payment-receipts/{receipt_id}
{
    "status": "confirmed",
    "transaction_hash": "0x...",
    "arc_payment_id": 42
}
```

### 8.3 Compliance Events API
**Create Event**:
```
POST /v1/public/{project_id}/compliance-events
{
    "agent_id": "compliance_agent_001",
    "event_type": "KYC_CHECK",
    "outcome": "PASS",
    "risk_score": 0.15,
    "details": {...},
    "run_id": "run_abc123"
}
```

**List Events with Filters**:
```
GET /v1/public/{project_id}/compliance-events?
  agent_id=compliance_agent_001&
  event_type=KYC_CHECK&
  outcome=PASS&
  min_risk_score=0.0&
  max_risk_score=0.5&
  limit=100
```

**Get Statistics**:
```
GET /v1/public/{project_id}/compliance-events/stats
→ Returns event counts by type, outcome, and average risk
```

### 8.4 Circle Wallet API
**Create Wallet**:
```
POST /v1/public/{project_id}/circle-wallets
{
    "agent_did": "did:key:z6Mk...",
    "wallet_type": "analyst|compliance|transaction",
    "description": "Optional description"
}
```

**List Agent Wallets**:
```
GET /v1/public/{project_id}/agents/{agent_did}/wallets
```

**Initiate Transfer**:
```
POST /v1/public/{project_id}/transfers
{
    "source_wallet_id": "wallet_src",
    "destination_wallet_id": "wallet_dst",
    "amount": "10.50",
    "x402_request_id": "x402_req_abc"
}
```

### 8.5 Gateway Payment API
**Hire Agent (Gasless)**:
```
POST /v1/public/gateway/{project_id}/hire-agent
Headers:
  X-API-Key: user_key
  X-Payment-Signature: payer=0x...,amount=10.50,signature=0x...,network=arc-testnet

{
    "agent_token_id": 0,
    "task_description": "Analyze Q4 earnings reports"
}
```

**Get Deposit Instructions**:
```
POST /v1/public/gateway/deposit
Headers:
  X-API-Key: user_key

Response:
{
    "deposit_address": "0x5f8D59332D3d2af9E4596DC1F4EafD1aC53499DE",
    "network": "arc-testnet",
    "minimum_deposit": "10.00",
    "qr_code_url": "https://...",
    "instructions": "Send USDC to the address above..."
}
```

### 8.6 Agent Management API
**Create Agent**:
```
POST /v1/public/{project_id}/agents
{
    "did": "did:key:z6MkhaXgBZ...",
    "role": "analyst|compliance|transaction|orchestrator",
    "name": "Research Agent Alpha",
    "description": "Specialized for financial research",
    "scope": "RUN|PROJECT|SYSTEM"
}
```

**List Agents**:
```
GET /v1/public/{project_id}/agents?limit=100&offset=0
```

---

## 9. PERSISTENCE & STORAGE

### 9.1 ZeroDB Tables
All data persisted to ZeroDB with the following key tables:

**x402_requests**
- Stores signed payment authorization requests
- Linked to agents, tasks, runs
- Supports memory and compliance event linkage

**payment_receipts**
- Payment transaction records
- Linked to X402 requests
- Blockchain transaction hashes
- Arc contract payment IDs

**compliance_events**
- All compliance checks and decisions
- Risk scores and outcomes
- Event types and details
- Filterable and searchable

**circle_wallets**
- Agent wallet metadata
- Circle API integration
- Blockchain addresses
- Balance tracking

**circle_transfers**
- USDC transfer records
- Status tracking
- Transaction hashes
- Source/destination links

**agents**
- Agent profiles
- DID mappings
- Role and scope
- Project association

---

## 10. CURRENT IMPLEMENTATION STATUS

### Implemented:
✅ X402 Protocol request schema and storage
✅ Agent DID system with validation
✅ Circle wallet creation and management
✅ USDC transfer initiation
✅ Payment receipt generation
✅ Compliance event creation and filtering
✅ X-API-Key authentication
✅ JWT Bearer token support (AINative + local)
✅ Gateway payment verification
✅ X402 request linkage to agents/tasks
✅ Full audit trail capabilities

### Partially Implemented:
🟡 Signature verification (DIDSigner exists, integration complete in X402 API)
🟡 Circle Gateway integration (schemas exist, full flow in gateway.py)
🟡 Auto-settlement cron job (Issue #150 mentioned but not implemented)

### Not Yet Implemented:
❌ Smart contract integration (Arc AgentTreasury)
❌ Real blockchain signature verification
❌ Policy enforcement engine
❌ Spend limits per agent
❌ Rate limiting
❌ Real Circle Gateway API calls
❌ Treasury management UI

---

## 11. SECURITY CONSIDERATIONS

### Authentication:
- Dual-factor support (API Key + JWT)
- AINative token validation with caching
- Token expiration enforcement
- Per-user key management

### Authorization:
- API-key based user isolation
- Project-level access control
- Agent scope enforcement

### Cryptography:
- DID signature verification (for X402)
- Payment signature verification (via Circle)
- Non-repudiation through signatures

### Audit:
- All requests traceable to agent
- All payments linked to X402
- All compliance checks recorded
- Full transaction history

---

## 12. DATA PRECISION & FORMATS

### Payment Amounts:
- USDC: 6 decimal places preserved as string
- Example: "1.500000" (not float to prevent precision loss)
- Stored and transmitted as strings

### Timestamps:
- ISO 8601 format: "2026-01-23T12:34:56.789Z"
- UTC timezone required
- Millisecond precision

### Identifiers:
- Agent IDs: `agent_{uuid[:12]}`
- Receipt IDs: `pay_rcpt_{uuid[:16]}`
- X402 Request IDs: `x402_req_{uuid[:16]}`
- Event IDs: `evt_{uuid[:16]}`
- Wallet IDs: `wallet_{uuid[:12]}`
- Transfer IDs: `transfer_{uuid[:12]}`

---

## Key Integration Points for Financial Controls

1. **Before Payment**: Signature verification → Compliance check → Amount validation
2. **During Payment**: Real-time status tracking → Transaction hash capture
3. **After Payment**: Receipt generation → Event logging → Treasury update
4. **Audit**: Link everything back to originating agent/task/run

This layered approach ensures no payment can be made without proper authorization, compliance, and audit trail.
