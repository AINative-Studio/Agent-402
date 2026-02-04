# Agent 402 - Quick Reference Guide

## Key File Locations

### Schemas (Data Models)
- `/backend/app/schemas/x402_protocol.py` - X402 payment authorization
- `/backend/app/schemas/x402_requests.py` - X402 request tracking
- `/backend/app/schemas/payment_tracking.py` - Payment receipts
- `/backend/app/schemas/agents.py` - Agent profiles
- `/backend/app/schemas/compliance_events.py` - Compliance tracking
- `/backend/app/schemas/gateway.py` - Gasless payment flow

### Services (Business Logic)
- `/backend/app/services/x402_service.py` - X402 request management
- `/backend/app/services/x402_payment_tracker.py` - Payment receipt tracking
- `/backend/app/services/circle_wallet_service.py` - Wallet & USDC transfers
- `/backend/app/services/compliance_service.py` - Compliance event management
- `/backend/app/services/agent_service.py` - Agent profile management
- `/backend/app/services/gateway_service.py` - Gateway payment verification

### API Endpoints
- `/backend/app/api/x402_requests.py` - X402 request endpoints
- `/backend/app/api/gateway.py` - Gasless payment endpoints
- `/backend/app/api/agents.py` - Agent management endpoints
- `/backend/app/api/compliance_events.py` - Compliance endpoints
- `/backend/app/api/circle.py` - Circle integration endpoints

### Authentication
- `/backend/app/core/auth.py` - X-API-Key and JWT validation
- `/backend/app/core/ainative_auth.py` - AINative token support
- `/backend/app/middleware/api_key_auth.py` - Request authentication

## Core Concepts

### Payment Flow
```
User deposits USDC → Signs payment intent → Backend verifies signature 
→ Creates X402 request → Generates receipt → Batched settlement to blockchain
```

### Audit Trail
```
X402 Request → Links to Agent → Links to Task → Links to Run
            → Links to Agent Memory (decision context)
            → Links to Compliance Events (risk checks)
            → Links to Payment Receipt (transaction)
```

### Agent Identity
```
Agent Profile → DID (did:key:z6Mk...) → Circle Wallet → Blockchain Address
               → Role (analyst/compliance/transaction/orchestrator)
               → Scope (SYSTEM/PROJECT/RUN)
               → 3 wallet types per agent (analyst/compliance/transaction)
```

## API Examples

### 1. Create X402 Request (Signed Payment Authorization)
```bash
POST /v1/public/{project_id}/x402-requests
Authorization: Bearer {token}

{
  "agent_id": "did:key:z6Mk...",
  "task_id": "task_001",
  "run_id": "run_001",
  "request_payload": {
    "type": "payment_authorization",
    "amount": "100.00",
    "currency": "USD"
  },
  "signature": "0x...",
  "linked_memory_ids": ["mem_123"],
  "linked_compliance_ids": ["evt_123"]
}
```

### 2. Hire Agent (Gasless Payment)
```bash
POST /v1/public/gateway/{project_id}/hire-agent
X-API-Key: {api_key}
X-Payment-Signature: payer=0x...,amount=10.50,signature=0x...,network=arc-testnet

{
  "agent_token_id": 0,
  "task_description": "Analyze earnings reports"
}
```

### 3. Create Compliance Event
```bash
POST /v1/public/{project_id}/compliance-events
X-API-Key: {api_key}

{
  "agent_id": "compliance_001",
  "event_type": "KYC_CHECK",
  "outcome": "PASS",
  "risk_score": 0.15,
  "details": {
    "verification_method": "document"
  }
}
```

### 4. Create Agent Wallet
```bash
POST /v1/public/{project_id}/circle-wallets
X-API-Key: {api_key}

{
  "agent_did": "did:key:z6Mk...",
  "wallet_type": "analyst",
  "description": "Analyst wallet"
}
```

## Data Structures

### X402 Request (Complete Audit)
```python
{
  "request_id": "x402_req_abc123",      # Unique identifier
  "project_id": "proj_xyz",              # Project context
  "agent_id": "agent_001",               # Who created it
  "task_id": "task_payment_001",         # Why it was created
  "run_id": "run_2026_01_10_001",       # Execution context
  "request_payload": {...},              # Payment details
  "signature": "0x...",                  # Cryptographic proof
  "status": "PENDING|APPROVED|REJECTED|EXPIRED|COMPLETED",
  "timestamp": "2026-01-10T12:34:56.789Z",
  "linked_memory_ids": ["mem_123"],     # Decision context
  "linked_compliance_ids": ["evt_123"],  # Risk checks
  "metadata": {}                         # Custom data
}
```

### Payment Receipt (Full Traceability)
```python
{
  "receipt_id": "pay_rcpt_abc123",       # Unique identifier
  "x402_request_id": "x402_req_abc",    # Links to authorization
  "from_agent_id": "agent_001",          # Sender
  "to_agent_id": "agent_002",            # Recipient
  "amount_usdc": "1.500000",             # Amount (6 decimals)
  "status": "PENDING|CONFIRMED|FAILED|REFUNDED",
  "transaction_hash": "0x...",           # Blockchain proof
  "arc_payment_id": 42,                  # Contract ID
  "treasury_from_id": 1,                 # Source treasury
  "treasury_to_id": 2,                   # Dest treasury
  "created_at": "2026-01-23T12:00:00Z",
  "confirmed_at": "2026-01-23T12:00:05Z"
}
```

