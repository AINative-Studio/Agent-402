/**
 * Chat completion tool tests — RED phase first
 * Built by AINative Dev Team
 * Refs #184
 */

import { AINativeClient } from '../src/client';
import { createChatCompletionTool } from '../src/tools/chat/completion';
import { PROVIDER_DEFAULTS, SUPPORTED_PROVIDERS } from '../src/tools/chat/providers';
import { getChatTools } from '../src/tools/chat/index';
import { ChatResult } from '../src/types';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeMockClient(): jest.Mocked<AINativeClient> {
  return {
    remember: jest.fn(),
    recall: jest.fn(),
    forget: jest.fn(),
    reflect: jest.fn(),
    chatCompletion: jest.fn(),
    vectorUpsert: jest.fn(),
    vectorSearch: jest.fn(),
    vectorDelete: jest.fn(),
  } as unknown as jest.Mocked<AINativeClient>;
}

function makeFakeChatResult(overrides?: Partial<ChatResult>): ChatResult {
  return {
    id: 'chat-001',
    provider: 'anthropic',
    model: 'claude-3-5-sonnet-20241022',
    content: 'Hello! How can I help you?',
    finish_reason: 'stop',
    usage: { prompt_tokens: 10, completion_tokens: 15, total_tokens: 25 },
    ...overrides,
  };
}

// ─── PROVIDER_DEFAULTS ────────────────────────────────────────────────────────

describe('PROVIDER_DEFAULTS', () => {
  it('includes default model for anthropic', () => {
    expect(PROVIDER_DEFAULTS.anthropic).toBeDefined();
    expect(PROVIDER_DEFAULTS.anthropic.model).toBeTruthy();
  });

  it('includes default model for openai', () => {
    expect(PROVIDER_DEFAULTS.openai).toBeDefined();
    expect(PROVIDER_DEFAULTS.openai.model).toBeTruthy();
  });

  it('includes default model for meta', () => {
    expect(PROVIDER_DEFAULTS.meta).toBeDefined();
    expect(PROVIDER_DEFAULTS.meta.model).toBeTruthy();
  });

  it('includes default model for google', () => {
    expect(PROVIDER_DEFAULTS.google).toBeDefined();
    expect(PROVIDER_DEFAULTS.google.model).toBeTruthy();
  });

  it('includes default model for mistral', () => {
    expect(PROVIDER_DEFAULTS.mistral).toBeDefined();
    expect(PROVIDER_DEFAULTS.mistral.model).toBeTruthy();
  });

  it('includes default model for nouscoder', () => {
    expect(PROVIDER_DEFAULTS.nouscoder).toBeDefined();
    expect(PROVIDER_DEFAULTS.nouscoder.model).toBeTruthy();
  });

  it('includes default model for cohere', () => {
    expect(PROVIDER_DEFAULTS.cohere).toBeDefined();
    expect(PROVIDER_DEFAULTS.cohere.model).toBeTruthy();
  });
});

describe('SUPPORTED_PROVIDERS', () => {
  it('contains all seven providers', () => {
    expect(SUPPORTED_PROVIDERS).toHaveLength(7);
  });

  it('includes anthropic', () => {
    expect(SUPPORTED_PROVIDERS).toContain('anthropic');
  });

  it('includes openai', () => {
    expect(SUPPORTED_PROVIDERS).toContain('openai');
  });

  it('includes meta', () => {
    expect(SUPPORTED_PROVIDERS).toContain('meta');
  });

  it('includes google', () => {
    expect(SUPPORTED_PROVIDERS).toContain('google');
  });

  it('includes mistral', () => {
    expect(SUPPORTED_PROVIDERS).toContain('mistral');
  });

  it('includes nouscoder', () => {
    expect(SUPPORTED_PROVIDERS).toContain('nouscoder');
  });

  it('includes cohere', () => {
    expect(SUPPORTED_PROVIDERS).toContain('cohere');
  });
});

// ─── createChatCompletionTool ─────────────────────────────────────────────────

