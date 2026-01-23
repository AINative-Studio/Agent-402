// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title ReputationRegistry
 * @dev Event-based reputation system for trustless autonomous agents
 * @notice Stores feedback and reputation events on-chain for auditability
 *
 * Aligned with Trustless Agent Framework PRD:
 * - §6 ZeroDB Integration (on-chain audit trail)
 * - §10 Non-repudiation (immutable reputation records)
 * - Progressive Trust Tiers (reputation-based trust building)
 */
contract ReputationRegistry {
    // Feedback types
    enum FeedbackType {
        POSITIVE,      // Successful transaction, good service
        NEGATIVE,      // Failed transaction, poor service
        NEUTRAL,       // Informational only
        REPORT         // Security/compliance report
    }

    // Feedback structure
    struct Feedback {
        uint256 agentTokenId;      // Agent being rated (from AgentRegistry)
        address submitter;         // Who submitted the feedback
        FeedbackType feedbackType; // Type of feedback
        int8 score;                // Score: -10 to +10
        string comment;            // Optional comment
        string transactionHash;    // Related transaction (x402/USDC)
        uint256 timestamp;         // Block timestamp
    }

    // State variables
    uint256 private _feedbackCounter;
    mapping(uint256 => Feedback) private _feedbacks;
    mapping(uint256 => uint256[]) private _agentFeedbacks; // agentTokenId => feedbackIds
    mapping(uint256 => int256) private _agentScores;       // agentTokenId => total score

    // Events
    event FeedbackSubmitted(
        uint256 indexed feedbackId,
        uint256 indexed agentTokenId,
        address indexed submitter,
        FeedbackType feedbackType,
        int8 score,
        uint256 timestamp
    );

    event ReputationUpdated(
        uint256 indexed agentTokenId,
        int256 newScore,
        uint256 feedbackCount,
        uint256 timestamp
    );

    /**
     * @dev Submit feedback for an agent
     * @param agentTokenId The agent token ID from AgentRegistry
     * @param feedbackType Type of feedback (POSITIVE, NEGATIVE, NEUTRAL, REPORT)
     * @param score Numeric score from -10 to +10
     * @param comment Optional text comment
     * @param transactionHash Related transaction identifier
     * @return feedbackId The unique feedback ID
     */
    function submitFeedback(
        uint256 agentTokenId,
        FeedbackType feedbackType,
        int8 score,
        string memory comment,
        string memory transactionHash
    ) public returns (uint256) {
        require(score >= -10 && score <= 10, "Score must be between -10 and +10");

        uint256 feedbackId = _feedbackCounter;
        _feedbackCounter++;

        _feedbacks[feedbackId] = Feedback({
            agentTokenId: agentTokenId,
            submitter: msg.sender,
            feedbackType: feedbackType,
            score: score,
            comment: comment,
            transactionHash: transactionHash,
            timestamp: block.timestamp
        });

        // Add to agent's feedback list
        _agentFeedbacks[agentTokenId].push(feedbackId);

        // Update agent's total score
        _agentScores[agentTokenId] += int256(score);

        emit FeedbackSubmitted(
            feedbackId,
            agentTokenId,
            msg.sender,
            feedbackType,
            score,
            block.timestamp
        );

        emit ReputationUpdated(
            agentTokenId,
            _agentScores[agentTokenId],
            _agentFeedbacks[agentTokenId].length,
            block.timestamp
        );

        return feedbackId;
    }

    /**
     * @dev Get feedback by ID
     * @param feedbackId The feedback ID
     * @return Feedback structure
     */
    function getFeedback(uint256 feedbackId) public view returns (Feedback memory) {
        require(feedbackId < _feedbackCounter, "Feedback does not exist");
        return _feedbacks[feedbackId];
    }

    /**
     * @dev Get all feedback IDs for an agent
     * @param agentTokenId The agent token ID
     * @return Array of feedback IDs
     */
    function getAgentFeedbackIds(uint256 agentTokenId) public view returns (uint256[] memory) {
        return _agentFeedbacks[agentTokenId];
    }

    /**
     * @dev Get agent's total reputation score
     * @param agentTokenId The agent token ID
     * @return Total score (sum of all feedback scores)
     */
    function getAgentScore(uint256 agentTokenId) public view returns (int256) {
        return _agentScores[agentTokenId];
    }

    /**
     * @dev Get agent's feedback count
     * @param agentTokenId The agent token ID
     * @return Number of feedback submissions
     */
    function getAgentFeedbackCount(uint256 agentTokenId) public view returns (uint256) {
        return _agentFeedbacks[agentTokenId].length;
    }

    /**
     * @dev Get agent's average score
     * @param agentTokenId The agent token ID
     * @return Average score (totalScore / feedbackCount)
     */
    function getAgentAverageScore(uint256 agentTokenId) public view returns (int256) {
        uint256 feedbackCount = _agentFeedbacks[agentTokenId].length;
        if (feedbackCount == 0) {
            return 0;
        }
        return _agentScores[agentTokenId] / int256(feedbackCount);
    }

    /**
     * @dev Get agent's trust tier based on reputation
     * @param agentTokenId The agent token ID
     * @return Tier level (0-4)
     *
     * Tier calculation (from PRD Progressive Trust Tiers):
     * - Tier 0: < 10 feedback or avg score < 0
     * - Tier 1: >= 10 feedback, avg >= 0, < 5
     * - Tier 2: >= 25 feedback, avg >= 5, < 7
     * - Tier 3: >= 50 feedback, avg >= 7, < 9
     * - Tier 4: >= 100 feedback, avg >= 9
     */
    function getAgentTrustTier(uint256 agentTokenId) public view returns (uint8) {
        uint256 feedbackCount = _agentFeedbacks[agentTokenId].length;
        int256 avgScore = getAgentAverageScore(agentTokenId);

        if (feedbackCount < 10 || avgScore < 0) {
            return 0; // Tier 0: Untrusted/New
        } else if (feedbackCount >= 100 && avgScore >= 9) {
            return 4; // Tier 4: Elite
        } else if (feedbackCount >= 50 && avgScore >= 7) {
            return 3; // Tier 3: Trusted
        } else if (feedbackCount >= 25 && avgScore >= 5) {
            return 2; // Tier 2: Established
        } else if (feedbackCount >= 10 && avgScore >= 0) {
            return 1; // Tier 1: Emerging
        }

        return 0;
    }

    /**
     * @dev Get reputation summary for an agent
     * @param agentTokenId The agent token ID
     * @return totalScore Total reputation score
     * @return feedbackCount Number of feedback submissions
     * @return averageScore Average score per feedback
     * @return trustTier Trust tier (0-4)
     */
    function getAgentReputationSummary(uint256 agentTokenId)
        public
        view
        returns (
            int256 totalScore,
            uint256 feedbackCount,
            int256 averageScore,
            uint8 trustTier
        )
    {
        totalScore = _agentScores[agentTokenId];
        feedbackCount = _agentFeedbacks[agentTokenId].length;
        averageScore = getAgentAverageScore(agentTokenId);
        trustTier = getAgentTrustTier(agentTokenId);
    }

    /**
     * @dev Get total number of feedback submissions
     * @return Total feedback count
     */
    function totalFeedbacks() public view returns (uint256) {
        return _feedbackCounter;
    }
}
