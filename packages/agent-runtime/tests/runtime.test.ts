/**
 * @ainative/agent-runtime — AgentRuntime tests
 * Built by AINative Dev Team
 * Refs #246
 *
 * RED phase: All tests written before implementation.
 */

import { AgentRuntime } from '../src/runtime';
import type {
  RuntimeConfig,
  AgentTask,
  StorageAdapter,
  LLMProvider,
  TurnResult,
  ToolCall,
} from '../src/types';

// ─── Test Doubles ─────────────────────────────────────────────────────────────

function makeMockStorage(): jest.Mocked<StorageAdapter> {
  return {
    storeMemory: jest.fn().mockResolvedValue({ id: 'mem-1' }),
    recallMemory: jest.fn().mockResolvedValue([]),
    storeRecord: jest.fn().mockResolvedValue({ id: 'rec-1' }),
    queryRecords: jest.fn().mockResolvedValue([]),
  };
}

function makeMockLLM(): jest.Mocked<LLMProvider> {
  return {
    chat: jest.fn().mockResolvedValue({ content: 'I will use the search tool.', toolCalls: [] }),
    chatWithTools: jest.fn().mockResolvedValue({
      content: 'Done.',
      toolCalls: [],
    }),
  };
}

function makeTask(overrides: Partial<AgentTask> = {}): AgentTask {
  return {
    id: 'task-1',
    description: 'Summarize recent news',
    tools: [],
    metadata: {},
    ...overrides,
  };
}

// ─── Constructor ──────────────────────────────────────────────────────────────