describe('createChatCompletionTool', () => {
  it('returns a tool with the correct name', () => {
    const client = makeMockClient();
    const tool = createChatCompletionTool(client);
    expect(tool.name).toBe('ainative_chat');
  });

  it('returns a tool with a non-empty description', () => {
    const client = makeMockClient();
    const tool = createChatCompletionTool(client);
    expect(tool.description.length).toBeGreaterThan(10);
  });

  it('calls client.chatCompletion with messages', async () => {
    const client = makeMockClient();
    client.chatCompletion.mockResolvedValueOnce(makeFakeChatResult());

    const tool = createChatCompletionTool(client);
    await tool.invoke({
      messages: [{ role: 'user', content: 'Hello' }],
    });

    expect(client.chatCompletion).toHaveBeenCalledWith(
      expect.objectContaining({
        messages: [{ role: 'user', content: 'Hello' }],
      }),
    );
  });

  it('routes to specified provider when provided', async () => {
    const client = makeMockClient();
    client.chatCompletion.mockResolvedValueOnce(
      makeFakeChatResult({ provider: 'openai', model: 'gpt-4o' }),
    );

    const tool = createChatCompletionTool(client);
    await tool.invoke({
      messages: [{ role: 'user', content: 'Test' }],
      provider: 'openai',
    });

    expect(client.chatCompletion).toHaveBeenCalledWith(
      expect.objectContaining({ provider: 'openai' }),
    );
  });

  it('uses anthropic as default provider when none is specified', async () => {
    const client = makeMockClient();
    client.chatCompletion.mockResolvedValueOnce(makeFakeChatResult());

    const tool = createChatCompletionTool(client);
    await tool.invoke({
      messages: [{ role: 'user', content: 'Hello' }],
    });

    expect(client.chatCompletion).toHaveBeenCalledWith(
      expect.objectContaining({ provider: 'anthropic' }),
    );
  });

  it('passes temperature to client when provided', async () => {
    const client = makeMockClient();
    client.chatCompletion.mockResolvedValueOnce(makeFakeChatResult());

    const tool = createChatCompletionTool(client);
    await tool.invoke({
      messages: [{ role: 'user', content: 'Hi' }],
      temperature: 0.7,
    });

    expect(client.chatCompletion).toHaveBeenCalledWith(
      expect.objectContaining({ temperature: 0.7 }),
    );
  });

  it('passes max_tokens to client when provided', async () => {
    const client = makeMockClient();
    client.chatCompletion.mockResolvedValueOnce(makeFakeChatResult());

    const tool = createChatCompletionTool(client);
    await tool.invoke({
      messages: [{ role: 'user', content: 'Hi' }],
      max_tokens: 512,
    });

    expect(client.chatCompletion).toHaveBeenCalledWith(
      expect.objectContaining({ max_tokens: 512 }),
    );
  });

  it('returns the assistant content from the response', async () => {
    const client = makeMockClient();
    client.chatCompletion.mockResolvedValueOnce(
      makeFakeChatResult({ content: 'Paris is the capital of France.' }),
    );

    const tool = createChatCompletionTool(client);
    const result = await tool.invoke({
      messages: [{ role: 'user', content: 'What is the capital of France?' }],
    });

    expect(result).toContain('Paris is the capital of France.');
  });

  it('returns an error string when client.chatCompletion throws', async () => {
    const client = makeMockClient();
    client.chatCompletion.mockRejectedValueOnce({ status: 429, message: 'Rate limited' });

    const tool = createChatCompletionTool(client);
    const result = await tool.invoke({
      messages: [{ role: 'user', content: 'Hello' }],
    });

    expect(result).toContain('Error');
  });

  it('includes provider and model info in the result', async () => {
    const client = makeMockClient();
    client.chatCompletion.mockResolvedValueOnce(
      makeFakeChatResult({ provider: 'google', model: 'gemini-1.5-pro' }),
    );

    const tool = createChatCompletionTool(client);
    const result = await tool.invoke({
      messages: [{ role: 'user', content: 'Hi' }],
      provider: 'google',
    });

    expect(result).toContain('gemini-1.5-pro');
  });
});

// ─── getChatTools ─────────────────────────────────────────────────────────────

describe('getChatTools', () => {
  it('returns an array of one tool', () => {
    const client = makeMockClient();
    const tools = getChatTools(client);
    expect(tools).toHaveLength(1);
  });

  it('includes ainative_chat', () => {
    const client = makeMockClient();
    const tools = getChatTools(client);
    expect(tools[0].name).toBe('ainative_chat');
  });
});
