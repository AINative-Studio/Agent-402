/**
 * @ainative/agent-runtime — SyncManager
 * Built by AINative Dev Team
 * Refs #247
 *
 * Periodically pushes local changes to cloud storage.
 * Conflict resolution: last-write-wins by createdAt timestamp.
 */

import type { StorageAdapter, SyncChange } from './types';
import type { LocalStorageAdapter } from './adapters/local-storage';

// ─── Config ───────────────────────────────────────────────────────────────────

export interface SyncManagerConfig {
  localStorage: LocalStorageAdapter;
  cloudStorage: StorageAdapter;
  /** Interval in ms between automatic syncs. Default: 30000 */
  syncInterval?: number;
}

// ─── SyncManager ──────────────────────────────────────────────────────────────

export class SyncManager {
  readonly syncInterval: number;

  private readonly localStorage: LocalStorageAdapter;
  private readonly cloudStorage: StorageAdapter;
  private timer: ReturnType<typeof setInterval> | null = null;

  isRunning = false;

  constructor(config: SyncManagerConfig) {
    this.localStorage = config.localStorage;
    this.cloudStorage = config.cloudStorage;
    this.syncInterval = config.syncInterval ?? 30000;
  }

  // ─── startSync ────────────────────────────────────────────────────────────

  async startSync(): Promise<void> {
    if (this.isRunning) return;
    this.isRunning = true;

    this.timer = setInterval(() => {
      void this.forcePush();
    }, this.syncInterval);
  }

  // ─── stopSync ─────────────────────────────────────────────────────────────

  async stopSync(): Promise<void> {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.isRunning = false;
  }

  // ─── forcePush ────────────────────────────────────────────────────────────

  /**
   * Immediately push all pending local changes to cloud.
   * Conflict resolution: last-write-wins (all items are independent rows).
   */
  async forcePush(): Promise<void> {
    const pending: SyncChange[] = await this.localStorage.getPendingChanges();
    if (pending.length === 0) return;

    const syncedIds: string[] = [];

    for (const change of pending) {
      try {
        if (change.type === 'memory') {
          await this.cloudStorage.storeMemory(
            change.content ?? '',
            change.metadata ?? {},
          );
        } else if (change.type === 'record' && change.table) {
          await this.cloudStorage.storeRecord(change.table, change.data ?? {});
        }
        syncedIds.push(change.id);
      } catch {
        // Leave failed items in the queue for the next sync attempt
      }
    }

    if (syncedIds.length > 0) {
      await this.localStorage.markSynced(syncedIds);
    }
  }

  // ─── getQueueSize ─────────────────────────────────────────────────────────

  async getQueueSize(): Promise<number> {
    return this.localStorage.getUnsyncedCount();
  }
}
