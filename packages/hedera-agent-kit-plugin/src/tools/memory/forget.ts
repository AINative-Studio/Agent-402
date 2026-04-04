/**
 * ainative_forget — Delete memory by ID tool
 * Built by AINative Dev Team
 * Refs #183
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { AINativeClient } from '../../client';
import { AINativeAPIError } from '../../types';

const ForgetSchema = z.object({
  id: z.string().describe('The unique ID of the memory to delete'),
});

export function createForgetTool(client: AINativeClient): DynamicStructuredTool {
  return new DynamicStructuredTool({
    name: 'ainative_forget',
    description:
      'Delete a specific memory by its ID. Use this to remove outdated, incorrect, or sensitive information from agent memory.',
    schema: ForgetSchema,
    func: async (input) => {
      try {
        const result = await client.forget({ id: input.id });
        if (result.success) {
          return `Memory ${result.id} deleted successfully.`;
        }
        return `Memory ${result.id} was not removed. It may not exist.`;
      } catch (err) {
        const apiErr = err as AINativeAPIError;
        return `Error deleting memory: ${apiErr.message ?? String(err)}`;
      }
    },
  });
}
