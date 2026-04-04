/**
 * ainative_vector_search — Semantic similarity search tool
 * Built by AINative Dev Team
 * Refs #185
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { AINativeClient } from '../../client';
import { AINativeAPIError } from '../../types';
import { VALID_DIMENSIONS } from './upsert';

const VectorSearchSchema = z.object({
  vector: z
    .array(z.number())
    .describe('Query vector for similarity search (must be 384, 768, 1024, or 1536 dimensions)'),
  top_k: z
    .number()
    .int()
    .positive()
    .optional()
    .describe('Number of nearest neighbors to return (default: 5)'),
  namespace: z
    .string()
    .optional()
    .describe('Namespace to search within (e.g., Hedera account ID)'),
  filter: z
    .record(z.union([z.string(), z.number(), z.boolean(), z.null()]))
    .optional()
    .describe('Metadata filter to narrow results'),
});

export function createVectorSearchTool(client: AINativeClient): DynamicStructuredTool {
  return new DynamicStructuredTool({
    name: 'ainative_vector_search',
    description:
      'Search for semantically similar vectors using a query embedding. Returns the nearest neighbors by cosine similarity. Supports namespace filtering for per-Hedera-account isolation.',
    schema: VectorSearchSchema,
    func: async (input) => {
      if (!(VALID_DIMENSIONS as number[]).includes(input.vector.length)) {
        return `Error: Invalid vector dimension ${input.vector.length}. Must be one of: ${VALID_DIMENSIONS.join(', ')}.`;
      }

      try {
        const result = await client.vectorSearch({
          vector: input.vector,
          top_k: input.top_k,
          namespace: input.namespace,
          filter: input.filter as Record<string, string | number | boolean | null> | undefined,
        });

        if (!result.matches || result.matches.length === 0) {
          return 'No matches found for the query vector.';
        }

        const formatted = result.matches
          .map((m, i) => `${i + 1}. [${m.id}] score: ${m.score}`)
          .join('\n');
        return `Found ${result.matches.length} match(es):\n${formatted}`;
      } catch (err) {
        const apiErr = err as AINativeAPIError;
        return `Error searching vectors: ${apiErr.message ?? String(err)}`;
      }
    },
  });
}
