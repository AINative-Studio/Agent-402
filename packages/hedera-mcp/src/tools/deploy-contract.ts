/**
 * hedera_deploy_contract — Deploy a smart contract bytecode on Hedera.
 *
 * Built by AINative Dev Team
 * Refs #268
 */

import type {
  HederaMCPTool,
  HederaMCPToolError,
  ToolContext,
  DeployContractInput,
  DeployContractOutput,
} from '../types';

function makeError(
  message: string,
  code: HederaMCPToolError['code'],
  httpStatus?: number,
): HederaMCPToolError {
  const err = new Error(message) as HederaMCPToolError;
  err.code = code;
  err.httpStatus = httpStatus;
  return err;
}

const MIRROR_BASE: Record<string, string> = {
  testnet: 'https://testnet.mirrornode.hedera.com/api/v1',
  mainnet: 'https://mainnet.mirrornode.hedera.com/api/v1',
};

export const deployContract: HederaMCPTool<DeployContractInput, DeployContractOutput> = {
  name: 'hedera_deploy_contract',
  description:
    'Deploy a smart contract bytecode to the Hedera network. ' +
    'Provide bytecode (hex), gas (must be > 0), and admin_account_id. ' +
    'Returns contract_id and transaction_id.',

  async execute(input: DeployContractInput, ctx?: ToolContext): Promise<DeployContractOutput> {
    // Validate input
    if (input.gas <= 0) {
      throw makeError(`gas must be positive, got ${input.gas}`, 'VALIDATION_ERROR');
    }

    const network = ctx?.network ?? 'testnet';
    const baseUrl = ctx?.mirrorNodeUrl ?? MIRROR_BASE[network];
    const fetchFn = ctx?.fetch ?? fetch;

    const response = await fetchFn(`${baseUrl}/contracts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bytecode: input.bytecode,
        gas: input.gas,
        admin_account_id: input.admin_account_id,
        memo: input.memo ?? '',
        initial_balance_hbar: input.initial_balance_hbar ?? 0,
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw makeError(
        `Contract deployment failed (HTTP ${response.status}): ${body}`,
        'CONTRACT_DEPLOY_FAILED',
        response.status,
      );
    }

    const data = await response.json() as {
      contract_id: string;
      transaction_id: string;
      evm_address?: string;
    };

    return {
      contract_id: data.contract_id,
      transaction_id: data.transaction_id,
      evm_address: data.evm_address,
    };
  },
};
