import { createAgentStore, createMemoryStore, createTaskStore } from '../src/index';

describe('createAgentStore', () => {
  it('initializes with empty agents', () => {
    const store = createAgentStore({ apiKey: 'k' });
    let state: any;
    store.subscribe(s => { state = s; });
    expect(state.agents).toEqual([]);
    expect(state.loading).toBe(false);
  });

  it('creates an agent and updates store', async () => {
    const store = createAgentStore({ apiKey: 'k' });
    let state: any;
    store.subscribe(s => { state = s; });
    const agent = await store.create('test', 'assistant');
    expect(agent).toHaveProperty('id');
    expect(state.agents).toHaveLength(1);
    expect(state.agents[0].name).toBe('test');
  });

  it('removes an agent from store', async () => {
    const store = createAgentStore({ apiKey: 'k' });
    let state: any;
    store.subscribe(s => { state = s; });
    const agent = await store.create('test', 'assistant');
    await store.remove(agent.id);
    expect(state.agents).toHaveLength(0);
  });
});

describe('createMemoryStore', () => {
  it('initializes with empty memories', () => {
    const store = createMemoryStore('agent-1');
    let state: any;
    store.subscribe(s => { state = s; });
    expect(state.memories).toEqual([]);
    expect(store.agentId).toBe('agent-1');
  });

  it('stores a memory and updates state', async () => {
    const store = createMemoryStore('agent-1');
    let state: any;
    store.subscribe(s => { state = s; });
    const id = await store.remember('test content');
    expect(id).toBeDefined();
    expect(state.memories).toHaveLength(1);
  });

  it('forgets a memory', async () => {
    const store = createMemoryStore('agent-1');
    let state: any;
    store.subscribe(s => { state = s; });
    const id = await store.remember('test');
    await store.forget(id);
    expect(state.memories).toHaveLength(0);
  });
});

describe('createTaskStore', () => {
  it('submits a task', async () => {
    const store = createTaskStore();
    let state: any;
    store.subscribe(s => { state = s; });
    const id = await store.submit('do something');
    expect(id).toBeDefined();
    expect(state.tasks).toHaveLength(1);
    expect(state.tasks[0].status).toBe('pending');
  });

  it('polls a task', async () => {
    const store = createTaskStore();
    const result = await store.poll('task-123');
    expect(result.status).toBe('completed');
  });
});
