/**
 * ainative_vector_upsert — Store vector embedding tool
 * Built by AINative Dev Team
 * Refs #185
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { AINativeClient } from '../../client';
import { AINativeAPIError, VectorDimension } from '../../types';

export const VALID_DIMENSIONS: VectorDimension[] = [384, 768, 1024, 1536];

const VectorUpsertSchema = z.object({
  vector: z
    .array(z.number())
    .describe('The embedding vector to store (must be 384, 768, 1024, or 1536 dimensions)'),
  id: z.string().optional().describe('Optional custom ID for the vector'),
  metadata: z
    .record(z.union([z.string(), z.number(), z.boolean(), z.null()]))
    .optional()
    .describe('Optional metadata to attach to the vector'),
  namespace: z
    .string()
    .optional()
    .describe('Namespace for isolation (e.g., Hedera account ID like 0.0.123)'),
});

function isValidDimension(dim: number): dim is VectorDimension {
  return (VALID_DIMENSIONS as number[]).includes(dim);
}

export function createVectorUpsertTool(client: AINativeClient): DynamicStructuredTool {
  return new DynamicStructuredTool({
    name: 'ainative_vector_upsert',
    description:
      'Store a vector embedding with optional metadata in AINative. Supports 384, 768, 1024, and 1536 dimension vectors. Use namespaces for per-Hedera-account isolation.',
    schema: VectorUpsertSchema,
    func: async (input) => {
      if (!isValidDimension(input.vector.length)) {
        return `Error: Invalid vector dimension ${input.vector.length}. Must be one of: ${VALID_DIMENSIONS.join(', ')}.`;
      }

      try {
        const result = await client.vectorUpsert({
          id: input.id,
          vector: input.vector,
          metadata: input.metadata as Record<string, string | number | boolean | null> | undefined,
          namespace: input.namespace,
        });

        return `Vector stored successfully. ID: ${result.id}`;
      } catch (err) {
        const apiErr = err as AINativeAPIError;
        return `Error upserting vector: ${apiErr.message ?? String(err)}`;
      }
    },
  });
}
