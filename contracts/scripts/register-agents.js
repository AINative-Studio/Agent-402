/**
 * Register 3 test agents on Arc Blockchain
 * Creates the Analyst, Compliance, and Transaction agents
 *
 * Usage:
 * npx hardhat run scripts/register-agents.js --network arc-testnet
 *
 * Refs Issue #113
 */

const hre = require("hardhat");
const fs = require('fs');

async function main() {
  console.log("🤖 Registering Agent-402 Test Agents...\n");

  const [deployer] = await hre.ethers.getSigners();
  console.log("📝 Registering with account:", deployer.address);

  // Load deployment info
  const deploymentPath = `./deployments/${hre.network.name}.json`;
  if (!fs.existsSync(deploymentPath)) {
    console.error(`❌ Deployment file not found: ${deploymentPath}`);
    console.error("Please run deploy.js first!");
    process.exit(1);
  }

  const deploymentInfo = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
  const agentRegistryAddress = deploymentInfo.contracts.AgentRegistry;
  const agentTreasuryAddress = deploymentInfo.contracts.AgentTreasury;

  console.log("📍 AgentRegistry:", agentRegistryAddress);
  console.log("📍 AgentTreasury:", agentTreasuryAddress, "\n");

  // Get contract instances
  const AgentRegistry = await hre.ethers.getContractFactory("AgentRegistry");
  const agentRegistry = AgentRegistry.attach(agentRegistryAddress);

  const AgentTreasury = await hre.ethers.getContractFactory("AgentTreasury");
  const agentTreasury = AgentTreasury.attach(agentTreasuryAddress);

  // Define 3 test agents (from PRD §5 Agent Personas)
  const agents = [
    {
      name: "Analyst Agent",
      did: "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
      role: "analyst",
      publicKey: "0x04a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abc"
    },
    {
      name: "Compliance Agent",
      did: "did:key:z6Mki9E8kZT3ybvrYqVqJQrW9vHn6YuVjAVdHqzBGbYQk2Jp",
      role: "compliance",
      publicKey: "0x04b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd"
    },
    {
      name: "Transaction Agent",
      did: "did:key:z6MkkKQ3EbHjE4VPZqL6LS2b4kXy7nZvJqW9vHn6YuVjAVdH",
      role: "transaction",
      publicKey: "0x04c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcde"
    }
  ];

  const registeredAgents = [];

  // Register each agent
  for (let i = 0; i < agents.length; i++) {
    const agent = agents[i];
    console.log(`🔹 Registering ${agent.name}...`);

    try {
      // Register agent
      const tx = await agentRegistry.registerAgent(
        deployer.address,
        agent.did,
        agent.role,
        agent.publicKey
      );
      const receipt = await tx.wait();

      // Get token ID from event
      const event = receipt.logs.find(log => {
        try {
          const parsed = agentRegistry.interface.parseLog(log);
          return parsed && parsed.name === 'AgentRegistered';
        } catch {
          return false;
        }
      });

      const tokenId = event ? agentRegistry.interface.parseLog(event).args.tokenId : i;

      console.log(`  ✅ Token ID: ${tokenId}`);
      console.log(`  📍 DID: ${agent.did}`);
      console.log(`  👤 Role: ${agent.role}`);

      // Create treasury for agent
      console.log(`  💰 Creating treasury...`);
      const treasuryTx = await agentTreasury.createTreasury(tokenId, deployer.address);
      const treasuryReceipt = await treasuryTx.wait();

      // Get treasury ID from event
      const treasuryEvent = treasuryReceipt.logs.find(log => {
        try {
          const parsed = agentTreasury.interface.parseLog(log);
          return parsed && parsed.name === 'TreasuryCreated';
        } catch {
          return false;
        }
      });

      const treasuryId = treasuryEvent ? agentTreasury.interface.parseLog(treasuryEvent).args.treasuryId : null;
      console.log(`  ✅ Treasury ID: ${treasuryId}\n`);

      registeredAgents.push({
        name: agent.name,
        tokenId: tokenId.toString(),
        treasuryId: treasuryId ? treasuryId.toString() : null,
        did: agent.did,
        role: agent.role,
        owner: deployer.address
      });

    } catch (error) {
      console.error(`  ❌ Error registering ${agent.name}:`, error.message);
    }
  }

  // Summary
  console.log("=".repeat(60));
  console.log("📋 REGISTRATION SUMMARY");
  console.log("=".repeat(60));
  console.log(`Network: ${hre.network.name}`);
  console.log(`Total Agents: ${registeredAgents.length}`);
  console.log("\nRegistered Agents:");

  registeredAgents.forEach((agent, idx) => {
    console.log(`\n${idx + 1}. ${agent.name}`);
    console.log(`   Token ID:    ${agent.tokenId}`);
    console.log(`   Treasury ID: ${agent.treasuryId}`);
    console.log(`   Role:        ${agent.role}`);
    console.log(`   DID:         ${agent.did}`);
  });

  console.log("\n" + "=".repeat(60));

  // Save registration info
  deploymentInfo.agents = registeredAgents;
  fs.writeFileSync(
    deploymentPath,
    JSON.stringify(deploymentInfo, null, 2)
  );

  console.log(`\n💾 Registration info saved to: ${deploymentPath}`);
  console.log("\n✨ Agent registration complete!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
