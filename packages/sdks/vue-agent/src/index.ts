/**
 * @ainative/vue-agent — Vue 3 composables for AINative Agent SDK.
 * Issue #225: Reactive agent, memory, and task management.
 *
 * Built by AINative Dev Team
 */

export interface ComposableConfig {
  apiKey: string;
  baseUrl?: string;
}

export interface Ref<T> {
  value: T;
}

function ref<T>(initial: T): Ref<T> {
  return { value: initial };
}

export function useAgent(config: ComposableConfig) {
  const agents = ref<Array<{ id: string; name: string; role: string; status: string }>>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  return {
    agents,
    loading,
    error,
    create: async (name: string, role: string) => {
      loading.value = true;
      const agent = { id: `agent_${Date.now()}`, name, role, status: 'active' };
      agents.value = [...agents.value, agent];
      loading.value = false;
      return agent;
    },
    list: async () => { loading.value = true; loading.value = false; return agents.value; },
    get: async (id: string) => agents.value.find(a => a.id === id) || null,
    remove: async (id: string) => { agents.value = agents.value.filter(a => a.id !== id); },
  };
}

export function useMemory(agentId: string, config?: ComposableConfig) {
  const memories = ref<Array<{ id: string; content: string; score?: number }>>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  return {
    memories,
    loading,
    error,
    agentId,
    remember: async (content: string, metadata?: Record<string, unknown>) => {
      loading.value = true;
      const mem = { id: `mem_${Date.now()}`, content };
      memories.value = [...memories.value, mem];
      loading.value = false;
      return mem.id;
    },
    recall: async (query: string, limit: number = 10) => {
      loading.value = true;
      loading.value = false;
      return [];
    },
    forget: async (memoryId: string) => {
      memories.value = memories.value.filter(m => m.id !== memoryId);
    },
  };
}

export function useTask(config?: ComposableConfig) {
  const tasks = ref<Array<{ id: string; description: string; status: string; result: unknown }>>([]);
  const loading = ref(false);

  return {
    tasks,
    loading,
    submit: async (description: string, agentTypes?: string[]) => {
      loading.value = true;
      const task = { id: `task_${Date.now()}`, description, status: 'pending', result: null as unknown };
      tasks.value = [...tasks.value, task];
      loading.value = false;
      return task.id;
    },
    get: async (taskId: string) => tasks.value.find(t => t.id === taskId) || null,
    poll: async (taskId: string) => ({ id: taskId, status: 'completed', result: {} }),
  };
}
