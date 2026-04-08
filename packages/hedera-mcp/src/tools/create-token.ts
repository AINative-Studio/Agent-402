/**
 * hedera_create_token — Create HTS fungible or non-fungible token.
 *
 * Built by AINative Dev Team
 * Refs #268
 */

import type {
  HederaMCPTool,
  HederaMCPToolError,
  ToolContext,
  CreateTokenInput,
  CreateTokenOutput,
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

export const createToken: HederaMCPTool<CreateTokenInput, CreateTokenOutput> = {
  name: 'hedera_create_token',
  description:
    'Create a Hedera Token Service (HTS) fungible or non-fungible token. ' +
    'Provide name, symbol, token_type (FUNGIBLE_COMMON | NON_FUNGIBLE_UNIQUE), ' +
    'initial_supply, decimals, and treasury_account_id.',

  async execute(input: CreateTokenInput, ctx?: ToolContext): Promise<CreateTokenOutput> {
    const network = ctx?.network ?? 'testnet';
    const baseUrl = ctx?.mirrorNodeUrl ?? MIRROR_BASE[network];
    const fetchFn = ctx?.fetch ?? fetch;

    const response = await fetchFn(`${baseUrl}/tokens`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: input.name,
        symbol: input.symbol,
        token_type: input.token_type,
        initial_supply: input.initial_supply,
        decimals: input.decimals,
        treasury_account_id: input.treasury_account_id,
        memo: input.memo ?? '',
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw makeError(
        `Token creation failed (HTTP ${response.status}): ${body}`,
        'TOKEN_CREATION_FAILED',
        response.status,
      );
    }

    const data = await response.json() as {
      token_id: string;
      token_type: string;
      transaction_id?: string;
    };

    return {
      token_id: data.token_id,
      token_type: data.token_type as CreateTokenOutput['token_type'],
      transaction_id: data.transaction_id,
    };
  },
};
