/**
 * hedera_query_balance — Get HBAR and HTS token balances for an account.
 *
 * Built by AINative Dev Team
 * Refs #268
 */

import type {
  HederaMCPTool,
  HederaMCPToolError,
  ToolContext,
  QueryBalanceInput,
  QueryBalanceOutput,
  TokenBalance,
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

export const queryBalance: HederaMCPTool<QueryBalanceInput, QueryBalanceOutput> = {
  name: 'hedera_query_balance',
  description:
    'Query HBAR and HTS token balances for a Hedera account. ' +
    'Provide account_id (e.g. 0.0.100). ' +
    'Returns hbar_balance and an array of token_balances.',

  async execute(input: QueryBalanceInput, ctx?: ToolContext): Promise<QueryBalanceOutput> {
    const network = ctx?.network ?? 'testnet';
    const baseUrl = ctx?.mirrorNodeUrl ?? MIRROR_BASE[network];
    const fetchFn = ctx?.fetch ?? fetch;

    const response = await fetchFn(
      `${baseUrl}/accounts/${encodeURIComponent(input.account_id)}`,
      {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      },
    );

    if (!response.ok) {
      const body = await response.text();
      throw makeError(
        `Balance query failed (HTTP ${response.status}): ${body}`,
        'BALANCE_QUERY_FAILED',
        response.status,
      );
    }

    const data = await response.json() as {
      account_id: string;
      hbar_balance: number;
      token_balances: Array<{ token_id: string; balance: number; decimals: number }>;
    };

    const tokenBalances: TokenBalance[] = (data.token_balances ?? []).map((t) => ({
      token_id: t.token_id,
      balance: t.balance,
      decimals: t.decimals ?? 0,
    }));

    return {
      account_id: data.account_id ?? input.account_id,
      hbar_balance: data.hbar_balance ?? 0,
      token_balances: tokenBalances,
    };
  },
};
