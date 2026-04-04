/**
 * RED tests for HttpClient
 * Built by AINative Dev Team
 * Refs #178
 */

import { HttpClient } from '../src/client';
import { AINativeSDKError, AuthenticationError, NotFoundError, RateLimitError } from '../src/errors';

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch as unknown as typeof fetch;

describe('HttpClient', () => {
  const defaultConfig = { apiKey: 'test-key-abc123' };

  beforeEach(() => {
    mockFetch.mockReset();
  });

  describe('constructor', () => {
    it('should accept an apiKey for authentication', () => {
      const client = new HttpClient({ apiKey: 'my-api-key' });
      expect(client).toBeInstanceOf(HttpClient);
    });

    it('should accept a jwt for authentication', () => {
      const client = new HttpClient({ jwt: 'my.jwt.token' });
      expect(client).toBeInstanceOf(HttpClient);
    });

    it('should use default base URL when none provided', () => {
      const client = new HttpClient(defaultConfig);
      expect(client.baseUrl).toBe('https://api.ainative.studio/v1');
    });

    it('should use custom base URL when provided', () => {
      const client = new HttpClient({ ...defaultConfig, baseUrl: 'https://custom.api.com/v2' });
      expect(client.baseUrl).toBe('https://custom.api.com/v2');
    });

    it('should throw when neither apiKey nor jwt is provided', () => {
      expect(() => new HttpClient({})).toThrow('AINativeSDK requires either apiKey or jwt');
    });

    it('should use default timeout of 30000ms', () => {
      const client = new HttpClient(defaultConfig);
      expect(client.timeout).toBe(30000);
    });

    it('should accept custom timeout', () => {
      const client = new HttpClient({ ...defaultConfig, timeout: 5000 });
      expect(client.timeout).toBe(5000);
    });
  });

  describe('request', () => {
    it('should send GET request with correct headers when using apiKey', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: 'agent-1' }),
      });

      const client = new HttpClient({ apiKey: 'my-api-key' });
      await client.get('/agents');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.ainative.studio/v1/agents',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer my-api-key',
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('should send GET request with Authorization Bearer when using jwt', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      const client = new HttpClient({ jwt: 'my.jwt.token' });
      await client.get('/agents');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer my.jwt.token',
          }),
        })
      );
    });

    it('should send POST request with JSON body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({ id: 'agent-1' }),
      });

      const client = new HttpClient(defaultConfig);
      await client.post('/agents', { name: 'test-agent', role: 'assistant' });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.ainative.studio/v1/agents',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'test-agent', role: 'assistant' }),
        })
      );
    });

    it('should send PATCH request with partial body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: 'agent-1', name: 'updated-name' }),
      });

      const client = new HttpClient(defaultConfig);
      await client.patch('/agents/agent-1', { name: 'updated-name' });

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.ainative.studio/v1/agents/agent-1',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ name: 'updated-name' }),
        })
      );
    });

    it('should send DELETE request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: async () => ({}),
      });

      const client = new HttpClient(defaultConfig);
      await client.delete('/agents/agent-1');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.ainative.studio/v1/agents/agent-1',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('should return parsed JSON response', async () => {
      const responseData = { id: 'agent-1', name: 'Test Agent' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => responseData,
      });

      const client = new HttpClient(defaultConfig);
      const result = await client.get('/agents/agent-1');

      expect(result).toEqual(responseData);
    });
  });

  describe('error handling', () => {
    it('should throw AuthenticationError on 401 response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Unauthorized', code: 'AUTH_ERROR' }),
      });

      const client = new HttpClient(defaultConfig);
      await expect(client.get('/agents')).rejects.toThrow(AuthenticationError);
    });

    it('should throw NotFoundError on 404 response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ error: 'Not Found', code: 'NOT_FOUND' }),
      });

      const client = new HttpClient(defaultConfig);
      await expect(client.get('/agents/nonexistent')).rejects.toThrow(NotFoundError);
    });

    it('should throw RateLimitError on 429 response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        json: async () => ({ error: 'Too Many Requests', code: 'RATE_LIMITED' }),
      });

      const client = new HttpClient(defaultConfig);
      await expect(client.get('/agents')).rejects.toThrow(RateLimitError);
    });

    it('should throw AINativeSDKError on generic server errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal Server Error', code: 'SERVER_ERROR' }),
      });

      const client = new HttpClient(defaultConfig);
      await expect(client.get('/agents')).rejects.toThrow(AINativeSDKError);
    });

    it('should include HTTP status code in thrown error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ error: 'Validation Error', code: 'VALIDATION_ERROR' }),
      });

      const client = new HttpClient(defaultConfig);
      try {
        await client.get('/agents');
        fail('Expected error to be thrown');
      } catch (e) {
        expect(e).toBeInstanceOf(AINativeSDKError);
        expect((e as AINativeSDKError).status).toBe(422);
      }
    });

    it('should throw AINativeSDKError on network failure', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      const client = new HttpClient(defaultConfig);
      await expect(client.get('/agents')).rejects.toThrow(AINativeSDKError);
    });
  });
});
