/**
 * @ainative/agent-sdk — Memory and Context Graph operations
 * Built by AINative Dev Team
 * Refs #179
 */

import type { HttpClient } from './client';
import type {
  Memory,
  MemoryStoreOptions,
  MemoryRecallOptions,
  MemoryRecallResult,
  MemoryReflectOptions,
  EntityContext,
  GraphEntity,
  GraphEdge,
  GraphTraverseOptions,
  GraphTraverseResult,
  GraphRagResult,
} from './types';

const MEMORY_BASE = '/api/v1/public/memory/v2';
const GRAPH_BASE = `${MEMORY_BASE}/graph`;

class GraphSubModule {
  constructor(private readonly client: HttpClient) {}

  /**
   * Traverse the context graph starting from a node.
   */
  async traverse(startNode: string, options?: GraphTraverseOptions): Promise<GraphTraverseResult> {
    const body: Record<string, unknown> = { start_node: startNode };

    if (options?.maxDepth !== undefined) body.max_depth = options.maxDepth;
    if (options?.relation) body.relation = options.relation;
    if (options?.direction) body.direction = options.direction;
    if (options?.limit !== undefined) body.limit = options.limit;

    return this.client.post<GraphTraverseResult>(`${GRAPH_BASE}/traverse`, body);
  }

  /**
   * Add an entity (node) to the graph.
   */
  async addEntity(entity: GraphEntity): Promise<GraphEntity> {
    return this.client.post<GraphEntity>(`${GRAPH_BASE}/entities`, entity);
  }

  /**
   * Add an edge (relationship) to the graph.
   */
  async addEdge(edge: GraphEdge): Promise<GraphEdge> {
    return this.client.post<GraphEdge>(`${GRAPH_BASE}/edges`, edge);
  }

  /**
   * Perform graph-enhanced RAG (Retrieval-Augmented Generation) for a query.
   */
  async graphrag(query: string): Promise<GraphRagResult> {
    return this.client.post<GraphRagResult>(`${GRAPH_BASE}/rag`, { query });
  }
}

export class MemoryModule {
  /** Context graph sub-module */
  readonly graph: GraphSubModule;

  constructor(private readonly client: HttpClient) {
    this.graph = new GraphSubModule(client);
  }

  /**
   * Store a memory (remember content).
   */
  async remember(content: string, options?: MemoryStoreOptions): Promise<Memory> {
    const body: Record<string, unknown> = { content };

    if (options?.namespace) body.namespace = options.namespace;
    if (options?.agentId) body.agent_id = options.agentId;
    if (options?.runId) body.run_id = options.runId;
    if (options?.memoryType) body.memory_type = options.memoryType;
    if (options?.metadata) body.metadata = options.metadata;

    return this.client.post<Memory>(`${MEMORY_BASE}/`, body);
  }

  /**
   * Recall memories via semantic search.
   */
  async recall(query: string, options?: MemoryRecallOptions): Promise<MemoryRecallResult> {
    const body: Record<string, unknown> = { query };

    if (options?.namespace) body.namespace = options.namespace;
    if (options?.topK !== undefined) body.top_k = options.topK;
    if (options?.agentId) body.agent_id = options.agentId;
    if (options?.minScore !== undefined) body.min_score = options.minScore;

    return this.client.post<MemoryRecallResult>(`${MEMORY_BASE}/search`, body);
  }

  /**
   * Delete a memory by ID.
   */
  async forget(memoryId: string): Promise<void> {
    await this.client.delete(`${MEMORY_BASE}/${memoryId}`);
  }

  /**
   * Get entity context (reflection) for a given entity ID.
   */
  async reflect(entityId: string, _options?: MemoryReflectOptions): Promise<EntityContext> {
    return this.client.get<EntityContext>(`${MEMORY_BASE}/entity/${entityId}`);
  }
}
