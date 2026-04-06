/**
 * @ainative/agent-sdk — React hooks unit tests
 * Built by AINative Dev Team
 * Refs #222
 *
 * Tests use React Testing Library patterns with jest mocks.
 * All hooks are tested as pure state machines without a DOM — we call the
 * factory functions directly and verify the returned state/actions.
 */

import {
  createAgentSwarmHook,
  createAgentMemoryHook,
  createAgentTaskHook,
  createAgentEventsHook,
} from '../src/hooks';
import type { SwarmConfig, SwarmState } from '../src/hooks/useAgentSwarm';
import type { AgentMemoryState } from '../src/hooks/useAgentMemory';
import type { AgentTaskState } from '../src/hooks/useAgentTask';
import type { AgentEventsState } from '../src/hooks/useAgentEvents';

// ─── Shared test fixtures ─────────────────────────────────────────────────────

function makeMemory(overrides: Partial<{ id: string; content: string }> = {}) {
  return {
    id: overrides.id ?? 'mem-1',
    content: overrides.content ?? 'test memory',
    namespace: 'default',
    metadata: {},
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  };
}

function makeAgent(overrides: Partial<{ id: string; name: string }> = {}) {
  return {
    id: overrides.id ?? 'agent-1',
    name: overrides.name ?? 'Agent Alpha',
    role: 'researcher',
    did: 'did:hedera:1',
    scope: 'RUN' as const,
    projectId: 'proj-1',
    status: 'active',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  };
}

function makeTask(overrides: Partial<{ id: string; status: string }> = {}) {
  return {
    id: overrides.id ?? 'task-1',
    description: 'do work',
    agent_types: ['researcher'],
    status: (overrides.status ?? 'pending') as 'pending' | 'running' | 'completed' | 'failed' | 'cancelled',
    projectId: 'proj-1',
    config: {},
    priority: 0,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  };
}

// ─── useAgentSwarm ────────────────────────────────────────────────────────────

