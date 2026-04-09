/**
 * hedera_transfer_hbar — Transfer HBAR between accounts.
 *
 * Built by AINative Dev Team
 * Refs #268
 */

import type {
  HederaMCPTool,
  HederaMCPToolError,
  ToolContext,
  TransferHbarInput,
  TransferHbarOutput,
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

export const transferHbar: HederaMCPTool<TransferHbarInput, TransferHbarOutput> = {
  name: 'hedera_transfer_hbar',
  description:
    'Transfer HBAR from one Hedera account to another. ' +
    'Requires sender_account_id, receiver_account_id, and amount_hbar (must be > 0).',

  async execute(input: TransferHbarInput, ctx?: ToolContext): Promise<TransferHbarOutput> {
    // Validate input
    if (input.amount_hbar <= 0) {
      throw makeError(
        `amount_hbar must be positive, got ${input.amount_hbar}`,
        'VALIDATION_ERROR',
      );
    }

    const network = ctx?.network ?? 'testnet';
    const baseUrl = ctx?.mirrorNodeUrl ?? MIRROR_BASE[network];
    const fetchFn = ctx?.fetch ?? fetch;

    const response = await fetchFn(`${baseUrl}/transactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'CRYPTOTRANSFER',
        sender_account_id: input.sender_account_id,
        receiver_account_id: input.receiver_account_id,
        amount_hbar: input.amount_hbar,
        memo: input.memo ?? '',
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw makeError(
        `HBAR transfer failed (HTTP ${response.status}): ${body}`,
        'TRANSFER_FAILED',
        response.status,
      );
    }

    const data = await response.json() as {
      transaction_id: string;
      status?: string;
      amount_hbar?: number;
    };

    return {
      transaction_id: data.transaction_id,
      status: (data.status as TransferHbarOutput['status']) ?? 'SUCCESS',
      amount_hbar: data.amount_hbar ?? input.amount_hbar,
      sender_account_id: input.sender_account_id,
      receiver_account_id: input.receiver_account_id,
    };
  },
};
