# Hedera Agent Kit Plugin Guide

Integrate Hedera USDC payments and wallet management into your AINative agents.

Built by AINative Dev Team | Refs #182, #187, #188

---

## Overview

The Hedera integration enables AINative agents to:

- **Create Hedera wallets** — AccountCreateTransaction via Hedera SDK
- **Receive USDC** — Native HTS token (token ID: 0.0.456858 on testnet)
- **Send USDC payments** — TransferTransaction with sub-3 second finality
- **Verify settlement** — Query mirror node for consensus timestamp
- **Audit trail** — All payments stored in ZeroDB

### Why Hedera?

| Feature | Hedera HTS | EVM/ERC-20 | Circle/USDC |
|---|---|---|---|
| Settlement time | < 3 seconds | 15–60 seconds | Minutes |
| Token type | Native HTS | Smart contract | API-managed |
| Token association | Required | Not required | Not required |
| Transaction cost | < $0.001 | Variable (gas) | Free |
| Energy usage | Carbon negative | Variable | N/A |

---

## Architecture

```
AINative Agent
    │
    ├── HederaWalletService (#188)
    │   ├── create_agent_wallet()     → AccountCreateTransaction
    │   ├── associate_usdc_token()   → TokenAssociateTransaction
    │   ├── get_balance()            → Mirror node REST API
    │   └── get_wallet_info()        → ZeroDB query
    │
    └── HederaPaymentService (#187)
        ├── transfer_usdc()          → TransferTransaction (HTS)
        ├── verify_settlement()      → Mirror node receipt query
        ├── get_payment_receipt()    → Mirror node REST API
        └── create_x402_payment()   → Full X402 payment flow
```

---

## Setup

### 1. Environment Variables

Add to your `.env`:

```env
# Hedera network configuration
HEDERA_NETWORK=testnet
HEDERA_OPERATOR_ID=0.0.YOUR_ACCOUNT_ID
HEDERA_OPERATOR_KEY=your_operator_private_key_hex

# USDC token IDs
USDC_TOKEN_ID_TESTNET=0.0.456858
USDC_TOKEN_ID_MAINNET=0.0.456858
```

### 2. Get Testnet Credentials

