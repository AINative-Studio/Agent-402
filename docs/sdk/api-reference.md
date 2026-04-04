# API Reference

Complete API reference for the AINative Agent-402 SDK.

Built by AINative Dev Team | Refs #182

---

## Authentication

All endpoints require the `X-API-Key` header:

```http
X-API-Key: your_api_key_here
```

Base URL pattern: `https://api.ainative.studio/v1/public/{project_id}`

---

## Agents

### Create Agent

```http
POST /v1/public/{project_id}/agents
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Human-readable agent name |
| `did` | string | Yes | Decentralized Identifier (did:key:... format) |
| `metadata` | object | No | Agent-specific metadata (role, capabilities, etc.) |

**Response `201`:**

```json
{
  "agent_id": "agt_abc123",
  "name": "financial-analyst",
  "did": "did:key:z6MkExample",
  "metadata": { "role": "analyst" },
  "created_at": "2026-04-03T12:00:00Z"
}
```

**TypeScript:**
```typescript
const agent = await client.agents.create({
  name: 'financial-analyst',
  did: 'did:key:z6MkExample',
  metadata: { role: 'analyst' },
});
```

**Python:**
```python
agent = await client.agents.create(
    name="financial-analyst",
    did="did:key:z6MkExample",
    metadata={"role": "analyst"},
)
```

---

### Get Agent

```http
GET /v1/public/{project_id}/agents/{agent_id}
```

**Response `200`:**

```json
{
  "agent_id": "agt_abc123",
  "name": "financial-analyst",
  "did": "did:key:z6MkExample",
  "metadata": {},
  "created_at": "2026-04-03T12:00:00Z"
}
```

---

### List Agents

```http
GET /v1/public/{project_id}/agents
```

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `limit` | integer | Max results (default: 100) |
| `offset` | integer | Pagination offset (default: 0) |

---

## Agent Memory

### Store Memory

```http
POST /v1/public/{project_id}/agent-memory
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `agent_id` | string | Yes | Agent to associate this memory with |
| `content` | string | Yes | Memory content to store and embed |
| `memory_type` | string | No | Memory type (preference, fact, decision) |
| `metadata` | object | No | Additional metadata |

**Response `201`:**

```json
{
  "memory_id": "mem_xyz789",
  "agent_id": "agt_abc123",
  "content": "User prefers concise summaries.",
  "memory_type": "preference",
  "created_at": "2026-04-03T12:00:00Z"
}
```

---

### Search Memory

```http
POST /v1/public/{project_id}/agent-memory/search
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `agent_id` | string | Yes | Agent whose memory to search |
| `query` | string | Yes | Semantic search query |
| `top_k` | integer | No | Number of results (default: 5) |

**Response `200`:**

```json
{
  "results": [
    {
      "memory_id": "mem_xyz789",
      "content": "User prefers concise summaries.",
      "score": 0.94,
      "metadata": {}
    }
  ],
  "total": 1
}
```

---

## Vectors

### Upsert Vector

```http
POST /v1/public/{project_id}/vectors/upsert
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Unique vector ID |
| `text` | string | Yes | Text to embed |
| `namespace` | string | No | Namespace for scoping (default: "default") |
| `metadata` | object | No | Additional metadata |
| `upsert` | boolean | No | Overwrite if exists (default: true) |

---

### Search Vectors

```http
POST /v1/public/{project_id}/vectors/search
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | Semantic search query |
| `namespace` | string | No | Namespace to search in |
| `top_k` | integer | No | Number of results (default: 10) |
| `filters` | object | No | Metadata filter conditions |
| `min_score` | float | No | Minimum similarity score (0.0–1.0) |

**Response `200`:**

```json
{
  "results": [
    {
      "id": "doc-001",
      "score": 0.934,
      "metadata": {
        "quarter": "Q4-2025",
        "content": "Revenue increased 23% YoY"
      }
    }
  ],
  "total": 1
}
```

---

## Files

### Upload File

```http
POST /v1/public/{project_id}/files
Content-Type: multipart/form-data
```

**Form fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | binary | Yes | File contents |
| `filename` | string | Yes | Original filename |
| `metadata` | JSON string | No | File metadata |

**Response `201`:**

```json
{
  "file_id": "file_abc123",
  "filename": "report.pdf",
  "size_bytes": 1024000,
  "content_type": "application/pdf",
  "created_at": "2026-04-03T12:00:00Z"
}
```

---

### Get File URL

```http
GET /v1/public/{project_id}/files/{file_id}/url
```

**Response `200`:**

```json
{
  "file_id": "file_abc123",
  "url": "https://storage.ainative.studio/files/...",
  "expires_at": "2026-04-03T13:00:00Z"
}
```

---

## Hedera Payments

### Create X402 Payment

```http
POST /v1/public/{project_id}/hedera/payments
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `agent_id` | string | Yes | Agent initiating the payment |
| `amount` | integer | Yes | USDC amount in smallest unit (1 USDC = 1,000,000) |
| `recipient` | string | Yes | Destination Hedera account ID |
| `task_id` | string | Yes | Task this payment is for |
| `from_account` | string | No | Source account (defaults to operator) |
| `memo` | string | No | Transaction memo (max 100 bytes) |

