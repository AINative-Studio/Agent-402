/**
 * Test Helpers for Agent-402 Smart Contracts
 * @description Shared utilities for contract testing
 * Refs #126
 */

const { ethers } = require("hardhat");

/**
 * Deploy all contracts and link them together
 * @returns {Promise<Object>} Deployed contract instances
 */
async function deployAllContracts() {
    const [owner, agent1, agent2, agent3, user1, user2] = await ethers.getSigners();

    // Deploy AgentRegistry
    const AgentRegistry = await ethers.getContractFactory("AgentRegistry");
    const agentRegistry = await AgentRegistry.deploy();
    await agentRegistry.waitForDeployment();

    // Deploy ReputationRegistry
    const ReputationRegistry = await ethers.getContractFactory("ReputationRegistry");
    const reputationRegistry = await ReputationRegistry.deploy();
    await reputationRegistry.waitForDeployment();

    // Deploy AgentTreasury
    const AgentTreasury = await ethers.getContractFactory("AgentTreasury");
    const agentTreasury = await AgentTreasury.deploy();
    await agentTreasury.waitForDeployment();

    return {
        agentRegistry,
        reputationRegistry,
        agentTreasury,
        owner,
        agent1,
        agent2,
        agent3,
        user1,
        user2
    };
}

/**
 * Deploy only AgentRegistry
 * @returns {Promise<Object>} Contract instance and signers
 */
async function deployAgentRegistry() {
    const [owner, agent1, agent2, agent3, user1] = await ethers.getSigners();

    const AgentRegistry = await ethers.getContractFactory("AgentRegistry");
    const agentRegistry = await AgentRegistry.deploy();
    await agentRegistry.waitForDeployment();

    return { agentRegistry, owner, agent1, agent2, agent3, user1 };
}

/**
 * Deploy only ReputationRegistry
 * @returns {Promise<Object>} Contract instance and signers
 */
async function deployReputationRegistry() {
    const [owner, submitter1, submitter2, submitter3] = await ethers.getSigners();

    const ReputationRegistry = await ethers.getContractFactory("ReputationRegistry");
    const reputationRegistry = await ReputationRegistry.deploy();
    await reputationRegistry.waitForDeployment();

    return { reputationRegistry, owner, submitter1, submitter2, submitter3 };
}

/**
 * Deploy only AgentTreasury
 * @returns {Promise<Object>} Contract instance and signers
 */
async function deployAgentTreasury() {
    const [owner, treasuryOwner1, treasuryOwner2, user1] = await ethers.getSigners();

    const AgentTreasury = await ethers.getContractFactory("AgentTreasury");
    const agentTreasury = await AgentTreasury.deploy();
    await agentTreasury.waitForDeployment();

    return { agentTreasury, owner, treasuryOwner1, treasuryOwner2, user1 };
}

/**
 * Create a sample agent metadata
 * @param {number} index Agent index for unique values
 * @returns {Object} Agent metadata
 */
function createAgentMetadata(index = 0) {
    return {
        did: `did:key:z6MkTestAgent${index}${Date.now()}`,
        role: ["analyst", "compliance", "transaction"][index % 3],
        publicKey: `0x${Buffer.from(`publicKey${index}`).toString("hex").padEnd(64, "0")}`
    };
}

/**
 * Register an agent with default metadata
 * @param {Object} agentRegistry Contract instance
 * @param {Object} owner Address to own the agent
 * @param {number} index Agent index
 * @returns {Promise<Object>} Transaction receipt and tokenId
 */
async function registerTestAgent(agentRegistry, owner, index = 0) {
    const metadata = createAgentMetadata(index);
    const tx = await agentRegistry.registerAgent(
        owner.address,
        metadata.did,
        metadata.role,
        metadata.publicKey
    );
    const receipt = await tx.wait();

    // Get tokenId from event
    const event = receipt.logs.find(
        log => log.fragment && log.fragment.name === "AgentRegistered"
    );
    const tokenId = event ? event.args[0] : BigInt(index);

    return { tx, receipt, tokenId, metadata };
}

/**
 * Submit multiple feedbacks to build reputation
 * @param {Object} reputationRegistry Contract instance
 * @param {BigInt} agentTokenId Agent token ID
 * @param {Object} submitter Signer for submissions
 * @param {number} count Number of feedbacks to submit
 * @param {number} score Score for each feedback
 * @returns {Promise<Array>} Array of feedback IDs
 */
async function submitMultipleFeedbacks(reputationRegistry, agentTokenId, submitter, count, score) {
    const feedbackIds = [];
    for (let i = 0; i < count; i++) {
        const tx = await reputationRegistry.connect(submitter).submitFeedback(
            agentTokenId,
            0, // POSITIVE
            score,
            `Feedback ${i}`,
            `txhash_${i}`
        );
        const receipt = await tx.wait();
        const event = receipt.logs.find(
            log => log.fragment && log.fragment.name === "FeedbackSubmitted"
        );
        if (event) {
            feedbackIds.push(event.args[0]);
        }
    }
    return feedbackIds;
}

/**
 * USDC amount helper (6 decimals)
 * @param {number} amount Amount in USDC
 * @returns {BigInt} Amount with 6 decimals
 */
function usdcAmount(amount) {
    return BigInt(amount) * BigInt(1e6);
}

/**
 * Get current block timestamp
 * @returns {Promise<number>} Current timestamp
 */
async function getBlockTimestamp() {
    const block = await ethers.provider.getBlock("latest");
    return block.timestamp;
}

/**
 * Mine blocks to advance time
 * @param {number} seconds Seconds to advance
 */
async function advanceTime(seconds) {
    await ethers.provider.send("evm_increaseTime", [seconds]);
    await ethers.provider.send("evm_mine");
}

/**
 * FeedbackType enum values
 */
const FeedbackType = {
    POSITIVE: 0,
    NEGATIVE: 1,
    NEUTRAL: 2,
    REPORT: 3
};

module.exports = {
    deployAllContracts,
    deployAgentRegistry,
    deployReputationRegistry,
    deployAgentTreasury,
    createAgentMetadata,
    registerTestAgent,
    submitMultipleFeedbacks,
    usdcAmount,
    getBlockTimestamp,
    advanceTime,
    FeedbackType
};