1. Go to [Hedera Portal](https://portal.hedera.com)
2. Create a testnet account
3. Copy your account ID and private key
4. Fund with testnet HBAR from the faucet

### 3. Verify the Setup

```bash
curl -X POST https://api.ainative.studio/v1/public/{project_id}/hedera/wallets \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "test-agent", "initial_balance": 10}'
```

---

## Core Concepts

### USDC Token ID

USDC on Hedera is a native HTS token — not an ERC-20 contract. The token ID is:

- **Testnet:** `0.0.456858`
- **Mainnet:** See [Hedera Token Explorer](https://hashscan.io)

### Token Association (Critical Step)

Before an account can receive HTS tokens, it must be "associated" with the token.
This is unique to Hedera and not required on EVM chains.

```
New wallet created
       │
       ▼
associate_usdc_token(account_id)   ← REQUIRED before first transfer
       │
       ▼
Account can now receive USDC
```

Always call `associate-usdc` after creating a wallet.

### Amount Format

USDC uses 6 decimal places. Amounts are always in smallest unit:

```
1 USDC     = 1,000,000
0.50 USDC  =   500,000
0.001 USDC =     1,000
```

### Transaction IDs

Hedera transaction IDs follow the format:
```
{account_id}@{unix_timestamp_seconds}.{nanoseconds}

Example: 0.0.12345@1711886400.000000000
```

---

## API Usage

### Create a Wallet for an Agent

```http
POST /v1/public/{project_id}/hedera/wallets
Content-Type: application/json
X-API-Key: your_key

{
  "agent_id": "agent_abc123",
  "initial_balance": 10
}
```

Response:
```json
{
  "agent_id": "agent_abc123",
  "account_id": "0.0.123456",
  "public_key": "302a300506032b6570032100...",
  "network": "testnet",
  "created_at": "2026-04-03T12:00:00Z"
}
```

### Associate USDC (Required Before Transfers)

```http
POST /v1/public/{project_id}/hedera/wallets/0.0.123456/associate-usdc
X-API-Key: your_key
```

Response:
```json
{
  "transaction_id": "0.0.12345@1711886400.000000000",
  "status": "SUCCESS",
  "account_id": "0.0.123456",
  "token_id": "0.0.456858"
}
```

### Send USDC Payment

```http
POST /v1/public/{project_id}/hedera/payments
Content-Type: application/json
X-API-Key: your_key

{
  "agent_id": "agent_abc123",
  "amount": 5000000,
  "recipient": "0.0.654321",
  "task_id": "task_xyz789",
  "memo": "Task completion payment"
}
```

Response:
```json
{
  "payment_id": "hdr_pay_abc123def456",
  "agent_id": "agent_abc123",
  "task_id": "task_xyz789",
  "amount": 5000000,
  "recipient": "0.0.654321",
  "transaction_id": "0.0.12345@1711886400.000000000",
  "status": "SUCCESS",
  "created_at": "2026-04-03T12:00:00Z",
  "transaction_hash": "0xabcdef..."
}
```

### Verify Settlement

```http
POST /v1/public/{project_id}/hedera/payments/verify
Content-Type: application/json
X-API-Key: your_key

{
  "transaction_id": "0.0.12345@1711886400.000000000"
}
```

Response:
```json
{
  "transaction_id": "0.0.12345@1711886400.000000000",
  "settled": true,
  "status": "SUCCESS",
  "consensus_timestamp": "2026-04-03T12:00:01.234Z"
}
```

---

## Complete Python Example

```python
import asyncio
import httpx
import os

API_KEY = os.environ["AINATIVE_API_KEY"]
PROJECT_ID = os.environ["AINATIVE_PROJECT_ID"]
BASE_URL = f"https://api.ainative.studio/v1/public/{PROJECT_ID}"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def hedera_payment_workflow(agent_id: str, task_id: str, recipient: str):
    """
    Complete Hedera USDC payment workflow:
    1. Create wallet
    2. Associate USDC token
    3. Check balance
    4. Send payment
    5. Verify settlement
    6. Get receipt
    """
    async with httpx.AsyncClient() as client:

        # Step 1: Create wallet
        print("Creating Hedera wallet...")
        wallet = (await client.post(
            f"{BASE_URL}/hedera/wallets",
            headers=HEADERS,
            json={"agent_id": agent_id, "initial_balance": 10},
        )).json()
        account_id = wallet["account_id"]
        print(f"  Account: {account_id}")

        # Step 2: Associate USDC (REQUIRED)
        print("\nAssociating USDC token...")
        assoc = (await client.post(
            f"{BASE_URL}/hedera/wallets/{account_id}/associate-usdc",
            headers=HEADERS,
        )).json()
        print(f"  Status: {assoc['status']}")

        # Step 3: Check balance
        print("\nChecking balance...")
        balance = (await client.get(
            f"{BASE_URL}/hedera/wallets/{account_id}/balance",
            headers=HEADERS,
        )).json()
        print(f"  HBAR: {balance['hbar']}")
        print(f"  USDC: {balance['usdc']}")

        # Step 4: Send payment (5 USDC)
        print("\nSending USDC payment...")
        payment = (await client.post(
            f"{BASE_URL}/hedera/payments",
            headers=HEADERS,
            json={
                "agent_id": agent_id,
                "amount": 5_000_000,  # 5 USDC
                "recipient": recipient,
                "task_id": task_id,
                "memo": f"Payment for task {task_id}",
            },
        )).json()
        print(f"  Payment ID: {payment['payment_id']}")
        print(f"  Transaction: {payment['transaction_id']}")

        # Step 5: Verify settlement
        print("\nVerifying settlement...")
        verification = (await client.post(
            f"{BASE_URL}/hedera/payments/verify",
            headers=HEADERS,
            json={"transaction_id": payment["transaction_id"]},
        )).json()
        print(f"  Settled: {verification['settled']}")
        print(f"  Consensus: {verification.get('consensus_timestamp')}")

        # Step 6: Get receipt
        print("\nFetching receipt...")
        receipt = (await client.get(
            f"{BASE_URL}/hedera/payments/{payment['payment_id']}/receipt",
            headers=HEADERS,
        )).json()
        print(f"  Hash: {receipt.get('hash')}")
        print(f"  Status: {receipt['status']}")


asyncio.run(hedera_payment_workflow(
    agent_id="agent_finance_001",
    task_id="task_invoice_processing",
    recipient="0.0.654321",
))
```

---

## Error Handling

```python
from httpx import HTTPStatusError

try:
    response = await client.post(
        f"{BASE_URL}/hedera/payments",
        headers=HEADERS,
        json={"agent_id": "agent_abc", "amount": 0, "recipient": "0.0.22222", "task_id": "task_1"},
    )
    response.raise_for_status()
except HTTPStatusError as e:
    error = e.response.json()
    print(f"Error code: {error['error_code']}")
    print(f"Detail: {error['detail']}")

# Common error codes:
# HEDERA_PAYMENT_ERROR (502) — Hedera network error or invalid amount
# HEDERA_WALLET_NOT_FOUND (404) — No wallet for this agent
# SCHEMA_VALIDATION_ERROR (422) — Invalid request body
```

---

## Hedera Mirror Node

You can verify transactions directly on the Hedera mirror node:

```bash
# Check transaction status
curl https://testnet.mirrornode.hedera.com/api/v1/transactions/0.0.12345-1711886400-000000000

# Check account balance
curl https://testnet.mirrornode.hedera.com/api/v1/balances?account.id=0.0.12345

# Check token associations
curl https://testnet.mirrornode.hedera.com/api/v1/accounts/0.0.12345/tokens
```

---

## Production Checklist

Before going to mainnet:

- [ ] Update `HEDERA_NETWORK=mainnet` in environment
- [ ] Update USDC token ID to mainnet token ID
- [ ] Fund operator account with HBAR on mainnet
- [ ] Test with small amounts first
- [ ] Set up monitoring for failed transactions
- [ ] Configure alerts for settlement timeouts
- [ ] Store private keys in a secrets manager (not environment variables)
- [ ] Implement proper key rotation

---

## Related Resources

- [Hedera Developer Portal](https://portal.hedera.com)
- [Hedera Token Service (HTS) Docs](https://docs.hedera.com/hedera/sdks-and-apis/sdks/token-service)
- [Hedera Mirror Node REST API](https://docs.hedera.com/hedera/sdks-and-apis/rest-api)
- [HashScan Explorer (Testnet)](https://hashscan.io/testnet)
- [API Reference](./api-reference.md) — Full endpoint documentation
- [Examples](./examples.md) — More code examples

Built by AINative Dev Team
