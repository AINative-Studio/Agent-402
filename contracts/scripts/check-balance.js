/**
 * Check wallet balance on Arc Testnet
 * Verifies deployer has USDC for gas fees
 */

const hre = require("hardhat");

async function main() {
  console.log("🔍 Checking Arc Testnet wallet balance...\n");

  const [deployer] = await hre.ethers.getSigners();

  console.log("📍 Network:", hre.network.name);
  console.log("🔑 Wallet address:", deployer.address);

  try {
    const balance = await hre.ethers.provider.getBalance(deployer.address);
    const balanceInUsdc = hre.ethers.formatUnits(balance, 6); // USDC has 6 decimals

    console.log("💰 USDC Balance:", balanceInUsdc, "USDC");

    if (parseFloat(balanceInUsdc) === 0) {
      console.log("\n❌ No USDC balance!");
      console.log("\n📝 Next steps:");
      console.log("1. Go to: https://faucet.circle.com");
      console.log("2. Connect wallet:", deployer.address);
      console.log("3. Request test USDC");
      console.log("4. Wait ~30 seconds");
      console.log("5. Run this script again\n");
      process.exit(1);
    } else if (parseFloat(balanceInUsdc) < 1) {
      console.log("\n⚠️  Low balance! You may need more USDC for deployment.");
      console.log("Get more at: https://faucet.circle.com\n");
    } else {
      console.log("\n✅ Balance looks good! Ready to deploy!\n");
    }

    console.log("🔗 View wallet on explorer:");
    console.log(`https://testnet.arcscan.app/address/${deployer.address}\n`);

  } catch (error) {
    console.error("❌ Error checking balance:", error.message);

    if (error.message.includes("could not detect network")) {
      console.log("\n💡 Tip: Make sure Arc Testnet RPC is accessible");
      console.log("RPC URL:", process.env.ARC_TESTNET_RPC_URL);
    }

    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