describe('useAgentSwarm', () => {
  const swarmConfig: SwarmConfig = {
    projectId: 'proj-1',
    agentConfigs: [
      { name: 'Alpha', role: 'researcher' },
      { name: 'Beta', role: 'writer' },
    ],
  };

  describe('initial state', () => {
    it('returns empty agents list on mount', () => {
      const { getState } = createAgentSwarmHook(swarmConfig);
      const state: SwarmState = getState();
      expect(state.agents).toEqual([]);
    });

    it('returns empty tasks list on mount', () => {
      const { getState } = createAgentSwarmHook(swarmConfig);
      expect(getState().tasks).toEqual([]);
    });

    it('returns idle status on mount', () => {
      const { getState } = createAgentSwarmHook(swarmConfig);
      expect(getState().status).toBe('idle');
    });

    it('exposes a start action', () => {
      const hook = createAgentSwarmHook(swarmConfig);
      expect(typeof hook.start).toBe('function');
    });

    it('exposes a stop action', () => {
      const hook = createAgentSwarmHook(swarmConfig);
      expect(typeof hook.stop).toBe('function');
    });

    it('exposes a dispatch action', () => {
      const hook = createAgentSwarmHook(swarmConfig);
      expect(typeof hook.dispatch).toBe('function');
    });
  });

  describe('start()', () => {
    it('transitions status to running after start', async () => {
      const mockSdk = {
        agents: {
          create: jest.fn().mockResolvedValue(makeAgent()),
          tasks: { create: jest.fn().mockResolvedValue(makeTask()) },
        },
      };
      const hook = createAgentSwarmHook(swarmConfig, mockSdk as never);
      await hook.start();
      expect(hook.getState().status).toBe('running');
    });

    it('populates agents after start', async () => {
      const agentA = makeAgent({ id: 'a-1', name: 'Alpha' });
      const agentB = makeAgent({ id: 'a-2', name: 'Beta' });
      const mockSdk = {
        agents: {
          create: jest.fn()
            .mockResolvedValueOnce(agentA)
            .mockResolvedValueOnce(agentB),
          tasks: { create: jest.fn().mockResolvedValue(makeTask()) },
        },
      };
      const hook = createAgentSwarmHook(swarmConfig, mockSdk as never);
      await hook.start();
      expect(hook.getState().agents).toHaveLength(2);
    });

    it('transitions to error status when agent creation fails', async () => {
      const mockSdk = {
        agents: {
          create: jest.fn().mockRejectedValue(new Error('API down')),
          tasks: { create: jest.fn() },
        },
      };
      const hook = createAgentSwarmHook(swarmConfig, mockSdk as never);
      await hook.start();
      expect(hook.getState().status).toBe('error');
    });
  });

  describe('stop()', () => {
    it('transitions status to idle after stop', async () => {
      const mockSdk = {
        agents: {
          create: jest.fn().mockResolvedValue(makeAgent()),
          tasks: { create: jest.fn().mockResolvedValue(makeTask()) },
        },
      };
      const hook = createAgentSwarmHook(swarmConfig, mockSdk as never);
      await hook.start();
      hook.stop();
      expect(hook.getState().status).toBe('idle');
    });

    it('clears agents after stop', async () => {
      const mockSdk = {
        agents: {
          create: jest.fn().mockResolvedValue(makeAgent()),
          tasks: { create: jest.fn().mockResolvedValue(makeTask()) },
        },
      };
      const hook = createAgentSwarmHook(swarmConfig, mockSdk as never);
      await hook.start();
      hook.stop();
      expect(hook.getState().agents).toEqual([]);
    });
  });

  describe('dispatch()', () => {
    it('adds a task to the tasks list after dispatch', async () => {
      const task = makeTask({ id: 'dispatched-task' });
      const mockSdk = {
        agents: {
          create: jest.fn().mockResolvedValue(makeAgent()),
          tasks: { create: jest.fn().mockResolvedValue(task) },
        },
      };
      const hook = createAgentSwarmHook(swarmConfig, mockSdk as never);
      await hook.start();
      await hook.dispatch({ description: 'do work' });
      expect(hook.getState().tasks).toContainEqual(expect.objectContaining({ id: 'dispatched-task' }));
    });
  });
});

// ─── useAgentMemory ───────────────────────────────────────────────────────────

