# Arc Testnet Setup Guide

Quick guide to get your wallet ready for deploying Agent-402 smart contracts.

**Issue:** [#113](https://github.com/AINative-Studio/Agent-402/issues/113)

---

## ✅ What You Need to Know

**Arc is a blockchain, not a service!**
- No sign-up required
- No API keys needed
- Just connect like any blockchain (Ethereum, Polygon, etc.)
- **Unique:** Arc uses USDC as gas (not ETH!)

---

## 🚀 Step-by-Step Setup (5 minutes)

### Step 1: Add Arc Testnet to MetaMask

**Option A: Automatic (Easiest)**
1. Go to: https://thirdweb.com/arc-testnet
2. Click "Add to MetaMask"
3. Confirm in MetaMask

**Option B: Manual**
1. Open MetaMask
2. Click network dropdown → "Add Network"
3. Enter these details:

```
Network Name: Arc Testnet
RPC URL: https://rpc.testnet.arc.network
Chain ID: 5042002
Currency Symbol: USDC
Block Explorer: https://testnet.arcscan.app
```

4. Click "Save"

---

### Step 2: Get Test USDC (Faucet)

**Important:** Arc uses USDC for gas fees, not ETH!

1. Go to: **https://faucet.circle.com**
2. Connect your MetaMask wallet
3. Select "Arc Testnet"
4. Click "Request test USDC"
5. Wait ~30 seconds

You should see test USDC appear in your wallet!

**Troubleshooting:**
- If faucet doesn't work, try switching to Arc Testnet network first
- You may need to add USDC token to MetaMask to see balance
- Check balance at: https://testnet.arcscan.app

---

### Step 3: Export Your Private Key

**⚠️ CRITICAL SECURITY WARNING:**
- **ONLY use a test wallet!**
- **NEVER use your real wallet with actual funds!**
- Create a new wallet just for this if needed

**Steps:**
1. In MetaMask, click the 3 dots (⋮)
2. Select "Account Details"
3. Click "Show Private Key"
4. Enter your MetaMask password
5. **Copy the private key**
6. Paste it into `/Users/aideveloper/Agent-402/contracts/.env`:

```bash
DEPLOYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
```

7. **Save the .env file**

---

### Step 4: Verify Setup

Run this command to check your wallet has funds:

```bash
# From contracts directory
npx hardhat run scripts/check-balance.js --network arc-testnet
```

Expected output:
```
Wallet: 0xYourAddress
Balance: 100.000000 USDC
Ready to deploy! ✅
```

---

## 📊 Arc Testnet Resources

| Resource | URL |
|----------|-----|
| **RPC Endpoint** | https://rpc.testnet.arc.network |
| **Chain ID** | 5042002 |
| **Faucet** | https://faucet.circle.com |
| **Explorer** | https://testnet.arcscan.app |
| **Gas Token** | USDC (not ETH!) |
| **Docs** | https://www.arc.network/docs |

---

## 🎯 What's Different About Arc?

1. **USDC as Gas** - Transaction fees paid in USDC, not ETH
2. **Circle Native** - Built by Circle specifically for USDC transactions
3. **Fast Finality** - Transactions confirm in < 1 second
4. **Low Cost** - Gas fees are fractions of a cent

---

## ❓ Common Issues

### "Insufficient funds for gas"
- Get more test USDC from faucet
- Check you're on Arc Testnet network

### "Network not found"
- Double-check Chain ID is 5042002
- Verify RPC URL: https://rpc.testnet.arc.network

### "Private key invalid"
- Make sure it starts with "0x"
- Check for extra spaces or quotes
- Regenerate from MetaMask if needed

### "Transaction failed"
- Check you have enough USDC for gas
- Verify you're connected to Arc Testnet
- Try increasing gas limit in deployment script

---

## 🔒 Security Checklist

Before deploying:
- [ ] Using a TEST WALLET ONLY (not real wallet)
- [ ] Private key in .env file (not committed to git)
- [ ] .env is in .gitignore
- [ ] Have test USDC from faucet
- [ ] Connected to Arc Testnet (Chain ID: 5042002)

---

## 🚀 Next Steps

Once setup is complete:

```bash
# 1. Deploy contracts
npm run deploy:arc-testnet

# 2. Register agents
npx hardhat run scripts/register-agents.js --network arc-testnet

# 3. Verify on explorer
# Visit https://testnet.arcscan.app
# Search for your contract addresses
```

---

## 📞 Need Help?

- **Arc Docs:** https://www.arc.network/docs
- **Circle Developer Discord:** https://discord.com/invite/circle
- **Issue #113:** https://github.com/AINative-Studio/Agent-402/issues/113

---

Built by AINative Dev Team
