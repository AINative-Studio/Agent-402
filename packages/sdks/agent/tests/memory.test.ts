/**
 * RED tests for Memory and Context Graph operations
 * Built by AINative Dev Team
 * Refs #179
 */

import { MemoryModule } from '../src/memory';
import { HttpClient } from '../src/client';
import type {
  Memory,
  MemoryStoreOptions,
  MemoryRecallOptions,
  MemoryRecallResult,
  EntityContext,
  GraphEntity,
  GraphEdge,
  GraphTraverseOptions,
  GraphTraverseResult,
  GraphRagResult,
} from '../src/types';

jest.mock('../src/client');

function makeMemory(overrides: Partial<Memory> = {}): Memory {
  return {
    id: 'mem_abc123456789',
    content: 'Test memory content',
    namespace: 'default',
    agentId: 'agent_xyz',
    runId: 'run_001',
    memoryType: 'context',
    metadata: {},
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeEntity(overrides: Partial<GraphEntity> = {}): GraphEntity {
  return {
    id: 'entity_abc',
    type: 'agent',
    label: 'Test Entity',
    properties: {},
    ...overrides,
  };
}

function makeEdge(overrides: Partial<GraphEdge> = {}): GraphEdge {
  return {
    id: 'edge_abc',
    sourceId: 'entity_a',
    targetId: 'entity_b',
    relation: 'knows',
    weight: 1.0,
    ...overrides,
  };
}

describe('MemoryModule', () => {
  let mockClient: jest.Mocked<HttpClient>;
  let memoryModule: MemoryModule;

  beforeEach(() => {
    mockClient = {
      get: jest.fn(),
      post: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
      baseUrl: 'https://api.ainative.studio/v1',
      timeout: 30000,
    } as unknown as jest.Mocked<HttpClient>;

    memoryModule = new MemoryModule(mockClient);
  });

  // ─── memory.remember ──────────────────────────────────────────────────────

  describe('remember', () => {
    it('should POST to the memory v2 endpoint with content', async () => {
      const expected = makeMemory({ content: 'The sky is blue' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.remember('The sky is blue');

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/',
        expect.objectContaining({ content: 'The sky is blue' })
      );
      expect(result).toEqual(expected);
    });

    it('should include namespace in request when provided', async () => {
      mockClient.post.mockResolvedValueOnce(makeMemory({ namespace: 'project-ns' }));
      const options: MemoryStoreOptions = { namespace: 'project-ns' };

      await memoryModule.remember('Some content', options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/',
        expect.objectContaining({ namespace: 'project-ns' })
      );
    });

    it('should include agentId in request when provided', async () => {
      mockClient.post.mockResolvedValueOnce(makeMemory());
      const options: MemoryStoreOptions = { agentId: 'agent_abc' };

      await memoryModule.remember('Memory for agent', options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/',
        expect.objectContaining({ agent_id: 'agent_abc' })
      );
    });

    it('should return a Memory with an id prefixed with mem_', async () => {
      const expected = makeMemory({ id: 'mem_abcdef1234567890' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.remember('Some content');

      expect(result.id).toMatch(/^mem_/);
    });

    it('should include memory_type in request when provided', async () => {
      mockClient.post.mockResolvedValueOnce(makeMemory());
      const options: MemoryStoreOptions = { memoryType: 'decision' };

      await memoryModule.remember('I decided to...', options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/',
        expect.objectContaining({ memory_type: 'decision' })
      );
    });
  });

  // ─── memory.recall ────────────────────────────────────────────────────────

  describe('recall', () => {
    it('should POST to the memory semantic search endpoint', async () => {
      const expected: MemoryRecallResult = {
        memories: [makeMemory()],
        query: 'sky color',
        total: 1,
      };
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.recall('sky color');

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/search',
        expect.objectContaining({ query: 'sky color' })
      );
      expect(result).toEqual(expected);
    });

    it('should include topK in request when provided', async () => {
      mockClient.post.mockResolvedValueOnce({ memories: [], query: 'test', total: 0 });
      const options: MemoryRecallOptions = { topK: 5 };

      await memoryModule.recall('test query', options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/search',
        expect.objectContaining({ top_k: 5 })
      );
    });

    it('should include namespace filter when provided', async () => {
      mockClient.post.mockResolvedValueOnce({ memories: [], query: 'test', total: 0 });
      const options: MemoryRecallOptions = { namespace: 'my-namespace' };

      await memoryModule.recall('test query', options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/search',
        expect.objectContaining({ namespace: 'my-namespace' })
      );
    });

    it('should return a MemoryRecallResult with memories array', async () => {
      const expected: MemoryRecallResult = {
        memories: [makeMemory({ score: 0.95 }), makeMemory({ score: 0.87 })],
        query: 'test',
        total: 2,
      };
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.recall('test');

      expect(result.memories).toHaveLength(2);
      expect(result.total).toBe(2);
    });
  });

  // ─── memory.forget ────────────────────────────────────────────────────────

  describe('forget', () => {
    it('should DELETE the memory at /api/v1/public/memory/v2/:memoryId', async () => {
      mockClient.delete.mockResolvedValueOnce({ success: true });

      await memoryModule.forget('mem_abc123456789');

      expect(mockClient.delete).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/mem_abc123456789'
      );
    });
  });

  // ─── memory.reflect ───────────────────────────────────────────────────────

  describe('reflect', () => {
    it('should GET the entity context from memory API', async () => {
      const expected: EntityContext = {
        entityId: 'entity_abc',
        memories: [makeMemory()],
        relationships: [],
        context: {},
      };
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await memoryModule.reflect('entity_abc');

      expect(mockClient.get).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/entity/entity_abc'
      );
      expect(result).toEqual(expected);
    });

    it('should return an EntityContext with memories and relationships', async () => {
      const expected: EntityContext = {
        entityId: 'entity_xyz',
        memories: [makeMemory(), makeMemory()],
        relationships: [makeEdge()],
        context: { summary: 'Entity summary' },
      };
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await memoryModule.reflect('entity_xyz');

      expect(result.entityId).toBe('entity_xyz');
      expect(result.memories).toHaveLength(2);
      expect(result.relationships).toHaveLength(1);
    });
  });

  // ─── memory.graph.traverse ────────────────────────────────────────────────

  describe('graph.traverse', () => {
    it('should POST to graph traverse endpoint with startNode', async () => {
      const expected: GraphTraverseResult = {
        startNode: 'entity_start',
        nodes: [makeEntity()],
        edges: [makeEdge()],
        depth: 2,
      };
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.graph.traverse('entity_start');

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/graph/traverse',
        expect.objectContaining({ start_node: 'entity_start' })
      );
      expect(result).toEqual(expected);
    });

    it('should include traversal options in request when provided', async () => {
      const options: GraphTraverseOptions = { maxDepth: 3, direction: 'outbound' };
      mockClient.post.mockResolvedValueOnce({
        startNode: 'entity_a',
        nodes: [],
        edges: [],
        depth: 3,
      });

      await memoryModule.graph.traverse('entity_a', options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/graph/traverse',
        expect.objectContaining({ max_depth: 3, direction: 'outbound' })
      );
    });

    it('should return nodes and edges from traversal', async () => {
      const nodes = [makeEntity({ id: 'n1' }), makeEntity({ id: 'n2' })];
      const edges = [makeEdge({ sourceId: 'n1', targetId: 'n2' })];
      mockClient.post.mockResolvedValueOnce({ startNode: 'n1', nodes, edges, depth: 1 });

      const result = await memoryModule.graph.traverse('n1');

      expect(result.nodes).toHaveLength(2);
      expect(result.edges).toHaveLength(1);
    });
  });

  // ─── memory.graph.addEntity ───────────────────────────────────────────────

  describe('graph.addEntity', () => {
    it('should POST entity to graph entities endpoint', async () => {
      const entity: GraphEntity = { type: 'document', label: 'My Doc' };
      const expected = makeEntity({ ...entity, id: 'entity_new' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.graph.addEntity(entity);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/graph/entities',
        entity
      );
      expect(result).toEqual(expected);
    });

    it('should return the created entity with an id', async () => {
      const entity: GraphEntity = { type: 'agent', label: 'My Agent' };
      const expected = makeEntity({ id: 'entity_created123' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.graph.addEntity(entity);

      expect(result.id).toBe('entity_created123');
    });
  });

  // ─── memory.graph.addEdge ─────────────────────────────────────────────────

  describe('graph.addEdge', () => {
    it('should POST edge to graph edges endpoint', async () => {
      const edge: GraphEdge = { sourceId: 'entity_a', targetId: 'entity_b', relation: 'uses' };
      const expected = makeEdge({ ...edge, id: 'edge_new' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.graph.addEdge(edge);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/graph/edges',
        edge
      );
      expect(result).toEqual(expected);
    });

    it('should return the created edge with an id', async () => {
      const edge: GraphEdge = { sourceId: 'n1', targetId: 'n2', relation: 'owns' };
      const expected = makeEdge({ id: 'edge_created456' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.graph.addEdge(edge);

      expect(result.id).toBe('edge_created456');
    });
  });

  // ─── memory.graph.graphrag ────────────────────────────────────────────────

  describe('graph.graphrag', () => {
    it('should POST query to graphrag endpoint', async () => {
      const expected: GraphRagResult = {
        answer: 'The answer is 42',
        sources: [makeMemory()],
        graph: { nodes: [makeEntity()], edges: [] },
        confidence: 0.92,
      };
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.graph.graphrag('What is the answer?');

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/memory/v2/graph/rag',
        expect.objectContaining({ query: 'What is the answer?' })
      );
      expect(result).toEqual(expected);
    });

    it('should return answer text and sources', async () => {
      const expected: GraphRagResult = {
        answer: 'Deep answer here',
        sources: [makeMemory(), makeMemory()],
        graph: { nodes: [], edges: [] },
        confidence: 0.75,
      };
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await memoryModule.graph.graphrag('Complex question');

      expect(result.answer).toBe('Deep answer here');
      expect(result.sources).toHaveLength(2);
      expect(result.confidence).toBe(0.75);
    });
  });
});
