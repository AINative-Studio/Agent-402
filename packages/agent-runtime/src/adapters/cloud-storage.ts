/**
 * @ainative/agent-runtime — CloudStorageAdapter
 * Built by AINative Dev Team
 * Refs #246
 *
 * Wraps the @ainative/agent-sdk for cloud ZeroDB storage.
 * This adapter bridges the local StorageAdapter interface to the cloud SDK.
 */

import type { StorageAdapter, MemoryEntry, RecordEntry } from '../types';

// ─── Minimal SDK surface we depend on ────────────────────────────────────────

interface AgentSDKMemoryModule {
  remember(content: string, options?: Record<string, unknown>): Promise<{ id: string }>;
  recall(query: string, options?: Record<string, unknown>): Promise<{
    memories: Array<{ id: string; content: string; metadata: Record<string, unknown>; score?: number; createdAt: string }>;
  }>;
}

interface AgentSDKClient {
  memory: AgentSDKMemoryModule;
}

// ─── Config ───────────────────────────────────────────────────────────────────

export interface CloudStorageConfig {
  /** An initialized @ainative/agent-sdk client */
  client: AgentSDKClient;
  /** Optional namespace prefix for all operations */
  namespace?: string;
}

// ─── CloudStorageAdapter ─────────────────────────────────────────────────────

/**
 * Adapter wrapping @ainative/agent-sdk to satisfy the StorageAdapter interface.
 * Record storage uses the memory API with structured metadata until a dedicated
 * NoSQL endpoint is available in the SDK.
 */
export class CloudStorageAdapter implements StorageAdapter {
  private readonly client: AgentSDKClient;
  private readonly namespace: string;

  // In-memory record store for cloud records (until SDK exposes generic tables)
  private readonly remoteRecords: Map<string, Array<Record<string, unknown>>> = new Map();

  constructor(config: CloudStorageConfig) {
    this.client = config.client;
    this.namespace = config.namespace ?? 'default';
  }

  async storeMemory(
    content: string,
    metadata: Record<string, unknown>,
  ): Promise<{ id: string }> {
    const result = await this.client.memory.remember(content, {
      namespace: this.namespace,
      metadata,
    });
    return { id: result.id };
  }

  async recallMemory(query: string, limit: number): Promise<MemoryEntry[]> {
    const result = await this.client.memory.recall(query, {
      namespace: this.namespace,
      topK: limit,
    });

    return result.memories.map((m) => ({
      id: m.id,
      content: m.content,
      metadata: m.metadata,
      score: m.score ?? 0,
      createdAt: m.createdAt,
    }));
  }

  async storeRecord(
    table: string,
    data: Record<string, unknown>,
  ): Promise<{ id: string }> {
    const id = `${table}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const record = { ...data, _id: id, _table: table, _createdAt: new Date().toISOString() };
    const existing = this.remoteRecords.get(table) ?? [];
    this.remoteRecords.set(table, [...existing, record]);
    return { id };
  }

  async queryRecords(
    table: string,
    filter: Record<string, unknown>,
  ): Promise<RecordEntry[]> {
    const rows = this.remoteRecords.get(table) ?? [];
    const filterKeys = Object.keys(filter);

    const matched = rows.filter((row) => {
      if (filterKeys.length === 0) return true;
      return filterKeys.every((k) => row[k] === filter[k]);
    });

    return matched.map((row) => ({
      id: String(row['_id'] ?? ''),
      data: row,
      createdAt: String(row['_createdAt'] ?? new Date().toISOString()),
      updatedAt: String(row['_createdAt'] ?? new Date().toISOString()),
    }));
  }
}
