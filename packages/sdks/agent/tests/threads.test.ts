/**
 * RED tests for SDK Thread Management — Issue #221.
 *
 * Tests ThreadsModule: create, get, list, delete, addMessage, resume, search.
 *
 * Built by AINative Dev Team
 * Refs #221
 */

import { ThreadsModule } from '../src/threads';
import { HttpClient } from '../src/client';

jest.mock('../src/client');

// ─── Helpers ────────────────────────────────────────────────────────────────

function makeThread(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'thread_abc123',
    agent_id: 'agent_xyz',
    title: 'Test Thread',
    status: 'active',
    metadata: {},
    created_at: '2026-01-01T00:00:00Z',
    messages: [],
    ...overrides,
  };
}

function makeMessage(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'msg_abc123',
    thread_id: 'thread_abc123',
    role: 'user',
    content: 'Hello!',
    metadata: {},
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeClient(): jest.Mocked<HttpClient> {
  return {
    baseUrl: 'https://api.ainative.studio/v1',
    timeout: 30000,
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  } as unknown as jest.Mocked<HttpClient>;
}

// ============================================================================
// describe ThreadsModule
// ============================================================================

describe('ThreadsModule', () => {
  let mockClient: jest.Mocked<HttpClient>;
  let module: ThreadsModule;

  beforeEach(() => {
    mockClient = makeClient();
    module = new ThreadsModule(mockClient);
  });

  // ─── create ───────────────────────────────────────────────────────────────

  describe('create', () => {
    it('should POST to the threads endpoint with agentId and title', async () => {
      const expected = makeThread();
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await module.create('agent_xyz', 'Test Thread');

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/threads',
        expect.objectContaining({ agent_id: 'agent_xyz', title: 'Test Thread' })
      );
      expect(result).toEqual(expected);
    });

    it('should include optional metadata when provided', async () => {
      mockClient.post.mockResolvedValueOnce(makeThread());
      await module.create('agent_1', 'T', { foo: 'bar' });

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/threads',
        expect.objectContaining({ metadata: { foo: 'bar' } })
      );
    });

    it('should return a thread object with an id', async () => {
      const expected = makeThread({ id: 'thread_newid' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await module.create('agent_2', 'New');

      expect(result).toHaveProperty('id', 'thread_newid');
    });
  });

  // ─── get ──────────────────────────────────────────────────────────────────

  describe('get', () => {
    it('should GET the thread by id', async () => {
      const expected = makeThread({ id: 'thread_456' });
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await module.get('thread_456');

      expect(mockClient.get).toHaveBeenCalledWith('/api/v1/threads/thread_456');
      expect(result).toEqual(expected);
    });

    it('should return a thread with messages array', async () => {
      const expected = makeThread({ messages: [makeMessage()] });
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await module.get('thread_789');

      expect(Array.isArray((result as any).messages)).toBe(true);
    });
  });

  // ─── list ─────────────────────────────────────────────────────────────────

  describe('list', () => {
    it('should GET threads for a given agentId', async () => {
      const expected = { threads: [makeThread()], total: 1 };
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await module.list('agent_xyz');

      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/threads')
      );
      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('agent_id=agent_xyz')
      );
      expect(result).toEqual(expected);
    });

    it('should return an object with threads array and total', async () => {
      mockClient.get.mockResolvedValueOnce({ threads: [], total: 0 });

      const result = await module.list('agent_empty') as any;

      expect(Array.isArray(result.threads)).toBe(true);
      expect(typeof result.total).toBe('number');
    });
  });

  // ─── delete ───────────────────────────────────────────────────────────────

  describe('delete', () => {
    it('should DELETE the thread by id', async () => {
      mockClient.delete.mockResolvedValueOnce(undefined);

      await module.delete('thread_del');

      expect(mockClient.delete).toHaveBeenCalledWith('/api/v1/threads/thread_del');
    });
  });

  // ─── addMessage ───────────────────────────────────────────────────────────

  describe('addMessage', () => {
    it('should POST a message to the thread messages endpoint', async () => {
      const expected = makeMessage({ role: 'user', content: 'Hi there' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await module.addMessage('thread_abc', 'user', 'Hi there');

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/threads/thread_abc/messages',
        expect.objectContaining({ role: 'user', content: 'Hi there' })
      );
      expect(result).toEqual(expected);
    });

    it('should include optional metadata when provided', async () => {
      mockClient.post.mockResolvedValueOnce(makeMessage());
      await module.addMessage('thread_abc', 'assistant', 'Reply', { source: 'llm' });

      expect(mockClient.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ metadata: { source: 'llm' } })
      );
    });

    it('should return a message with an id', async () => {
      const expected = makeMessage({ id: 'msg_newid' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await module.addMessage('thread_abc', 'user', 'Hello');

      expect(result).toHaveProperty('id', 'msg_newid');
    });
  });

  // ─── resume ───────────────────────────────────────────────────────────────

  describe('resume', () => {
    it('should GET the resume endpoint for the thread', async () => {
      const expected = { thread_id: 'thread_abc', messages: [makeMessage()] };
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await module.resume('thread_abc');

      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/threads/thread_abc/resume')
      );
      expect(result).toEqual(expected);
    });

    it('should pass context_window parameter when provided', async () => {
      mockClient.get.mockResolvedValueOnce({ thread_id: 'thread_abc', messages: [] });

      await module.resume('thread_abc', 5);

      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('context_window=5')
      );
    });

    it('should return an object with thread_id and messages', async () => {
      mockClient.get.mockResolvedValueOnce({ thread_id: 'thread_abc', messages: [] });

      const result = await module.resume('thread_abc') as any;

      expect(result).toHaveProperty('thread_id');
      expect(Array.isArray(result.messages)).toBe(true);
    });
  });

  // ─── search ───────────────────────────────────────────────────────────────

  describe('search', () => {
    it('should GET the threads search endpoint with the query', async () => {
      const expected = [makeThread({ title: 'Payment chat' })];
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await module.search('payment', 'agent_xyz');

      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/threads/search')
      );
      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('query=payment')
      );
      expect(result).toEqual(expected);
    });

    it('should include agent_id in the search request', async () => {
      mockClient.get.mockResolvedValueOnce([]);

      await module.search('hello', 'agent_123');

      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('agent_id=agent_123')
      );
    });

    it('should pass limit parameter when provided', async () => {
      mockClient.get.mockResolvedValueOnce([]);

      await module.search('query', 'agent_1', 5);

      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('limit=5')
      );
    });

    it('should return an array of thread objects', async () => {
      mockClient.get.mockResolvedValueOnce([makeThread(), makeThread()]);

      const result = await module.search('x', 'agent_2') as any[];

      expect(Array.isArray(result)).toBe(true);
    });
  });
});
