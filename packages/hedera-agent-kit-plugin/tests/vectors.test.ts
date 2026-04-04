/**
 * Vector tools tests — RED phase first
 * Built by AINative Dev Team
 * Refs #185
 */

import { AINativeClient } from '../src/client';
import { createVectorUpsertTool } from '../src/tools/vectors/upsert';
import { createVectorSearchTool } from '../src/tools/vectors/search';
import { createVectorDeleteTool } from '../src/tools/vectors/delete';
import { getVectorTools } from '../src/tools/vectors/index';
import { VALID_DIMENSIONS } from '../src/tools/vectors/upsert';
import {
  VectorUpsertResult,
  VectorSearchResult,
  VectorDeleteResult,
} from '../src/types';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeMockClient(): jest.Mocked<AINativeClient> {
  return {
    remember: jest.fn(),
    recall: jest.fn(),
    forget: jest.fn(),
    reflect: jest.fn(),
    chatCompletion: jest.fn(),
    vectorUpsert: jest.fn(),
    vectorSearch: jest.fn(),
    vectorDelete: jest.fn(),
  } as unknown as jest.Mocked<AINativeClient>;
}

function makeVector(dim: number): number[] {
  return Array.from({ length: dim }, () => Math.random());
}

// ─── VALID_DIMENSIONS ─────────────────────────────────────────────────────────

describe('VALID_DIMENSIONS', () => {
  it('includes 384', () => {
    expect(VALID_DIMENSIONS).toContain(384);
  });

  it('includes 768', () => {
    expect(VALID_DIMENSIONS).toContain(768);
  });

  it('includes 1024', () => {
    expect(VALID_DIMENSIONS).toContain(1024);
  });

  it('includes 1536', () => {
    expect(VALID_DIMENSIONS).toContain(1536);
  });

  it('has exactly four entries', () => {
    expect(VALID_DIMENSIONS).toHaveLength(4);
  });
});

// ─── createVectorUpsertTool ───────────────────────────────────────────────────

describe('createVectorUpsertTool', () => {
  it('returns a tool with the correct name', () => {
    const client = makeMockClient();
    const tool = createVectorUpsertTool(client);
    expect(tool.name).toBe('ainative_vector_upsert');
  });

  it('returns a tool with a non-empty description', () => {
    const client = makeMockClient();
    const tool = createVectorUpsertTool(client);
    expect(tool.description.length).toBeGreaterThan(10);
  });

  it('calls client.vectorUpsert with the vector', async () => {
    const client = makeMockClient();
    const vec = makeVector(384);
    const fakeResult: VectorUpsertResult = {
      id: 'vec-001',
      upserted: true,
    };
    client.vectorUpsert.mockResolvedValueOnce(fakeResult);

    const tool = createVectorUpsertTool(client);
    await tool.invoke({ vector: vec });

    expect(client.vectorUpsert).toHaveBeenCalledWith(
      expect.objectContaining({ vector: vec }),
    );
  });

  it('rejects vectors with invalid dimensions', async () => {
    const client = makeMockClient();
    const tool = createVectorUpsertTool(client);
    const invalidVec = makeVector(100);

    const result = await tool.invoke({ vector: invalidVec });

    expect(result).toContain('Error');
    expect(client.vectorUpsert).not.toHaveBeenCalled();
  });

  it('accepts a 768-dimension vector', async () => {
    const client = makeMockClient();
    client.vectorUpsert.mockResolvedValueOnce({ id: 'vec-002', upserted: true });

    const tool = createVectorUpsertTool(client);
    await tool.invoke({ vector: makeVector(768) });

    expect(client.vectorUpsert).toHaveBeenCalled();
  });

  it('accepts a 1024-dimension vector', async () => {
    const client = makeMockClient();
    client.vectorUpsert.mockResolvedValueOnce({ id: 'vec-003', upserted: true });

    const tool = createVectorUpsertTool(client);
    await tool.invoke({ vector: makeVector(1024) });

    expect(client.vectorUpsert).toHaveBeenCalled();
  });

  it('accepts a 1536-dimension vector', async () => {
    const client = makeMockClient();
    client.vectorUpsert.mockResolvedValueOnce({ id: 'vec-004', upserted: true });

    const tool = createVectorUpsertTool(client);
    await tool.invoke({ vector: makeVector(1536) });

    expect(client.vectorUpsert).toHaveBeenCalled();
  });

  it('passes namespace to client when provided', async () => {
    const client = makeMockClient();
    client.vectorUpsert.mockResolvedValueOnce({ id: 'vec-005', upserted: true, namespace: '0.0.123' });

    const tool = createVectorUpsertTool(client);
    await tool.invoke({ vector: makeVector(384), namespace: '0.0.123' });

    expect(client.vectorUpsert).toHaveBeenCalledWith(
      expect.objectContaining({ namespace: '0.0.123' }),
    );
  });

  it('passes metadata to client when provided', async () => {
    const client = makeMockClient();
    client.vectorUpsert.mockResolvedValueOnce({ id: 'vec-006', upserted: true });

    const tool = createVectorUpsertTool(client);
    await tool.invoke({ vector: makeVector(384), metadata: { source: 'doc-1' } });

    expect(client.vectorUpsert).toHaveBeenCalledWith(
      expect.objectContaining({ metadata: { source: 'doc-1' } }),
    );
  });

  it('returns vector id in success result', async () => {
    const client = makeMockClient();
    client.vectorUpsert.mockResolvedValueOnce({ id: 'vec-007', upserted: true });

    const tool = createVectorUpsertTool(client);
    const result = await tool.invoke({ vector: makeVector(384) });

    expect(result).toContain('vec-007');
  });

  it('returns an error string when client.vectorUpsert throws', async () => {
    const client = makeMockClient();
    client.vectorUpsert.mockRejectedValueOnce({ status: 503, message: 'Service unavailable' });

    const tool = createVectorUpsertTool(client);
    const result = await tool.invoke({ vector: makeVector(384) });

    expect(result).toContain('Error');
  });
});