describe('useAgentMemory', () => {
  const agentId = 'agent-42';

  describe('initial state', () => {
    it('returns empty memories array on mount', () => {
      const { getState } = createAgentMemoryHook(agentId);
      const state: AgentMemoryState = getState();
      expect(state.memories).toEqual([]);
    });

    it('returns loading false on mount', () => {
      const { getState } = createAgentMemoryHook(agentId);
      expect(getState().loading).toBe(false);
    });

    it('exposes remember action', () => {
      const hook = createAgentMemoryHook(agentId);
      expect(typeof hook.remember).toBe('function');
    });

    it('exposes recall action', () => {
      const hook = createAgentMemoryHook(agentId);
      expect(typeof hook.recall).toBe('function');
    });

    it('exposes forget action', () => {
      const hook = createAgentMemoryHook(agentId);
      expect(typeof hook.forget).toBe('function');
    });
  });

  describe('remember()', () => {
    it('adds returned memory to memories list', async () => {
      const memory = makeMemory({ content: 'learned something' });
      const mockSdk = {
        memory: { remember: jest.fn().mockResolvedValue(memory) },
      };
      const hook = createAgentMemoryHook(agentId, mockSdk as never);
      await hook.remember('learned something');
      expect(hook.getState().memories).toContainEqual(memory);
    });

    it('sets loading true during the async call', async () => {
      let capturedLoading = false;
      const mockSdk = {
        memory: {
          remember: jest.fn().mockImplementation(async () => {
            capturedLoading = hook.getState().loading;
            return makeMemory();
          }),
        },
      };
      const hook = createAgentMemoryHook(agentId, mockSdk as never);
      await hook.remember('test');
      expect(capturedLoading).toBe(true);
    });

    it('resets loading to false after remember resolves', async () => {
      const mockSdk = {
        memory: { remember: jest.fn().mockResolvedValue(makeMemory()) },
      };
      const hook = createAgentMemoryHook(agentId, mockSdk as never);
      await hook.remember('test');
      expect(hook.getState().loading).toBe(false);
    });

    it('calls sdk.memory.remember with agentId in options', async () => {
      const mockSdk = {
        memory: { remember: jest.fn().mockResolvedValue(makeMemory()) },
      };
      const hook = createAgentMemoryHook(agentId, mockSdk as never);
      await hook.remember('content');
      expect(mockSdk.memory.remember).toHaveBeenCalledWith('content', expect.objectContaining({ agentId }));
    });
  });

  describe('recall()', () => {
    it('returns matching memories from the SDK', async () => {
      const memories = [makeMemory({ id: 'r-1' }), makeMemory({ id: 'r-2' })];
      const mockSdk = {
        memory: { recall: jest.fn().mockResolvedValue({ memories, query: 'test', total: 2 }) },
      };
      const hook = createAgentMemoryHook(agentId, mockSdk as never);
      const result = await hook.recall('test query');
      expect(result).toEqual(memories);
    });

    it('updates state memories with recalled results', async () => {
      const memories = [makeMemory()];
      const mockSdk = {
        memory: { recall: jest.fn().mockResolvedValue({ memories, query: 'q', total: 1 }) },
      };
      const hook = createAgentMemoryHook(agentId, mockSdk as never);
      await hook.recall('q');
      expect(hook.getState().memories).toEqual(memories);
    });
  });

  describe('forget()', () => {
    it('removes forgotten memory from memories list', async () => {
      const mem = makeMemory({ id: 'to-forget' });
      const mockRemember = jest.fn().mockResolvedValue(mem);
      const mockForget = jest.fn().mockResolvedValue(undefined);
      const mockSdk = {
        memory: { remember: mockRemember, forget: mockForget },
      };
      const hook = createAgentMemoryHook(agentId, mockSdk as never);
      await hook.remember('something');
      await hook.forget('to-forget');
      expect(hook.getState().memories.find(m => m.id === 'to-forget')).toBeUndefined();
    });

    it('calls sdk.memory.forget with the memory id', async () => {
      const mockSdk = {
        memory: { forget: jest.fn().mockResolvedValue(undefined) },
      };
      const hook = createAgentMemoryHook(agentId, mockSdk as never);
      await hook.forget('mem-xyz');
      expect(mockSdk.memory.forget).toHaveBeenCalledWith('mem-xyz');
    });
  });
});

// ─── useAgentTask ─────────────────────────────────────────────────────────────

