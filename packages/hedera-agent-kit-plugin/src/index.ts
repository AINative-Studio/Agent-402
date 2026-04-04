/**
 * @ainative/hedera-agent-kit-plugin — Plugin entry point
 * Built by AINative Dev Team
 * Refs #183, #184, #185, #186
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { AINativeClient } from './client';
import { AINativePluginConfig } from './types';
import { getMemoryTools } from './tools/memory/index';
import { getChatTools } from './tools/chat/index';
import { getVectorTools } from './tools/vectors/index';

export { AINativeClient } from './client';
export { DEFAULT_BASE_URL } from './client';
export * from './types';
export { getMemoryTools } from './tools/memory/index';
export { getChatTools } from './tools/chat/index';
export { getVectorTools } from './tools/vectors/index';

/**
 * Returns all AINative tools as an array of LangChain DynamicStructuredTools.
 * Compatible with Hedera Agent Kit v3 plugin architecture.
 *
 * @param config - Plugin configuration with API key and optional baseUrl
 * @returns Array of 8 tools: 4 memory + 1 chat + 3 vector
 */
export function getAINativeTools(
  config: AINativePluginConfig,
): DynamicStructuredTool[] {
  const apiKey = config.apiKey?.trim() || process.env.AINATIVE_API_KEY?.trim() || '';

  const client = new AINativeClient(apiKey, config.baseUrl);

  return [
    ...getMemoryTools(client),
    ...getChatTools(client),
    ...getVectorTools(client),
  ];
}

/**
 * Alias for getAINativeTools — register all AINative tools with a Hedera agent.
 */
export function registerAINativeTools(
  config: AINativePluginConfig,
): DynamicStructuredTool[] {
  return getAINativeTools(config);
}
