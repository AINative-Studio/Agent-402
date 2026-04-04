/**
 * ainative_remember — Store memory tool
 * Built by AINative Dev Team
 * Refs #183
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { AINativeClient } from '../../client';
import { AINativeAPIError } from '../../types';

const RememberSchema = z.object({
  content: z.string().describe('The content to store in memory'),
  agent_id: z.string().optional().describe('Agent identifier for scoping memory'),
  metadata: z
    .record(z.union([z.string(), z.number(), z.boolean(), z.null()]))
    .optional()
    .describe('Optional key-value metadata to attach to the memory'),
});

export function createRememberTool(client: AINativeClient): DynamicStructuredTool {
  return new DynamicStructuredTool({
    name: 'ainative_remember',
    description:
      'Store a piece of information in persistent agent memory. Use this to remember facts, preferences, or context about the user or ongoing task.',
    schema: RememberSchema,
    func: async (input) => {
      try {
        const result = await client.remember({
          content: input.content,
          agent_id: input.agent_id,
          metadata: input.metadata as Record<string, string | number | boolean | null> | undefined,
        });
        return `Memory stored successfully. ID: ${result.id}`;
      } catch (err) {
        const apiErr = err as AINativeAPIError;
        return `Error storing memory: ${apiErr.message ?? String(err)}`;
      }
    },
  });
}
