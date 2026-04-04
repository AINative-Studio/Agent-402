/**
 * Vector tools — barrel export
 * Built by AINative Dev Team
 * Refs #185
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { AINativeClient } from '../../client';
import { createVectorUpsertTool } from './upsert';
import { createVectorSearchTool } from './search';
import { createVectorDeleteTool } from './delete';

export { createVectorUpsertTool, VALID_DIMENSIONS } from './upsert';
export { createVectorSearchTool } from './search';
export { createVectorDeleteTool } from './delete';

export function getVectorTools(client: AINativeClient): DynamicStructuredTool[] {
  return [
    createVectorUpsertTool(client),
    createVectorSearchTool(client),
    createVectorDeleteTool(client),
  ];
}
