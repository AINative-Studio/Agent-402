/**
 * ainative_vector_delete — Remove vector tool
 * Built by AINative Dev Team
 * Refs #185
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { AINativeClient } from '../../client';
import { AINativeAPIError } from '../../types';

const VectorDeleteSchema = z.object({
  id: z.string().describe('The ID of the vector to delete'),
  namespace: z
    .string()
    .optional()
    .describe('Namespace the vector belongs to (e.g., Hedera account ID)'),
});

export function createVectorDeleteTool(client: AINativeClient): DynamicStructuredTool {
  return new DynamicStructuredTool({
    name: 'ainative_vector_delete',
    description:
      'Remove a specific vector from AINative by its ID. Optionally specify a namespace to target the correct vector when using per-Hedera-account isolation.',
    schema: VectorDeleteSchema,
    func: async (input) => {
      try {
        const result = await client.vectorDelete({
          id: input.id,
          namespace: input.namespace,
        });

        if (result.success) {
          return `Vector ${result.id} deleted successfully.`;
        }
        return `Vector ${result.id} could not be removed. It may not exist.`;
      } catch (err) {
        const apiErr = err as AINativeAPIError;
        return `Error deleting vector: ${apiErr.message ?? String(err)}`;
      }
    },
  });
}
