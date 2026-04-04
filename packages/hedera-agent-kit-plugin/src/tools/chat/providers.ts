/**
 * Provider routing configuration for AINative chat completions
 * Built by AINative Dev Team
 * Refs #184
 */

import { ChatProvider } from '../../types';

export const SUPPORTED_PROVIDERS: ChatProvider[] = [
  'anthropic',
  'openai',
  'meta',
  'google',
  'mistral',
  'nouscoder',
  'cohere',
];

export interface ProviderDefaults {
  model: string;
  maxTokens?: number;
}

export const PROVIDER_DEFAULTS: Record<ChatProvider, ProviderDefaults> = {
  anthropic: {
    model: 'claude-3-5-sonnet-20241022',
    maxTokens: 8192,
  },
  openai: {
    model: 'gpt-4o',
    maxTokens: 4096,
  },
  meta: {
    model: 'meta-llama/Llama-3.1-70B-Instruct',
    maxTokens: 4096,
  },
  google: {
    model: 'gemini-1.5-pro',
    maxTokens: 8192,
  },
  mistral: {
    model: 'mistral-large-latest',
    maxTokens: 4096,
  },
  nouscoder: {
    model: 'NousResearch/Nous-Hermes-2-Yi-34B',
    maxTokens: 4096,
  },
  cohere: {
    model: 'command-r-plus',
    maxTokens: 4096,
  },
};

export const DEFAULT_PROVIDER: ChatProvider = 'anthropic';
