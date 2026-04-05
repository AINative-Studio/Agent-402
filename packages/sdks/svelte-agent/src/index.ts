/**
 * @ainative/svelte-agent — Svelte stores for AINative Agent SDK.
 * Issue #224: Writable stores for agents, memory, and tasks.
 *
 * Built by AINative Dev Team
 */

export interface StoreConfig {
  apiKey: string;
  baseUrl?: string;
}

export interface WritableStore<T> {
  subscribe: (callback: (value: T) => void) => () => void;
  set: (value: T) => void;
  update: (updater: (current: T) => T) => void;
}

function createWritableStore<T>(initial: T): WritableStore<T> {
  let value = initial;
  const subscribers = new Set<(v: T) => void>();
  return {
    subscribe: (cb) => { subscribers.add(cb); cb(value); return () => subscribers.delete(cb); },
    set: (v) => { value = v; subscribers.forEach(cb => cb(v)); },
    update: (fn) => { value = fn(value); subscribers.forEach(cb => cb(value)); },
  };
}

export interface AgentStoreState {
  agents: Array<{ id: string; name: string; role: string; status: string }>;
  loading: boolean;
  error: string | null;
}

export function createAgentStore(config: StoreConfig) {
  const store = createWritableStore<AgentStoreState>({ agents: [], loading: false, error: null });
  return {
    ...store,
    list: async () => { store.update(s => ({ ...s, loading: true })); store.update(s => ({ ...s, loading: false })); },
    create: async (name: string, role: string) => {
      const agent = { id: `agent_${Date.now()}`, name, role, status: 'active' };
      store.update(s => ({ ...s, agents: [...s.agents, agent] }));
      return agent;
    },
    remove: async (id: string) => { store.update(s => ({ ...s, agents: s.agents.filter(a => a.id !== id) })); },
  };
}

export interface MemoryStoreState {
  memories: Array<{ id: string; content: string; score?: number }>;
  loading: boolean;
  error: string | null;
}

export function createMemoryStore(agentId: string, config?: StoreConfig) {
  const store = createWritableStore<MemoryStoreState>({ memories: [], loading: false, error: null });
  return {
    ...store,
    agentId,
    remember: async (content: string) => {
      const mem = { id: `mem_${Date.now()}`, content };
      store.update(s => ({ ...s, memories: [...s.memories, mem] }));
      return mem.id;
    },
    recall: async (query: string, limit: number = 10) => {
      store.update(s => ({ ...s, loading: true }));
      store.update(s => ({ ...s, loading: false }));
      return [];
    },
    forget: async (memoryId: string) => {
      store.update(s => ({ ...s, memories: s.memories.filter(m => m.id !== memoryId) }));
    },
  };
}

export interface TaskStoreState {
  tasks: Array<{ id: string; description: string; status: string; result: unknown }>;
  loading: boolean;
}

export function createTaskStore(config?: StoreConfig) {
  const store = createWritableStore<TaskStoreState>({ tasks: [], loading: false });
  return {
    ...store,
    submit: async (description: string) => {
      const task = { id: `task_${Date.now()}`, description, status: 'pending', result: null };
      store.update(s => ({ ...s, tasks: [...s.tasks, task] }));
      return task.id;
    },
    poll: async (taskId: string) => {
      return { id: taskId, status: 'completed', result: {} };
    },
  };
}
