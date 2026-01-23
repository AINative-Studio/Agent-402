/**
 * ReputationRegistry Contract Tests
 * @description Comprehensive tests for event-based reputation system
 * Refs #126
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const {
    deployReputationRegistry,
    submitMultipleFeedbacks,
    FeedbackType
} = require("./helpers");

describe("ReputationRegistry", function () {
    let reputationRegistry;
    let owner, submitter1, submitter2, submitter3;

    // Test agent token ID (simulated from AgentRegistry)
    const AGENT_TOKEN_ID = 0n;

    beforeEach(async function () {
        const deployment = await deployReputationRegistry();
        reputationRegistry = deployment.reputationRegistry;
        owner = deployment.owner;
        submitter1 = deployment.submitter1;
        submitter2 = deployment.submitter2;
        submitter3 = deployment.submitter3;
    });

    describe("Deployment", function () {
        it("should start with zero feedbacks", async function () {
            expect(await reputationRegistry.totalFeedbacks()).to.equal(0);
        });

        it("should return zero score for new agents", async function () {
            expect(await reputationRegistry.getAgentScore(AGENT_TOKEN_ID)).to.equal(0);
        });

        it("should return zero feedback count for new agents", async function () {
            expect(await reputationRegistry.getAgentFeedbackCount(AGENT_TOKEN_ID)).to.equal(0);
        });
    });

    describe("Feedback Submission", function () {
        it("should accept positive feedback and update score", async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID,
                FeedbackType.POSITIVE,
                8,
                "Great service!",
                "0xtxhash123"
            );

            expect(await reputationRegistry.getAgentScore(AGENT_TOKEN_ID)).to.equal(8);
            expect(await reputationRegistry.getAgentFeedbackCount(AGENT_TOKEN_ID)).to.equal(1);
        });

        it("should accept negative feedback and update score", async function () {
            // First add positive to have balance
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID,
                FeedbackType.POSITIVE,
                5,
                "Good",
                "0xtxhash1"
            );

            await reputationRegistry.connect(submitter2).submitFeedback(
                AGENT_TOKEN_ID,
                FeedbackType.NEGATIVE,
                -5,
                "Poor service",
                "0xtxhash2"
            );

            expect(await reputationRegistry.getAgentScore(AGENT_TOKEN_ID)).to.equal(0);
            expect(await reputationRegistry.getAgentFeedbackCount(AGENT_TOKEN_ID)).to.equal(2);
        });

        it("should accept neutral feedback", async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID,
                FeedbackType.NEUTRAL,
                0,
                "Informational note",
                "0xtxhash123"
            );

            expect(await reputationRegistry.getAgentScore(AGENT_TOKEN_ID)).to.equal(0);
            expect(await reputationRegistry.getAgentFeedbackCount(AGENT_TOKEN_ID)).to.equal(1);
        });

        it("should accept report feedback type", async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID,
                FeedbackType.REPORT,
                -10,
                "Security concern reported",
                "0xtxhash123"
            );

            expect(await reputationRegistry.getAgentScore(AGENT_TOKEN_ID)).to.equal(-10);
        });

        it("should emit FeedbackSubmitted event with correct parameters", async function () {
            await expect(
                reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID,
                    FeedbackType.POSITIVE,
                    8,
                    "Great work!",
                    "0xtxhash123"
                )
            )
                .to.emit(reputationRegistry, "FeedbackSubmitted")
                .withArgs(
                    0n, // feedbackId
                    AGENT_TOKEN_ID,
                    submitter1.address,
                    FeedbackType.POSITIVE,
                    8,
                    (timestamp) => timestamp > 0
                );
        });

        it("should emit ReputationUpdated event", async function () {
            await expect(
                reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID,
                    FeedbackType.POSITIVE,
                    8,
                    "Great work!",
                    "0xtxhash123"
                )
            )
                .to.emit(reputationRegistry, "ReputationUpdated")
                .withArgs(
                    AGENT_TOKEN_ID,
                    8n, // newScore
                    1n, // feedbackCount
                    (timestamp) => timestamp > 0
                );
        });

        it("should return incrementing feedback IDs", async function () {
            for (let i = 0; i < 3; i++) {
                const tx = await reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID,
                    FeedbackType.POSITIVE,
                    5,
                    `Feedback ${i}`,
                    `0xtxhash${i}`
                );
                const receipt = await tx.wait();
                const event = receipt.logs.find(
                    log => log.fragment && log.fragment.name === "FeedbackSubmitted"
                );
                expect(event.args[0]).to.equal(BigInt(i));
            }
        });
    });

    describe("Score Validation", function () {
        it("should reject score above 10", async function () {
            await expect(
                reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID,
                    FeedbackType.POSITIVE,
                    11,
                    "Too high",
                    "0xtxhash"
                )
            ).to.be.revertedWith("Score must be between -10 and +10");
        });

        it("should reject score below -10", async function () {
            await expect(
                reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID,
                    FeedbackType.NEGATIVE,
                    -11,
                    "Too low",
                    "0xtxhash"
                )
            ).to.be.revertedWith("Score must be between -10 and +10");
        });

        it("should accept maximum score of 10", async function () {
            await expect(
                reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID,
                    FeedbackType.POSITIVE,
                    10,
                    "Perfect!",
                    "0xtxhash"
                )
            ).to.not.be.reverted;
        });

        it("should accept minimum score of -10", async function () {
            await expect(
                reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID,
                    FeedbackType.NEGATIVE,
                    -10,
                    "Terrible!",
                    "0xtxhash"
                )
            ).to.not.be.reverted;
        });

        it("should accept zero score", async function () {
            await expect(
                reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID,
                    FeedbackType.NEUTRAL,
                    0,
                    "Neutral",
                    "0xtxhash"
                )
            ).to.not.be.reverted;
        });
    });

    describe("Feedback Retrieval", function () {
        beforeEach(async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID,
                FeedbackType.POSITIVE,
                8,
                "Great service!",
                "0xtxhash123"
            );
        });

        it("should return correct feedback by ID", async function () {
            const feedback = await reputationRegistry.getFeedback(0);

            expect(feedback.agentTokenId).to.equal(AGENT_TOKEN_ID);
            expect(feedback.submitter).to.equal(submitter1.address);
            expect(feedback.feedbackType).to.equal(FeedbackType.POSITIVE);
            expect(feedback.score).to.equal(8);
            expect(feedback.comment).to.equal("Great service!");
            expect(feedback.transactionHash).to.equal("0xtxhash123");
            expect(feedback.timestamp).to.be.greaterThan(0);
        });

        it("should revert for non-existent feedback ID", async function () {
            await expect(
                reputationRegistry.getFeedback(999)
            ).to.be.revertedWith("Feedback does not exist");
        });

        it("should return correct feedback IDs for agent", async function () {
            // Add more feedbacks
            await reputationRegistry.connect(submitter2).submitFeedback(
                AGENT_TOKEN_ID,
                FeedbackType.POSITIVE,
                7,
                "Good",
                "0xtxhash456"
            );

            const feedbackIds = await reputationRegistry.getAgentFeedbackIds(AGENT_TOKEN_ID);

            expect(feedbackIds.length).to.equal(2);
            expect(feedbackIds[0]).to.equal(0n);
            expect(feedbackIds[1]).to.equal(1n);
        });
    });

    describe("Score Calculation", function () {
        it("should calculate correct total score from multiple feedbacks", async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID, FeedbackType.POSITIVE, 8, "", ""
            );
            await reputationRegistry.connect(submitter2).submitFeedback(
                AGENT_TOKEN_ID, FeedbackType.POSITIVE, 6, "", ""
            );
            await reputationRegistry.connect(submitter3).submitFeedback(
                AGENT_TOKEN_ID, FeedbackType.NEGATIVE, -2, "", ""
            );

            expect(await reputationRegistry.getAgentScore(AGENT_TOKEN_ID)).to.equal(12);
        });

        it("should calculate correct average score", async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID, FeedbackType.POSITIVE, 10, "", ""
            );
            await reputationRegistry.connect(submitter2).submitFeedback(
                AGENT_TOKEN_ID, FeedbackType.POSITIVE, 8, "", ""
            );
            await reputationRegistry.connect(submitter3).submitFeedback(
                AGENT_TOKEN_ID, FeedbackType.POSITIVE, 6, "", ""
            );

            // Average: (10 + 8 + 6) / 3 = 8
            expect(await reputationRegistry.getAgentAverageScore(AGENT_TOKEN_ID)).to.equal(8);
        });

        it("should return zero average for agents with no feedback", async function () {
            expect(await reputationRegistry.getAgentAverageScore(AGENT_TOKEN_ID)).to.equal(0);
        });

        it("should handle negative total scores", async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID, FeedbackType.NEGATIVE, -5, "", ""
            );
            await reputationRegistry.connect(submitter2).submitFeedback(
                AGENT_TOKEN_ID, FeedbackType.NEGATIVE, -8, "", ""
            );

            expect(await reputationRegistry.getAgentScore(AGENT_TOKEN_ID)).to.equal(-13);
        });
    });

    describe("Trust Tiers", function () {
        it("should return tier 0 for new agents", async function () {
            expect(await reputationRegistry.getAgentTrustTier(AGENT_TOKEN_ID)).to.equal(0);
        });

        it("should return tier 0 for agents with less than 10 feedbacks", async function () {
            await submitMultipleFeedbacks(reputationRegistry, AGENT_TOKEN_ID, submitter1, 9, 10);

            expect(await reputationRegistry.getAgentTrustTier(AGENT_TOKEN_ID)).to.equal(0);
        });

        it("should return tier 0 for agents with negative average", async function () {
            // Submit 15 feedbacks but with negative average
            for (let i = 0; i < 15; i++) {
                await reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID, FeedbackType.NEGATIVE, -2, "", ""
                );
            }

            expect(await reputationRegistry.getAgentTrustTier(AGENT_TOKEN_ID)).to.equal(0);
        });

        it("should return tier 1 for agents with >= 10 feedbacks and avg >= 0", async function () {
            // 10 feedbacks with average score of 3
            for (let i = 0; i < 10; i++) {
                await reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID, FeedbackType.POSITIVE, 3, "", ""
                );
            }

            expect(await reputationRegistry.getAgentTrustTier(AGENT_TOKEN_ID)).to.equal(1);
        });

        it("should return tier 2 for agents with >= 25 feedbacks and avg >= 5", async function () {
            // 25 feedbacks with average score of 6
            for (let i = 0; i < 25; i++) {
                await reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID, FeedbackType.POSITIVE, 6, "", ""
                );
            }

            expect(await reputationRegistry.getAgentTrustTier(AGENT_TOKEN_ID)).to.equal(2);
        });

        it("should return tier 3 for agents with >= 50 feedbacks and avg >= 7", async function () {
            // 50 feedbacks with average score of 8
            for (let i = 0; i < 50; i++) {
                await reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID, FeedbackType.POSITIVE, 8, "", ""
                );
            }

            expect(await reputationRegistry.getAgentTrustTier(AGENT_TOKEN_ID)).to.equal(3);
        });

        it("should return tier 4 for agents with >= 100 feedbacks and avg >= 9", async function () {
            // 100 feedbacks with average score of 10
            for (let i = 0; i < 100; i++) {
                await reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID, FeedbackType.POSITIVE, 10, "", ""
                );
            }

            expect(await reputationRegistry.getAgentTrustTier(AGENT_TOKEN_ID)).to.equal(4);
        });

        it("should upgrade tier after threshold reached", async function () {
            // Start at tier 0
            expect(await reputationRegistry.getAgentTrustTier(AGENT_TOKEN_ID)).to.equal(0);

            // Add 10 feedbacks with score 3 -> tier 1 (>= 10 feedbacks, avg >= 0 but < 5)
            for (let i = 0; i < 10; i++) {
                await reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID, FeedbackType.POSITIVE, 3, "", ""
                );
            }
            // With 10 feedbacks and avg 3, tier is 1 (>= 10 && avg >= 0)
            expect(await reputationRegistry.getAgentTrustTier(AGENT_TOKEN_ID)).to.equal(1);
        });
    });

    describe("Reputation Summary", function () {
        beforeEach(async function () {
            // Submit 25 feedbacks with varying scores
            for (let i = 0; i < 25; i++) {
                await reputationRegistry.connect(submitter1).submitFeedback(
                    AGENT_TOKEN_ID,
                    FeedbackType.POSITIVE,
                    i < 20 ? 8 : 6, // 20 with 8, 5 with 6
                    "",
                    ""
                );
            }
        });

        it("should return complete reputation summary", async function () {
            const summary = await reputationRegistry.getAgentReputationSummary(AGENT_TOKEN_ID);

            // Total: 20*8 + 5*6 = 160 + 30 = 190
            expect(summary.totalScore).to.equal(190);
            expect(summary.feedbackCount).to.equal(25);
            // Average: 190 / 25 = 7.6, integer division = 7
            expect(summary.averageScore).to.equal(7);
            // Tier: 25 feedbacks, avg 7 -> tier 2 (>= 25 && avg >= 5, but < 50 for tier 3)
            expect(summary.trustTier).to.equal(2);
        });
    });

    describe("Multiple Agents", function () {
        const AGENT_1 = 0n;
        const AGENT_2 = 1n;
        const AGENT_3 = 2n;

        it("should track feedback separately for different agents", async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_1, FeedbackType.POSITIVE, 10, "", ""
            );
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_2, FeedbackType.POSITIVE, 5, "", ""
            );
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_3, FeedbackType.NEGATIVE, -3, "", ""
            );

            expect(await reputationRegistry.getAgentScore(AGENT_1)).to.equal(10);
            expect(await reputationRegistry.getAgentScore(AGENT_2)).to.equal(5);
            expect(await reputationRegistry.getAgentScore(AGENT_3)).to.equal(-3);
        });

        it("should track feedback counts separately", async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_1, FeedbackType.POSITIVE, 5, "", ""
            );
            await reputationRegistry.connect(submitter2).submitFeedback(
                AGENT_1, FeedbackType.POSITIVE, 5, "", ""
            );
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_2, FeedbackType.POSITIVE, 5, "", ""
            );

            expect(await reputationRegistry.getAgentFeedbackCount(AGENT_1)).to.equal(2);
            expect(await reputationRegistry.getAgentFeedbackCount(AGENT_2)).to.equal(1);
        });
    });

    describe("Gas Usage", function () {
        it("should submit feedback within reasonable gas limits", async function () {
            const tx = await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID,
                FeedbackType.POSITIVE,
                8,
                "Great service! This is a reasonably long comment for testing.",
                "0x1234567890abcdef1234567890abcdef12345678"
            );
            const receipt = await tx.wait();

            // Feedback submission should use less than 300k gas (includes storage for comments)
            expect(receipt.gasUsed).to.be.lessThan(300000n);
            console.log(`        Gas used for feedback submission: ${receipt.gasUsed}`);
        });

        it("should retrieve feedback efficiently", async function () {
            await reputationRegistry.connect(submitter1).submitFeedback(
                AGENT_TOKEN_ID, FeedbackType.POSITIVE, 8, "Test", "0xtxhash"
            );

            // View functions don't consume gas in transactions, but we can measure call
            const feedback = await reputationRegistry.getFeedback(0);
            expect(feedback.score).to.equal(8);
        });
    });
});
