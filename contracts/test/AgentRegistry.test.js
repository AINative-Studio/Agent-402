/**
 * AgentRegistry Contract Tests
 * @description Comprehensive tests for ERC-721 agent identity registry
 * Refs #126
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const {
    deployAgentRegistry,
    createAgentMetadata,
    registerTestAgent
} = require("./helpers");

describe("AgentRegistry", function () {
    let agentRegistry;
    let owner, agent1, agent2, agent3, user1;

    beforeEach(async function () {
        const deployment = await deployAgentRegistry();
        agentRegistry = deployment.agentRegistry;
        owner = deployment.owner;
        agent1 = deployment.agent1;
        agent2 = deployment.agent2;
        agent3 = deployment.agent3;
        user1 = deployment.user1;
    });

    describe("Deployment", function () {
        it("should deploy with correct name and symbol", async function () {
            expect(await agentRegistry.name()).to.equal("TrustlessAgent");
            expect(await agentRegistry.symbol()).to.equal("AGENT");
        });

        it("should set deployer as owner", async function () {
            expect(await agentRegistry.owner()).to.equal(owner.address);
        });

        it("should start with zero agents", async function () {
            expect(await agentRegistry.totalAgents()).to.equal(0);
        });
    });

    describe("Agent Registration", function () {
        it("should register a new agent and mint NFT", async function () {
            const metadata = createAgentMetadata(0);

            const tx = await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );
            await tx.wait();

            // Check NFT ownership
            expect(await agentRegistry.ownerOf(0)).to.equal(agent1.address);
            expect(await agentRegistry.balanceOf(agent1.address)).to.equal(1);

            // Check total agents
            expect(await agentRegistry.totalAgents()).to.equal(1);
        });

        it("should store correct agent metadata", async function () {
            const metadata = createAgentMetadata(0);

            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );

            const storedMetadata = await agentRegistry.getAgentMetadata(0);

            expect(storedMetadata.did).to.equal(metadata.did);
            expect(storedMetadata.role).to.equal(metadata.role);
            expect(storedMetadata.publicKey).to.equal(metadata.publicKey);
            expect(storedMetadata.active).to.equal(true);
            expect(storedMetadata.registeredAt).to.be.greaterThan(0);
        });

        it("should return correct token ID", async function () {
            const metadata = createAgentMetadata(0);

            const tx = await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );
            const receipt = await tx.wait();

            // Get returned token ID from transaction
            const event = receipt.logs.find(
                log => log.fragment && log.fragment.name === "AgentRegistered"
            );
            expect(event.args[0]).to.equal(0n);
        });

        it("should increment token IDs sequentially", async function () {
            for (let i = 0; i < 3; i++) {
                const metadata = createAgentMetadata(i);
                await agentRegistry.registerAgent(
                    [agent1, agent2, agent3][i].address,
                    metadata.did,
                    metadata.role,
                    metadata.publicKey
                );
            }

            expect(await agentRegistry.totalAgents()).to.equal(3);
            expect(await agentRegistry.ownerOf(0)).to.equal(agent1.address);
            expect(await agentRegistry.ownerOf(1)).to.equal(agent2.address);
            expect(await agentRegistry.ownerOf(2)).to.equal(agent3.address);
        });

        it("should allow any address to register agents", async function () {
            const metadata = createAgentMetadata(0);

            // Non-owner can register
            await expect(
                agentRegistry.connect(user1).registerAgent(
                    agent1.address,
                    metadata.did,
                    metadata.role,
                    metadata.publicKey
                )
            ).to.not.be.reverted;
        });

        it("should emit AgentRegistered event with correct parameters", async function () {
            const metadata = createAgentMetadata(0);

            await expect(
                agentRegistry.registerAgent(
                    agent1.address,
                    metadata.did,
                    metadata.role,
                    metadata.publicKey
                )
            )
                .to.emit(agentRegistry, "AgentRegistered")
                .withArgs(
                    0n,
                    agent1.address,
                    metadata.did,
                    metadata.role,
                    (timestamp) => timestamp > 0
                );
        });
    });

    describe("Registration Validation", function () {
        it("should prevent duplicate DID registration", async function () {
            const metadata = createAgentMetadata(0);

            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );

            await expect(
                agentRegistry.registerAgent(
                    agent2.address,
                    metadata.did, // Same DID
                    "compliance",
                    metadata.publicKey
                )
            ).to.be.revertedWith("DID already registered");
        });

        it("should reject empty DID", async function () {
            await expect(
                agentRegistry.registerAgent(
                    agent1.address,
                    "", // Empty DID
                    "analyst",
                    "0x1234"
                )
            ).to.be.revertedWith("DID cannot be empty");
        });

        it("should reject empty role", async function () {
            await expect(
                agentRegistry.registerAgent(
                    agent1.address,
                    "did:key:z6Mk123",
                    "", // Empty role
                    "0x1234"
                )
            ).to.be.revertedWith("Role cannot be empty");
        });

        it("should reject empty public key", async function () {
            await expect(
                agentRegistry.registerAgent(
                    agent1.address,
                    "did:key:z6Mk123",
                    "analyst",
                    "" // Empty public key
                )
            ).to.be.revertedWith("Public key cannot be empty");
        });
    });

    describe("DID Lookup", function () {
        it("should return correct token ID by DID", async function () {
            const metadata = createAgentMetadata(0);

            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );

            const tokenId = await agentRegistry.getTokenIdByDID(metadata.did);
            expect(tokenId).to.equal(0n);
        });

        it("should correctly report DID registration status", async function () {
            const metadata = createAgentMetadata(0);

            expect(await agentRegistry.isDIDRegistered(metadata.did)).to.equal(false);

            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );

            expect(await agentRegistry.isDIDRegistered(metadata.did)).to.equal(true);
        });

        it("should revert when looking up unregistered DID", async function () {
            await expect(
                agentRegistry.getTokenIdByDID("did:key:nonexistent")
            ).to.be.revertedWith("DID not registered");
        });
    });

    describe("Agent Metadata", function () {
        beforeEach(async function () {
            const metadata = createAgentMetadata(0);
            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );
        });

        it("should return complete metadata structure", async function () {
            const metadata = await agentRegistry.getAgentMetadata(0);

            expect(metadata.did).to.be.a("string");
            expect(metadata.role).to.be.a("string");
            expect(metadata.publicKey).to.be.a("string");
            expect(typeof metadata.registeredAt).to.equal("bigint");
            expect(typeof metadata.active).to.equal("boolean");
        });

        it("should revert for non-existent token ID", async function () {
            await expect(
                agentRegistry.getAgentMetadata(999)
            ).to.be.revertedWith("Agent does not exist");
        });
    });

    describe("Agent Deactivation", function () {
        beforeEach(async function () {
            const metadata = createAgentMetadata(0);
            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );
        });

        it("should allow owner to deactivate agent", async function () {
            expect(await agentRegistry.isAgentActive(0)).to.equal(true);

            await agentRegistry.connect(agent1).deactivateAgent(0);

            expect(await agentRegistry.isAgentActive(0)).to.equal(false);
        });

        it("should emit AgentDeactivated event", async function () {
            const metadata = await agentRegistry.getAgentMetadata(0);

            await expect(agentRegistry.connect(agent1).deactivateAgent(0))
                .to.emit(agentRegistry, "AgentDeactivated")
                .withArgs(0n, metadata.did, (timestamp) => timestamp > 0);
        });

        it("should prevent non-owner from deactivating", async function () {
            await expect(
                agentRegistry.connect(agent2).deactivateAgent(0)
            ).to.be.revertedWith("Not agent owner");
        });

        it("should prevent double deactivation", async function () {
            await agentRegistry.connect(agent1).deactivateAgent(0);

            await expect(
                agentRegistry.connect(agent1).deactivateAgent(0)
            ).to.be.revertedWith("Agent already inactive");
        });
    });

    describe("Agent Reactivation", function () {
        beforeEach(async function () {
            const metadata = createAgentMetadata(0);
            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );
            await agentRegistry.connect(agent1).deactivateAgent(0);
        });

        it("should allow owner to reactivate agent", async function () {
            expect(await agentRegistry.isAgentActive(0)).to.equal(false);

            await agentRegistry.connect(agent1).reactivateAgent(0);

            expect(await agentRegistry.isAgentActive(0)).to.equal(true);
        });

        it("should emit AgentReactivated event", async function () {
            const metadata = await agentRegistry.getAgentMetadata(0);

            await expect(agentRegistry.connect(agent1).reactivateAgent(0))
                .to.emit(agentRegistry, "AgentReactivated")
                .withArgs(0n, metadata.did, (timestamp) => timestamp > 0);
        });

        it("should prevent non-owner from reactivating", async function () {
            await expect(
                agentRegistry.connect(agent2).reactivateAgent(0)
            ).to.be.revertedWith("Not agent owner");
        });

        it("should prevent reactivating already active agent", async function () {
            await agentRegistry.connect(agent1).reactivateAgent(0);

            await expect(
                agentRegistry.connect(agent1).reactivateAgent(0)
            ).to.be.revertedWith("Agent already active");
        });
    });

    describe("Active Status Check", function () {
        it("should return true for active agents", async function () {
            const metadata = createAgentMetadata(0);
            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );

            expect(await agentRegistry.isAgentActive(0)).to.equal(true);
        });

        it("should return false for inactive agents", async function () {
            const metadata = createAgentMetadata(0);
            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );
            await agentRegistry.connect(agent1).deactivateAgent(0);

            expect(await agentRegistry.isAgentActive(0)).to.equal(false);
        });

        it("should revert for non-existent token ID", async function () {
            await expect(
                agentRegistry.isAgentActive(999)
            ).to.be.revertedWith("Agent does not exist");
        });
    });

    describe("Token URI", function () {
        it("should return data URI for valid token", async function () {
            const metadata = createAgentMetadata(0);
            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );

            const uri = await agentRegistry.tokenURI(0);
            expect(uri).to.include("data:application/json;base64,");
        });

        it("should revert for non-existent token", async function () {
            await expect(
                agentRegistry.tokenURI(999)
            ).to.be.revertedWith("Agent does not exist");
        });
    });

    describe("ERC-721 Compliance", function () {
        beforeEach(async function () {
            const metadata = createAgentMetadata(0);
            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );
        });

        it("should support ERC-721 interface", async function () {
            // ERC-721 interface ID: 0x80ac58cd
            expect(await agentRegistry.supportsInterface("0x80ac58cd")).to.equal(true);
        });

        it("should allow token transfers", async function () {
            await agentRegistry.connect(agent1).transferFrom(
                agent1.address,
                agent2.address,
                0
            );

            expect(await agentRegistry.ownerOf(0)).to.equal(agent2.address);
        });

        it("should update balance after transfer", async function () {
            await agentRegistry.connect(agent1).transferFrom(
                agent1.address,
                agent2.address,
                0
            );

            expect(await agentRegistry.balanceOf(agent1.address)).to.equal(0);
            expect(await agentRegistry.balanceOf(agent2.address)).to.equal(1);
        });

        it("should emit Transfer event", async function () {
            await expect(
                agentRegistry.connect(agent1).transferFrom(
                    agent1.address,
                    agent2.address,
                    0
                )
            )
                .to.emit(agentRegistry, "Transfer")
                .withArgs(agent1.address, agent2.address, 0n);
        });
    });

    describe("Gas Usage", function () {
        it("should register agent within reasonable gas limits", async function () {
            const metadata = createAgentMetadata(0);

            const tx = await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );
            const receipt = await tx.wait();

            // Registration should use less than 400k gas (includes NFT minting)
            expect(receipt.gasUsed).to.be.lessThan(400000n);
            console.log(`        Gas used for registration: ${receipt.gasUsed}`);
        });

        it("should deactivate agent within reasonable gas limits", async function () {
            const metadata = createAgentMetadata(0);
            await agentRegistry.registerAgent(
                agent1.address,
                metadata.did,
                metadata.role,
                metadata.publicKey
            );

            const tx = await agentRegistry.connect(agent1).deactivateAgent(0);
            const receipt = await tx.wait();

            // Deactivation should use less than 50k gas
            expect(receipt.gasUsed).to.be.lessThan(50000n);
            console.log(`        Gas used for deactivation: ${receipt.gasUsed}`);
        });
    });
});
