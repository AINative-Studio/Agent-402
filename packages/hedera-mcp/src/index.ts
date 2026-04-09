/**
 * @ainative/hedera-mcp — MCP server entry point.
 *
 * Exports 5 Hedera tools:
 *   - hedera_transfer_hbar   : transfer HBAR between accounts
 *   - hedera_create_token    : create HTS fungible/non-fungible token
 *   - hedera_submit_message  : submit message to HCS topic
 *   - hedera_query_balance   : get HBAR + token balances
 *   - hedera_deploy_contract : deploy smart contract bytecode
 *
 * Built by AINative Dev Team
 * Refs #268
 */

export { transferHbar } from './tools/transfer-hbar';
export { createToken } from './tools/create-token';
export { submitMessage } from './tools/submit-message';
export { queryBalance } from './tools/query-balance';
export { deployContract } from './tools/deploy-contract';

export type {
  ToolContext,
  HederaMCPToolError,
  HederaMCPTool,
  TransferHbarInput,
  TransferHbarOutput,
  CreateTokenInput,
  CreateTokenOutput,
  SubmitMessageInput,
  SubmitMessageOutput,
  QueryBalanceInput,
  QueryBalanceOutput,
  TokenBalance,
  DeployContractInput,
  DeployContractOutput,
} from './types';

import { transferHbar } from './tools/transfer-hbar';
import { createToken } from './tools/create-token';
import { submitMessage } from './tools/submit-message';
import { queryBalance } from './tools/query-balance';
import { deployContract } from './tools/deploy-contract';

/** All 5 Hedera MCP tools as an array. */
export const hederaMCPTools = [
  transferHbar,
  createToken,
  submitMessage,
  queryBalance,
  deployContract,
] as const;

/** MCP tool manifest — maps tool names to descriptions. */
export const hederaMCPManifest = hederaMCPTools.map((tool) => ({
  name: tool.name,
  description: tool.description,
}));