// ─── createVectorSearchTool ───────────────────────────────────────────────────

describe('createVectorSearchTool', () => {
  it('returns a tool with the correct name', () => {
    const client = makeMockClient();
    const tool = createVectorSearchTool(client);
    expect(tool.name).toBe('ainative_vector_search');
  });

  it('returns a tool with a non-empty description', () => {
    const client = makeMockClient();
    const tool = createVectorSearchTool(client);
    expect(tool.description.length).toBeGreaterThan(10);
  });

  it('calls client.vectorSearch with the query vector', async () => {
    const client = makeMockClient();
    const queryVec = makeVector(384);
    const fakeResult: VectorSearchResult = {
      matches: [{ id: 'vec-001', score: 0.98 }],
    };
    client.vectorSearch.mockResolvedValueOnce(fakeResult);

    const tool = createVectorSearchTool(client);
    await tool.invoke({ vector: queryVec });

    expect(client.vectorSearch).toHaveBeenCalledWith(
      expect.objectContaining({ vector: queryVec }),
    );
  });

  it('rejects query vectors with invalid dimensions', async () => {
    const client = makeMockClient();
    const tool = createVectorSearchTool(client);

    const result = await tool.invoke({ vector: makeVector(256) });

    expect(result).toContain('Error');
    expect(client.vectorSearch).not.toHaveBeenCalled();
  });

  it('passes top_k to client when provided', async () => {
    const client = makeMockClient();
    client.vectorSearch.mockResolvedValueOnce({ matches: [] });

    const tool = createVectorSearchTool(client);
    await tool.invoke({ vector: makeVector(384), top_k: 10 });

    expect(client.vectorSearch).toHaveBeenCalledWith(
      expect.objectContaining({ top_k: 10 }),
    );
  });

  it('passes namespace filter to client when provided', async () => {
    const client = makeMockClient();
    client.vectorSearch.mockResolvedValueOnce({ matches: [] });

    const tool = createVectorSearchTool(client);
    await tool.invoke({ vector: makeVector(384), namespace: '0.0.456' });

    expect(client.vectorSearch).toHaveBeenCalledWith(
      expect.objectContaining({ namespace: '0.0.456' }),
    );
  });

  it('returns a message when no matches are found', async () => {
    const client = makeMockClient();
    client.vectorSearch.mockResolvedValueOnce({ matches: [] });

    const tool = createVectorSearchTool(client);
    const result = await tool.invoke({ vector: makeVector(384) });

    expect(result).toContain('No matches');
  });

  it('returns match ids and scores in result', async () => {
    const client = makeMockClient();
    client.vectorSearch.mockResolvedValueOnce({
      matches: [{ id: 'vec-100', score: 0.91 }],
    });

    const tool = createVectorSearchTool(client);
    const result = await tool.invoke({ vector: makeVector(384) });

    expect(result).toContain('vec-100');
    expect(result).toContain('0.91');
  });

  it('returns an error string when client.vectorSearch throws', async () => {
    const client = makeMockClient();
    client.vectorSearch.mockRejectedValueOnce({ status: 500, message: 'Internal error' });

    const tool = createVectorSearchTool(client);
    const result = await tool.invoke({ vector: makeVector(384) });

    expect(result).toContain('Error');
  });
});

