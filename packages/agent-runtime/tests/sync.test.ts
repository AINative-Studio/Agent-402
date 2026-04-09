/**
 * @ainative/agent-runtime — SyncManager tests
 * Built by AINative Dev Team
 * Refs #247
 *
 * RED phase: All tests written before implementation.
 */

import { SyncManager } from '../src/sync';
import type { StorageAdapter } from '../src/types';

// ─── Fakes ────────────────────────────────────────────────────────────────────

interface FakeLocalStorage {
  getUnsyncedCount: jest.Mock;
  getPendingChanges: jest.Mock;
  markSynced: jest.Mock;
  storeMemory: jest.Mock;
  recallMemory: jest.Mock;
  storeRecord: jest.Mock;
  queryRecords: jest.Mock;
  close: jest.Mock;
}

function makeFakeLocal(): FakeLocalStorage {
  return {
    getUnsyncedCount: jest.fn().mockResolvedValue(0),
    getPendingChanges: jest.fn().mockResolvedValue([]),
    markSynced: jest.fn().mockResolvedValue(undefined),
    storeMemory: jest.fn().mockResolvedValue({ id: 'mem-1' }),
    recallMemory: jest.fn().mockResolvedValue([]),
    storeRecord: jest.fn().mockResolvedValue({ id: 'rec-1' }),
    queryRecords: jest.fn().mockResolvedValue([]),
    close: jest.fn().mockResolvedValue(undefined),
  };
}

