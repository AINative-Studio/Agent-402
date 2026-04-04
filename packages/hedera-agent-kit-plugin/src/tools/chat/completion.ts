/**
 * ainative_chat — Chat completion tool
 * Built by AINative Dev Team
 * Refs #184
 */

import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { AINativeClient } from '../../client';
import { AINativeAPIError, ChatProvider } from '../../types';
import { DEFAULT_PROVIDER, PROVIDER_DEFAULTS, SUPPORTED_PROVIDERS } from './providers';

const ChatMessageSchema = z.object({
  role: z.enum(['system', 'user', 'assistant']).describe('Role of the message sender'),
  content: z.string().describe('Content of the message'),
});

const ChatCompletionSchema = z.object({
  messages: z
    .array(ChatMessageSchema)
    .min(1)
    .describe('Conversation messages to send to the LLM'),
  provider: z
    .enum(SUPPORTED_PROVIDERS as [ChatProvider, ...ChatProvider[]])
    .optional()
    .describe('LLM provider to use (anthropic, openai, meta, google, mistral, nouscoder, cohere)'),
  model: z.string().optional().describe('Specific model override for the chosen provider'),
  temperature: z
    .number()
    .min(0)
    .max(2)
    .optional()
    .describe('Sampling temperature (0-2)'),
  max_tokens: z
    .number()
    .int()
    .positive()
    .optional()
    .describe('Maximum tokens in the response'),
  stream: z.boolean().optional().describe('Enable streaming (SSE)'),
});

export function createChatCompletionTool(client: AINativeClient): DynamicStructuredTool {
  return new DynamicStructuredTool({
    name: 'ainative_chat',
    description:
      'Send a chat completion request to any of 7 LLM providers via AINative: Anthropic (Claude), OpenAI (GPT), Meta (Llama), Google (Gemini), Mistral, NousCoder, or Cohere. Returns the assistant response.',
    schema: ChatCompletionSchema,
    func: async (input) => {
      try {
        const provider = input.provider ?? DEFAULT_PROVIDER;
        const providerDefaults = PROVIDER_DEFAULTS[provider];
        const model = input.model ?? providerDefaults.model;

        const result = await client.chatCompletion({
          messages: input.messages,
          provider,
          model,
          temperature: input.temperature,
          max_tokens: input.max_tokens,
          stream: input.stream,
        });

        return `[${result.provider}/${result.model}] ${result.content}`;
      } catch (err) {
        const apiErr = err as AINativeAPIError;
        return `Error completing chat: ${apiErr.message ?? String(err)}`;
      }
    },
  });
}
