# Hedera Identity API Reference

Issue #195: Agent Identity Documentation — API reference.

Base URL: `https://api.ainative.studio/api/v1`

All endpoints require `X-API-Key` or `Authorization: Bearer <jwt>` unless stated otherwise.

---

## Endpoints

- [POST /agents/register](#post-agentsregister)
- [GET /agents/{id}/did](#get-agentsiddid)
- [POST /agents/directory/search](#post-agentsdirectorysearch)

---

## POST /agents/register

Register an agent as an HTS NFT with a `did:hedera` identifier.

This endpoint:
1. Generates an Ed25519 keypair for the agent.
2. Creates an HCS topic to anchor the DID document.
3. Mints one NFT from the shared agent registry token.
4. Publishes the DID document as an HCS message.
5. Submits an HCS-14 registration message to the directory topic.
6. Persists the agent record in ZeroDB (append-only).

### Request

```
POST /api/v1/agents/register
Content-Type: application/json
X-API-Key: <key>
```

**Body:**

```json
{
  "name": "FinanceResearcher-v1",
  "capabilities": [
    "payment.initiate",
    "market.read",
    "compliance.report"
  ],
  "endpoint": "https://api.ainative.studio/agents/finance-researcher",
  "metadata": {
    "version": "1.0.0",
    "owner_account": "0.0.12345"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Human-readable agent name (max 64 chars) |
| `capabilities` | string[] | Yes | AAP capability strings (min 1) |
| `endpoint` | string | No | Service endpoint URL for the DID document |
| `metadata` | object | No | Arbitrary key-value metadata stored in NFT |

### Response `201 Created`

```json
{
  "agent_id": "did:hedera:testnet:z6MkiTBz1ymuepAQ4HEHYSF1H8quG5GLVVQR3djdX3mDooWp_0.0.98765",
  "did": "did:hedera:testnet:z6MkiTBz1ymuepAQ4HEHYSF1H8quG5GLVVQR3djdX3mDooWp_0.0.98765",
  "nft_serial": 42,
  "hcs_topic_id": "0.0.98765",
  "public_key": "z6MkiTBz1ymuepAQ4HEHYSF1H8quG5GLVVQR3djdX3mDooWp",
  "created_at": "2026-04-03T12:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | Canonical agent identifier (same as `did`) |
| `did` | string | Full `did:hedera` DID |
| `nft_serial` | integer | HTS NFT serial number |
| `hcs_topic_id` | string | Hedera topic that anchors the DID document |
| `public_key` | string | Base58btc-encoded Ed25519 public key |
| `created_at` | string | ISO 8601 UTC timestamp |

### Error responses

| Status | `error_code` | When |
|--------|-------------|------|
| 409 | `DUPLICATE_AGENT_DID` | DID already registered in this project |
| 422 | `SCHEMA_VALIDATION_ERROR` | Missing or invalid request fields |
| 502 | `HEDERA_NETWORK_ERROR` | Hedera SDK call failed |

---

## GET /agents/{id}/did

Resolve a `did:hedera` DID document for a registered agent.

### Request

```
GET /api/v1/agents/{id}/did
X-API-Key: <key>
```

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Agent DID or numeric agent ID |

**Example:**

```
GET /api/v1/agents/did:hedera:testnet:z6Mk..._0.0.98765/did
```

### Response `200 OK`

```json
{
  "@context": ["https://www.w3.org/ns/did/v1"],
  "id": "did:hedera:testnet:z6MkiTBz1ymuepAQ4HEHYSF1H8quG5GLVVQR3djdX3mDooWp_0.0.98765",
  "verificationMethod": [
    {
      "id": "did:hedera:testnet:z6Mk..._0.0.98765#key-1",
      "type": "Ed25519VerificationKey2020",
      "controller": "did:hedera:testnet:z6Mk..._0.0.98765",
      "publicKeyMultibase": "z6MkiTBz1ymuepAQ4HEHYSF1H8quG5GLVVQR3djdX3mDooWp"
    }
  ],
  "authentication": ["#key-1"],
  "service": [
    {
      "id": "#agent-endpoint",
      "type": "AgentService",
      "serviceEndpoint": "https://api.ainative.studio/agents/finance-researcher"
    },
    {
      "id": "#capabilities",
      "type": "AAPCapabilitySet",
      "serviceEndpoint": {
        "capabilities": ["payment.initiate", "market.read"],
        "aap_version": "1.0"
      }
    }
  ],
  "resolved_at": "2026-04-03T12:01:00Z"
}
```

### Error responses

| Status | `error_code` | When |
|--------|-------------|------|
| 404 | `AGENT_NOT_FOUND` | No agent with the provided ID |
| 502 | `HEDERA_NETWORK_ERROR` | Could not fetch HCS messages for DID resolution |

---

## POST /agents/directory/search

Query the HCS-14 agent directory.  Returns agents matching the requested
capability filters, optionally filtered by name or DID prefix.

### Request

```
POST /api/v1/agents/directory/search
Content-Type: application/json
X-API-Key: <key>
```

**Body:**

```json
{
  "capabilities": ["payment.initiate"],
  "name_contains": "Finance",
  "limit": 20,
  "offset": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `capabilities` | string[] | No | Return only agents with ALL listed capabilities |
| `name_contains` | string | No | Case-insensitive substring match on agent name |
| `limit` | integer | No | Max results per page (default: 20, max: 100) |
| `offset` | integer | No | Pagination offset (default: 0) |

### Response `200 OK`

```json
{
  "agents": [
    {
      "agent_id": "did:hedera:testnet:z6Mk..._0.0.98765",
      "name": "FinanceResearcher-v1",
      "capabilities": ["payment.initiate", "market.read"],
      "endpoint": "https://api.ainative.studio/agents/finance-researcher",
      "registered_at": "2026-04-03T12:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `agents` | object[] | Array of matching agent summaries |
| `total` | integer | Total matching agents (for pagination) |
| `limit` | integer | Page size used |
| `offset` | integer | Offset used |

### Error responses

| Status | `error_code` | When |
|--------|-------------|------|
| 422 | `SCHEMA_VALIDATION_ERROR` | Invalid query parameters |
| 502 | `HEDERA_NETWORK_ERROR` | Cannot read HCS-14 directory topic |
