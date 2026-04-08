/**
 * Input/output schemas for the Hedera MCP server tools.
 *
 * Built by AINative Dev Team
 * Refs #268
 */

// ---------------------------------------------------------------------------
// Shared context passed to each tool's execute method
// ---------------------------------------------------------------------------

export interface ToolContext {
  /** Injectable fetch function — defaults to global fetch in production. */
  fetch?: typeof fetch;
  /** Optional Hedera network (testnet | mainnet). Defaults to testnet. */
  network?: 'testnet' | 'mainnet';
  /** Optional mirror node base URL override. */
  mirrorNodeUrl?: string;
}

// ---------------------------------------------------------------------------
// Shared error type
// ---------------------------------------------------------------------------

export interface HederaMCPToolError extends Error {
  /** Machine-readable error code. */
  code:
    | 'VALIDATION_ERROR'
    | 'TRANSFER_FAILED'
    | 'TOKEN_CREATION_FAILED'
    | 'MESSAGE_SUBMIT_FAILED'
    | 'BALANCE_QUERY_FAILED'
    | 'CONTRACT_DEPLOY_FAILED'
    | 'UNKNOWN_ERROR';
  /** HTTP status from the Hedera REST API, if applicable. */
  httpStatus?: number;
}

// ---------------------------------------------------------------------------
// hedera_transfer_hbar
// ---------------------------------------------------------------------------

export interface TransferHbarInput {
  /** Sender Hedera account ID (e.g. 0.0.100). */
  sender_account_id: string;
  /** Receiver Hedera account ID (e.g. 0.0.200). */
  receiver_account_id: string;
  /** Amount in HBAR (must be > 0). */
  amount_hbar: number;
  /** Optional transaction memo. */
  memo?: string;
}

export interface TransferHbarOutput {
  /** Hedera transaction ID. */
  transaction_id: string;
  /** Transaction status. */
  status: 'SUCCESS' | 'FAILED';
  /** Amount transferred. */
  amount_hbar: number;
  /** Sender account. */
  sender_account_id?: string;
  /** Receiver account. */
  receiver_account_id?: string;
}

// ---------------------------------------------------------------------------
// hedera_create_token
// ---------------------------------------------------------------------------

export type TokenType = 'FUNGIBLE_COMMON' | 'NON_FUNGIBLE_UNIQUE';

export interface CreateTokenInput {
  /** Token name. */
  name: string;
  /** Token ticker symbol. */
  symbol: string;
  /** Fungible or NFT. */
  token_type: TokenType;
  /** Initial supply (0 for NFT). */
  initial_supply: number;
  /** Decimal places (0 for NFT). */
  decimals: number;
  /** Treasury account ID. */
  treasury_account_id: string;
  /** Optional token memo. */
  memo?: string;
}

export interface CreateTokenOutput {
  /** Hedera token ID (e.g. 0.0.999). */
  token_id: string;
  /** Type of token created. */
  token_type: TokenType;
  /** Transaction ID for the creation. */
  transaction_id?: string;
}

// ---------------------------------------------------------------------------
// hedera_submit_message
// ---------------------------------------------------------------------------

export interface SubmitMessageInput {
  /** HCS topic ID (e.g. 0.0.555). */
  topic_id: string;
  /** Message content to submit. */
  message: string;
  /** Optional submit key (private key hex or DER). */
  submit_key?: string;
}

export interface SubmitMessageOutput {
  /** HCS topic ID. */
  topic_id: string;
  /** Sequence number of the submitted message. */
  sequence_number: number;
  /** Consensus timestamp from HCS. */
  consensus_timestamp: string;
  /** Transaction ID. */
  transaction_id?: string;
}

// ---------------------------------------------------------------------------
// hedera_query_balance
// ---------------------------------------------------------------------------

export interface QueryBalanceInput {
  /** Hedera account ID to query. */
  account_id: string;
}

export interface TokenBalance {
  /** HTS token ID. */
  token_id: string;
  /** Raw balance (apply decimals for actual value). */
  balance: number;
  /** Token decimals. */
  decimals: number;
}

export interface QueryBalanceOutput {
  /** Account ID queried. */
  account_id: string;
  /** HBAR balance (in HBAR, not tinybars). */
  hbar_balance: number;
  /** HTS token balances. */
  token_balances: TokenBalance[];
}

// ---------------------------------------------------------------------------
// hedera_deploy_contract
// ---------------------------------------------------------------------------

export interface DeployContractInput {
  /** EVM bytecode (hex string, optionally prefixed with 0x). */
  bytecode: string;
  /** Gas limit for deployment. Must be > 0. */
  gas: number;
  /** Admin account ID. */
  admin_account_id: string;
  /** Optional contract memo. */
  memo?: string;
  /** Optional initial HBAR to send with deployment (in HBAR). */
  initial_balance_hbar?: number;
}

export interface DeployContractOutput {
  /** Deployed contract ID (e.g. 0.0.12345). */
  contract_id: string;
  /** Deployment transaction ID. */
  transaction_id: string;
  /** EVM address of the deployed contract. */
  evm_address?: string;
}

// ---------------------------------------------------------------------------
// Tool definition interface
// ---------------------------------------------------------------------------

export interface HederaMCPTool<TInput, TOutput> {
  /** Machine-readable tool name. */
  name: string;
  /** Human-readable description for the MCP manifest. */
  description: string;
  /** Execute the tool with the given input and optional context. */
  execute(input: TInput, ctx?: ToolContext): Promise<TOutput>;
}
