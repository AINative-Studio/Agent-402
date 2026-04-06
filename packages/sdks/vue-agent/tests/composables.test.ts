import { useAgent, useMemory, useTask } from '../src/index';

describe('useAgent', () => {
  it('initializes with empty agents', () => {
    const { agents, loading } = useAgent({ apiKey: 'k' });
    expect(agents.value).toEqual([]);
    expect(loading.value).toBe(false);
  });

  it('creates an agent reactively', async () => {
    const { agents, create } = useAgent({ apiKey: 'k' });
    const agent = await create('test', 'assistant');
    expect(agent).toHaveProperty('id');
    expect(agents.value).toHaveLength(1);
  });

  it('removes an agent', async () => {
    const { agents, create, remove } = useAgent({ apiKey: 'k' });
    const agent = await create('test', 'assistant');
    await remove(agent.id);
    expect(agents.value).toHaveLength(0);
  });

  it('lists agents', async () => {
    const { list, create } = useAgent({ apiKey: 'k' });
    await create('a1', 'role1');
    const result = await list();
    expect(result).toHaveLength(1);
  });

  it('gets agent by id', async () => {
    const { get, create } = useAgent({ apiKey: 'k' });
    const agent = await create('test', 'role');
    const found = await get(agent.id);
    expect(found?.name).toBe('test');
  });
});

describe('useMemory', () => {
  it('initializes with agent ID', () => {
    const { agentId, memories } = useMemory('agent-1');
    expect(agentId).toBe('agent-1');
    expect(memories.value).toEqual([]);
  });

  it('remembers content reactively', async () => {
    const { memories, remember } = useMemory('agent-1');
    const id = await remember('hello world');
    expect(id).toBeDefined();
    expect(memories.value).toHaveLength(1);
  });

  it('forgets a memory', async () => {
    const { memories, remember, forget } = useMemory('agent-1');
    const id = await remember('temp');
    await forget(id);
    expect(memories.value).toHaveLength(0);
  });
});

describe('useTask', () => {
  it('submits a task reactively', async () => {
    const { tasks, submit } = useTask();
    const id = await submit('do something');
    expect(id).toBeDefined();
    expect(tasks.value).toHaveLength(1);
    expect(tasks.value[0].status).toBe('pending');
  });

  it('polls a task for completion', async () => {
    const { poll } = useTask();
    const result = await poll('task-123');
    expect(result?.status).toBe('completed');
  });

  it('gets a task by id', async () => {
    const { submit, get } = useTask();
    const id = await submit('test task');
    const task = await get(id);
    expect(task?.description).toBe('test task');
  });
});
