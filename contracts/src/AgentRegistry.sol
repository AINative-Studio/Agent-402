// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title AgentRegistry
 * @dev ERC-721 based agent identity registry for trustless autonomous agents
 * @notice Each agent receives a unique NFT representing their on-chain identity
 *
 * Aligned with Trustless Agent Framework PRD:
 * - §5 Agent Personas (DID-based identities)
 * - §6 ZeroDB Integration (on-chain + off-chain hybrid)
 * - §10 Non-repudiation (immutable identity records)
 */
contract AgentRegistry is ERC721, Ownable {
    using Strings for uint256;

    // Agent metadata structure
    struct AgentMetadata {
        string did;              // Decentralized identifier (did:key:...)
        string role;             // Agent role: "analyst", "compliance", "transaction"
        string publicKey;        // Public key for signature verification
        uint256 registeredAt;    // Block timestamp of registration
        bool active;             // Agent status
    }

    // State variables
    uint256 private _tokenIdCounter;
    mapping(uint256 => AgentMetadata) private _agentMetadata;
    mapping(string => uint256) private _didToTokenId;
    mapping(string => bool) private _didRegistered;

    // Events
    event AgentRegistered(
        uint256 indexed tokenId,
        address indexed owner,
        string did,
        string role,
        uint256 timestamp
    );

    event AgentDeactivated(
        uint256 indexed tokenId,
        string did,
        uint256 timestamp
    );

    event AgentReactivated(
        uint256 indexed tokenId,
        string did,
        uint256 timestamp
    );

    /**
     * @dev Constructor - initializes the ERC-721 contract
     */
    constructor() ERC721("TrustlessAgent", "AGENT") Ownable(msg.sender) {
        _tokenIdCounter = 0;
    }

    /**
     * @dev Register a new agent on-chain
     * @param to Address that will own the agent NFT
     * @param did Decentralized identifier (must be unique)
     * @param role Agent role (analyst, compliance, transaction)
     * @param publicKey Public key for signature verification
     * @return tokenId The unique token ID assigned to this agent
     */
    function registerAgent(
        address to,
        string memory did,
        string memory role,
        string memory publicKey
    ) public returns (uint256) {
        require(bytes(did).length > 0, "DID cannot be empty");
        require(bytes(role).length > 0, "Role cannot be empty");
        require(bytes(publicKey).length > 0, "Public key cannot be empty");
        require(!_didRegistered[did], "DID already registered");

        uint256 tokenId = _tokenIdCounter;
        _tokenIdCounter++;

        _safeMint(to, tokenId);

        _agentMetadata[tokenId] = AgentMetadata({
            did: did,
            role: role,
            publicKey: publicKey,
            registeredAt: block.timestamp,
            active: true
        });

        _didToTokenId[did] = tokenId;
        _didRegistered[did] = true;

        emit AgentRegistered(tokenId, to, did, role, block.timestamp);

        return tokenId;
    }

    /**
     * @dev Get agent metadata by token ID
     * @param tokenId The token ID to query
     * @return Agent metadata structure
     */
    function getAgentMetadata(uint256 tokenId) public view returns (AgentMetadata memory) {
        require(_ownerOf(tokenId) != address(0), "Agent does not exist");
        return _agentMetadata[tokenId];
    }

    /**
     * @dev Get token ID by DID
     * @param did Decentralized identifier
     * @return tokenId The token ID associated with this DID
     */
    function getTokenIdByDID(string memory did) public view returns (uint256) {
        require(_didRegistered[did], "DID not registered");
        return _didToTokenId[did];
    }

    /**
     * @dev Check if a DID is registered
     * @param did Decentralized identifier
     * @return bool True if registered, false otherwise
     */
    function isDIDRegistered(string memory did) public view returns (bool) {
        return _didRegistered[did];
    }

    /**
     * @dev Deactivate an agent (only owner)
     * @param tokenId The token ID to deactivate
     */
    function deactivateAgent(uint256 tokenId) public {
        require(ownerOf(tokenId) == msg.sender, "Not agent owner");
        require(_agentMetadata[tokenId].active, "Agent already inactive");

        _agentMetadata[tokenId].active = false;

        emit AgentDeactivated(tokenId, _agentMetadata[tokenId].did, block.timestamp);
    }

    /**
     * @dev Reactivate an agent (only owner)
     * @param tokenId The token ID to reactivate
     */
    function reactivateAgent(uint256 tokenId) public {
        require(ownerOf(tokenId) == msg.sender, "Not agent owner");
        require(!_agentMetadata[tokenId].active, "Agent already active");

        _agentMetadata[tokenId].active = true;

        emit AgentReactivated(tokenId, _agentMetadata[tokenId].did, block.timestamp);
    }

    /**
     * @dev Check if an agent is active
     * @param tokenId The token ID to check
     * @return bool True if active, false otherwise
     */
    function isAgentActive(uint256 tokenId) public view returns (bool) {
        require(_ownerOf(tokenId) != address(0), "Agent does not exist");
        return _agentMetadata[tokenId].active;
    }

    /**
     * @dev Get total number of registered agents
     * @return uint256 Total agent count
     */
    function totalAgents() public view returns (uint256) {
        return _tokenIdCounter;
    }

    /**
     * @dev Override tokenURI to return agent metadata
     * @param tokenId The token ID
     * @return string JSON metadata URI
     */
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_ownerOf(tokenId) != address(0), "Agent does not exist");

        AgentMetadata memory metadata = _agentMetadata[tokenId];

        // For MVP, return simple data URI with JSON
        // In production, this would point to IPFS or similar decentralized storage
        return string(abi.encodePacked(
            "data:application/json;base64,",
            _base64Encode(bytes(string(abi.encodePacked(
                '{"did":"', metadata.did, '",',
                '"role":"', metadata.role, '",',
                '"active":', metadata.active ? 'true' : 'false', ',',
                '"registeredAt":', Strings.toString(metadata.registeredAt), '}'
            ))))
        ));
    }

    /**
     * @dev Simple base64 encoding helper
     */
    function _base64Encode(bytes memory data) private pure returns (string memory) {
        // Simplified base64 encoding for demo purposes
        // In production, use a full base64 library
        return "eyJwbGFjZWhvbGRlciI6dHJ1ZX0="; // Placeholder
    }
}
