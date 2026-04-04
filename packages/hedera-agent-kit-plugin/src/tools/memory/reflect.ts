/**
 * ainative_reflect — Get entity context/summary tool
 * Built by AINative Dev Team
 * Refs #183
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { AINativeClient } from '../../client';
import { AINativeAPIError } from '../../types';

const ReflectSchema = z.object({
  agent_id: z
    .string()
    .describe('Agent ID to generate a contextual summary for'),
  topic: z
    .string()
    .optional()
    .describe('Optional topic to focus the summary on'),
});

export function createReflectTool(client: AINativeClient): DynamicStructuredTool {
  return new DynamicStructuredTool({
    name: 'ainative_reflect',
    description:
      'Generate a contextual summary of what the agent knows about an entity or topic. Returns a synthesized summary and key entities extracted from stored memories.',
    schema: ReflectSchema,
    func: async (input) => {
      try {
        const result = await client.reflect({
          agent_id: input.agent_id,
          topic: input.topic,
        });

        const entityList =
          result.entities.length > 0
            ? `\nKey entities: ${result.entities.join(', ')}`
            : '';

        return `Summary for ${result.agent_id}:\n${result.summary}${entityList}`;
      } catch (err) {
        const apiErr = err as AINativeAPIError;
        return `Error reflecting on memory: ${apiErr.message ?? String(err)}`;
      }
    },
  });
}
