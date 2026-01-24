# Circle Integration Manual Testing Guide

This guide covers how to test the Circle Developer-Controlled Wallets integration in the Agent-402 platform.

## Prerequisites

1. **Backend running** on `http://localhost:8000`
2. **Frontend running** on `http://localhost:5173` (or production at `agent402.ainative.studio`)
3. **Circle Console access** at [console.circle.com](https://console.circle.com)
4. **AINative account** for authentication

## Test Credentials

- **Email**: `admin@ainative.studio`
- **Password**: `Admin2025!Secure`

---

## Part 1: Circle Console Verification

### 1.1 Verify Wallet Set
1. Go to [console.circle.com](https://console.circle.com)
2. Navigate to **Programmable Wallets** → **Wallet Sets**
3. Verify wallet set exists: `Agent402-Wallets`
4. Wallet Set ID: `d000fe0f-7547-56f0-97f9-1226508b91d5`

### 1.2 Verify Agent Wallets
1. Navigate to **Programmable Wallets** → **Wallets**
2. Verify 3 wallets exist on **ARC-TESTNET**:

| Agent | Wallet ID | Address |
|-------|-----------|---------|
| Analyst | `699e2ea4-f508-5afa-a1bd-5a8f648bedf1` | `0x6bd005d0c4970c32f4b6e3b2121785ab1f0dabdb` |
| Compliance | `6a4f70de-aae1-5819-9aa4-7e94084bd2bb` | `0x460b48cbc8814a51fc6ad0cef740a44c0eb73fd9` |
| Transaction | `9fe6cff6-e176-5130-a9c2-bfeca5e31008` | `0x40889b44ef4ad7bbb921ef68ff9ee7bfbdfbd50e` |

### 1.3 Check Wallet Balances
1. Click on each wallet
2. Verify USDC-TESTNET balance is visible
3. Note the current balances for comparison after transfers

---

## Part 2: UI Testing

### 2.1 Login to Dashboard
1. Navigate to the frontend URL
2. Enter credentials:
   - Email: `admin@ainative.studio`
   - Password: `Admin2025!Secure`
3. Click **Login**
4. Verify redirect to Dashboard

### 2.2 View Circle Wallet Balances (Dashboard)
1. On the Dashboard, look for the **Circle Wallets** section
2. Verify all 3 agent wallets are displayed:
   - Analyst Agent with USDC balance
   - Compliance Agent with USDC balance
   - Transaction Agent with USDC balance
3. Balances should match Circle Console values

### 2.3 View Transaction History
1. In the Circle Wallets section, click on a wallet or navigate to transaction history
2. Verify recent transfers are displayed:
   - Transfer from Analyst → Compliance (5 USDC)
   - Transfer from Compliance → Analyst (2 USDC)
3. Each transaction should show:
   - Amount
   - Status (COMPLETE)
   - Transaction hash (clickable link to block explorer)

---

## Part 3: API Testing (via curl or Postman)

### 3.1 Get Auth Token
```bash
TOKEN=$(curl -s -X POST "https://api.ainative.studio/v1/public/auth/login-json" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@ainative.studio","password":"Admin2025!Secure"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
```

### 3.2 List Circle Wallets
```bash
curl -s "http://localhost:8000/v1/public/{project_id}/circle/wallets" \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

### 3.3 Get Wallet Balance
```bash
curl -s "http://localhost:8000/v1/public/{project_id}/circle/wallets/699e2ea4-f508-5afa-a1bd-5a8f648bedf1" \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

### 3.4 Create a Transfer
```bash
curl -s -X POST "http://localhost:8000/v1/public/{project_id}/circle/transfers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_wallet_id": "699e2ea4-f508-5afa-a1bd-5a8f648bedf1",
    "destination_wallet_id": "6a4f70de-aae1-5819-9aa4-7e94084bd2bb",
    "amount": "1.00"
  }' | jq
```

### 3.5 Check Transfer Status
```bash
curl -s "http://localhost:8000/v1/public/{project_id}/circle/transfers/{transfer_id}" \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

---

## Part 4: End-to-End Demo Flow

This is the complete flow for a submission video:

### Step 1: Show MetaMask Transaction (Existing Flow)
1. Connect MetaMask wallet on the website
2. Navigate to an agent (e.g., Analyst Agent)
3. Click **Hire Agent**
4. Approve transaction in MetaMask popup
5. Wait for confirmation
6. Show transaction on **Arc Block Explorer**

### Step 2: Show Circle Programmatic Payment (New Flow)
1. Open **Circle Developer Console** ([console.circle.com](https://console.circle.com))
2. Navigate to **Transactions**
3. Show the programmatic transfers:
   - Analyst → Compliance (5 USDC)
   - Compliance → Analyst (2 USDC)
4. Click on a transaction to show details
5. Copy transaction hash
6. Open **Arc Block Explorer** and paste the hash
7. Show the verified transaction on-chain

### Step 3: Show Dashboard Integration
1. Return to the Agent-402 Dashboard
2. Show Circle Wallet balances for all 3 agents
3. Show transaction history
4. Demonstrate that both MetaMask (user) and Circle (programmatic) transactions are tracked

---

## Part 5: Verification Checklist

### Circle Console
- [ ] Wallet set exists
- [ ] 3 agent wallets created on ARC-TESTNET
- [ ] Wallets have USDC-TESTNET balance
- [ ] Transactions visible in console

### Arc Block Explorer
- [ ] Transactions verifiable by hash
- [ ] Correct source/destination addresses
- [ ] Correct amounts

### Frontend UI
- [ ] Login works with AINative credentials
- [ ] Circle wallet balances displayed
- [ ] Transaction history visible
- [ ] Block explorer links work

### Backend API
- [ ] `/circle/wallets` endpoint returns wallets
- [ ] `/circle/wallets/{id}` returns balance
- [ ] `/circle/transfers` creates transfers
- [ ] `/circle/transfers/{id}` returns status

---

## Troubleshooting

### "Missing X-API-Key header"
- Backend may need restart to pick up auth changes
- Ensure using `Authorization: Bearer {token}` header

### "Project not found"
- Create a project first or use an existing project ID
- Check `/v1/public/projects` for available projects

### "API parameter invalid" on transfers
- Ensure `blockchain: "ARC-TESTNET"` is included
- Verify wallet IDs are valid UUIDs

### Circle wallet balance not updating
- Balances may take a few seconds to update after transfer
- Refresh the page or wait for polling interval

---

## Quick Reference

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/public/{project}/circle/wallets` | GET | List wallets |
| `/v1/public/{project}/circle/wallets` | POST | Create wallet |
| `/v1/public/{project}/circle/wallets/{id}` | GET | Get wallet & balance |
| `/v1/public/{project}/circle/transfers` | POST | Create transfer |
| `/v1/public/{project}/circle/transfers/{id}` | GET | Get transfer status |
| `/v1/public/{project}/agents/{id}/pay` | POST | Pay agent (backend-initiated) |

### Wallet Addresses (ARC-TESTNET)
```
Analyst:    0x6bd005d0c4970c32f4b6e3b2121785ab1f0dabdb
Compliance: 0x460b48cbc8814a51fc6ad0cef740a44c0eb73fd9
Transaction: 0x40889b44ef4ad7bbb921ef68ff9ee7bfbdfbd50e
```

### Circle Console Links
- Console: https://console.circle.com
- Wallets: https://console.circle.com/wallets
- Transactions: https://console.circle.com/transactions