// ─── createVectorDeleteTool ───────────────────────────────────────────────────

describe('createVectorDeleteTool', () => {
  it('returns a tool with the correct name', () => {
    const client = makeMockClient();
    const tool = createVectorDeleteTool(client);
    expect(tool.name).toBe('ainative_vector_delete');
  });

  it('returns a tool with a non-empty description', () => {
    const client = makeMockClient();
    const tool = createVectorDeleteTool(client);
    expect(tool.description.length).toBeGreaterThan(10);
  });

  it('calls client.vectorDelete with the vector id', async () => {
    const client = makeMockClient();
    const fakeResult: VectorDeleteResult = { success: true, id: 'vec-001' };
    client.vectorDelete.mockResolvedValueOnce(fakeResult);

    const tool = createVectorDeleteTool(client);
    await tool.invoke({ id: 'vec-001' });

    expect(client.vectorDelete).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'vec-001' }),
    );
  });

  it('passes namespace to client when provided', async () => {
    const client = makeMockClient();
    client.vectorDelete.mockResolvedValueOnce({ success: true, id: 'vec-002' });

    const tool = createVectorDeleteTool(client);
    await tool.invoke({ id: 'vec-002', namespace: '0.0.789' });

    expect(client.vectorDelete).toHaveBeenCalledWith(
      expect.objectContaining({ namespace: '0.0.789' }),
    );
  });

  it('returns a success message after deletion', async () => {
    const client = makeMockClient();
    client.vectorDelete.mockResolvedValueOnce({ success: true, id: 'vec-xyz' });

    const tool = createVectorDeleteTool(client);
    const result = await tool.invoke({ id: 'vec-xyz' });

    expect(result.toLowerCase()).toMatch(/deleted|removed|success/);
  });

  it('returns an error string when client.vectorDelete throws', async () => {
    const client = makeMockClient();
    client.vectorDelete.mockRejectedValueOnce({ status: 404, message: 'Vector not found' });

    const tool = createVectorDeleteTool(client);
    const result = await tool.invoke({ id: 'vec-missing' });

    expect(result).toContain('Error');
  });
});

// ─── getVectorTools ───────────────────────────────────────────────────────────

describe('getVectorTools', () => {
  it('returns an array of three tools', () => {
    const client = makeMockClient();
    const tools = getVectorTools(client);
    expect(tools).toHaveLength(3);
  });

  it('includes ainative_vector_upsert, ainative_vector_search, ainative_vector_delete', () => {
    const client = makeMockClient();
    const tools = getVectorTools(client);
    const names = tools.map((t) => t.name);
    expect(names).toContain('ainative_vector_upsert');
    expect(names).toContain('ainative_vector_search');
    expect(names).toContain('ainative_vector_delete');
  });
});
