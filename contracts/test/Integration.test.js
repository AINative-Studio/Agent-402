/**
 * Integration Tests for Agent-402 Smart Contracts
 * @description End-to-end workflow tests across all contracts
 * Refs #126
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const {
    deployAllContracts,
    usdcAmount,
    FeedbackType
} = require("./helpers");

describe("Contract Integration", function () {
    let agentRegistry, reputationRegistry, agentTreasury;
    let owner, agent1, agent2, agent3, user1, user2;

    beforeEach(async function () {
        const deployment = await deployAllContracts();
        agentRegistry = deployment.agentRegistry;
        reputationRegistry = deployment.reputationRegistry;
        agentTreasury = deployment.agentTreasury;
        owner = deployment.owner;
        agent1 = deployment.agent1;
        agent2 = deployment.agent2;
        agent3 = deployment.agent3;
        user1 = deployment.user1;
        user2 = deployment.user2;
    });

    describe("Full Workflow", function () {
        it("should complete agent registration -> hire -> payment -> feedback cycle", async function () {
            // === Step 1: Register two agents ===
            const analystDID = "did:key:z6MkAnalyst123";
            const transactorDID = "did:key:z6MkTransactor456";

            // Register analyst agent
            const tx1 = await agentRegistry.registerAgent(
                agent1.address,
                analystDID,
                "analyst",
                "0xanalystpubkey"
            );
            const receipt1 = await tx1.wait();
            const agentEvent1 = receipt1.logs.find(
                log => log.fragment && log.fragment.name === "AgentRegistered"
            );
            const analystTokenId = agentEvent1.args[0];

            // Register transaction agent
            const tx2 = await agentRegistry.registerAgent(
                agent2.address,
                transactorDID,
                "transaction",
                "0xtransactorpubkey"
            );
            const receipt2 = await tx2.wait();
            const agentEvent2 = receipt2.logs.find(
                log => log.fragment && log.fragment.name === "AgentRegistered"
            );
            const transactorTokenId = agentEvent2.args[0];

            // Verify registrations
            expect(await agentRegistry.totalAgents()).to.equal(2);
            expect(await agentRegistry.isDIDRegistered(analystDID)).to.be.true;
            expect(await agentRegistry.isDIDRegistered(transactorDID)).to.be.true;

            // === Step 2: Create treasuries for both agents ===
            await agentTreasury.createTreasury(analystTokenId, agent1.address);
            await agentTreasury.createTreasury(transactorTokenId, agent2.address);

            const analystTreasuryId = await agentTreasury.getTreasuryByAgent(analystTokenId);
            const transactorTreasuryId = await agentTreasury.getTreasuryByAgent(transactorTokenId);

            expect(analystTreasuryId).to.be.greaterThan(0);
            expect(transactorTreasuryId).to.be.greaterThan(0);

            // === Step 3: Fund analyst's treasury (simulating client deposit) ===
            const fundAmount = usdcAmount(500); // 500 USDC
            await agentTreasury.fundTreasury(analystTreasuryId, fundAmount);

            expect(await agentTreasury.getTreasuryBalance(analystTreasuryId))
                .to.equal(fundAmount);

            // === Step 4: Process payment (analyst pays transaction agent for service) ===
            const paymentAmount = usdcAmount(50); // 50 USDC for API call
            const x402ReceiptHash = "0x" + "abcd".repeat(16);

            await agentTreasury.connect(agent1).processPayment(
                analystTreasuryId,
                transactorTreasuryId,
                paymentAmount,
                "x402-api-call",
                x402ReceiptHash
            );

            // Verify balances updated
            expect(await agentTreasury.getTreasuryBalance(analystTreasuryId))
                .to.equal(fundAmount - paymentAmount);
            expect(await agentTreasury.getTreasuryBalance(transactorTreasuryId))
                .to.equal(paymentAmount);

            // === Step 5: Submit feedback to ReputationRegistry ===
            // Agent1 (analyst) gives positive feedback to agent2 (transactor)
            await reputationRegistry.connect(agent1).submitFeedback(
                transactorTokenId,
                FeedbackType.POSITIVE,
                9,
                "Excellent transaction execution, fast and reliable",
                x402ReceiptHash
            );

            // Verify reputation updated
            expect(await reputationRegistry.getAgentScore(transactorTokenId)).to.equal(9);
            expect(await reputationRegistry.getAgentFeedbackCount(transactorTokenId)).to.equal(1);

            // === Step 6: Verify all state updates ===
            // Agent metadata still accessible
            const analystMetadata = await agentRegistry.getAgentMetadata(analystTokenId);
            expect(analystMetadata.active).to.be.true;
            expect(analystMetadata.role).to.equal("analyst");

            // Payment recorded
            const payment = await agentTreasury.getPayment(0);
            expect(payment.fromTreasuryId).to.equal(analystTreasuryId);
            expect(payment.toTreasuryId).to.equal(transactorTreasuryId);
            expect(payment.amount).to.equal(paymentAmount);

            // Feedback recorded
            const feedback = await reputationRegistry.getFeedback(0);
            expect(feedback.agentTokenId).to.equal(transactorTokenId);
            expect(feedback.submitter).to.equal(agent1.address);
            expect(feedback.score).to.equal(9);
        });

        it("should handle multi-agent workflow with compliance checks", async function () {
            // Register 3 agents: analyst, compliance, transaction
            const agents = [
                { signer: agent1, did: "did:key:z6MkAnalyst", role: "analyst" },
                { signer: agent2, did: "did:key:z6MkCompliance", role: "compliance" },
                { signer: agent3, did: "did:key:z6MkTransaction", role: "transaction" }
            ];

            const tokenIds = [];
            const treasuryIds = [];

            // Register all agents and create treasuries
            for (const agent of agents) {
                const tx = await agentRegistry.registerAgent(
                    agent.signer.address,
                    agent.did,
                    agent.role,
                    `0x${agent.role}pubkey`
                );
                const receipt = await tx.wait();
                const event = receipt.logs.find(
                    log => log.fragment && log.fragment.name === "AgentRegistered"
                );
                tokenIds.push(event.args[0]);

                await agentTreasury.createTreasury(event.args[0], agent.signer.address);
                const treasuryId = await agentTreasury.getTreasuryByAgent(event.args[0]);
                treasuryIds.push(treasuryId);
            }

            // Fund analyst treasury
            await agentTreasury.fundTreasury(treasuryIds[0], usdcAmount(1000));

            // Analyst pays compliance for review
            await agentTreasury.connect(agent1).processPayment(
                treasuryIds[0],
                treasuryIds[1],
                usdcAmount(25),
                "compliance-review",
                "0xcompliancereceipthash"
            );

            // Analyst pays transaction agent
            await agentTreasury.connect(agent1).processPayment(
                treasuryIds[0],
                treasuryIds[2],
                usdcAmount(75),
                "transaction-execution",
                "0xtransactionreceipthash"
            );

            // Submit feedback for all agents involved
            // User1 reviews analyst
            await reputationRegistry.connect(user1).submitFeedback(
                tokenIds[0], FeedbackType.POSITIVE, 8, "Good analysis", ""
            );

            // Analyst reviews compliance
            await reputationRegistry.connect(agent1).submitFeedback(
                tokenIds[1], FeedbackType.POSITIVE, 9, "Thorough compliance check", ""
            );

            // Analyst reviews transaction agent
            await reputationRegistry.connect(agent1).submitFeedback(
                tokenIds[2], FeedbackType.POSITIVE, 10, "Perfect execution", ""
            );

            // Verify final state
            expect(await agentTreasury.getTreasuryBalance(treasuryIds[0])).to.equal(usdcAmount(900));
            expect(await agentTreasury.getTreasuryBalance(treasuryIds[1])).to.equal(usdcAmount(25));
            expect(await agentTreasury.getTreasuryBalance(treasuryIds[2])).to.equal(usdcAmount(75));

            expect(await reputationRegistry.getAgentScore(tokenIds[0])).to.equal(8);
            expect(await reputationRegistry.getAgentScore(tokenIds[1])).to.equal(9);
            expect(await reputationRegistry.getAgentScore(tokenIds[2])).to.equal(10);
        });
    });

    describe("Cross-Contract Events", function () {
        it("should emit events that frontend can track for agent lifecycle", async function () {
            // Registration event
            await expect(
                agentRegistry.registerAgent(
                    agent1.address,
                    "did:key:z6MkTest123",
                    "analyst",
                    "0xpubkey"
                )
            )
                .to.emit(agentRegistry, "AgentRegistered")
                .withArgs(
                    0n,
                    agent1.address,
                    "did:key:z6MkTest123",
                    "analyst",
                    (timestamp) => timestamp > 0
                );

            // Treasury creation event
            await expect(
                agentTreasury.createTreasury(0, agent1.address)
            )
                .to.emit(agentTreasury, "TreasuryCreated")
                .withArgs(1n, 0n, agent1.address, (timestamp) => timestamp > 0);

            // Funding event
            await expect(
                agentTreasury.fundTreasury(1, usdcAmount(100))
            )
                .to.emit(agentTreasury, "TreasuryFunded")
                .withArgs(1n, usdcAmount(100), usdcAmount(100), (timestamp) => timestamp > 0);
        });

        it("should emit trackable payment and feedback events", async function () {
            // Setup: register two agents with treasuries
            await agentRegistry.registerAgent(agent1.address, "did:key:a1", "analyst", "0xa1");
            await agentRegistry.registerAgent(agent2.address, "did:key:a2", "transaction", "0xa2");
            await agentTreasury.createTreasury(0, agent1.address);
            await agentTreasury.createTreasury(1, agent2.address);
            await agentTreasury.fundTreasury(1, usdcAmount(1000));

            // Payment event
            await expect(
                agentTreasury.connect(agent1).processPayment(
                    1, 2, usdcAmount(50), "api-call", "0xreceipt"
                )
            )
                .to.emit(agentTreasury, "PaymentProcessed")
                .withArgs(0n, 1n, 2n, usdcAmount(50), "api-call", (timestamp) => timestamp > 0);

            // Feedback event
            await expect(
                reputationRegistry.connect(agent1).submitFeedback(
                    1n, FeedbackType.POSITIVE, 8, "Great job!", "0xreceipt"
                )
            )
                .to.emit(reputationRegistry, "FeedbackSubmitted")
                .withArgs(0n, 1n, agent1.address, FeedbackType.POSITIVE, 8, (timestamp) => timestamp > 0);

            // Reputation update event
            await expect(
                reputationRegistry.connect(agent2).submitFeedback(
                    1n, FeedbackType.POSITIVE, 7, "Good!", ""
                )
            )
                .to.emit(reputationRegistry, "ReputationUpdated")
                .withArgs(1n, 15n, 2n, (timestamp) => timestamp > 0);
        });
    });

    describe("Agent Deactivation Impact", function () {
        it("should allow feedback for deactivated agents (historical)", async function () {
            // Register and deactivate agent
            await agentRegistry.registerAgent(
                agent1.address,
                "did:key:z6MkDeactivated",
                "analyst",
                "0xpubkey"
            );
            await agentRegistry.connect(agent1).deactivateAgent(0);

            // Feedback should still be possible (for historical accuracy)
            await expect(
                reputationRegistry.connect(user1).submitFeedback(
                    0n, FeedbackType.NEGATIVE, -5, "Had issues before deactivation", ""
                )
            ).to.not.be.reverted;

            expect(await reputationRegistry.getAgentScore(0)).to.equal(-5);
        });

        it("should track agent activity status correctly", async function () {
            await agentRegistry.registerAgent(
                agent1.address,
                "did:key:z6MkActive",
                "analyst",
                "0xpubkey"
            );

            expect(await agentRegistry.isAgentActive(0)).to.be.true;

            await agentRegistry.connect(agent1).deactivateAgent(0);
            expect(await agentRegistry.isAgentActive(0)).to.be.false;

            await agentRegistry.connect(agent1).reactivateAgent(0);
            expect(await agentRegistry.isAgentActive(0)).to.be.true;
        });
    });

    describe("Trust Tier Progression", function () {
        it("should progress through trust tiers with consistent positive feedback", async function () {
            // Register agent
            await agentRegistry.registerAgent(
                agent1.address,
                "did:key:z6MkProgressive",
                "analyst",
                "0xpubkey"
            );

            // Initial tier: 0
            expect(await reputationRegistry.getAgentTrustTier(0)).to.equal(0);

            // Submit 10 feedbacks with score 9 -> should reach tier 1
            for (let i = 0; i < 10; i++) {
                await reputationRegistry.connect(user1).submitFeedback(
                    0n, FeedbackType.POSITIVE, 9, "", ""
                );
            }
            // With 10 feedbacks and avg 9, tier is 1 (>= 10 && >= 0, but < 25 for tier 2)
            expect(await reputationRegistry.getAgentTrustTier(0)).to.equal(1);

            // Submit 15 more (total 25) -> tier 2 (>= 25 && >= 5)
            for (let i = 0; i < 15; i++) {
                await reputationRegistry.connect(user2).submitFeedback(
                    0n, FeedbackType.POSITIVE, 9, "", ""
                );
            }
            // 25 feedbacks with avg 9 qualifies for tier 2 (>= 25 && avg >= 5)
            // But NOT tier 3 which requires >= 50 feedbacks
            expect(await reputationRegistry.getAgentTrustTier(0)).to.equal(2);
        });
    });

    describe("Token Transfer and Ownership", function () {
        it("should maintain treasury ownership after NFT transfer", async function () {
            // Register agent and create treasury
            await agentRegistry.registerAgent(
                agent1.address,
                "did:key:z6MkTransfer",
                "analyst",
                "0xpubkey"
            );
            await agentTreasury.createTreasury(0, agent1.address);
            await agentTreasury.fundTreasury(1, usdcAmount(100));

            // Transfer NFT to agent2
            await agentRegistry.connect(agent1).transferFrom(
                agent1.address,
                agent2.address,
                0
            );

            // NFT ownership changed
            expect(await agentRegistry.ownerOf(0)).to.equal(agent2.address);

            // Treasury ownership remains with original owner (by design)
            // This is a security feature - treasury ownership is explicit
            const treasury = await agentTreasury.getTreasury(1);
            expect(treasury.owner).to.equal(agent1.address);

            // Original owner can still withdraw
            await expect(
                agentTreasury.connect(agent1).withdrawFromTreasury(
                    1, agent1.address, usdcAmount(50)
                )
            ).to.not.be.reverted;
        });
    });

    describe("Edge Cases", function () {
        it("should handle agent with no treasury gracefully", async function () {
            // Register agent without creating treasury
            await agentRegistry.registerAgent(
                agent1.address,
                "did:key:z6MkNoTreasury",
                "analyst",
                "0xpubkey"
            );

            // Query treasury by agent returns 0 (not found)
            expect(await agentTreasury.getTreasuryByAgent(0)).to.equal(0);

            // Feedback still works
            await reputationRegistry.connect(user1).submitFeedback(
                0n, FeedbackType.POSITIVE, 8, "Works without treasury", ""
            );
            expect(await reputationRegistry.getAgentScore(0)).to.equal(8);
        });

        it("should handle multiple payment cycles correctly", async function () {
            // Setup
            await agentRegistry.registerAgent(agent1.address, "did1", "analyst", "0x1");
            await agentRegistry.registerAgent(agent2.address, "did2", "transaction", "0x2");
            await agentTreasury.createTreasury(0, agent1.address);
            await agentTreasury.createTreasury(1, agent2.address);

            // Multiple fund/pay cycles
            for (let cycle = 0; cycle < 3; cycle++) {
                await agentTreasury.fundTreasury(1, usdcAmount(100));

                await agentTreasury.connect(agent1).processPayment(
                    1, 2, usdcAmount(30), `cycle-${cycle}`, `receipt-${cycle}`
                );
            }

            // Final balances:
            // Treasury 1: 100*3 - 30*3 = 210 USDC
            // Treasury 2: 30*3 = 90 USDC
            expect(await agentTreasury.getTreasuryBalance(1)).to.equal(usdcAmount(210));
            expect(await agentTreasury.getTreasuryBalance(2)).to.equal(usdcAmount(90));

            // 3 payments total
            expect(await agentTreasury.totalPayments()).to.equal(3);
        });

        it("should isolate feedback between different agents", async function () {
            // Register 3 agents
            for (let i = 0; i < 3; i++) {
                await agentRegistry.registerAgent(
                    [agent1, agent2, agent3][i].address,
                    `did:key:agent${i}`,
                    "analyst",
                    `0xpubkey${i}`
                );
            }

            // Submit different feedback to each
            await reputationRegistry.connect(user1).submitFeedback(
                0n, FeedbackType.POSITIVE, 10, "", ""
            );
            await reputationRegistry.connect(user1).submitFeedback(
                1n, FeedbackType.POSITIVE, 5, "", ""
            );
            await reputationRegistry.connect(user1).submitFeedback(
                2n, FeedbackType.NEGATIVE, -3, "", ""
            );

            // Verify isolation
            expect(await reputationRegistry.getAgentScore(0n)).to.equal(10);
            expect(await reputationRegistry.getAgentScore(1n)).to.equal(5);
            expect(await reputationRegistry.getAgentScore(2n)).to.equal(-3);

            expect(await reputationRegistry.getAgentFeedbackCount(0n)).to.equal(1);
            expect(await reputationRegistry.getAgentFeedbackCount(1n)).to.equal(1);
            expect(await reputationRegistry.getAgentFeedbackCount(2n)).to.equal(1);
        });
    });

    describe("Gas Usage Across Workflow", function () {
        it("should complete full workflow within acceptable gas limits", async function () {
            let totalGas = 0n;

            // 1. Register agent
            const tx1 = await agentRegistry.registerAgent(
                agent1.address,
                "did:key:z6MkGasTest",
                "analyst",
                "0xpubkey"
            );
            const receipt1 = await tx1.wait();
            totalGas += receipt1.gasUsed;
            console.log(`        Agent registration: ${receipt1.gasUsed} gas`);

            // 2. Create treasury
            const tx2 = await agentTreasury.createTreasury(0, agent1.address);
            const receipt2 = await tx2.wait();
            totalGas += receipt2.gasUsed;
            console.log(`        Treasury creation: ${receipt2.gasUsed} gas`);

            // 3. Fund treasury
            const tx3 = await agentTreasury.fundTreasury(1, usdcAmount(1000));
            const receipt3 = await tx3.wait();
            totalGas += receipt3.gasUsed;
            console.log(`        Treasury funding: ${receipt3.gasUsed} gas`);

            // 4. Create second agent and treasury for payment
            await agentRegistry.registerAgent(agent2.address, "did2", "transaction", "0x2");
            await agentTreasury.createTreasury(1, agent2.address);

            // 5. Process payment
            const tx4 = await agentTreasury.connect(agent1).processPayment(
                1, 2, usdcAmount(100), "api-call", "0xreceipt"
            );
            const receipt4 = await tx4.wait();
            totalGas += receipt4.gasUsed;
            console.log(`        Payment processing: ${receipt4.gasUsed} gas`);

            // 6. Submit feedback
            const tx5 = await reputationRegistry.connect(agent1).submitFeedback(
                1n, FeedbackType.POSITIVE, 9, "Great service!", "0xreceipt"
            );
            const receipt5 = await tx5.wait();
            totalGas += receipt5.gasUsed;
            console.log(`        Feedback submission: ${receipt5.gasUsed} gas`);

            console.log(`        Total gas for workflow: ${totalGas}`);

            // Total workflow should be under 1M gas
            expect(totalGas).to.be.lessThan(1000000n);
        });
    });
});
