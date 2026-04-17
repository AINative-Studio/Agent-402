# Testnet Operations Runbook

**Refs #293** — Pre-workshop testnet readiness checklist for Tutorial 2 (Payments & Trust).

Run this checklist end-to-end before the workshop starts to confirm the operator
account has the balances and token associations needed to support all attendees.

## Capacity

Provision for **1.5× the attendee count** to absorb retries and failed Associate
attempts. For a 50-attendee workshop:

| Resource                         | Per attendee | 50-attendee total | Buffer (1.5×) |
|----------------------------------|--------------|-------------------|---------------|
| HBAR for new wallet creation     | ~5 HBAR      | 250 HBAR          | 375 HBAR      |
| HBAR for tx fees (~0.01 each)    | ~0.1 HBAR    | 5 HBAR            | 10 HBAR       |
| USDC for agent demo transfer     | 2 USDC       | 100 USDC          | 150 USDC      |

## Pre-workshop checklist

```bash
# Operator env sanity
cd backend
cat .env | grep -E 'HEDERA_OPERATOR|ZERODB'

# Server up
uvicorn app.main:app --reload --port 8000 &
sleep 3

# Smoke
python3 ../scripts/workshop_smoke_test.py
```

### 1. Operator balance

```bash
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/v1/public/proj_workshop/hedera/wallets/$HEDERA_OPERATOR_ID/balance
```

Expected: `hbar_balance >= 400`, `usdc_balance >= 150`.

If short, fund via the Hedera testnet faucets:
- HBAR: https://portal.hedera.com/
- USDC: https://portal.hedera.com/faucet (USDC associate + faucet in one step)

### 2. End-to-end payment flow

Run through Tutorial 2 steps against testnet as an operator:

```bash
# 1. Create wallet
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"agent_id":"probe-agent"}' \
  http://localhost:8000/api/v1/hedera/wallets
# => save account_id

# 2. Associate USDC
curl -X POST -H "X-API-Key: $API_KEY" \
  http://localhost:8000/api/v1/hedera/wallets/{account_id}/associate-usdc

# 3. Check balance (0 USDC expected)
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/api/v1/hedera/wallets/{account_id}/balance

# 4. Execute USDC payment
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"agent_id":"probe-agent","amount":1000000,"recipient":"0.0.22222","task_id":"probe-task-1","memo":"testnet probe"}' \
  http://localhost:8000/api/v1/hedera/payments
# => save transaction_id

# 5. Verify receipt
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/api/v1/hedera/payments/{transaction_id}/verify
# => verified: true, consensus_timestamp non-empty

# 6. Open mirror_node_url from response in a browser — expect a 200 JSON payload
```

All six steps must succeed before declaring testnet ready.

### 3. Mirror node availability

```bash
curl -s https://testnet.mirrornode.hedera.com/api/v1/accounts/$HEDERA_OPERATOR_ID | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(d['account'])"
```

If this fails, the Hedera mirror node is likely degraded (check
https://status.hedera.com/). Payment tests will still settle but the
`mirror_node_url` in verify responses may 5xx.

## Faucet flow for attendees

Attendees needing testnet HBAR can either:
1. Create a new Hedera portal account at https://portal.hedera.com/ and copy the seed funding, or
2. Request HBAR from the in-portal faucet (10,000 HBAR / 24h per account).

Document this in the workshop intro — attendees without HBAR will fail at
Tutorial 2 Step 4 with `INSUFFICIENT_PAYER_BALANCE`.

## Known edge cases

| Scenario                                    | Symptom                              | Fix                                                       |
|---------------------------------------------|--------------------------------------|-----------------------------------------------------------|
| Attendee never called `/associate-usdc`     | Payment 400 `TOKEN_NOT_ASSOCIATED_TO_ACCOUNT` | Repeat Step 2 of Tutorial 2                              |
| Mirror node lag (>5s to index)              | `/verify` returns `verified: false`  | Retry verify 10–15s later; mirror node eventually catches up |
| Operator HBAR below ~50                     | New wallet creation 502              | Refund operator from https://portal.hedera.com/           |
| USDC token ID mismatch                      | `TOKEN_NOT_ASSOCIATED_TO_ACCOUNT`    | Confirm `.env` `USDC_TOKEN_ID=0.0.456858` (testnet)       |

Add any new failure mode you hit here, with the resolution, so the next operator doesn't rediscover it.
