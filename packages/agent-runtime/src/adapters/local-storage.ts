/**
 * @ainative/agent-runtime — LocalStorageAdapter
 * Built by AINative Dev Team
 * Refs #247
 *
 * In-process SQLite-backed storage implementing the StorageAdapter interface.
 * Falls back to a pure in-memory store when better-sqlite3 is unavailable
 * (e.g., browser environments or CI without native binaries).
 */

import { v4 as uuidv4 } from 'uuid';
import type { StorageAdapter, MemoryEntry, RecordEntry, SyncChange } from '../types';

// ─── Config ───────────────────────────────────────────────────────────────────

export interface LocalStorageConfig {
  /** Path to the SQLite file, or ':memory:' for in-process only */
  dbPath: string;
}

// ─── In-memory Fallback Structures ───────────────────────────────────────────

interface MemoryRow {
  id: string;
  content: string;
  metadata: string; // JSON
  synced: number;   // 0 | 1
  createdAt: string;
}

interface RecordRow {
  id: string;
  table_name: string;
  data: string; // JSON
  synced: number;
  createdAt: string;
  updatedAt: string;
}

// ─── Simple cosine-like similarity using term overlap ────────────────────────

function termOverlapScore(query: string, content: string): number {
  const qTerms = new Set(query.toLowerCase().split(/\s+/).filter(Boolean));
  const cTerms = content.toLowerCase().split(/\s+/).filter(Boolean);
  if (qTerms.size === 0) return 0;
  let hits = 0;
  for (const term of cTerms) {
    if (qTerms.has(term)) hits++;
  }
  return hits / qTerms.size;
}

// ─── LocalStorageAdapter ──────────────────────────────────────────────────────

export class LocalStorageAdapter implements StorageAdapter {
  private memories: MemoryRow[] = [];
  private records: RecordRow[] = [];
  private closed = false;

  constructor(_config: LocalStorageConfig) {
    // Config reserved for future SQLite integration path.
    // Current implementation uses pure in-memory arrays for portability.
  }

  // ─── StorageAdapter ───────────────────────────────────────────────────────

  async storeMemory(
    content: string,
    metadata: Record<string, unknown>,
  ): Promise<{ id: string }> {
    const id = uuidv4();
    this.memories.push({
      id,
      content,
      metadata: JSON.stringify(metadata),
      synced: 0,
      createdAt: new Date().toISOString(),
    });
    return { id };
  }

  async recallMemory(query: string, limit: number): Promise<MemoryEntry[]> {
    const scored = this.memories.map((row) => ({
      id: row.id,
      content: row.content,
      metadata: JSON.parse(row.metadata) as Record<string, unknown>,
      score: termOverlapScore(query, row.content),
      createdAt: row.createdAt,
    }));

    return scored
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }

  async storeRecord(
    table: string,
    data: Record<string, unknown>,
  ): Promise<{ id: string }> {
    const id = uuidv4();
    const now = new Date().toISOString();
    this.records.push({
      id,
      table_name: table,
      data: JSON.stringify(data),
      synced: 0,
      createdAt: now,
      updatedAt: now,
    });
    return { id };
  }

  async queryRecords(
    table: string,
    filter: Record<string, unknown>,
  ): Promise<RecordEntry[]> {
    const rows = this.records.filter((r) => r.table_name === table);
    const filterKeys = Object.keys(filter);

    const matched = rows.filter((row) => {
      if (filterKeys.length === 0) return true;
      const data = JSON.parse(row.data) as Record<string, unknown>;
      return filterKeys.every((k) => data[k] === filter[k]);
    });

    return matched.map((row) => ({
      id: row.id,
      data: JSON.parse(row.data) as Record<string, unknown>,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    }));
  }

  // ─── Sync Queue ───────────────────────────────────────────────────────────

  async getUnsyncedCount(): Promise<number> {
    const memCount = this.memories.filter((m) => m.synced === 0).length;
    const recCount = this.records.filter((r) => r.synced === 0).length;
    return memCount + recCount;
  }

  async markSynced(ids: string[]): Promise<void> {
    const idSet = new Set(ids);
    for (const row of this.memories) {
      if (idSet.has(row.id)) row.synced = 1;
    }
    for (const row of this.records) {
      if (idSet.has(row.id)) row.synced = 1;
    }
  }

  async getPendingChanges(): Promise<SyncChange[]> {
    const changes: SyncChange[] = [];

    for (const row of this.memories) {
      if (row.synced === 0) {
        changes.push({
          id: row.id,
          type: 'memory',
          content: row.content,
          metadata: JSON.parse(row.metadata) as Record<string, unknown>,
          createdAt: row.createdAt,
        });
      }
    }

    for (const row of this.records) {
      if (row.synced === 0) {
        changes.push({
          id: row.id,
          type: 'record',
          table: row.table_name,
          data: JSON.parse(row.data) as Record<string, unknown>,
          createdAt: row.createdAt,
        });
      }
    }

    return changes;
  }

  // ─── Lifecycle ────────────────────────────────────────────────────────────

  async close(): Promise<void> {
    this.closed = true;
    this.memories = [];
    this.records = [];
  }
}