describe('useAgentTask', () => {
  const taskId = 'task-99';

  describe('initial state', () => {
    it('returns null task on mount', () => {
      const { getState } = createAgentTaskHook(taskId);
      const state: AgentTaskState = getState();
      expect(state.task).toBeNull();
    });

    it('returns null result on mount', () => {
      const { getState } = createAgentTaskHook(taskId);
      expect(getState().result).toBeNull();
    });

    it('returns null error on mount', () => {
      const { getState } = createAgentTaskHook(taskId);
      expect(getState().error).toBeNull();
    });

    it('returns 0 progress on mount', () => {
      const { getState } = createAgentTaskHook(taskId);
      expect(getState().progress).toBe(0);
    });

    it('returns pending status on mount', () => {
      const { getState } = createAgentTaskHook(taskId);
      expect(getState().status).toBe('pending');
    });

    it('exposes a fetch action', () => {
      const hook = createAgentTaskHook(taskId);
      expect(typeof hook.fetch).toBe('function');
    });

    it('exposes a poll action', () => {
      const hook = createAgentTaskHook(taskId);
      expect(typeof hook.poll).toBe('function');
    });
  });

  describe('fetch()', () => {
    it('populates task after fetch', async () => {
      const task = makeTask({ id: taskId, status: 'running' });
      const mockSdk = { agents: { tasks: { get: jest.fn().mockResolvedValue(task) } } };
      const hook = createAgentTaskHook(taskId, mockSdk as never);
      await hook.fetch();
      expect(hook.getState().task).toEqual(task);
    });

    it('sets status from fetched task', async () => {
      const task = makeTask({ id: taskId, status: 'completed' });
      const mockSdk = { agents: { tasks: { get: jest.fn().mockResolvedValue(task) } } };
      const hook = createAgentTaskHook(taskId, mockSdk as never);
      await hook.fetch();
      expect(hook.getState().status).toBe('completed');
    });

    it('sets result when task is completed', async () => {
      const task = { ...makeTask({ id: taskId, status: 'completed' }), result: { output: 'done' } };
      const mockSdk = { agents: { tasks: { get: jest.fn().mockResolvedValue(task) } } };
      const hook = createAgentTaskHook(taskId, mockSdk as never);
      await hook.fetch();
      expect(hook.getState().result).toEqual({ output: 'done' });
    });

    it('sets error message when task has failed', async () => {
      const task = { ...makeTask({ id: taskId, status: 'failed' }), error: 'timeout' };
      const mockSdk = { agents: { tasks: { get: jest.fn().mockResolvedValue(task) } } };
      const hook = createAgentTaskHook(taskId, mockSdk as never);
      await hook.fetch();
      expect(hook.getState().error).toBe('timeout');
    });

    it('sets progress to 100 when task is completed', async () => {
      const task = makeTask({ id: taskId, status: 'completed' });
      const mockSdk = { agents: { tasks: { get: jest.fn().mockResolvedValue(task) } } };
      const hook = createAgentTaskHook(taskId, mockSdk as never);
      await hook.fetch();
      expect(hook.getState().progress).toBe(100);
    });

    it('sets progress to 50 when task is running', async () => {
      const task = makeTask({ id: taskId, status: 'running' });
      const mockSdk = { agents: { tasks: { get: jest.fn().mockResolvedValue(task) } } };
      const hook = createAgentTaskHook(taskId, mockSdk as never);
      await hook.fetch();
      expect(hook.getState().progress).toBe(50);
    });
  });

  describe('poll()', () => {
    it('resolves when the task reaches completed status', async () => {
      const task = makeTask({ id: taskId, status: 'completed' });
      const mockSdk = { agents: { tasks: { get: jest.fn().mockResolvedValue(task) } } };
      const hook = createAgentTaskHook(taskId, mockSdk as never);
      await expect(hook.poll({ intervalMs: 10, maxAttempts: 3 })).resolves.toBeUndefined();
    });

    it('resolves when the task reaches failed status', async () => {
      const task = makeTask({ id: taskId, status: 'failed' });
      const mockSdk = { agents: { tasks: { get: jest.fn().mockResolvedValue(task) } } };
      const hook = createAgentTaskHook(taskId, mockSdk as never);
      await expect(hook.poll({ intervalMs: 10, maxAttempts: 3 })).resolves.toBeUndefined();
    });

    it('rejects with timeout error if task never reaches terminal status', async () => {
      const task = makeTask({ id: taskId, status: 'running' });
      const mockSdk = { agents: { tasks: { get: jest.fn().mockResolvedValue(task) } } };
      const hook = createAgentTaskHook(taskId, mockSdk as never);
      await expect(hook.poll({ intervalMs: 10, maxAttempts: 2 })).rejects.toThrow('timeout');
    });
  });
});

// ─── useAgentEvents ───────────────────────────────────────────────────────────

