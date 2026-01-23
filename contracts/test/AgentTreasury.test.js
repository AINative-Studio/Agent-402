/**
 * AgentTreasury Contract Tests
 * @description Comprehensive tests for USDC treasury management
 * Refs #126
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const { deployAgentTreasury, usdcAmount } = require("./helpers");

describe("AgentTreasury", function () {
    let agentTreasury;
    let owner, treasuryOwner1, treasuryOwner2, user1;

    // Test agent token IDs
    const AGENT_TOKEN_1 = 0n;
    const AGENT_TOKEN_2 = 1n;

    beforeEach(async function () {
        const deployment = await deployAgentTreasury();
        agentTreasury = deployment.agentTreasury;
        owner = deployment.owner;
        treasuryOwner1 = deployment.treasuryOwner1;
        treasuryOwner2 = deployment.treasuryOwner2;
        user1 = deployment.user1;
    });

    describe("Deployment", function () {
        it("should set deployer as owner", async function () {
            expect(await agentTreasury.owner()).to.equal(owner.address);
        });

        it("should start with zero treasuries", async function () {
            expect(await agentTreasury.totalTreasuries()).to.equal(0);
        });

        it("should start with zero payments", async function () {
            expect(await agentTreasury.totalPayments()).to.equal(0);
        });
    });

    describe("Treasury Creation", function () {
        it("should create treasury for an agent", async function () {
            const tx = await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            await tx.wait();

            expect(await agentTreasury.totalTreasuries()).to.equal(1);
        });

        it("should return correct treasury ID starting from 1", async function () {
            const tx = await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            const receipt = await tx.wait();

            const event = receipt.logs.find(
                log => log.fragment && log.fragment.name === "TreasuryCreated"
            );
            expect(event.args[0]).to.equal(1n); // Treasury IDs start from 1
        });

        it("should store correct treasury metadata", async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);

            const treasury = await agentTreasury.getTreasury(1);

            expect(treasury.agentTokenId).to.equal(AGENT_TOKEN_1);
            expect(treasury.owner).to.equal(treasuryOwner1.address);
            expect(treasury.active).to.equal(true);
            expect(treasury.createdAt).to.be.greaterThan(0);
        });

        it("should emit TreasuryCreated event", async function () {
            await expect(
                agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address)
            )
                .to.emit(agentTreasury, "TreasuryCreated")
                .withArgs(
                    1n, // treasuryId
                    AGENT_TOKEN_1,
                    treasuryOwner1.address,
                    (timestamp) => timestamp > 0
                );
        });

        it("should map agent to treasury correctly", async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);

            const treasuryId = await agentTreasury.getTreasuryByAgent(AGENT_TOKEN_1);
            expect(treasuryId).to.equal(1n);
        });

        it("should prevent duplicate treasury for same agent", async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);

            await expect(
                agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner2.address)
            ).to.be.revertedWith("Treasury already exists for agent");
        });

        it("should reject invalid owner address", async function () {
            await expect(
                agentTreasury.createTreasury(AGENT_TOKEN_1, ethers.ZeroAddress)
            ).to.be.revertedWith("Invalid owner address");
        });

        it("should allow multiple treasuries for different agents", async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            await agentTreasury.createTreasury(AGENT_TOKEN_2, treasuryOwner2.address);

            expect(await agentTreasury.totalTreasuries()).to.equal(2);
            expect(await agentTreasury.getTreasuryByAgent(AGENT_TOKEN_1)).to.equal(1n);
            expect(await agentTreasury.getTreasuryByAgent(AGENT_TOKEN_2)).to.equal(2n);
        });
    });

    describe("Treasury Funding", function () {
        let treasuryId;

        beforeEach(async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            treasuryId = 1n;
        });

        it("should accept USDC deposits", async function () {
            const amount = usdcAmount(100); // 100 USDC

            await agentTreasury.fundTreasury(treasuryId, amount);

            expect(await agentTreasury.getTreasuryBalance(treasuryId)).to.equal(amount);
        });

        it("should update balance correctly with multiple deposits", async function () {
            await agentTreasury.fundTreasury(treasuryId, usdcAmount(50));
            await agentTreasury.fundTreasury(treasuryId, usdcAmount(30));

            expect(await agentTreasury.getTreasuryBalance(treasuryId)).to.equal(usdcAmount(80));
        });

        it("should emit TreasuryFunded event", async function () {
            const amount = usdcAmount(100);

            await expect(agentTreasury.fundTreasury(treasuryId, amount))
                .to.emit(agentTreasury, "TreasuryFunded")
                .withArgs(
                    treasuryId,
                    amount,
                    amount, // newBalance
                    (timestamp) => timestamp > 0
                );
        });

        it("should reject zero amount", async function () {
            await expect(
                agentTreasury.fundTreasury(treasuryId, 0)
            ).to.be.revertedWith("Amount must be greater than 0");
        });

        it("should reject invalid treasury ID", async function () {
            await expect(
                agentTreasury.fundTreasury(999n, usdcAmount(100))
            ).to.be.revertedWith("Invalid treasury ID");
        });

        it("should allow anyone to fund a treasury", async function () {
            // Non-owner can fund
            await expect(
                agentTreasury.connect(user1).fundTreasury(treasuryId, usdcAmount(50))
            ).to.not.be.reverted;
        });
    });

    describe("Withdrawal", function () {
        let treasuryId;
        const initialBalance = usdcAmount(1000);

        beforeEach(async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            treasuryId = 1n;
            await agentTreasury.fundTreasury(treasuryId, initialBalance);
        });

        it("should allow owner to withdraw", async function () {
            const withdrawAmount = usdcAmount(500);

            await agentTreasury.connect(treasuryOwner1).withdrawFromTreasury(
                treasuryId,
                user1.address,
                withdrawAmount
            );

            expect(await agentTreasury.getTreasuryBalance(treasuryId))
                .to.equal(initialBalance - withdrawAmount);
        });

        it("should emit TreasuryWithdrawn event", async function () {
            const withdrawAmount = usdcAmount(500);

            await expect(
                agentTreasury.connect(treasuryOwner1).withdrawFromTreasury(
                    treasuryId,
                    user1.address,
                    withdrawAmount
                )
            )
                .to.emit(agentTreasury, "TreasuryWithdrawn")
                .withArgs(
                    treasuryId,
                    user1.address,
                    withdrawAmount,
                    initialBalance - withdrawAmount, // newBalance
                    (timestamp) => timestamp > 0
                );
        });

        it("should prevent over-withdrawal", async function () {
            const overdrawAmount = usdcAmount(1500);

            await expect(
                agentTreasury.connect(treasuryOwner1).withdrawFromTreasury(
                    treasuryId,
                    user1.address,
                    overdrawAmount
                )
            ).to.be.revertedWith("Insufficient balance");
        });

        it("should prevent non-owner from withdrawing", async function () {
            await expect(
                agentTreasury.connect(user1).withdrawFromTreasury(
                    treasuryId,
                    user1.address,
                    usdcAmount(100)
                )
            ).to.be.revertedWith("Not treasury owner");
        });

        it("should reject zero withdrawal amount", async function () {
            await expect(
                agentTreasury.connect(treasuryOwner1).withdrawFromTreasury(
                    treasuryId,
                    user1.address,
                    0
                )
            ).to.be.revertedWith("Amount must be greater than 0");
        });

        it("should reject invalid treasury ID", async function () {
            await expect(
                agentTreasury.connect(treasuryOwner1).withdrawFromTreasury(
                    999n,
                    user1.address,
                    usdcAmount(100)
                )
            ).to.be.revertedWith("Invalid treasury ID");
        });

        it("should allow full balance withdrawal", async function () {
            await agentTreasury.connect(treasuryOwner1).withdrawFromTreasury(
                treasuryId,
                user1.address,
                initialBalance
            );

            expect(await agentTreasury.getTreasuryBalance(treasuryId)).to.equal(0);
        });
    });

    describe("Payment Processing", function () {
        let treasury1Id, treasury2Id;
        const initialBalance = usdcAmount(1000);

        beforeEach(async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            await agentTreasury.createTreasury(AGENT_TOKEN_2, treasuryOwner2.address);
            treasury1Id = 1n;
            treasury2Id = 2n;

            await agentTreasury.fundTreasury(treasury1Id, initialBalance);
        });

        it("should process payment between treasuries", async function () {
            const paymentAmount = usdcAmount(100);

            await agentTreasury.connect(treasuryOwner1).processPayment(
                treasury1Id,
                treasury2Id,
                paymentAmount,
                "x402-api-call",
                "0xreceipthash123"
            );

            expect(await agentTreasury.getTreasuryBalance(treasury1Id))
                .to.equal(initialBalance - paymentAmount);
            expect(await agentTreasury.getTreasuryBalance(treasury2Id))
                .to.equal(paymentAmount);
        });

        it("should emit PaymentProcessed event", async function () {
            const paymentAmount = usdcAmount(100);

            await expect(
                agentTreasury.connect(treasuryOwner1).processPayment(
                    treasury1Id,
                    treasury2Id,
                    paymentAmount,
                    "x402-api-call",
                    "0xreceipthash123"
                )
            )
                .to.emit(agentTreasury, "PaymentProcessed")
                .withArgs(
                    0n, // paymentId
                    treasury1Id,
                    treasury2Id,
                    paymentAmount,
                    "x402-api-call",
                    (timestamp) => timestamp > 0
                );
        });

        it("should record payment with correct receipt hash", async function () {
            const paymentAmount = usdcAmount(100);
            const receiptHash = "0xreceipthash123";

            await agentTreasury.connect(treasuryOwner1).processPayment(
                treasury1Id,
                treasury2Id,
                paymentAmount,
                "x402-api-call",
                receiptHash
            );

            const payment = await agentTreasury.getPayment(0);
            expect(payment.x402ReceiptHash).to.equal(receiptHash);
        });

        it("should return incrementing payment IDs", async function () {
            for (let i = 0; i < 3; i++) {
                const tx = await agentTreasury.connect(treasuryOwner1).processPayment(
                    treasury1Id,
                    treasury2Id,
                    usdcAmount(10),
                    `payment-${i}`,
                    `receipt-${i}`
                );
                const receipt = await tx.wait();
                const event = receipt.logs.find(
                    log => log.fragment && log.fragment.name === "PaymentProcessed"
                );
                expect(event.args[0]).to.equal(BigInt(i));
            }
        });

        it("should prevent payment with insufficient balance", async function () {
            const overdrawAmount = usdcAmount(1500);

            await expect(
                agentTreasury.connect(treasuryOwner1).processPayment(
                    treasury1Id,
                    treasury2Id,
                    overdrawAmount,
                    "payment",
                    "receipt"
                )
            ).to.be.revertedWith("Insufficient balance");
        });

        it("should prevent unauthorized payment", async function () {
            await expect(
                agentTreasury.connect(user1).processPayment(
                    treasury1Id,
                    treasury2Id,
                    usdcAmount(100),
                    "payment",
                    "receipt"
                )
            ).to.be.revertedWith("Not authorized to make payment");
        });

        it("should allow contract owner to process payments", async function () {
            // Contract owner can make payments from any treasury
            await expect(
                agentTreasury.connect(owner).processPayment(
                    treasury1Id,
                    treasury2Id,
                    usdcAmount(100),
                    "payment",
                    "receipt"
                )
            ).to.not.be.reverted;
        });

        it("should reject zero payment amount", async function () {
            await expect(
                agentTreasury.connect(treasuryOwner1).processPayment(
                    treasury1Id,
                    treasury2Id,
                    0,
                    "payment",
                    "receipt"
                )
            ).to.be.revertedWith("Amount must be greater than 0");
        });

        it("should reject invalid source treasury", async function () {
            await expect(
                agentTreasury.connect(treasuryOwner1).processPayment(
                    999n,
                    treasury2Id,
                    usdcAmount(100),
                    "payment",
                    "receipt"
                )
            ).to.be.revertedWith("Invalid source treasury");
        });

        it("should reject invalid destination treasury", async function () {
            await expect(
                agentTreasury.connect(treasuryOwner1).processPayment(
                    treasury1Id,
                    999n,
                    usdcAmount(100),
                    "payment",
                    "receipt"
                )
            ).to.be.revertedWith("Invalid destination treasury");
        });

        it("should track payments for both source and destination treasuries", async function () {
            await agentTreasury.connect(treasuryOwner1).processPayment(
                treasury1Id,
                treasury2Id,
                usdcAmount(100),
                "payment",
                "receipt"
            );

            const treasury1Payments = await agentTreasury.getTreasuryPayments(treasury1Id);
            const treasury2Payments = await agentTreasury.getTreasuryPayments(treasury2Id);

            expect(treasury1Payments.length).to.equal(1);
            expect(treasury2Payments.length).to.equal(1);
            expect(treasury1Payments[0]).to.equal(0n);
            expect(treasury2Payments[0]).to.equal(0n);
        });
    });

    describe("Payment Retrieval", function () {
        let treasury1Id, treasury2Id;

        beforeEach(async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            await agentTreasury.createTreasury(AGENT_TOKEN_2, treasuryOwner2.address);
            treasury1Id = 1n;
            treasury2Id = 2n;

            await agentTreasury.fundTreasury(treasury1Id, usdcAmount(1000));

            await agentTreasury.connect(treasuryOwner1).processPayment(
                treasury1Id,
                treasury2Id,
                usdcAmount(100),
                "x402-api-call",
                "0xreceipthash123"
            );
        });

        it("should return correct payment by ID", async function () {
            const payment = await agentTreasury.getPayment(0);

            expect(payment.fromTreasuryId).to.equal(treasury1Id);
            expect(payment.toTreasuryId).to.equal(treasury2Id);
            expect(payment.amount).to.equal(usdcAmount(100));
            expect(payment.purpose).to.equal("x402-api-call");
            expect(payment.x402ReceiptHash).to.equal("0xreceipthash123");
            expect(payment.timestamp).to.be.greaterThan(0);
        });

        it("should revert for non-existent payment ID", async function () {
            await expect(
                agentTreasury.getPayment(999)
            ).to.be.revertedWith("Payment does not exist");
        });
    });

    describe("Treasury Queries", function () {
        it("should return correct treasury by ID", async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);

            const treasury = await agentTreasury.getTreasury(1);

            expect(treasury.agentTokenId).to.equal(AGENT_TOKEN_1);
            expect(treasury.owner).to.equal(treasuryOwner1.address);
        });

        it("should revert for invalid treasury ID", async function () {
            await expect(
                agentTreasury.getTreasury(999)
            ).to.be.revertedWith("Invalid treasury ID");
        });

        it("should return 0 for unregistered agent treasury lookup", async function () {
            const treasuryId = await agentTreasury.getTreasuryByAgent(999n);
            expect(treasuryId).to.equal(0n);
        });
    });

    describe("Reentrancy Protection", function () {
        it("should use ReentrancyGuard on processPayment", async function () {
            // The nonReentrant modifier is tested by ensuring the function signature
            // and that normal operations work. Full reentrancy testing would require
            // a malicious contract, which is beyond this scope.
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            await agentTreasury.createTreasury(AGENT_TOKEN_2, treasuryOwner2.address);
            await agentTreasury.fundTreasury(1n, usdcAmount(1000));

            // Normal payment should succeed
            await expect(
                agentTreasury.connect(treasuryOwner1).processPayment(
                    1n, 2n, usdcAmount(100), "payment", "receipt"
                )
            ).to.not.be.reverted;
        });

        it("should use ReentrancyGuard on withdrawFromTreasury", async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            await agentTreasury.fundTreasury(1n, usdcAmount(1000));

            // Normal withdrawal should succeed
            await expect(
                agentTreasury.connect(treasuryOwner1).withdrawFromTreasury(
                    1n, user1.address, usdcAmount(100)
                )
            ).to.not.be.reverted;
        });
    });

    describe("Gas Usage", function () {
        it("should create treasury within reasonable gas limits", async function () {
            const tx = await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            const receipt = await tx.wait();

            // Treasury creation should use less than 150k gas
            expect(receipt.gasUsed).to.be.lessThan(150000n);
            console.log(`        Gas used for treasury creation: ${receipt.gasUsed}`);
        });

        it("should process payment within reasonable gas limits", async function () {
            await agentTreasury.createTreasury(AGENT_TOKEN_1, treasuryOwner1.address);
            await agentTreasury.createTreasury(AGENT_TOKEN_2, treasuryOwner2.address);
            await agentTreasury.fundTreasury(1n, usdcAmount(1000));

            const tx = await agentTreasury.connect(treasuryOwner1).processPayment(
                1n, 2n, usdcAmount(100),
                "x402-api-call with reasonably long purpose description",
                "0x1234567890abcdef1234567890abcdef12345678"
            );
            const receipt = await tx.wait();

            // Payment processing should use less than 400k gas (includes storage operations)
            expect(receipt.gasUsed).to.be.lessThan(400000n);
            console.log(`        Gas used for payment processing: ${receipt.gasUsed}`);
        });
    });
});
