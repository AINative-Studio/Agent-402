/**
 * Memory tools — barrel export
 * Built by AINative Dev Team
 * Refs #183
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { AINativeClient } from '../../client';
import { createRememberTool } from './remember';
import { createRecallTool } from './recall';
import { createForgetTool } from './forget';
import { createReflectTool } from './reflect';

export { createRememberTool } from './remember';
export { createRecallTool } from './recall';
export { createForgetTool } from './forget';
export { createReflectTool } from './reflect';

export function getMemoryTools(client: AINativeClient): DynamicStructuredTool[] {
  return [
    createRememberTool(client),
    createRecallTool(client),
    createForgetTool(client),
    createReflectTool(client),
  ];
}
