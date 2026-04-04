# Hedera Agent Identity Guide

Issue #195: Agent Identity Documentation — development guide.

This guide explains how Agent-402 represents each agent as a unique, verifiable
on-chain identity using Hedera Token Service (HTS) NFTs, `did:hedera` DIDs, and
the HCS-14 directory protocol.

---

## Table of Contents

1. [Concepts](#1-concepts)
2. [HTS NFT Agent Registry](#2-hts-nft-agent-registry)
3. [did:hedera DID Integration](#3-didhedera-did-integration)
4. [HCS-14 Directory Registration](#4-hcs-14-directory-registration)
5. [AAP Capability Mapping](#5-aap-capability-mapping)
6. [Example Registration Flow](#6-example-registration-flow)
7. [Error Reference](#7-error-reference)

---

## 1. Concepts

### Why on-chain agent identity?

Agent-402 targets autonomous fintech workflows where every action must be
auditable and non-repudiable (PRD §10).  Giving each agent a blockchain-anchored
identity means:

- **Verifiable provenance** — any payment or decision can be traced to a
  specific agent instance.
- **Portable reputation** — a DID-linked reputation score survives service
  restarts or infrastructure migrations.
- **Interoperability** — other agents and services can discover capabilities
  via the HCS-14 open directory without a centralised registry.

### Component overview

| Component | Purpose |
|-----------|---------|
| HTS NFT | Unique, tamper-proof agent token on Hedera mainnet/testnet |
| `did:hedera` | W3C-compliant Decentralised Identifier anchored via HCS |
| HCS-14 directory | Topic-based agent capability advertisement |
| AAP | Agent Ability Protocol — structured capability declarations |

---

## 2. HTS NFT Agent Registry

### Minting an agent NFT

Each agent registration mints one NFT from the shared `AGENT_REGISTRY_TOKEN_ID`
Non-Fungible Token.  The NFT serial number becomes the agent's immutable numeric
identifier within the registry.

**NFT metadata schema (JSON, stored in IPFS / HCS topic):**

```json
{
  "agent_id": "did:hedera:testnet:z6MkiTBz1ymuepAQ4HEHYSF1H8quG5GLVVQR3djdX3mDooWp",
  "name": "FinanceResearcher-v1",
  "version": "1.0.0",
  "capabilities": ["payment.initiate", "market.read", "compliance.report"],
  "created_at": "2026-04-03T00:00:00Z",
  "owner_account": "0.0.12345"
}
```

### Token configuration

```
Token type:        NON_FUNGIBLE_UNIQUE
Supply type:       INFINITE
Treasury account:  AINative operator account
Admin key:         None (immutable after creation — PRD §10)
KYC key:           None
Freeze key:        None
```

Removing the admin key after initial setup guarantees that NFT metadata cannot
be altered post-issuance, satisfying the non-repudiation requirement.

---

## 3. did:hedera DID Integration

### DID format

```
did:hedera:<network>:<publicKeyMultibase>_<topicId>
```

Example:

```
did:hedera:testnet:z6MkiTBz1ymuepAQ4HEHYSF1H8quG5GLVVQR3djdX3mDooWp_0.0.98765
```

- `<network>` — `mainnet` or `testnet`
- `<publicKeyMultibase>` — base58btc-encoded Ed25519 public key
- `<topicId>` — Hedera Consensus Service topic that anchors the DID document

### DID Document fields relevant to agents

```json
{
  "@context": ["https://www.w3.org/ns/did/v1"],
  "id": "did:hedera:testnet:z6Mk..._0.0.98765",
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
      "serviceEndpoint": "https://api.ainative.studio/agents/0.0.12345"
    }
  ]
}
```

### Key management

Agent private keys are generated at registration time and stored encrypted in
the agent's ZeroDB record.  The public key is published in the DID document and
on the HTS NFT metadata.

---

## 4. HCS-14 Directory Registration

HCS-14 defines a Hedera Consensus Service topic used as an open agent directory.
Any agent that submits a valid registration message to the directory topic becomes
discoverable by other agents and orchestrators.

### Directory topic

The directory topic ID is configured in `backend/app/core/config.py` as
`HEDERA_AGENT_DIRECTORY_TOPIC_ID`.

### Registration message format

```json
{
  "p": "hcs-14",
  "op": "register",
  "agent_id": "did:hedera:testnet:z6Mk..._0.0.98765",
  "name": "FinanceResearcher-v1",
  "capabilities": ["payment.initiate", "market.read"],
  "endpoint": "https://api.ainative.studio/agents/0.0.12345",
  "timestamp": "2026-04-03T00:00:00Z",
  "signature": "<Ed25519 signature over canonical JSON>"
}
```

### Message validation rules

1. `p` must equal `"hcs-14"`.
2. `op` must be one of `register`, `update`, `deregister`.
3. `agent_id` must resolve to a valid `did:hedera` DID document.
4. `signature` must verify against the `authentication` key in the DID document.
5. `timestamp` must be within 5 minutes of the consensus timestamp.

---

## 5. AAP Capability Mapping

The Agent Ability Protocol (AAP) provides a structured vocabulary for declaring
what an agent can do.  Capabilities are expressed as dot-separated namespaced
strings.

### Standard capability namespaces

| Namespace | Description |
|-----------|-------------|
| `payment.*` | Initiate, approve, or cancel USDC payments |
| `market.*` | Read market data, prices, or order books |
| `compliance.*` | Generate or submit compliance reports |
| `memory.*` | Store or retrieve agent memory |
| `directory.*` | Register in or query the HCS-14 directory |
| `reputation.*` | Submit or read HCS-anchored reputation feedback |

### Specific capabilities

| Capability string | Description |
|-------------------|-------------|
| `payment.initiate` | Agent may originate a payment transaction |
| `payment.approve` | Agent may countersign a multi-sig payment |
| `market.read` | Agent may query price feeds and order books |
| `compliance.report` | Agent may submit compliance event records |
| `memory.write` | Agent may persist new memory entries |
| `memory.read` | Agent may retrieve its own memory entries |

### Capability declaration in the DID service endpoint

```json
{
  "id": "#capabilities",
  "type": "AAPCapabilitySet",
  "serviceEndpoint": {
    "capabilities": ["payment.initiate", "market.read", "compliance.report"],
    "aap_version": "1.0"
  }
}
```

---

## 6. Example Registration Flow

The following sequence registers a new agent end-to-end.

```
Client                  Agent-402 API             Hedera Network
  |                          |                          |
  |-- POST /agents/register ->|                          |
  |   { name, capabilities } |                          |
  |                          |-- Generate Ed25519 keypair
  |                          |-- Create HCS topic ------>|
  |                          |<- topic_id ---------------| 0.0.98765
  |                          |-- Mint HTS NFT ---------->|
  |                          |<- nft_serial_number ------| 42
  |                          |-- Publish DID document -->| (HCS message)
  |                          |-- Submit HCS-14 register->| (directory topic)
  |                          |-- Store agent record in ZeroDB
  |<- 201 { agent_id, did } -|
```

### Step-by-step

**Step 1 — Generate identity material**

```python
from hedera import PrivateKey
private_key = PrivateKey.generate_ed25519()
public_key = private_key.get_public_key()
```

**Step 2 — Create HCS topic for DID anchoring**

```python
from hedera import TopicCreateTransaction, Client
topic_id = (
    TopicCreateTransaction()
    .set_topic_memo(f"DID anchor for {agent_name}")
    .execute(client)
    .get_receipt(client)
    .topic_id
)
```

**Step 3 — Mint the agent NFT**

```python
from hedera import TokenMintTransaction
serial = (
    TokenMintTransaction()
    .set_token_id(AGENT_REGISTRY_TOKEN_ID)
    .add_metadata(json.dumps(nft_metadata).encode())
    .execute(client)
    .get_receipt(client)
    .serial_numbers[0]
)
```

**Step 4 — Publish the DID document to the HCS topic**

```python
from hedera import TopicMessageSubmitTransaction
did_document_json = json.dumps(did_document)
TopicMessageSubmitTransaction() \
    .set_topic_id(topic_id) \
    .set_message(did_document_json) \
    .execute(client)
```

**Step 5 — Register in the HCS-14 directory**

```python
import json, hashlib
from hedera import TopicMessageSubmitTransaction

registration_msg = {
    "p": "hcs-14",
    "op": "register",
    "agent_id": did,
    "name": agent_name,
    "capabilities": capabilities,
    "endpoint": endpoint_url,
    "timestamp": datetime.utcnow().isoformat() + "Z",
}
canonical = json.dumps(registration_msg, sort_keys=True).encode()
signature = private_key.sign(canonical).hex()
registration_msg["signature"] = signature

TopicMessageSubmitTransaction() \
    .set_topic_id(HEDERA_AGENT_DIRECTORY_TOPIC_ID) \
    .set_message(json.dumps(registration_msg)) \
    .execute(client)
```

**Step 6 — Store in ZeroDB**

The API persists the agent record (DID, public key, NFT serial, capabilities)
in the `agents` ZeroDB table, which is append-only for audit integrity.

---

## 7. Error Reference

| Error code | HTTP | Meaning |
|------------|------|---------|
| `AGENT_NOT_FOUND` | 404 | No agent with the given DID or ID |
| `DUPLICATE_AGENT_DID` | 409 | Agent with this DID already registered |
| `HEDERA_NETWORK_ERROR` | 502 | Hedera SDK call failed |
| `INVALID_SIGNATURE` | 422 | HCS-14 message signature invalid |
| `IMMUTABLE_RECORD` | 403 | Attempt to modify append-only agent record |