**Response `201`:**

```json
{
  "payment_id": "hdr_pay_abc123",
  "agent_id": "agent_abc123",
  "task_id": "task_xyz789",
  "amount": 5000000,
  "recipient": "0.0.22222",
  "transaction_id": "0.0.12345@1234567890.000000000",
  "status": "SUCCESS",
  "created_at": "2026-04-03T12:00:00Z",
  "transaction_hash": "0xabcdef..."
}
```

---

### Verify Settlement

```http
POST /v1/public/{project_id}/hedera/payments/verify
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `transaction_id` | string | Yes | Hedera transaction ID to verify |

**Response `200`:**

```json
{
  "transaction_id": "0.0.12345@1234567890.000000000",
  "settled": true,
  "status": "SUCCESS",
  "consensus_timestamp": "2026-04-03T12:00:00Z"
}
```

---

### Get Payment Receipt

```http
GET /v1/public/{project_id}/hedera/payments/{payment_id}/receipt
```

**Response `200`:**

```json
{
  "transaction_id": "0.0.12345@1234567890.000000000",
  "hash": "0xabcdef1234567890...",
  "status": "SUCCESS",
  "consensus_timestamp": "2026-04-03T12:00:00.123Z",
  "charged_tx_fee": 100000
}
```

---

## Hedera Wallets

### Create Agent Wallet

```http
POST /v1/public/{project_id}/hedera/wallets
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `agent_id` | string | Yes | Agent to create wallet for |
| `initial_balance` | integer | No | Initial HBAR balance in whole HBAR (default: 0) |

**Response `201`:**

```json
{
  "agent_id": "agent_abc123",
  "account_id": "0.0.12345",
  "public_key": "302a300506032b6570032100...",
  "network": "testnet",
  "created_at": "2026-04-03T12:00:00Z"
}
```

---

### Associate USDC Token

```http
POST /v1/public/{project_id}/hedera/wallets/{account_id}/associate-usdc
```

Token association is required before an account can receive USDC on Hedera.
Call this once after creating a wallet.

**Response `200`:**

```json
{
  "transaction_id": "0.0.12345@1234567890.000000000",
  "status": "SUCCESS",
  "account_id": "0.0.12345",
  "token_id": "0.0.456858"
}
```

---

### Get Wallet Balance

```http
GET /v1/public/{project_id}/hedera/wallets/{account_id}/balance
```

**Response `200`:**

```json
{
  "account_id": "0.0.12345",
  "hbar": "100.0",
  "usdc": "50.000000",
  "usdc_raw": "50000000"
}
```

---

## Error Responses

All errors follow the standard format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE"
}
```

### Common Error Codes

| error_code | HTTP Status | Description |
|---|---|---|
| `INVALID_API_KEY` | 401 | Missing or invalid API key |
| `PROJECT_NOT_FOUND` | 404 | Project ID not found |
| `AGENT_NOT_FOUND` | 404 | Agent not found |
| `HEDERA_WALLET_NOT_FOUND` | 404 | No Hedera wallet for agent |
| `HEDERA_PAYMENT_ERROR` | 502 | Hedera network error |
| `HEDERA_WALLET_ERROR` | 502 | Hedera wallet operation failed |
| `ZERODB_ERROR` | 502 | ZeroDB service error |
| `SCHEMA_VALIDATION_ERROR` | 422 | Request body validation failed |

Built by AINative Dev Team