describe('useAgentEvents', () => {
  const agentId = 'agent-events-1';

  describe('initial state', () => {
    it('returns empty events array on mount', () => {
      const { getState } = createAgentEventsHook(agentId, ['task.completed']);
      const state: AgentEventsState = getState();
      expect(state.events).toEqual([]);
    });

    it('returns connected false on mount', () => {
      const { getState } = createAgentEventsHook(agentId, []);
      expect(getState().connected).toBe(false);
    });

    it('exposes a subscribe action', () => {
      const hook = createAgentEventsHook(agentId, []);
      expect(typeof hook.subscribe).toBe('function');
    });

    it('exposes an unsubscribe action', () => {
      const hook = createAgentEventsHook(agentId, []);
      expect(typeof hook.unsubscribe).toBe('function');
    });

    it('exposes a clearEvents action', () => {
      const hook = createAgentEventsHook(agentId, []);
      expect(typeof hook.clearEvents).toBe('function');
    });
  });

  describe('subscribe()', () => {
    it('sets connected to true after subscribe', () => {
      const mockEmitter = { on: jest.fn(), off: jest.fn(), emit: jest.fn() };
      const hook = createAgentEventsHook(agentId, ['task.completed'], mockEmitter as never);
      hook.subscribe();
      expect(hook.getState().connected).toBe(true);
    });

    it('registers event listeners for each event type', () => {
      const mockEmitter = { on: jest.fn(), off: jest.fn(), emit: jest.fn() };
      const hook = createAgentEventsHook(agentId, ['task.completed', 'task.failed'], mockEmitter as never);
      hook.subscribe();
      expect(mockEmitter.on).toHaveBeenCalledTimes(2);
    });

    it('registers listener for the specified event type', () => {
      const mockEmitter = { on: jest.fn(), off: jest.fn(), emit: jest.fn() };
      const hook = createAgentEventsHook(agentId, ['task.completed'], mockEmitter as never);
      hook.subscribe();
      expect(mockEmitter.on).toHaveBeenCalledWith('task.completed', expect.any(Function));
    });
  });

  describe('unsubscribe()', () => {
    it('sets connected to false after unsubscribe', () => {
      const mockEmitter = { on: jest.fn(), off: jest.fn(), emit: jest.fn() };
      const hook = createAgentEventsHook(agentId, ['task.completed'], mockEmitter as never);
      hook.subscribe();
      hook.unsubscribe();
      expect(hook.getState().connected).toBe(false);
    });

    it('removes event listeners for each event type', () => {
      const mockEmitter = { on: jest.fn(), off: jest.fn(), emit: jest.fn() };
      const hook = createAgentEventsHook(agentId, ['task.completed', 'task.failed'], mockEmitter as never);
      hook.subscribe();
      hook.unsubscribe();
      expect(mockEmitter.off).toHaveBeenCalledTimes(2);
    });
  });

  describe('event reception', () => {
    it('appends incoming events to the events list', () => {
      let listener: ((e: unknown) => void) | undefined;
      const mockEmitter = {
        on: jest.fn((_, cb) => { listener = cb; }),
        off: jest.fn(),
        emit: jest.fn(),
      };
      const hook = createAgentEventsHook(agentId, ['task.completed'], mockEmitter as never);
      hook.subscribe();
      const event = { type: 'task.completed', payload: { taskId: 'abc' } };
      listener!(event);
      expect(hook.getState().events).toContainEqual(event);
    });
  });

  describe('clearEvents()', () => {
    it('empties the events list', () => {
      let listener: ((e: unknown) => void) | undefined;
      const mockEmitter = {
        on: jest.fn((_, cb) => { listener = cb; }),
        off: jest.fn(),
        emit: jest.fn(),
      };
      const hook = createAgentEventsHook(agentId, ['task.completed'], mockEmitter as never);
      hook.subscribe();
      listener!({ type: 'task.completed', payload: {} });
      hook.clearEvents();
      expect(hook.getState().events).toEqual([]);
    });
  });
});
