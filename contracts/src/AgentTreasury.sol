// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title AgentTreasury
 * @dev Circle Wallet wrapper for agent treasury management
 * @notice Each agent has a dedicated treasury for receiving and sending USDC
 *
 * Aligned with Trustless Agent Framework PRD:
 * - §8 X402 Protocol (micropayments integration)
 * - §6 ZeroDB Integration (payment audit trail)
 * - §10 Non-repudiation (all payments on-chain)
 */
contract AgentTreasury is Ownable, ReentrancyGuard {
    // Treasury metadata
    struct Treasury {
        uint256 agentTokenId;     // Agent token ID from AgentRegistry
        address owner;            // Agent owner address
        uint256 createdAt;        // Block timestamp
        bool active;              // Treasury status
    }

    // Payment record
    struct Payment {
        uint256 fromTreasuryId;   // Source treasury ID
        uint256 toTreasuryId;     // Destination treasury ID
        uint256 amount;           // USDC amount (6 decimals)
        string purpose;           // Payment purpose (e.g., "x402-api-call")
        string x402ReceiptHash;   // X402 protocol receipt hash
        uint256 timestamp;        // Block timestamp
    }

    // State variables
    uint256 private _treasuryCounter;
    uint256 private _paymentCounter;

    mapping(uint256 => Treasury) private _treasuries;
    mapping(uint256 => uint256) private _agentToTreasury; // agentTokenId => treasuryId
    mapping(uint256 => uint256[]) private _treasuryPayments; // treasuryId => paymentIds
    mapping(uint256 => Payment) private _payments;

    // USDC balance tracking (in real implementation, use actual USDC contract)
    mapping(uint256 => uint256) private _treasuryBalances; // treasuryId => balance

    // Events
    event TreasuryCreated(
        uint256 indexed treasuryId,
        uint256 indexed agentTokenId,
        address indexed owner,
        uint256 timestamp
    );

    event PaymentProcessed(
        uint256 indexed paymentId,
        uint256 indexed fromTreasuryId,
        uint256 indexed toTreasuryId,
        uint256 amount,
        string purpose,
        uint256 timestamp
    );

    event TreasuryFunded(
        uint256 indexed treasuryId,
        uint256 amount,
        uint256 newBalance,
        uint256 timestamp
    );

    event TreasuryWithdrawn(
        uint256 indexed treasuryId,
        address indexed to,
        uint256 amount,
        uint256 newBalance,
        uint256 timestamp
    );

    constructor() Ownable(msg.sender) {
        _treasuryCounter = 0;
        _paymentCounter = 0;
    }

    /**
     * @dev Create a treasury for an agent
     * @param agentTokenId The agent token ID from AgentRegistry
     * @param owner The agent owner address
     * @return treasuryId The unique treasury ID
     */
    function createTreasury(uint256 agentTokenId, address owner) public returns (uint256) {
        require(owner != address(0), "Invalid owner address");
        require(_agentToTreasury[agentTokenId] == 0, "Treasury already exists for agent");

        uint256 treasuryId = _treasuryCounter + 1; // Start from 1, reserve 0 for "not found"
        _treasuryCounter++;

        _treasuries[treasuryId] = Treasury({
            agentTokenId: agentTokenId,
            owner: owner,
            createdAt: block.timestamp,
            active: true
        });

        _agentToTreasury[agentTokenId] = treasuryId;

        emit TreasuryCreated(treasuryId, agentTokenId, owner, block.timestamp);

        return treasuryId;
    }

    /**
     * @dev Fund a treasury with USDC (testnet simulation)
     * @param treasuryId The treasury ID
     * @param amount Amount of USDC (6 decimals)
     */
    function fundTreasury(uint256 treasuryId, uint256 amount) public payable {
        require(treasuryId > 0 && treasuryId <= _treasuryCounter, "Invalid treasury ID");
        require(amount > 0, "Amount must be greater than 0");
        require(_treasuries[treasuryId].active, "Treasury not active");

        // In production: Transfer actual USDC from msg.sender
        // For testnet: Simulate balance update
        _treasuryBalances[treasuryId] += amount;

        emit TreasuryFunded(treasuryId, amount, _treasuryBalances[treasuryId], block.timestamp);
    }

    /**
     * @dev Process payment from one treasury to another
     * @param fromTreasuryId Source treasury
     * @param toTreasuryId Destination treasury
     * @param amount USDC amount (6 decimals)
     * @param purpose Payment purpose
     * @param x402ReceiptHash X402 protocol receipt hash
     * @return paymentId The unique payment ID
     */
    function processPayment(
        uint256 fromTreasuryId,
        uint256 toTreasuryId,
        uint256 amount,
        string memory purpose,
        string memory x402ReceiptHash
    ) public nonReentrant returns (uint256) {
        require(fromTreasuryId > 0 && fromTreasuryId <= _treasuryCounter, "Invalid source treasury");
        require(toTreasuryId > 0 && toTreasuryId <= _treasuryCounter, "Invalid destination treasury");
        require(amount > 0, "Amount must be greater than 0");
        require(_treasuries[fromTreasuryId].active, "Source treasury not active");
        require(_treasuries[toTreasuryId].active, "Destination treasury not active");

        // Only treasury owner can authorize payments
        require(
            _treasuries[fromTreasuryId].owner == msg.sender || msg.sender == owner(),
            "Not authorized to make payment"
        );

        // Check balance
        require(_treasuryBalances[fromTreasuryId] >= amount, "Insufficient balance");

        uint256 paymentId = _paymentCounter;
        _paymentCounter++;

        // Transfer balance
        _treasuryBalances[fromTreasuryId] -= amount;
        _treasuryBalances[toTreasuryId] += amount;

        // Record payment
        _payments[paymentId] = Payment({
            fromTreasuryId: fromTreasuryId,
            toTreasuryId: toTreasuryId,
            amount: amount,
            purpose: purpose,
            x402ReceiptHash: x402ReceiptHash,
            timestamp: block.timestamp
        });

        _treasuryPayments[fromTreasuryId].push(paymentId);
        _treasuryPayments[toTreasuryId].push(paymentId);

        emit PaymentProcessed(
            paymentId,
            fromTreasuryId,
            toTreasuryId,
            amount,
            purpose,
            block.timestamp
        );

        return paymentId;
    }

    /**
     * @dev Withdraw USDC from treasury to external address
     * @param treasuryId The treasury ID
     * @param to Destination address
     * @param amount Amount to withdraw
     */
    function withdrawFromTreasury(
        uint256 treasuryId,
        address to,
        uint256 amount
    ) public nonReentrant {
        require(treasuryId > 0 && treasuryId <= _treasuryCounter, "Invalid treasury ID");
        require(_treasuries[treasuryId].owner == msg.sender, "Not treasury owner");
        require(_treasuryBalances[treasuryId] >= amount, "Insufficient balance");
        require(amount > 0, "Amount must be greater than 0");

        _treasuryBalances[treasuryId] -= amount;

        // In production: Transfer actual USDC to 'to' address
        // For testnet: Just emit event

        emit TreasuryWithdrawn(treasuryId, to, amount, _treasuryBalances[treasuryId], block.timestamp);
    }

    /**
     * @dev Get treasury by ID
     * @param treasuryId The treasury ID
     * @return Treasury structure
     */
    function getTreasury(uint256 treasuryId) public view returns (Treasury memory) {
        require(treasuryId > 0 && treasuryId <= _treasuryCounter, "Invalid treasury ID");
        return _treasuries[treasuryId];
    }

    /**
     * @dev Get treasury ID by agent token ID
     * @param agentTokenId The agent token ID
     * @return treasuryId The treasury ID (0 if not found)
     */
    function getTreasuryByAgent(uint256 agentTokenId) public view returns (uint256) {
        return _agentToTreasury[agentTokenId];
    }

    /**
     * @dev Get treasury balance
     * @param treasuryId The treasury ID
     * @return Balance in USDC (6 decimals)
     */
    function getTreasuryBalance(uint256 treasuryId) public view returns (uint256) {
        require(treasuryId > 0 && treasuryId <= _treasuryCounter, "Invalid treasury ID");
        return _treasuryBalances[treasuryId];
    }

    /**
     * @dev Get payment by ID
     * @param paymentId The payment ID
     * @return Payment structure
     */
    function getPayment(uint256 paymentId) public view returns (Payment memory) {
        require(paymentId < _paymentCounter, "Payment does not exist");
        return _payments[paymentId];
    }

    /**
     * @dev Get all payment IDs for a treasury
     * @param treasuryId The treasury ID
     * @return Array of payment IDs
     */
    function getTreasuryPayments(uint256 treasuryId) public view returns (uint256[] memory) {
        return _treasuryPayments[treasuryId];
    }

    /**
     * @dev Get total number of treasuries
     * @return Total treasury count
     */
    function totalTreasuries() public view returns (uint256) {
        return _treasuryCounter;
    }

    /**
     * @dev Get total number of payments
     * @return Total payment count
     */
    function totalPayments() public view returns (uint256) {
        return _paymentCounter;
    }
}
