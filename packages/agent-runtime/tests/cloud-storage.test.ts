/**
 * @ainative/agent-runtime — CloudStorageAdapter tests
 * Built by AINative Dev Team
 * Refs #246
 *
 * RED phase: Written before implementation run.
 */

import { CloudStorageAdapter } from '../src/adapters/cloud-storage';

// ─── Mock SDK client ──────────────────────────────────────────────────────────

function makeMockClient() {
  return {
    memory: {
      remember: jest.fn().mockResolvedValue({ id: 'cloud-mem-1' }),
      recall: jest.fn().mockResolvedValue({
        memories: [
          {
            id: 'cloud-mem-1',
            content: 'Cloud memory',
            metadata: { tag: 'cloud' },
            score: 0.95,
            createdAt: new Date().toISOString(),
          },
        ],
      }),
    },
  };
}

describe('CloudStorageAdapter', () => {
  // ─── storeMemory ──────────────────────────────────────────────────────────

  describe('storeMemory()', () => {
    it('delegates to sdk.memory.remember and returns the id', async () => {
      const client = makeMockClient();
      const adapter = new CloudStorageAdapter({ client });
      const result = await adapter.storeMemory('test content', { key: 'val' });
      expect(result.id).toBe('cloud-mem-1');
      expect(client.memory.remember).toHaveBeenCalledWith(
        'test content',
        expect.objectContaining({ namespace: 'default', metadata: { key: 'val' } }),
      );
    });

    it('uses the configured namespace', async () => {
      const client = makeMockClient();
      const adapter = new CloudStorageAdapter({ client, namespace: 'my-ns' });
      await adapter.storeMemory('hello', {});
      expect(client.memory.remember).toHaveBeenCalledWith(
        'hello',
        expect.objectContaining({ namespace: 'my-ns' }),
      );
    });
  });

  // ─── recallMemory ─────────────────────────────────────────────────────────

  describe('recallMemory()', () => {
    it('calls sdk.memory.recall with correct query and topK', async () => {
      const client = makeMockClient();
      const adapter = new CloudStorageAdapter({ client });
      await adapter.recallMemory('search query', 5);
      expect(client.memory.recall).toHaveBeenCalledWith(
        'search query',
        expect.objectContaining({ topK: 5 }),
      );
    });

    it('maps SDK result to MemoryEntry array', async () => {
      const client = makeMockClient();
      const adapter = new CloudStorageAdapter({ client });
      const results = await adapter.recallMemory('query', 10);
      expect(results).toHaveLength(1);
      expect(results[0].id).toBe('cloud-mem-1');
      expect(results[0].content).toBe('Cloud memory');
      expect(results[0].score).toBe(0.95);
    });

    it('defaults missing score to 0', async () => {
      const client = makeMockClient();
      client.memory.recall.mockResolvedValueOnce({
        memories: [
          { id: 'm-2', content: 'No score', metadata: {}, createdAt: new Date().toISOString() },
        ],
      });
      const adapter = new CloudStorageAdapter({ client });
      const results = await adapter.recallMemory('query', 1);
      expect(results[0].score).toBe(0);
    });
  });

  // ─── storeRecord ──────────────────────────────────────────────────────────

  describe('storeRecord()', () => {
    it('returns a generated id', async () => {
      const client = makeMockClient();
      const adapter = new CloudStorageAdapter({ client });
      const result = await adapter.storeRecord('agents', { name: 'Bot' });
      expect(result.id).toBeDefined();
      expect(typeof result.id).toBe('string');
    });

    it('assigns unique ids to separate records', async () => {
      const client = makeMockClient();
      const adapter = new CloudStorageAdapter({ client });
      const r1 = await adapter.storeRecord('tasks', { a: 1 });
      const r2 = await adapter.storeRecord('tasks', { a: 2 });
      expect(r1.id).not.toBe(r2.id);
    });
  });

  // ─── queryRecords ─────────────────────────────────────────────────────────

  describe('queryRecords()', () => {
    it('returns empty array for unknown table', async () => {
      const client = makeMockClient();
      const adapter = new CloudStorageAdapter({ client });
      const results = await adapter.queryRecords('nonexistent', {});
      expect(results).toEqual([]);
    });

    it('returns all records when filter is empty', async () => {
      const client = makeMockClient();
      const adapter = new CloudStorageAdapter({ client });
      await adapter.storeRecord('logs', { msg: 'a' });
      await adapter.storeRecord('logs', { msg: 'b' });
      const results = await adapter.queryRecords('logs', {});
      expect(results).toHaveLength(2);
    });

    it('filters by matching field', async () => {
      const client = makeMockClient();
      const adapter = new CloudStorageAdapter({ client });
      await adapter.storeRecord('users', { role: 'admin', name: 'Alice' });
      await adapter.storeRecord('users', { role: 'viewer', name: 'Bob' });
      const results = await adapter.queryRecords('users', { role: 'admin' });
      expect(results).toHaveLength(1);
    });
  });
});
