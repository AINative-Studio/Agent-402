/**
 * Memory tools tests — RED phase first
 * Built by AINative Dev Team
 * Refs #183
 */

import { AINativeClient } from '../src/client';
import { createRememberTool } from '../src/tools/memory/remember';
import { createRecallTool } from '../src/tools/memory/recall';
import { createForgetTool } from '../src/tools/memory/forget';
import { createReflectTool } from '../src/tools/memory/reflect';
import { getMemoryTools } from '../src/tools/memory/index';
import {
  RememberResult,
  RecallResult,
  ForgetResult,
  ReflectResult,
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

// ─── createRememberTool ───────────────────────────────────────────────────────

describe('createRememberTool', () => {
  it('returns a tool with the correct name', () => {
    const client = makeMockClient();
    const tool = createRememberTool(client);
    expect(tool.name).toBe('ainative_remember');
  });

  it('returns a tool with a non-empty description', () => {
    const client = makeMockClient();
    const tool = createRememberTool(client);
    expect(tool.description.length).toBeGreaterThan(10);
  });

  it('calls client.remember with content and stores the memory', async () => {
    const client = makeMockClient();
    const fakeResult: RememberResult = {
      id: 'mem-001',
      content: 'User prefers dark mode',
      created_at: '2026-04-03T00:00:00Z',
    };
    client.remember.mockResolvedValueOnce(fakeResult);

    const tool = createRememberTool(client);
    const result = await tool.invoke({ content: 'User prefers dark mode' });

    expect(client.remember).toHaveBeenCalledWith(
      expect.objectContaining({ content: 'User prefers dark mode' }),
    );
    expect(result).toContain('mem-001');
  });

  it('passes agent_id to the client when provided', async () => {
    const client = makeMockClient();
    const fakeResult: RememberResult = {
      id: 'mem-002',
      content: 'Test memory',
      agent_id: 'agent-xyz',
      created_at: '2026-04-03T00:00:00Z',
    };
    client.remember.mockResolvedValueOnce(fakeResult);

    const tool = createRememberTool(client);
    await tool.invoke({ content: 'Test memory', agent_id: 'agent-xyz' });

    expect(client.remember).toHaveBeenCalledWith(
      expect.objectContaining({ agent_id: 'agent-xyz' }),
    );
  });

  it('passes metadata to the client when provided', async () => {
    const client = makeMockClient();
    const fakeResult: RememberResult = {
      id: 'mem-003',
      content: 'Meta memory',
      metadata: { source: 'test' },
      created_at: '2026-04-03T00:00:00Z',
    };
    client.remember.mockResolvedValueOnce(fakeResult);

    const tool = createRememberTool(client);
    await tool.invoke({ content: 'Meta memory', metadata: { source: 'test' } });

    expect(client.remember).toHaveBeenCalledWith(
      expect.objectContaining({ metadata: { source: 'test' } }),
    );
  });

  it('returns an error string when client.remember throws', async () => {
    const client = makeMockClient();
    client.remember.mockRejectedValueOnce({ status: 401, message: 'Unauthorized' });

    const tool = createRememberTool(client);
    const result = await tool.invoke({ content: 'Test' });

    expect(result).toContain('Error');
  });
});

// ─── createRecallTool ─────────────────────────────────────────────────────────

describe('createRecallTool', () => {
  it('returns a tool with the correct name', () => {
    const client = makeMockClient();
    const tool = createRecallTool(client);
    expect(tool.name).toBe('ainative_recall');
  });

  it('returns a tool with a non-empty description', () => {
    const client = makeMockClient();
    const tool = createRecallTool(client);
    expect(tool.description.length).toBeGreaterThan(10);
  });

  it('calls client.recall with the query', async () => {
    const client = makeMockClient();
    const fakeResult: RecallResult = {
      memories: [
        { id: 'mem-001', content: 'User prefers dark mode', score: 0.95 },
      ],
    };
    client.recall.mockResolvedValueOnce(fakeResult);

    const tool = createRecallTool(client);
    const result = await tool.invoke({ query: 'user preferences' });

    expect(client.recall).toHaveBeenCalledWith(
      expect.objectContaining({ query: 'user preferences' }),
    );
    expect(result).toContain('dark mode');
  });

  it('passes limit to client when provided', async () => {
    const client = makeMockClient();
    client.recall.mockResolvedValueOnce({ memories: [] });

    const tool = createRecallTool(client);
    await tool.invoke({ query: 'test', limit: 5 });

    expect(client.recall).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 5 }),
    );
  });

  it('passes agent_id filter to client when provided', async () => {
    const client = makeMockClient();
    client.recall.mockResolvedValueOnce({ memories: [] });

    const tool = createRecallTool(client);
    await tool.invoke({ query: 'test', agent_id: 'agent-123' });

    expect(client.recall).toHaveBeenCalledWith(
      expect.objectContaining({ agent_id: 'agent-123' }),
    );
  });

  it('returns a message when no memories are found', async () => {
    const client = makeMockClient();
    client.recall.mockResolvedValueOnce({ memories: [] });

    const tool = createRecallTool(client);
    const result = await tool.invoke({ query: 'nothing here' });

    expect(result).toContain('No memories');
  });

  it('returns an error string when client.recall throws', async () => {
    const client = makeMockClient();
    client.recall.mockRejectedValueOnce({ status: 500, message: 'Server error' });

    const tool = createRecallTool(client);
    const result = await tool.invoke({ query: 'test' });

    expect(result).toContain('Error');
  });
});

