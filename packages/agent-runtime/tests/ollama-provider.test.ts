/**
 * @ainative/agent-runtime — OllamaProvider tests
 * Built by AINative Dev Team
 * Refs #248
 *
 * RED phase: All tests written before implementation.
 */

import { OllamaProvider } from '../src/adapters/ollama-provider';

// ─── Mock fetch ───────────────────────────────────────────────────────────────

const mockFetch = jest.fn();
global.fetch = mockFetch;

function makeOllamaResponse(content: string, toolCalls: unknown[] = []) {
  return {
    model: 'llama3.2',
    message: {
      role: 'assistant',
      content,
      tool_calls: toolCalls,
    },
    done: true,
  };
}

function mockOllamaFetch(body: unknown) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => body,
  });
}

describe('OllamaProvider', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  // ─── Constructor ──────────────────────────────────────────────────────────

  describe('constructor', () => {
    it('creates provider with default baseUrl and model', () => {
      const provider = new OllamaProvider({});
      expect(provider.baseUrl).toBe('http://localhost:11434');
      expect(provider.model).toBe('llama3.2');
    });

    it('accepts custom baseUrl', () => {
      const provider = new OllamaProvider({ baseUrl: 'http://remote:11434' });
      expect(provider.baseUrl).toBe('http://remote:11434');
    });

    it('accepts custom model', () => {
      const provider = new OllamaProvider({ model: 'mistral' });
      expect(provider.model).toBe('mistral');
    });
  });

  // ─── chat() ───────────────────────────────────────────────────────────────

  describe('chat()', () => {
    it('calls /api/chat with messages array', async () => {
      mockOllamaFetch(makeOllamaResponse('Hello!'));
      const provider = new OllamaProvider({});
      await provider.chat([{ role: 'user', content: 'Hello' }]);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:11434/api/chat',
        expect.objectContaining({ method: 'POST' }),
      );
    });

    it('sends correct model in request body', async () => {
      mockOllamaFetch(makeOllamaResponse('Hi'));
      const provider = new OllamaProvider({ model: 'llama3.2' });
      await provider.chat([{ role: 'user', content: 'Hello' }]);

      const body = JSON.parse((mockFetch.mock.calls[0][1] as RequestInit).body as string);
      expect(body.model).toBe('llama3.2');
    });

    it('sets stream to false in request body', async () => {
      mockOllamaFetch(makeOllamaResponse('Hi'));
      const provider = new OllamaProvider({});
      await provider.chat([{ role: 'user', content: 'Hi' }]);

      const body = JSON.parse((mockFetch.mock.calls[0][1] as RequestInit).body as string);
      expect(body.stream).toBe(false);
    });

    it('returns content from Ollama response', async () => {
      mockOllamaFetch(makeOllamaResponse('The answer is 42.'));
      const provider = new OllamaProvider({});
      const result = await provider.chat([{ role: 'user', content: 'What is the answer?' }]);
      expect(result.content).toBe('The answer is 42.');
    });

    it('returns empty toolCalls array for plain text response', async () => {
      mockOllamaFetch(makeOllamaResponse('Just text.'));
      const provider = new OllamaProvider({});
      const result = await provider.chat([{ role: 'user', content: 'Hi' }]);
      expect(result.toolCalls).toEqual([]);
    });

    it('throws when Ollama returns non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500, text: async () => 'Internal Server Error' });
      const provider = new OllamaProvider({});
      await expect(provider.chat([{ role: 'user', content: 'Hi' }])).rejects.toThrow();
    });

    it('passes options.temperature to request body when provided', async () => {
      mockOllamaFetch(makeOllamaResponse('ok'));
      const provider = new OllamaProvider({});
      await provider.chat([{ role: 'user', content: 'hi' }], { temperature: 0.2 });

      const body = JSON.parse((mockFetch.mock.calls[0][1] as RequestInit).body as string);
      expect(body.options?.temperature).toBe(0.2);
    });
  });

  // ─── chatWithTools() ──────────────────────────────────────────────────────

  describe('chatWithTools()', () => {
    const tools = [
      {
        name: 'get_weather',
        description: 'Get current weather',
        parameters: {
          type: 'object',
          properties: { city: { type: 'string' } },
          required: ['city'],
        },
      },
    ];

    it('includes tools in the request body', async () => {
      mockOllamaFetch(makeOllamaResponse('Calling weather tool...', [
        { function: { name: 'get_weather', arguments: { city: 'Austin' } } },
      ]));
      const provider = new OllamaProvider({});
      await provider.chatWithTools([{ role: 'user', content: 'Weather in Austin?' }], tools);

      const body = JSON.parse((mockFetch.mock.calls[0][1] as RequestInit).body as string);
      expect(body.tools).toBeDefined();
      expect(body.tools[0].function.name).toBe('get_weather');
    });

    it('converts Ollama tool_calls to ToolCall format', async () => {
      mockOllamaFetch(makeOllamaResponse('', [
        { function: { name: 'get_weather', arguments: { city: 'Austin' } } },
      ]));
      const provider = new OllamaProvider({});
      const result = await provider.chatWithTools(
        [{ role: 'user', content: 'Weather?' }],
        tools,
      );
      expect(result.toolCalls).toHaveLength(1);
      expect(result.toolCalls[0].name).toBe('get_weather');
      expect(result.toolCalls[0].args).toEqual({ city: 'Austin' });
    });

    it('returns content and empty toolCalls when no tool is used', async () => {
      mockOllamaFetch(makeOllamaResponse('The weather is sunny.'));
      const provider = new OllamaProvider({});
      const result = await provider.chatWithTools(
        [{ role: 'user', content: 'How are you?' }],
        tools,
      );
      expect(result.content).toBe('The weather is sunny.');
      expect(result.toolCalls).toEqual([]);
    });

    it('passes options.temperature to request body in chatWithTools', async () => {
      mockOllamaFetch(makeOllamaResponse('ok'));
      const provider = new OllamaProvider({});
      await provider.chatWithTools(
        [{ role: 'user', content: 'hi' }],
        tools,
        { temperature: 0.5 },
      );
      const body = JSON.parse((mockFetch.mock.calls[0][1] as RequestInit).body as string);
      expect(body.options?.temperature).toBe(0.5);
    });

    it('throws when Ollama returns non-ok response in chatWithTools', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 503, text: async () => 'Service Unavailable' });
      const provider = new OllamaProvider({});
      await expect(provider.chatWithTools(
        [{ role: 'user', content: 'hi' }],
        tools,
      )).rejects.toThrow('503');
    });

    it('assigns a unique id to each tool call', async () => {
      mockOllamaFetch(makeOllamaResponse('', [
        { function: { name: 'get_weather', arguments: { city: 'Austin' } } },
        { function: { name: 'get_weather', arguments: { city: 'Dallas' } } },
      ]));
      const provider = new OllamaProvider({});
      const result = await provider.chatWithTools(
        [{ role: 'user', content: 'Weather in TX?' }],
        tools,
      );
      const ids = result.toolCalls.map((tc) => tc.id);
      expect(new Set(ids).size).toBe(ids.length);
    });
  });
});
