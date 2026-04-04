/**
 * ainative_recall — Semantic memory search tool
 * Built by AINative Dev Team
 * Refs #183
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { AINativeClient } from '../../client';
import { AINativeAPIError } from '../../types';

const RecallSchema = z.object({
  query: z.string().describe('Semantic search query to find relevant memories'),
  limit: z
    .number()
    .int()
    .positive()
    .optional()
    .describe('Maximum number of memories to return'),
  agent_id: z
    .string()
    .optional()
    .describe('Filter memories by agent ID'),
  filters: z
    .record(z.union([z.string(), z.number(), z.boolean(), z.null()]))
    .optional()
    .describe('Additional metadata filters'),
});

export function createRecallTool(client: AINativeClient): DynamicStructuredTool {
  return new DynamicStructuredTool({
    name: 'ainative_recall',
    description:
      'Search agent memory using semantic similarity. Returns relevant memories matching the query. Use this to retrieve past context, facts, or user preferences.',
    schema: RecallSchema,
    func: async (input) => {
      try {
        const result = await client.recall({
          query: input.query,
          limit: input.limit,
          agent_id: input.agent_id,
          filters: input.filters as Record<string, string | number | boolean | null> | undefined,
        });

        if (!result.memories || result.memories.length === 0) {
          return 'No memories found matching the query.';
        }

        const formatted = result.memories
          .map((m, i) => `${i + 1}. [${m.id}] (score: ${m.score.toFixed(3)}) ${m.content}`)
          .join('\n');
        return `Found ${result.memories.length} memories:\n${formatted}`;
      } catch (err) {
        const apiErr = err as AINativeAPIError;
        return `Error recalling memories: ${apiErr.message ?? String(err)}`;
      }
    },
  });
}