// ─── createForgetTool ─────────────────────────────────────────────────────────

describe('createForgetTool', () => {
  it('returns a tool with the correct name', () => {
    const client = makeMockClient();
    const tool = createForgetTool(client);
    expect(tool.name).toBe('ainative_forget');
  });

  it('returns a tool with a non-empty description', () => {
    const client = makeMockClient();
    const tool = createForgetTool(client);
    expect(tool.description.length).toBeGreaterThan(10);
  });

  it('calls client.forget with the memory ID', async () => {
    const client = makeMockClient();
    const fakeResult: ForgetResult = { success: true, id: 'mem-001' };
    client.forget.mockResolvedValueOnce(fakeResult);

    const tool = createForgetTool(client);
    const result = await tool.invoke({ id: 'mem-001' });

    expect(client.forget).toHaveBeenCalledWith({ id: 'mem-001' });
    expect(result).toContain('mem-001');
  });

  it('returns a success message when deletion succeeds', async () => {
    const client = makeMockClient();
    client.forget.mockResolvedValueOnce({ success: true, id: 'mem-abc' });

    const tool = createForgetTool(client);
    const result = await tool.invoke({ id: 'mem-abc' });

    expect(result.toLowerCase()).toMatch(/deleted|removed|forgotten|success/);
  });

  it('returns an error string when client.forget throws', async () => {
    const client = makeMockClient();
    client.forget.mockRejectedValueOnce({ status: 404, message: 'Not found' });

    const tool = createForgetTool(client);
    const result = await tool.invoke({ id: 'mem-missing' });

    expect(result).toContain('Error');
  });
});

// ─── createReflectTool ────────────────────────────────────────────────────────

describe('createReflectTool', () => {
  it('returns a tool with the correct name', () => {
    const client = makeMockClient();
    const tool = createReflectTool(client);
    expect(tool.name).toBe('ainative_reflect');
  });

  it('returns a tool with a non-empty description', () => {
    const client = makeMockClient();
    const tool = createReflectTool(client);
    expect(tool.description.length).toBeGreaterThan(10);
  });

  it('calls client.reflect with agent_id', async () => {
    const client = makeMockClient();
    const fakeResult: ReflectResult = {
      summary: 'User is a developer who prefers dark mode.',
      entities: ['dark mode', 'developer'],
      agent_id: 'agent-xyz',
    };
    client.reflect.mockResolvedValueOnce(fakeResult);

    const tool = createReflectTool(client);
    const result = await tool.invoke({ agent_id: 'agent-xyz' });

    expect(client.reflect).toHaveBeenCalledWith(
      expect.objectContaining({ agent_id: 'agent-xyz' }),
    );
    expect(result).toContain('developer');
  });

  it('passes optional topic to client when provided', async () => {
    const client = makeMockClient();
    client.reflect.mockResolvedValueOnce({
      summary: 'Topic summary',
      entities: [],
      agent_id: 'agent-1',
    });

    const tool = createReflectTool(client);
    await tool.invoke({ agent_id: 'agent-1', topic: 'preferences' });

    expect(client.reflect).toHaveBeenCalledWith(
      expect.objectContaining({ topic: 'preferences' }),
    );
  });

  it('returns an error string when client.reflect throws', async () => {
    const client = makeMockClient();
    client.reflect.mockRejectedValueOnce({ status: 422, message: 'Unprocessable' });

    const tool = createReflectTool(client);
    const result = await tool.invoke({ agent_id: 'agent-bad' });

    expect(result).toContain('Error');
  });
});

// ─── getMemoryTools ───────────────────────────────────────────────────────────

describe('getMemoryTools', () => {
  it('returns an array of four tools', () => {
    const client = makeMockClient();
    const tools = getMemoryTools(client);
    expect(tools).toHaveLength(4);
  });

  it('includes ainative_remember, ainative_recall, ainative_forget, ainative_reflect', () => {
    const client = makeMockClient();
    const tools = getMemoryTools(client);
    const names = tools.map((t) => t.name);
    expect(names).toContain('ainative_remember');
    expect(names).toContain('ainative_recall');
    expect(names).toContain('ainative_forget');
    expect(names).toContain('ainative_reflect');
  });
});
