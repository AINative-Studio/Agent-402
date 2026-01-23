require("@nomicfoundation/hardhat-toolbox");

// Load environment variables
require('dotenv').config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    hardhat: {
      chainId: 31337
    },
    "arc-testnet": {
      url: process.env.ARC_TESTNET_RPC_URL || "https://rpc.testnet.arc.network",
      chainId: 5042002, // Arc testnet chain ID
      accounts: process.env.DEPLOYER_PRIVATE_KEY ? [process.env.DEPLOYER_PRIVATE_KEY] : [],
      gas: "auto",
      gasPrice: "auto"
    },
    "arc-mainnet": {
      url: process.env.ARC_MAINNET_RPC_URL || "https://mainnet.arc.xyz",
      chainId: 1993, // Arc mainnet chain ID (placeholder - verify actual)
      accounts: process.env.DEPLOYER_PRIVATE_KEY ? [process.env.DEPLOYER_PRIVATE_KEY] : [],
      gas: "auto",
      gasPrice: "auto"
    }
  },
  etherscan: {
    apiKey: {
      "arc-testnet": process.env.ARC_EXPLORER_API_KEY || "placeholder",
      "arc-mainnet": process.env.ARC_EXPLORER_API_KEY || "placeholder"
    },
    customChains: [
      {
        network: "arc-testnet",
        chainId: 5042002,
        urls: {
          apiURL: "https://testnet.arcscan.app/api",
          browserURL: "https://testnet.arcscan.app"
        }
      },
      {
        network: "arc-mainnet",
        chainId: 1993,
        urls: {
          apiURL: "https://explorer.arc.xyz/api",
          browserURL: "https://explorer.arc.xyz"
        }
      }
    ]
  },
  paths: {
    sources: "./src",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
