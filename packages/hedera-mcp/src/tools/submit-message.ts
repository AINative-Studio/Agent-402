/**
 * hedera_submit_message — Submit a message to an HCS topic.
 *
 * Built by AINative Dev Team
 * Refs #268
 */

import type {
  HederaMCPTool,
  HederaMCPToolError,
  ToolContext,
  SubmitMessageInput,
  SubmitMessageOutput,
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

export const submitMessage: HederaMCPTool<SubmitMessageInput, SubmitMessageOutput> = {
  name: 'hedera_submit_message',
  description:
    'Submit a message to a Hedera Consensus Service (HCS) topic. ' +
    'Provide topic_id and message (non-empty string). ' +
    'Returns sequence_number and consensus_timestamp.',

  async execute(input: SubmitMessageInput, ctx?: ToolContext): Promise<SubmitMessageOutput> {
    // Validate input
    if (!input.message || input.message.trim().length === 0) {
      throw makeError('message must be a non-empty string', 'VALIDATION_ERROR');
    }

    const network = ctx?.network ?? 'testnet';
    const baseUrl = ctx?.mirrorNodeUrl ?? MIRROR_BASE[network];
    const fetchFn = ctx?.fetch ?? fetch;

    const response = await fetchFn(`${baseUrl}/topics/${input.topic_id}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: input.message,
        submit_key: input.submit_key,
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw makeError(
        `Message submission failed (HTTP ${response.status}): ${body}`,
        'MESSAGE_SUBMIT_FAILED',
        response.status,
      );
    }

    const data = await response.json() as {
      sequence_number: number;
      consensus_timestamp: string;
      topic_id: string;
      transaction_id?: string;
    };

    return {
      topic_id: data.topic_id ?? input.topic_id,
      sequence_number: data.sequence_number,
      consensus_timestamp: data.consensus_timestamp,
      transaction_id: data.transaction_id,
    };
  },
};
