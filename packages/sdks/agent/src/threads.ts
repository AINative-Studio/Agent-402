/**
 * @ainative/agent-sdk — Thread Management
 * Built by AINative Dev Team
 * Refs #221
 *
 * Provides CRUD operations for persistent conversation threads,
 * plus resume and search helpers.
 */

import type { HttpClient } from './client';

const THREADS_BASE = '/api/v1/threads';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Thread {
  id: string;
  agent_id: string;
  title: string;
  status: string;
  metadata: Record<string, unknown>;
  created_at: string;
  messages: ThreadMessage[];
}

export interface ThreadMessage {
  id: string;
  thread_id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ThreadListResult {
  threads: Thread[];
  total: number;
}

export interface ThreadContextResult {
  thread_id: string;
  messages: ThreadMessage[];
}

// ─── Module ───────────────────────────────────────────────────────────────────

/**
 * ThreadsModule provides persistent conversation thread management.
 *
 * Threads are stored in the backend and support:
 * - Full CRUD lifecycle
 * - Message appending
 * - Context-window resume (last N messages)
 * - Keyword/semantic search
 */
export class ThreadsModule {
  constructor(private readonly client: HttpClient) {}

  // ─── create ────────────────────────────────────────────────────────────────

  /**
   * Create a new conversation thread.
   *
   * @param agentId  - The agent that owns this thread.
   * @param title    - Human-readable thread title.
   * @param metadata - Optional metadata key/value pairs.
   * @returns The created Thread record.
   */
  async create(
    agentId: string,
    title: string,
    metadata?: Record<string, unknown>,
  ): Promise<Thread> {
    const body: Record<string, unknown> = { agent_id: agentId, title };
    if (metadata !== undefined) body.metadata = metadata;
    return this.client.post<Thread>(THREADS_BASE, body);
  }

  // ─── get ───────────────────────────────────────────────────────────────────

  /**
   * Retrieve a thread by ID including all messages.
   *
   * @param threadId - Thread identifier.
   * @returns Thread record with embedded messages.
   */
  async get(threadId: string): Promise<Thread> {
    return this.client.get<Thread>(`${THREADS_BASE}/${threadId}`);
  }

  // ─── list ──────────────────────────────────────────────────────────────────

  /**
   * List active threads for an agent with pagination.
   *
   * @param agentId - Filter by this agent.
   * @param limit   - Maximum results (default 20).
   * @param offset  - Results to skip (default 0).
   * @returns Paginated ThreadListResult.
   */
  async list(
    agentId: string,
    limit = 20,
    offset = 0,
  ): Promise<ThreadListResult> {
    const qs = new URLSearchParams({
      agent_id: agentId,
      limit: String(limit),
      offset: String(offset),
    }).toString();
    return this.client.get<ThreadListResult>(`${THREADS_BASE}?${qs}`);
  }

  // ─── delete ────────────────────────────────────────────────────────────────

  /**
   * Soft-delete a thread.
   *
   * @param threadId - Thread identifier.
   */
  async delete(threadId: string): Promise<void> {
    await this.client.delete(`${THREADS_BASE}/${threadId}`);
  }

  // ─── addMessage ────────────────────────────────────────────────────────────

  /**
   * Append a message to an existing thread.
   *
   * @param threadId - Target thread.
   * @param role     - Message role ('user', 'assistant', 'system').
   * @param content  - Message body text.
   * @param metadata - Optional message metadata.
   * @returns The created ThreadMessage.
   */
  async addMessage(
    threadId: string,
    role: string,
    content: string,
    metadata?: Record<string, unknown>,
  ): Promise<ThreadMessage> {
    const body: Record<string, unknown> = { role, content };
    if (metadata !== undefined) body.metadata = metadata;
    return this.client.post<ThreadMessage>(
      `${THREADS_BASE}/${threadId}/messages`,
      body,
    );
  }

  // ─── resume ────────────────────────────────────────────────────────────────

  /**
   * Load the last N messages from a thread as resumption context.
   *
   * @param threadId      - Thread to resume.
   * @param contextWindow - Number of most-recent messages (default 10).
   * @returns Object with thread_id and messages.
   */
  async resume(
    threadId: string,
    contextWindow?: number,
  ): Promise<ThreadContextResult> {
    const qs = contextWindow !== undefined
      ? `?context_window=${contextWindow}`
      : '';
    return this.client.get<ThreadContextResult>(
      `${THREADS_BASE}/${threadId}/resume${qs}`,
    );
  }

  // ─── search ────────────────────────────────────────────────────────────────

  /**
   * Search for threads by keyword or semantic similarity.
   *
   * @param query   - Search query string.
   * @param agentId - Restrict search to this agent's threads.
   * @param limit   - Maximum results (default 10).
   * @returns Array of matching Thread objects.
   */
  async search(
    query: string,
    agentId: string,
    limit = 10,
  ): Promise<Thread[]> {
    const qs = new URLSearchParams({
      query,
      agent_id: agentId,
      limit: String(limit),
    }).toString();
    return this.client.get<Thread[]>(`${THREADS_BASE}/search?${qs}`);
  }
}