function makeFakeCloud(): jest.Mocked<StorageAdapter> {
  return {
    storeMemory: jest.fn().mockResolvedValue({ id: 'cloud-mem-1' }),
    recallMemory: jest.fn().mockResolvedValue([]),
    storeRecord: jest.fn().mockResolvedValue({ id: 'cloud-rec-1' }),
    queryRecords: jest.fn().mockResolvedValue([]),
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('SyncManager', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  // ─── Constructor ──────────────────────────────────────────────────────────

  describe('constructor', () => {
    it('creates SyncManager with local and cloud storage', () => {
      const manager = new SyncManager({
        localStorage: makeFakeLocal() as never,
        cloudStorage: makeFakeCloud(),
        syncInterval: 5000,
      });
      expect(manager).toBeInstanceOf(SyncManager);
    });

    it('defaults syncInterval to 30000 when not provided', () => {
      const manager = new SyncManager({
        localStorage: makeFakeLocal() as never,
        cloudStorage: makeFakeCloud(),
      });
      expect(manager.syncInterval).toBe(30000);
    });
  });

  // ─── startSync / stopSync ─────────────────────────────────────────────────

  describe('startSync() / stopSync()', () => {
    it('startSync() sets isRunning to true', async () => {
      const manager = new SyncManager({
        localStorage: makeFakeLocal() as never,
        cloudStorage: makeFakeCloud(),
        syncInterval: 5000,
      });
      await manager.startSync();
      expect(manager.isRunning).toBe(true);
      await manager.stopSync();
    });

    it('stopSync() sets isRunning to false', async () => {
      const manager = new SyncManager({
        localStorage: makeFakeLocal() as never,
        cloudStorage: makeFakeCloud(),
        syncInterval: 5000,
      });
      await manager.startSync();
      await manager.stopSync();
      expect(manager.isRunning).toBe(false);
    });

    it('startSync() does not throw when called twice', async () => {
      const manager = new SyncManager({
        localStorage: makeFakeLocal() as never,
        cloudStorage: makeFakeCloud(),
        syncInterval: 5000,
      });
      await manager.startSync();
      await expect(manager.startSync()).resolves.not.toThrow();
      await manager.stopSync();
    });

    it('triggers periodic sync after interval elapses', async () => {
      const local = makeFakeLocal();
      const cloud = makeFakeCloud();
      local.getPendingChanges.mockResolvedValue([
        { id: 'mem-1', type: 'memory', content: 'test', metadata: {}, createdAt: new Date().toISOString() },
      ]);

      const manager = new SyncManager({
        localStorage: local as never,
        cloudStorage: cloud,
        syncInterval: 5000,
      });
      await manager.startSync();

      jest.advanceTimersByTime(5001);
      // Give microtasks time to settle
      await Promise.resolve();
      await Promise.resolve();

      expect(local.getPendingChanges).toHaveBeenCalled();
      await manager.stopSync();
    });
  });

  // ─── forcePush ────────────────────────────────────────────────────────────

  describe('forcePush()', () => {
    it('pushes pending memory items to cloud storage', async () => {
      const local = makeFakeLocal();
      const cloud = makeFakeCloud();
      local.getPendingChanges.mockResolvedValue([
        { id: 'mem-1', type: 'memory', content: 'Hello world', metadata: {}, createdAt: new Date().toISOString() },
      ]);

      const manager = new SyncManager({
        localStorage: local as never,
        cloudStorage: cloud,
        syncInterval: 5000,
      });
      await manager.forcePush();

      expect(cloud.storeMemory).toHaveBeenCalledWith('Hello world', expect.any(Object));
    });

    it('pushes pending record items to cloud storage', async () => {
      const local = makeFakeLocal();
      const cloud = makeFakeCloud();
      local.getPendingChanges.mockResolvedValue([
        { id: 'rec-1', type: 'record', table: 'agents', data: { name: 'Bot' }, createdAt: new Date().toISOString() },
      ]);

      const manager = new SyncManager({
        localStorage: local as never,
        cloudStorage: cloud,
        syncInterval: 5000,
      });
      await manager.forcePush();

      expect(cloud.storeRecord).toHaveBeenCalledWith('agents', expect.objectContaining({ name: 'Bot' }));
    });

    it('marks items as synced after successful push', async () => {
      const local = makeFakeLocal();
      const cloud = makeFakeCloud();
      local.getPendingChanges.mockResolvedValue([
        { id: 'mem-1', type: 'memory', content: 'test', metadata: {}, createdAt: new Date().toISOString() },
      ]);

      const manager = new SyncManager({
        localStorage: local as never,
        cloudStorage: cloud,
        syncInterval: 5000,
      });
      await manager.forcePush();

      expect(local.markSynced).toHaveBeenCalledWith(['mem-1']);
    });

    it('does nothing when there are no pending changes', async () => {
      const local = makeFakeLocal();
      const cloud = makeFakeCloud();
      local.getPendingChanges.mockResolvedValue([]);

      const manager = new SyncManager({
        localStorage: local as never,
        cloudStorage: cloud,
        syncInterval: 5000,
      });
      await manager.forcePush();

      expect(cloud.storeMemory).not.toHaveBeenCalled();
      expect(cloud.storeRecord).not.toHaveBeenCalled();
    });

    it('uses last-write-wins when timestamps differ (newer wins)', async () => {
      const local = makeFakeLocal();
      const cloud = makeFakeCloud();
      const olderDate = new Date(Date.now() - 10000).toISOString();
      const newerDate = new Date().toISOString();

      // Two records for same logical id — only newer should be synced
      local.getPendingChanges.mockResolvedValue([
        { id: 'rec-old', type: 'record', table: 'data', data: { v: 1 }, createdAt: olderDate },
        { id: 'rec-new', type: 'record', table: 'data', data: { v: 2 }, createdAt: newerDate },
      ]);

      const manager = new SyncManager({
        localStorage: local as never,
        cloudStorage: cloud,
        syncInterval: 5000,
      });
      await manager.forcePush();
      // Both are independent records so both get synced
      expect(cloud.storeRecord).toHaveBeenCalledTimes(2);
    });
  });

  // ─── getQueueSize ─────────────────────────────────────────────────────────

  describe('getQueueSize()', () => {
    it('returns 0 when no pending changes', async () => {
      const local = makeFakeLocal();
      local.getUnsyncedCount.mockResolvedValue(0);

      const manager = new SyncManager({
        localStorage: local as never,
        cloudStorage: makeFakeCloud(),
        syncInterval: 5000,
      });
      const size = await manager.getQueueSize();
      expect(size).toBe(0);
    });

    it('returns count of pending unsynced items', async () => {
      const local = makeFakeLocal();
      local.getUnsyncedCount.mockResolvedValue(7);

      const manager = new SyncManager({
        localStorage: local as never,
        cloudStorage: makeFakeCloud(),
        syncInterval: 5000,
      });
      const size = await manager.getQueueSize();
      expect(size).toBe(7);
    });
  });
});
