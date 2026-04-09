/**
 * @ainative/agent-runtime — LocalStorageAdapter tests
 * Built by AINative Dev Team
 * Refs #247
 *
 * RED phase: All tests written before implementation.
 */

import { LocalStorageAdapter } from '../src/adapters/local-storage';

describe('LocalStorageAdapter', () => {
  let adapter: LocalStorageAdapter;

  beforeEach(() => {
    adapter = new LocalStorageAdapter({ dbPath: ':memory:' });
  });

  afterEach(async () => {
    await adapter.close();
  });

  // ─── storeMemory ──────────────────────────────────────────────────────────

  describe('storeMemory()', () => {
    it('stores a memory entry and returns an id', async () => {
      const result = await adapter.storeMemory('The sky is blue', { source: 'test' });
      expect(result.id).toBeDefined();
      expect(typeof result.id).toBe('string');
    });

    it('stores memory with content preserved', async () => {
      await adapter.storeMemory('Important fact about cats', {});
      const recalled = await adapter.recallMemory('cats', 1);
      expect(recalled[0].content).toBe('Important fact about cats');
    });

    it('stores metadata alongside content', async () => {
      await adapter.storeMemory('Memory with metadata', { tag: 'test', priority: 1 });
      const recalled = await adapter.recallMemory('metadata', 1);
      expect(recalled[0].metadata).toMatchObject({ tag: 'test', priority: 1 });
    });

    it('assigns a createdAt timestamp to each memory', async () => {
      const result = await adapter.storeMemory('Timestamped memory', {});
      expect(result.id).toBeDefined();
      const recalled = await adapter.recallMemory('Timestamped', 1);
      expect(recalled[0].createdAt).toBeDefined();
    });

    it('stores multiple memories independently', async () => {
      await adapter.storeMemory('Memory one about dogs', {});
      await adapter.storeMemory('Memory two about cats', {});
      const dogs = await adapter.recallMemory('dogs', 1);
      const cats = await adapter.recallMemory('cats', 1);
      expect(dogs[0].content).toBe('Memory one about dogs');
      expect(cats[0].content).toBe('Memory two about cats');
    });
  });

  // ─── recallMemory ─────────────────────────────────────────────────────────

  describe('recallMemory()', () => {
    it('returns empty array when no memories exist', async () => {
      const results = await adapter.recallMemory('anything', 5);
      expect(results).toEqual([]);
    });

    it('returns at most `limit` results', async () => {
      await adapter.storeMemory('Alpha memory', {});
      await adapter.storeMemory('Beta memory', {});
      await adapter.storeMemory('Gamma memory', {});

      const results = await adapter.recallMemory('memory', 2);
      expect(results.length).toBeLessThanOrEqual(2);
    });

    it('returns memories sorted by similarity score descending', async () => {
      await adapter.storeMemory('The quick brown fox', {});
      await adapter.storeMemory('A totally unrelated sentence about chairs', {});
      await adapter.storeMemory('The fox jumped quickly', {});

      const results = await adapter.recallMemory('fox quick', 3);
      expect(results.length).toBeGreaterThan(0);
      // Scores should be descending
      for (let i = 1; i < results.length; i++) {
        expect(results[i - 1].score).toBeGreaterThanOrEqual(results[i].score);
      }
    });

    it('each recalled result has id, content, metadata, score, createdAt', async () => {
      await adapter.storeMemory('Complete memory entry', { key: 'value' });
      const results = await adapter.recallMemory('complete', 1);
      const mem = results[0];
      expect(mem).toHaveProperty('id');
      expect(mem).toHaveProperty('content');
      expect(mem).toHaveProperty('metadata');
      expect(mem).toHaveProperty('score');
      expect(mem).toHaveProperty('createdAt');
    });
  });

  // ─── storeRecord ──────────────────────────────────────────────────────────

  describe('storeRecord()', () => {
    it('stores a record and returns an id', async () => {
      const result = await adapter.storeRecord('agents', { name: 'Agent-1', role: 'researcher' });
      expect(result.id).toBeDefined();
    });

    it('assigns a unique id to each record', async () => {
      const r1 = await adapter.storeRecord('tasks', { desc: 'Task A' });
      const r2 = await adapter.storeRecord('tasks', { desc: 'Task B' });
      expect(r1.id).not.toBe(r2.id);
    });

    it('stores records in different tables independently', async () => {
      await adapter.storeRecord('table_a', { val: 1 });
      await adapter.storeRecord('table_b', { val: 2 });
      const a = await adapter.queryRecords('table_a', {});
      const b = await adapter.queryRecords('table_b', {});
      expect(a).toHaveLength(1);
      expect(b).toHaveLength(1);
    });

    it('adds a createdAt and updatedAt to each record', async () => {
      await adapter.storeRecord('logs', { msg: 'hello' });
      const records = await adapter.queryRecords('logs', {});
      expect(records[0]).toHaveProperty('createdAt');
      expect(records[0]).toHaveProperty('updatedAt');
    });
  });

  // ─── queryRecords ─────────────────────────────────────────────────────────

  describe('queryRecords()', () => {
    it('returns all records when filter is empty', async () => {
      await adapter.storeRecord('items', { name: 'alpha' });
      await adapter.storeRecord('items', { name: 'beta' });
      const results = await adapter.queryRecords('items', {});
      expect(results).toHaveLength(2);
    });

    it('returns empty array for unknown table', async () => {
      const results = await adapter.queryRecords('nonexistent', {});
      expect(results).toEqual([]);
    });

    it('filters by a single field', async () => {
      await adapter.storeRecord('users', { role: 'admin', name: 'Alice' });
      await adapter.storeRecord('users', { role: 'viewer', name: 'Bob' });
      const results = await adapter.queryRecords('users', { role: 'admin' });
      expect(results).toHaveLength(1);
      expect(results[0].data).toMatchObject({ role: 'admin', name: 'Alice' });
    });

    it('filters by multiple fields', async () => {
      await adapter.storeRecord('orders', { status: 'open', priority: 'high' });
      await adapter.storeRecord('orders', { status: 'open', priority: 'low' });
      await adapter.storeRecord('orders', { status: 'closed', priority: 'high' });
      const results = await adapter.queryRecords('orders', { status: 'open', priority: 'high' });
      expect(results).toHaveLength(1);
    });

    it('returns the stored data inside each result', async () => {
      await adapter.storeRecord('events', { type: 'login', userId: 'u-1' });
      const results = await adapter.queryRecords('events', {});
      expect(results[0].data).toMatchObject({ type: 'login', userId: 'u-1' });
    });
  });

  // ─── Sync Queue ───────────────────────────────────────────────────────────

  describe('sync queue', () => {
    it('getUnsyncedCount() returns 0 when fresh', async () => {
      const count = await adapter.getUnsyncedCount();
      expect(count).toBe(0);
    });

    it('getUnsyncedCount() increments after storeMemory', async () => {
      await adapter.storeMemory('unsynced memory', {});
      const count = await adapter.getUnsyncedCount();
      expect(count).toBe(1);
    });

    it('getUnsyncedCount() increments after storeRecord', async () => {
      await adapter.storeRecord('table', { x: 1 });
      const count = await adapter.getUnsyncedCount();
      expect(count).toBe(1);
    });

    it('markSynced() reduces the unsynced count', async () => {
      const result = await adapter.storeMemory('to sync', {});
      await adapter.markSynced([result.id]);
      const count = await adapter.getUnsyncedCount();
      expect(count).toBe(0);
    });

    it('getPendingChanges() returns records not yet synced', async () => {
      await adapter.storeMemory('pending memory', {});
      await adapter.storeRecord('pending_table', { data: 'pending' });
      const pending = await adapter.getPendingChanges();
      expect(pending.length).toBe(2);
    });
  });
});