### Compliance Event (Risk Tracking)
```python
{
  "event_id": "evt_abc123",              # Unique identifier
  "project_id": "proj_xyz",
  "agent_id": "compliance_001",          # Which agent checked
  "event_type": "KYC_CHECK|KYT_CHECK|RISK_ASSESSMENT|COMPLIANCE_DECISION|AUDIT_LOG",
  "outcome": "PASS|FAIL|PENDING|ESCALATED|ERROR",
  "risk_score": 0.15,                    # 0.0-1.0 (LOW/MEDIUM/HIGH/CRITICAL)
  "details": {...},                      # Context data
  "run_id": "run_abc123",                # Workflow context
  "timestamp": "2026-01-10T12:34:56.789Z"
}
```

### Agent Profile
```python
{
  "id": "agent_abc123",                  # Internal ID
  "did": "did:key:z6Mk...",             # Decentralized ID
  "role": "analyst|compliance|transaction|orchestrator",
  "name": "Research Agent Alpha",
  "description": "Specialized for financial research",
  "scope": "SYSTEM|PROJECT|RUN",
  "project_id": "proj_xyz",
  "created_at": "2026-01-23T12:00:00Z",
  "updated_at": "2026-01-23T12:00:00Z"
}
```

## Authentication Methods

### Method 1: X-API-Key
```bash
curl -H "X-API-Key: sk_user_abc123def456789" https://api.agent402.com/v1/public/...
```

### Method 2: JWT Bearer Token (AINative)
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." https://api.agent402.com/v1/public/...
```

## Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| INVALID_API_KEY | 401 | API key missing/invalid/expired |
| TOKEN_EXPIRED | 401 | JWT token has expired |
| INVALID_TOKEN | 401 | JWT token invalid |
| PAYMENT_REQUIRED | 402 | X-Payment-Signature header missing |
| INSUFFICIENT_PAYMENT | 402 | Payment amount too low |
| INVALID_SIGNATURE | 401 | Payment signature verification failed |
| X402_REQUEST_NOT_FOUND | 404 | X402 request not found |
| PAYMENT_RECEIPT_NOT_FOUND | 404 | Receipt not found |
| DUPLICATE_WALLET | 409 | Wallet already exists for agent/type |

## Query Examples

### List X402 Requests by Agent
```bash
GET /v1/public/{project_id}/x402-requests?agent_id=agent_001&limit=50&offset=0
```

### List Payment Receipts by Status
```bash
GET /v1/public/{project_id}/payment-receipts?status=confirmed&limit=100
```

### List Compliance Events by Risk
```bash
GET /v1/public/{project_id}/compliance-events?
  min_risk_score=0.5&
  max_risk_score=1.0&
  event_type=RISK_ASSESSMENT
```

### Get Compliance Stats
```bash
GET /v1/public/{project_id}/compliance-events/stats
```

## ZeroDB Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| x402_requests | Payment authorizations | request_id, agent_id, task_id, run_id |
| payment_receipts | Payment records | receipt_id, x402_request_id, status |
| compliance_events | Risk tracking | event_id, agent_id, event_type, outcome |
| circle_wallets | Agent wallets | wallet_id, agent_did, wallet_type |
| circle_transfers | USDC transfers | transfer_id, amount, status |
| agents | Agent profiles | agent_id, did, role, project_id |

## Spending Formula

```
Required Amount = $10.00 * (1.0 + max(0, (description_length - 100) / 1000))

Examples:
- 100 chars: $10.00
- 600 chars: $10.50
- 2100 chars: $12.00
```

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| X402 Protocol | ✅ Full | Request validation + storage |
| DID System | ✅ Full | Validation + signature support |
| Circle Wallets | ✅ Full | Creation + USDC transfers |
| Compliance Events | ✅ Full | Creation + filtering + stats |
| Gateway Payments | ✅ Full | Signature verification ready |
| Audit Trail | ✅ Full | Agent/task/run linkage complete |
| Authentication | ✅ Full | API Key + JWT (AINative) |
| Receipts | ✅ Full | Automatic generation + tracking |
| Smart Contracts | ❌ TODO | Arc integration pending |
| Spend Limits | ❌ TODO | Not yet implemented |
| Policy Engine | ❌ TODO | Planned for Phase 2 |

## Key Integration Sequence

1. **User deposits USDC** → Gateway account funded
2. **User calls hire-agent** → X-Payment-Signature verified
3. **Backend creates X402 request** → Audit record created
4. **Backend creates task** → X402 request linked
5. **Compliance checks run** → Compliance events created
6. **Payment confirmed** → Receipt generated
7. **Settlement batched** → Blockchain transaction sent
8. **Query audit trail** → Full provenance available

## Contact & Documentation

- Full analysis: `/AGENT_402_CODEBASE_ANALYSIS.md`
- API tests: `/backend/app/tests/`
- Smart contract: `/contracts/`
