# Agent-402 Smart Contracts (Arc Blockchain)

Trustless Agent Framework smart contracts for the Arc/Circle "Agentic Commerce" Hackathon.

**Issue:** [#113](https://github.com/AINative-Studio/Agent-402/issues/113)
**Deadline:** January 23, 2026 (5:00 PM PST)

---

## 📋 Contracts

### 1. AgentRegistry.sol
**ERC-721 based agent identity registry**

- Each agent receives a unique NFT representing their on-chain identity
- Stores DID (Decentralized Identifier), role, public key
- Supports activation/deactivation
- Implements ERC-721 standard for composability

**Key Functions:**
- `registerAgent(address, did, role, publicKey)` - Register new agent
- `getAgentMetadata(tokenId)` - Get agent details
- `getTokenIdByDID(did)` - Lookup by DID
- `isAgentActive(tokenId)` - Check agent status

### 2. ReputationRegistry.sol
**Event-based reputation system**

- Stores feedback and reputation events on-chain
- Calculates trust tiers (0-4) based on feedback
- Immutable audit trail for all agent interactions
- Supports Progressive Trust Tiers from PRD

**Key Functions:**
- `submitFeedback(agentTokenId, type, score, comment, txHash)` - Submit feedback
- `getAgentScore(agentTokenId)` - Get total reputation score
- `getAgentTrustTier(agentTokenId)` - Get trust tier (0-4)
- `getAgentReputationSummary(agentTokenId)` - Full reputation data

**Trust Tiers:**
- **Tier 0**: < 10 feedback or avg score < 0 (Untrusted/New)
- **Tier 1**: >= 10 feedback, avg >= 0 (Emerging)
- **Tier 2**: >= 25 feedback, avg >= 5 (Established)
- **Tier 3**: >= 50 feedback, avg >= 7 (Trusted)
- **Tier 4**: >= 100 feedback, avg >= 9 (Elite)

### 3. AgentTreasury.sol
**Circle Wallet wrapper for agent treasury management**

- Each agent has a dedicated treasury for USDC payments
- Records all payments on-chain with X402 receipt hashes
- Supports agent-to-agent payments
- Testnet simulation (production uses actual USDC contract)

**Key Functions:**
- `createTreasury(agentTokenId, owner)` - Create agent treasury
- `fundTreasury(treasuryId, amount)` - Add USDC to treasury
- `processPayment(from, to, amount, purpose, x402Hash)` - Agent-to-agent payment
- `getTreasuryBalance(treasuryId)` - Check balance

---

## 🚀 Quick Start

### Prerequisites

```bash
node >= 18.0.0
npm >= 9.0.0
```

### Installation

```bash
cd contracts
npm install
```

### Configuration

Create `.env` in contracts directory:

```bash
# Arc Network Configuration
ARC_TESTNET_RPC_URL=https://testnet.arc.xyz
ARC_MAINNET_RPC_URL=https://mainnet.arc.xyz
ARC_EXPLORER_API_KEY=your_api_key_here

# Deployment
DEPLOYER_PRIVATE_KEY=your_private_key_here
```

**⚠️ NEVER commit .env to git!**

---

## 📦 Deployment

### 1. Compile Contracts

```bash
npm run compile
```

### 2. Deploy to Arc Testnet

```bash
npm run deploy:arc-testnet
```

This will:
- Deploy all 3 contracts to Arc Testnet
- Save deployment addresses to `deployments/arc-testnet.json`
- Display verification commands

### 3. Register Test Agents

```bash
npx hardhat run scripts/register-agents.js --network arc-testnet
```

This will:
- Register 3 agents: Analyst, Compliance, Transaction
- Create treasuries for each agent
- Save agent details to deployment file

### 4. Verify Contracts on Arc Explorer

```bash
npx hardhat verify --network arc-testnet <CONTRACT_ADDRESS>
```

---

## 🧪 Testing

### Run Unit Tests

```bash
npm test
```

### Run Tests with Coverage

```bash
npm run test:coverage
```

### Test on Local Hardhat Network

```bash
# Terminal 1: Start local node
npx hardhat node

# Terminal 2: Deploy to local network
npx hardhat run scripts/deploy.js --network localhost
npx hardhat run scripts/register-agents.js --network localhost
```

---

## 📁 Project Structure

```
contracts/
├── src/                      # Solidity contracts
│   ├── AgentRegistry.sol
│   ├── ReputationRegistry.sol
│   └── AgentTreasury.sol
├── scripts/                  # Deployment scripts
│   ├── deploy.js
│   └── register-agents.js
├── test/                     # Contract tests
├── deployments/              # Deployment artifacts
│   └── arc-testnet.json
├── hardhat.config.js         # Hardhat configuration
├── package.json
└── README.md
```

---

## 🔗 Integration with Agent-402

### Backend Integration

```python
# app/services/arc_blockchain.py
import json
from web3 import Web3

class ArcBlockchainService:
    def __init__(self):
        with open('contracts/deployments/arc-testnet.json') as f:
            deployment = json.load(f)

        self.agent_registry_address = deployment['contracts']['AgentRegistry']
        self.reputation_registry_address = deployment['contracts']['ReputationRegistry']
        self.agent_treasury_address = deployment['contracts']['AgentTreasury']

        # Initialize Web3 connection
        self.w3 = Web3(Web3.HTTPProvider('https://testnet.arc.xyz'))

    def register_agent(self, did, role, public_key):
        """Register agent on-chain"""
        # Implementation using web3.py
        pass

    def submit_feedback(self, agent_token_id, score, comment):
        """Submit reputation feedback"""
        pass

    def process_payment(self, from_agent, to_agent, amount, x402_receipt):
        """Process USDC payment between agents"""
        pass
```

### Agent Usage

```python
# app/agents/analyst_agent.py
from crewai import Agent
from app.services.arc_blockchain import ArcBlockchainService

arc = ArcBlockchainService()

# Register agent on-chain
token_id = arc.register_agent(
    did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
    role="analyst",
    public_key="0x04a1b2c3..."
)

# Use agent for tasks...
# After task completion, update reputation
arc.submit_feedback(token_id, score=8, comment="Excellent analysis")
```

---

## 📊 Deployment Artifacts

After deployment, check `deployments/arc-testnet.json`:

```json
{
  "network": "arc-testnet",
  "deployer": "0x...",
  "timestamp": "2026-01-22T...",
  "contracts": {
    "AgentRegistry": "0x...",
    "ReputationRegistry": "0x...",
    "AgentTreasury": "0x..."
  },
  "agents": [
    {
      "name": "Analyst Agent",
      "tokenId": "0",
      "treasuryId": "1",
      "did": "did:key:z6Mkh...",
      "role": "analyst"
    }
  ]
}
```

---

## 🎯 Hackathon Acceptance Criteria

- [x] All 3 contracts implemented
- [ ] Contracts compiled without errors
- [ ] Contracts deployed to Arc Testnet
- [ ] Contract addresses verified on Arc Explorer
- [ ] 3 test agents registered on-chain
- [ ] Reputation events emitting correctly
- [ ] Treasury contracts created for each agent

---

## 🔍 Verification on Arc Explorer

After deployment, verify contracts at:
- **Testnet Explorer:** https://explorer-testnet.arc.xyz
- **Mainnet Explorer:** https://explorer.arc.xyz

Search for contract addresses from `deployments/arc-testnet.json`.

---

## 📚 References

- [Trustless Agent Framework PRD](../docs/product/trustless-agent-framework/PRD.md)
- [Phase 2 Hackathon Strategy](../docs/product/PHASE_2_HACKATHON_STRATEGY.md)
- [Arc Documentation](https://docs.arc.xyz)
- [Circle Developer Docs](https://developers.circle.com/)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)

---

Built by AINative Dev Team
All Data Services Built on ZeroDB
