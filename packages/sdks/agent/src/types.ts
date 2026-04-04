/**
 * @ainative/agent-sdk — TypeScript type definitions
 * Built by AINative Dev Team
 * Refs #178 #179 #180
 */

// ─── SDK Configuration ────────────────────────────────────────────────────────

export interface AINativeSDKConfig {
  /** API key for authentication */
  apiKey?: string;
  /** JWT token for authentication */
  jwt?: string;
  /** Base URL for the AINative API (default: https://api.ainative.studio/v1) */
  baseUrl?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
}

// ─── Agent Types (#178) ───────────────────────────────────────────────────────

export type AgentScope = 'RUN' | 'PROJECT' | 'GLOBAL';

export interface AgentConfig {
  name: string;
  role: string;
  did?: string;
  description?: string;
  scope?: AgentScope;
  projectId?: string;
  metadata?: Record<string, unknown>;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  did: string;
  description?: string;
  scope: AgentScope;
  projectId: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, unknown>;
}

export interface AgentUpdateConfig {
  name?: string;
  role?: string;
  description?: string;
  scope?: AgentScope;
  metadata?: Record<string, unknown>;
}

export interface AgentListResponse {
  agents: Agent[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Task Types (#178) ────────────────────────────────────────────────────────

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface TaskConfig {
  description: string;
  agent_types?: string[];
  config?: Record<string, unknown>;
  projectId?: string;
  priority?: number;
  metadata?: Record<string, unknown>;
}

export interface Task {
  id: string;
  description: string;
  agent_types: string[];
  status: TaskStatus;
  projectId: string;
  config: Record<string, unknown>;
  priority: number;
  result?: unknown;
  error?: string;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, unknown>;
}

export interface TaskListOptions {
  status?: TaskStatus;
  projectId?: string;
  limit?: number;
  offset?: number;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Memory Types (#179) ──────────────────────────────────────────────────────

export interface MemoryStoreOptions {
  namespace?: string;
  agentId?: string;
  runId?: string;
  memoryType?: string;
  metadata?: Record<string, unknown>;
}

export interface MemoryRecallOptions {
  namespace?: string;
  topK?: number;
  agentId?: string;
  minScore?: number;
}

export interface MemoryReflectOptions {
  namespace?: string;
  depth?: number;
}

export interface Memory {
  id: string;
  content: string;
  namespace: string;
  agentId?: string;
  runId?: string;
  memoryType?: string;
  metadata: Record<string, unknown>;
  score?: number;
  createdAt: string;
  updatedAt: string;
}

export interface MemoryRecallResult {
  memories: Memory[];
  query: string;
  total: number;
}

export interface EntityContext {
  entityId: string;
  memories: Memory[];
  relationships: GraphEdge[];
  context: Record<string, unknown>;
}

// ─── Graph Types (#179) ───────────────────────────────────────────────────────

export interface GraphEntity {
  id?: string;
  type: string;
  label: string;
  properties?: Record<string, unknown>;
}

export interface GraphEdge {
  id?: string;
  sourceId: string;
  targetId: string;
  relation: string;
  weight?: number;
  properties?: Record<string, unknown>;
}

export interface GraphTraverseOptions {
  maxDepth?: number;
  relation?: string;
  direction?: 'outbound' | 'inbound' | 'any';
  limit?: number;
}

export interface GraphTraverseResult {
  startNode: string;
  nodes: GraphEntity[];
  edges: GraphEdge[];
  depth: number;
}

export interface GraphRagResult {
  answer: string;
  sources: Memory[];
  graph: {
    nodes: GraphEntity[];
    edges: GraphEdge[];
  };
  confidence: number;
}

// ─── Vector Types (#180) ──────────────────────────────────────────────────────

export type SupportedDimension = 384 | 768 | 1024 | 1536;

export interface VectorUpsertOptions {
  namespace?: string;
  vectorId?: string;
  model?: string;
}

export interface VectorSearchOptions {
  namespace?: string;
  topK?: number;
  minScore?: number;
  filter?: Record<string, unknown>;
}

export interface VectorMetadata {
  document?: string;
  model?: string;
  dimensions?: number;
  [key: string]: unknown;
}

export interface Vector {
  id: string;
  embedding: number[];
  metadata: VectorMetadata;
  namespace: string;
  dimensions: number;
  createdAt: string;
}

export interface VectorSearchResult {
  id: string;
  score: number;
  metadata: VectorMetadata;
  namespace: string;
}

export interface VectorUpsertResult {
  id: string;
  created: boolean;
  dimensions: number;
  model?: string;
}

// ─── File Types (#180) ────────────────────────────────────────────────────────

export interface FileUploadOptions {
  namespace?: string;
  metadata?: Record<string, unknown>;
  contentType?: string;
}

export interface FileListOptions {
  namespace?: string;
  limit?: number;
  offset?: number;
}

export interface StoredFile {
  id: string;
  name: string;
  size: number;
  contentType: string;
  namespace: string;
  url?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface FileListResponse {
  files: StoredFile[];
  total: number;
  limit: number;
  offset: number;
}

// ─── API Response Envelope ────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface ApiError {
  status: number;
  code: string;
  message: string;
  details?: unknown;
}
