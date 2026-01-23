/**
 * Deployment script for Arc Blockchain
 * Deploys AgentRegistry, ReputationRegistry, and AgentTreasury contracts
 *
 * Usage:
 * - Arc Testnet: npx hardhat run scripts/deploy.js --network arc-testnet
 * - Arc Mainnet: npx hardhat run scripts/deploy.js --network arc-mainnet
 *
 * Refs Issue #113
 */

const hre = require("hardhat");

async function main() {
  console.log("🚀 Deploying Agent-402 Smart Contracts to Arc Blockchain...\n");

  const [deployer] = await hre.ethers.getSigners();
  console.log("📝 Deploying with account:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("💰 Account balance:", hre.ethers.formatEther(balance), "ETH\n");

  // 1. Deploy AgentRegistry
  console.log("🔹 Deploying AgentRegistry (ERC-721 Agent Identity)...");
  const AgentRegistry = await hre.ethers.getContractFactory("AgentRegistry");
  const agentRegistry = await AgentRegistry.deploy();
  await agentRegistry.waitForDeployment();
  const agentRegistryAddress = await agentRegistry.getAddress();
  console.log("✅ AgentRegistry deployed to:", agentRegistryAddress);

  // 2. Deploy ReputationRegistry
  console.log("\n🔹 Deploying ReputationRegistry (Feedback & Reputation)...");
  const ReputationRegistry = await hre.ethers.getContractFactory("ReputationRegistry");
  const reputationRegistry = await ReputationRegistry.deploy();
  await reputationRegistry.waitForDeployment();
  const reputationRegistryAddress = await reputationRegistry.getAddress();
  console.log("✅ ReputationRegistry deployed to:", reputationRegistryAddress);

  // 3. Deploy AgentTreasury
  console.log("\n🔹 Deploying AgentTreasury (Circle Wallet Wrapper)...");
  const AgentTreasury = await hre.ethers.getContractFactory("AgentTreasury");
  const agentTreasury = await AgentTreasury.deploy();
  await agentTreasury.waitForDeployment();
  const agentTreasuryAddress = await agentTreasury.getAddress();
  console.log("✅ AgentTreasury deployed to:", agentTreasuryAddress);

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log("📋 DEPLOYMENT SUMMARY");
  console.log("=".repeat(60));
  console.log("Network:", hre.network.name);
  console.log("Deployer:", deployer.address);
  console.log("\nContract Addresses:");
  console.log("  AgentRegistry:      ", agentRegistryAddress);
  console.log("  ReputationRegistry: ", reputationRegistryAddress);
  console.log("  AgentTreasury:      ", agentTreasuryAddress);
  console.log("=".repeat(60));

  // Save deployment info
  const deploymentInfo = {
    network: hre.network.name,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: {
      AgentRegistry: agentRegistryAddress,
      ReputationRegistry: reputationRegistryAddress,
      AgentTreasury: agentTreasuryAddress
    }
  };

  const fs = require('fs');
  const deploymentPath = `./deployments/${hre.network.name}.json`;

  // Create deployments directory if it doesn't exist
  if (!fs.existsSync('./deployments')) {
    fs.mkdirSync('./deployments');
  }

  fs.writeFileSync(
    deploymentPath,
    JSON.stringify(deploymentInfo, null, 2)
  );

  console.log(`\n💾 Deployment info saved to: ${deploymentPath}`);

  // Verification instructions
  if (hre.network.name !== 'hardhat' && hre.network.name !== 'localhost') {
    console.log("\n📝 To verify contracts on Arc Explorer, run:");
    console.log(`npx hardhat verify --network ${hre.network.name} ${agentRegistryAddress}`);
    console.log(`npx hardhat verify --network ${hre.network.name} ${reputationRegistryAddress}`);
    console.log(`npx hardhat verify --network ${hre.network.name} ${agentTreasuryAddress}`);
  }

  console.log("\n✨ Deployment complete!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
