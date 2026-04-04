/**
 * Chat tools — barrel export
 * Built by AINative Dev Team
 * Refs #184
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { AINativeClient } from '../../client';
import { createChatCompletionTool } from './completion';

export { createChatCompletionTool } from './completion';
export { PROVIDER_DEFAULTS, SUPPORTED_PROVIDERS, DEFAULT_PROVIDER } from './providers';

export function getChatTools(client: AINativeClient): DynamicStructuredTool[] {
  return [createChatCompletionTool(client)];
}
