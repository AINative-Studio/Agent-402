/**
 * @ainative/agent-sdk
 * Built by AINative Dev Team
 * Refs #178 #179 #180
 *
 * TypeScript SDK for the AINative platform.
 *
 * @example
 * ```typescript
 * import { AINativeSDK } from '@ainative/agent-sdk';
 *
 * const sdk = new AINativeSDK({ apiKey: 'your-api-key' });
 *
 * // Agent operations
 * const agent = await sdk.agents.create({ name: 'My Agent', role: 'researcher' });
 *
 * // Memory operations
 * await sdk.memory.remember('Important context', { namespace: 'my-project' });
 * const results = await sdk.memory.recall('relevant topic');
 *
 * // Vector operations
 * await sdk.vectors.upsert(embedding384, { document: 'text' });
 * const similar = await sdk.vectors.search('query text');
 *
 * // File operations
 * const file = await sdk.files.upload(blob);
 * ```
 */

import { HttpClient } from './client';
import { AgentsModule } from './agents';
import { MemoryModule } from './memory';
import { VectorsModule } from './vectors';
import { FilesModule } from './files';
import { EventsModule } from './events';
import { ThreadsModule } from './threads';
import type { AINativeSDKConfig } from './types';

export class AINativeSDK {
  /** Agent CRUD and Task Management — Issue #178 */
  readonly agents: AgentsModule;

  /** Memory and Context Graph — Issue #179 */
  readonly memory: MemoryModule;

  /** Vector operations — Issue #180 */
  readonly vectors: VectorsModule;

  /** File operations — Issue #180 */
  readonly files: FilesModule;

  /** Real-time event subscriptions (WebSocket + SSE) — Issue #213 */
  readonly events: EventsModule;

  /** Persistent conversation thread management — Issue #221 */
  readonly threads: ThreadsModule;

  constructor(config: AINativeSDKConfig) {
    const client = new HttpClient(config);
    this.agents = new AgentsModule(client);
    this.memory = new MemoryModule(client);
    this.vectors = new VectorsModule(client);
    this.files = new FilesModule(client);
    this.events = new EventsModule(client);
    this.threads = new ThreadsModule(client);
  }
}

// Named exports for tree-shaking and direct module use
export { HttpClient } from './client';
export { AgentsModule } from './agents';
export { MemoryModule } from './memory';
export { VectorsModule } from './vectors';
export { FilesModule } from './files';
export { EventsModule } from './events';
export { ThreadsModule } from './threads';
export {
  AINativeSDKError,
  AuthenticationError,
  NotFoundError,
  RateLimitError,
  ValidationError,
  NetworkError,
} from './errors';

// Type exports
export type {
  AINativeSDKConfig,
  AgentScope,
  AgentConfig,
  Agent,
  AgentUpdateConfig,
  AgentListResponse,
  TaskStatus,
  TaskConfig,
  Task,
  TaskListOptions,
  TaskListResponse,
  MemoryStoreOptions,
  MemoryRecallOptions,
  MemoryReflectOptions,
  Memory,
  MemoryRecallResult,
  EntityContext,
  GraphEntity,
  GraphEdge,
  GraphTraverseOptions,
  GraphTraverseResult,
  GraphRagResult,
  SupportedDimension,
  VectorUpsertOptions,
  VectorSearchOptions,
  VectorMetadata,
  Vector,
  VectorSearchResult,
  VectorUpsertResult,
  FileUploadOptions,
  FileListOptions,
  StoredFile,
  FileListResponse,
  ApiResponse,
  ApiError,
} from './types';
