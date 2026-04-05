/**
 * React hooks for AINative Agent SDK.
 * Issue #222: Agent swarm and memory hooks.
 *
 * Built by AINative Dev Team
 */

export interface UseAgentSwarmConfig {
  apiKey: string;
  baseUrl?: string;
  agentTypes?: string[];
}

export interface SwarmState {
  agents: AgentInfo[];
  tasks: TaskInfo[];
  status: 'idle' | 'running' | 'completed' | 'error';
  error: string | null;
}

export interface AgentInfo {
  id: string;
  name: string;
  role: string;
  status: string;
}

export interface TaskInfo {
  id: string;
  description: string;
  status: string;
  progress: number;
  result: unknown | null;
}

export interface MemoryState {
  memories: MemoryEntry[];
  loading: boolean;
  error: string | null;
}

export interface MemoryEntry {
  id: string;
  content: string;
  score?: number;
  created_at?: string;
}

export interface TaskState {
  task: TaskInfo | null;
  status: string;
  progress: number;
  result: unknown | null;
  error: string | null;
}

export interface EventSubscription {
  id: string;
  unsubscribe: () => void;
}

/**
 * Hook to manage an agent swarm lifecycle.
 * Returns reactive state for agents, tasks, and swarm status.
 */
export function useAgentSwarm(config: UseAgentSwarmConfig): {
  state: SwarmState;
  submitTask: (description: string, agentTypes?: string[]) => Promise<string>;
  cancelTask: (taskId: string) => Promise<void>;
  refresh: () => Promise<void>;
} {
  const state: SwarmState = {
    agents: [],
    tasks: [],
    status: 'idle',
    error: null,
  };

  return {
    state,
    submitTask: async (description: string, _agentTypes?: string[]) => {
      state.status = 'running';
      // In real impl, calls sdk.tasks.create()
      return `task_${Date.now()}`;
    },
    cancelTask: async (_taskId: string) => {
      state.status = 'idle';
    },
    refresh: async () => {
      // In real impl, polls sdk.agents.list() and sdk.tasks.list()
    },
  };
}

/**
 * Hook for agent memory operations.
 * Provides remember, recall, forget with reactive state.
 */
export function useAgentMemory(agentId: string, config?: { apiKey?: string; baseUrl?: string }): {
  state: MemoryState;
  remember: (content: string, metadata?: Record<string, unknown>) => Promise<string>;
  recall: (query: string, limit?: number) => Promise<MemoryEntry[]>;
  forget: (memoryId: string) => Promise<void>;
} {
  const state: MemoryState = {
    memories: [],
    loading: false,
    error: null,
  };

  return {
    state,
    remember: async (content: string, _metadata?: Record<string, unknown>) => {
      state.loading = true;
      const id = `mem_${Date.now()}`;
      state.memories.push({ id, content });
      state.loading = false;
      return id;
    },
    recall: async (query: string, limit: number = 10) => {
      state.loading = true;
      // In real impl, calls sdk.memory.recall(query, { limit })
      state.loading = false;
      return state.memories.slice(0, limit);
    },
    forget: async (memoryId: string) => {
      state.memories = state.memories.filter(m => m.id !== memoryId);
    },
  };
}

/**
 * Hook for tracking a single task's lifecycle.
 */
export function useAgentTask(taskId: string, config?: { apiKey?: string; baseUrl?: string }): {
  state: TaskState;
  poll: () => Promise<void>;
  cancel: () => Promise<void>;
} {
  const state: TaskState = {
    task: null,
    status: 'pending',
    progress: 0,
    result: null,
    error: null,
  };

  return {
    state,
    poll: async () => {
      // In real impl, calls sdk.tasks.get(taskId)
    },
    cancel: async () => {
      state.status = 'cancelled';
    },
  };
}

/**
 * Hook for real-time agent event subscription.
 */
export function useAgentEvents(
  agentId: string,
  eventTypes: string[],
  config?: { apiKey?: string; baseUrl?: string }
): {
  events: Array<{ type: string; payload: unknown; timestamp: string }>;
  connected: boolean;
  subscribe: () => EventSubscription;
  unsubscribe: (subscriptionId: string) => void;
} {
  const events: Array<{ type: string; payload: unknown; timestamp: string }> = [];
  let connected = false;

  return {
    events,
    connected,
    subscribe: () => {
      connected = true;
      const id = `sub_${Date.now()}`;
      return { id, unsubscribe: () => { connected = false; } };
    },
    unsubscribe: (_subscriptionId: string) => {
      connected = false;
    },
  };
}
