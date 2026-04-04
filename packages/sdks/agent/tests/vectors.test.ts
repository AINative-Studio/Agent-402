/**
 * RED tests for Vector operations
 * Built by AINative Dev Team
 * Refs #180
 */

import { VectorsModule } from '../src/vectors';
import { HttpClient } from '../src/client';
import { AINativeSDKError } from '../src/errors';
import type {
  Vector,
  VectorUpsertOptions,
  VectorSearchOptions,
  VectorSearchResult,
  VectorUpsertResult,
  VectorMetadata,
} from '../src/types';

jest.mock('../src/client');

function make384Embedding(): number[] {
  return Array.from({ length: 384 }, (_, i) => i * 0.001);
}

function make768Embedding(): number[] {
  return Array.from({ length: 768 }, (_, i) => i * 0.001);
}

function make1024Embedding(): number[] {
  return Array.from({ length: 1024 }, (_, i) => i * 0.001);
}

function make1536Embedding(): number[] {
  return Array.from({ length: 1536 }, (_, i) => i * 0.001);
}

function makeVector(overrides: Partial<Vector> = {}): Vector {
  return {
    id: 'vec_abc1234567890123',
    embedding: make384Embedding(),
    metadata: { document: 'test text', model: 'BAAI/bge-small-en-v1.5' },
    namespace: 'default',
    dimensions: 384,
    createdAt: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeSearchResult(overrides: Partial<VectorSearchResult> = {}): VectorSearchResult {
  return {
    id: 'vec_abc123',
    score: 0.95,
    metadata: { document: 'matched doc' },
    namespace: 'default',
    ...overrides,
  };
}

describe('VectorsModule', () => {
  let mockClient: jest.Mocked<HttpClient>;
  let vectorsModule: VectorsModule;

  beforeEach(() => {
    mockClient = {
      get: jest.fn(),
      post: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
      baseUrl: 'https://api.ainative.studio/v1',
      timeout: 30000,
    } as unknown as jest.Mocked<HttpClient>;

    vectorsModule = new VectorsModule(mockClient);
  });

  // ─── vectors.upsert ───────────────────────────────────────────────────────

  describe('upsert', () => {
    it('should POST embedding to /api/v1/public/vectors/', async () => {
      const embedding = make384Embedding();
      const metadata: VectorMetadata = { document: 'hello world' };
      const expected: VectorUpsertResult = { id: 'vec_new', created: true, dimensions: 384 };
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await vectorsModule.upsert(embedding, metadata);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/vectors/',
        expect.objectContaining({ embedding, metadata })
      );
      expect(result).toEqual(expected);
    });

    it('should return a VectorUpsertResult with id and created flag', async () => {
      const expected: VectorUpsertResult = { id: 'vec_created', created: true, dimensions: 384 };
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await vectorsModule.upsert(make384Embedding(), {});

      expect(result.id).toMatch(/^vec_/);
      expect(result.created).toBe(true);
    });

    it('should include namespace in request when provided', async () => {
      const options: VectorUpsertOptions = { namespace: 'my-ns' };
      mockClient.post.mockResolvedValueOnce({ id: 'vec_x', created: true, dimensions: 384 });

      await vectorsModule.upsert(make384Embedding(), {}, options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/vectors/',
        expect.objectContaining({ namespace: 'my-ns' })
      );
    });

    it('should include vectorId in request when provided', async () => {
      const options: VectorUpsertOptions = { vectorId: 'vec_custom_id' };
      mockClient.post.mockResolvedValueOnce({ id: 'vec_custom_id', created: false, dimensions: 384 });

      await vectorsModule.upsert(make384Embedding(), {}, options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/vectors/',
        expect.objectContaining({ vector_id: 'vec_custom_id' })
      );
    });

    it('should accept 384-dimension embeddings', async () => {
      mockClient.post.mockResolvedValueOnce({ id: 'vec_384', created: true, dimensions: 384 });

      await expect(vectorsModule.upsert(make384Embedding(), {})).resolves.not.toThrow();
    });

    it('should accept 768-dimension embeddings', async () => {
      mockClient.post.mockResolvedValueOnce({ id: 'vec_768', created: true, dimensions: 768 });

      await expect(vectorsModule.upsert(make768Embedding(), {})).resolves.not.toThrow();
    });

    it('should accept 1024-dimension embeddings', async () => {
      mockClient.post.mockResolvedValueOnce({ id: 'vec_1024', created: true, dimensions: 1024 });

      await expect(vectorsModule.upsert(make1024Embedding(), {})).resolves.not.toThrow();
    });

    it('should accept 1536-dimension embeddings', async () => {
      mockClient.post.mockResolvedValueOnce({ id: 'vec_1536', created: true, dimensions: 1536 });

      await expect(vectorsModule.upsert(make1536Embedding(), {})).resolves.not.toThrow();
    });

    it('should throw AINativeSDKError for invalid dimension count', async () => {
      const invalidEmbedding = Array.from({ length: 512 }, () => 0.1);

      await expect(vectorsModule.upsert(invalidEmbedding, {})).rejects.toThrow(AINativeSDKError);
    });

    it('should include the invalid dimension count in the error message', async () => {
      const invalidEmbedding = Array.from({ length: 100 }, () => 0.1);

      try {
        await vectorsModule.upsert(invalidEmbedding, {});
        fail('Expected error');
      } catch (e) {
        expect((e as Error).message).toContain('100');
      }
    });

    it('should mention supported dimensions in validation error', async () => {
      const invalidEmbedding = Array.from({ length: 200 }, () => 0.1);

      try {
        await vectorsModule.upsert(invalidEmbedding, {});
        fail('Expected error');
      } catch (e) {
        const msg = (e as Error).message;
        expect(msg).toContain('384');
      }
    });
  });

  // ─── vectors.search ───────────────────────────────────────────────────────

  describe('search', () => {
    it('should POST query to /api/v1/public/vectors/search', async () => {
      const response = { results: [makeSearchResult()], total: 1 };
      mockClient.post.mockResolvedValueOnce(response);

      const result = await vectorsModule.search('find similar documents');

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/vectors/search',
        expect.objectContaining({ query: 'find similar documents' })
      );
      expect(result).toEqual(response);
    });

    it('should include topK in request when provided', async () => {
      const options: VectorSearchOptions = { topK: 10 };
      mockClient.post.mockResolvedValueOnce({ results: [], total: 0 });

      await vectorsModule.search('test query', options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/vectors/search',
        expect.objectContaining({ top_k: 10 })
      );
    });

    it('should include namespace filter when provided', async () => {
      const options: VectorSearchOptions = { namespace: 'custom-ns' };
      mockClient.post.mockResolvedValueOnce({ results: [], total: 0 });

      await vectorsModule.search('test', options);

      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/v1/public/vectors/search',
        expect.objectContaining({ namespace: 'custom-ns' })
      );
    });

    it('should return search results with scores', async () => {
      const results = [
        makeSearchResult({ score: 0.95 }),
        makeSearchResult({ score: 0.87 }),
        makeSearchResult({ score: 0.72 }),
      ];
      mockClient.post.mockResolvedValueOnce({ results, total: 3 });

      const response = await vectorsModule.search('query');

      expect(response.results).toHaveLength(3);
      expect(response.results[0].score).toBe(0.95);
    });
  });

  // ─── vectors.delete ───────────────────────────────────────────────────────

  describe('delete', () => {
    it('should DELETE the vector at /api/v1/public/vectors/:vectorId', async () => {
      mockClient.delete.mockResolvedValueOnce({ success: true });

      await vectorsModule.delete('vec_abc123456789012');

      expect(mockClient.delete).toHaveBeenCalledWith(
        '/api/v1/public/vectors/vec_abc123456789012'
      );
    });
  });
});