describe('AgentRuntime', () => {
  describe('constructor', () => {
    it('creates runtime with required config', () => {
      const storage = makeMockStorage();
      const llmProvider = makeMockLLM();
      const runtime = new AgentRuntime({ storage, llmProvider });
      expect(runtime).toBeInstanceOf(AgentRuntime);
    });

    it('defaults maxTurns to 10 when not provided', () => {
      const runtime = new AgentRuntime({
        storage: makeMockStorage(),
        llmProvider: makeMockLLM(),
      });
      expect(runtime.maxTurns).toBe(10);
    });

    it('accepts custom maxTurns', () => {
      const runtime = new AgentRuntime({
        storage: makeMockStorage(),
        llmProvider: makeMockLLM(),
        maxTurns: 5,
      });
      expect(runtime.maxTurns).toBe(5);
    });

    it('accepts optional tools array', () => {
      const tool = { name: 'search', description: 'search the web', execute: jest.fn() };
      const runtime = new AgentRuntime({
        storage: makeMockStorage(),
        llmProvider: makeMockLLM(),
        tools: [tool],
      });
      expect(runtime).toBeInstanceOf(AgentRuntime);
    });
  });

  // ─── run() ────────────────────────────────────────────────────────────────

  describe('run()', () => {
    it('resolves with a result containing the task id', async () => {
      const storage = makeMockStorage();
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({ content: 'Final answer.', toolCalls: [] });

      const runtime = new AgentRuntime({ storage, llmProvider: llm, maxTurns: 1 });
      const result = await runtime.run(makeTask());
      expect(result.taskId).toBe('task-1');
    });

    it('resolves with status "complete" on success', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({ content: 'Done.', toolCalls: [] });

      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, maxTurns: 1 });
      const result = await runtime.run(makeTask());
      expect(result.status).toBe('complete');
    });

    it('stops after maxTurns and returns status "max_turns_reached"', async () => {
      const llm = makeMockLLM();
      // Always returns a tool call so the loop never self-terminates
      llm.chatWithTools.mockResolvedValue({
        content: '',
        toolCalls: [{ id: 'tc-1', name: 'search', args: { q: 'test' } }],
      });

      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, maxTurns: 3 });
      const task = makeTask({
        tools: [{ name: 'search', description: 'search', execute: jest.fn().mockResolvedValue('result') }],
      });
      const result = await runtime.run(task);
      expect(result.status).toBe('max_turns_reached');
      expect(result.turns).toHaveLength(3);
    });

    it('returns status "error" when LLM throws', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockRejectedValue(new Error('LLM unavailable'));

      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, maxTurns: 1 });
      const result = await runtime.run(makeTask());
      expect(result.status).toBe('error');
      expect(result.error).toMatch(/LLM unavailable/);
    });

    it('stores final result in storage', async () => {
      const storage = makeMockStorage();
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({ content: 'Final answer.', toolCalls: [] });

      const runtime = new AgentRuntime({ storage, llmProvider: llm, maxTurns: 1 });
      await runtime.run(makeTask({ id: 'task-42' }));

      expect(storage.storeRecord).toHaveBeenCalledWith(
        'agent_runs',
        expect.objectContaining({ taskId: 'task-42' }),
      );
    });
  });

  // ─── step() ───────────────────────────────────────────────────────────────

  describe('step()', () => {
    it('calls LLM chatWithTools with messages from context', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({ content: 'Thought.', toolCalls: [] });
      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm });

      await runtime.step({ messages: [{ role: 'user', content: 'hello' }], tools: [] });
      expect(llm.chatWithTools).toHaveBeenCalledWith(
        [{ role: 'user', content: 'hello' }],
        [],
        undefined,
      );
    });

    it('returns a TurnResult with thought from LLM', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({ content: 'My thought.', toolCalls: [] });
      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm });

      const turn: TurnResult = await runtime.step({ messages: [], tools: [] });
      expect(turn.thought).toBe('My thought.');
    });

    it('executes a tool call when LLM returns toolCalls', async () => {
      const mockTool = { name: 'calculator', description: 'math', execute: jest.fn().mockResolvedValue('42') };
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({
        content: '',
        toolCalls: [{ id: 'tc-1', name: 'calculator', args: { expr: '6*7' } }],
      });

      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, tools: [mockTool] });
      const turn = await runtime.step({ messages: [], tools: [mockTool] });

      expect(mockTool.execute).toHaveBeenCalledWith({ expr: '6*7' });
      expect(turn.toolCalls).toHaveLength(1);
      expect(turn.toolCalls[0].result).toBe('42');
    });

    it('records error for unknown tool in TurnResult', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({
        content: '',
        toolCalls: [{ id: 'tc-99', name: 'unknown-tool', args: {} }],
      });
      // No tools registered — unknown-tool won't be found
      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm });
      const turn = await runtime.step({ messages: [], tools: [] });
      expect(turn.toolCalls[0].error).toMatch(/unknown-tool/);
    });

    it('records tool error in TurnResult when tool throws', async () => {
      const mockTool = { name: 'fail-tool', description: 'fails', execute: jest.fn().mockRejectedValue(new Error('tool error')) };
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({
        content: '',
        toolCalls: [{ id: 'tc-2', name: 'fail-tool', args: {} }],
      });

      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, tools: [mockTool] });
      const turn = await runtime.step({ messages: [], tools: [mockTool] });

      expect(turn.toolCalls[0].error).toMatch(/tool error/);
    });
  });

  // ─── Event Emitter ────────────────────────────────────────────────────────

  describe('on() / event emitter', () => {
    it('emits "turn_start" at the beginning of each turn', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({ content: 'ok', toolCalls: [] });
      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, maxTurns: 2 });

      const events: unknown[] = [];
      runtime.on('turn_start', (data) => events.push(data));
      await runtime.run(makeTask());
      expect(events.length).toBeGreaterThanOrEqual(1);
    });

    it('emits "turn_end" after each completed turn', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({ content: 'ok', toolCalls: [] });
      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, maxTurns: 1 });

      const events: unknown[] = [];
      runtime.on('turn_end', (data) => events.push(data));
      await runtime.run(makeTask());
      expect(events).toHaveLength(1);
    });

    it('emits "tool_call" when a tool is invoked', async () => {
      const mockTool = { name: 'search', description: 'search', execute: jest.fn().mockResolvedValue('results') };
      const llm = makeMockLLM();
      llm.chatWithTools
        .mockResolvedValueOnce({ content: '', toolCalls: [{ id: 'tc-1', name: 'search', args: { q: 'hi' } }] })
        .mockResolvedValueOnce({ content: 'done', toolCalls: [] });

      const runtime = new AgentRuntime({
        storage: makeMockStorage(),
        llmProvider: llm,
        tools: [mockTool],
        maxTurns: 5,
      });

      const toolCallEvents: unknown[] = [];
      runtime.on('tool_call', (data) => toolCallEvents.push(data));
      await runtime.run(makeTask({ tools: [mockTool] }));
      expect(toolCallEvents.length).toBeGreaterThanOrEqual(1);
    });

    it('emits "tool_result" after each tool execution', async () => {
      const mockTool = { name: 'search', description: 'search', execute: jest.fn().mockResolvedValue('found it') };
      const llm = makeMockLLM();
      llm.chatWithTools
        .mockResolvedValueOnce({ content: '', toolCalls: [{ id: 'tc-1', name: 'search', args: {} }] })
        .mockResolvedValueOnce({ content: 'done', toolCalls: [] });

      const runtime = new AgentRuntime({
        storage: makeMockStorage(),
        llmProvider: llm,
        tools: [mockTool],
        maxTurns: 5,
      });

      const resultEvents: unknown[] = [];
      runtime.on('tool_result', (data) => resultEvents.push(data));
      await runtime.run(makeTask({ tools: [mockTool] }));
      expect(resultEvents.length).toBeGreaterThanOrEqual(1);
    });

    it('emits "complete" when the run finishes successfully', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({ content: 'done', toolCalls: [] });
      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, maxTurns: 1 });

      const completeEvents: unknown[] = [];
      runtime.on('complete', (data) => completeEvents.push(data));
      await runtime.run(makeTask());
      expect(completeEvents).toHaveLength(1);
    });

    it('emits "error" when the run fails', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockRejectedValue(new Error('boom'));
      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, maxTurns: 1 });

      const errorEvents: unknown[] = [];
      runtime.on('error', (data) => errorEvents.push(data));
      await runtime.run(makeTask());
      expect(errorEvents).toHaveLength(1);
    });

    it('supports multiple listeners on the same event', async () => {
      const llm = makeMockLLM();
      llm.chatWithTools.mockResolvedValue({ content: 'done', toolCalls: [] });
      const runtime = new AgentRuntime({ storage: makeMockStorage(), llmProvider: llm, maxTurns: 1 });

      const a: unknown[] = [];
      const b: unknown[] = [];
      runtime.on('complete', (d) => a.push(d));
      runtime.on('complete', (d) => b.push(d));
      await runtime.run(makeTask());
      expect(a).toHaveLength(1);
      expect(b).toHaveLength(1);
    });
  });
});
