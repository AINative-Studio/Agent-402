/**
 * RED tests for Agent CRUD and Task Management
 * Built by AINative Dev Team
 * Refs #178
 */

import { AgentsModule } from '../src/agents';
import { HttpClient } from '../src/client';
import type { Agent, AgentConfig, AgentUpdateConfig, Task, TaskConfig, TaskListOptions } from '../src/types';

// Mock HttpClient
jest.mock('../src/client');
const MockedHttpClient = HttpClient as jest.MockedClass<typeof HttpClient>;

function makeAgent(overrides: Partial<Agent> = {}): Agent {
  return {
    id: 'agent_abc123',
    name: 'Test Agent',
    role: 'assistant',
    did: 'did:ainative:abc123',
    scope: 'RUN',
    projectId: 'proj_xyz',
    status: 'active',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'task_abc123',
    description: 'Test task',
    agent_types: ['assistant'],
    status: 'pending',
    projectId: 'proj_xyz',
    config: {},
    priority: 1,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('AgentsModule', () => {
  let mockClient: jest.Mocked<HttpClient>;
  let agentsModule: AgentsModule;

  beforeEach(() => {
    MockedHttpClient.mockClear();
    mockClient = {
      get: jest.fn(),
      post: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
      baseUrl: 'https://api.ainative.studio/v1',
      timeout: 30000,
    } as unknown as jest.Mocked<HttpClient>;

    agentsModule = new AgentsModule(mockClient);
  });

  // ─── Agent CRUD ────────────────────────────────────────────────────────────

  describe('agents.create', () => {
    it('should POST to /agents with the provided config', async () => {
      const config: AgentConfig = { name: 'My Agent', role: 'researcher' };
      const expected = makeAgent({ name: 'My Agent', role: 'researcher' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await agentsModule.create(config);

      expect(mockClient.post).toHaveBeenCalledWith('/agents', config);
      expect(result).toEqual(expected);
    });

    it('should return the created Agent with an id', async () => {
      const config: AgentConfig = { name: 'Agent A', role: 'analyst' };
      const expected = makeAgent({ name: 'Agent A', id: 'agent_new001' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await agentsModule.create(config);

      expect(result.id).toBe('agent_new001');
    });

    it('should include optional scope in the request when provided', async () => {
      const config: AgentConfig = { name: 'Scoped Agent', role: 'analyst', scope: 'PROJECT' };
      mockClient.post.mockResolvedValueOnce(makeAgent({ scope: 'PROJECT' }));

      await agentsModule.create(config);

      expect(mockClient.post).toHaveBeenCalledWith('/agents', expect.objectContaining({ scope: 'PROJECT' }));
    });
  });

  describe('agents.get', () => {
    it('should GET /agents/:id', async () => {
      const expected = makeAgent({ id: 'agent_xyz' });
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await agentsModule.get('agent_xyz');

      expect(mockClient.get).toHaveBeenCalledWith('/agents/agent_xyz');
      expect(result).toEqual(expected);
    });

    it('should return the agent matching the given id', async () => {
      const expected = makeAgent({ id: 'agent_abc' });
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await agentsModule.get('agent_abc');

      expect(result.id).toBe('agent_abc');
    });
  });

  describe('agents.list', () => {
    it('should GET /agents', async () => {
      const response = { agents: [makeAgent()], total: 1, limit: 100, offset: 0 };
      mockClient.get.mockResolvedValueOnce(response);

      const result = await agentsModule.list();

      expect(mockClient.get).toHaveBeenCalledWith('/agents');
      expect(result).toEqual(response);
    });

    it('should return a list of agents', async () => {
      const agents = [makeAgent({ id: 'agent_1' }), makeAgent({ id: 'agent_2' })];
      const response = { agents, total: 2, limit: 100, offset: 0 };
      mockClient.get.mockResolvedValueOnce(response);

      const result = await agentsModule.list();

      expect(result.agents).toHaveLength(2);
    });
  });

  describe('agents.update', () => {
    it('should PATCH /agents/:id with update config', async () => {
      const update: AgentUpdateConfig = { name: 'Updated Name' };
      const expected = makeAgent({ name: 'Updated Name' });
      mockClient.patch.mockResolvedValueOnce(expected);

      const result = await agentsModule.update('agent_abc123', update);

      expect(mockClient.patch).toHaveBeenCalledWith('/agents/agent_abc123', update);
      expect(result).toEqual(expected);
    });

    it('should return the updated agent', async () => {
      const update: AgentUpdateConfig = { role: 'new-role' };
      const expected = makeAgent({ role: 'new-role' });
      mockClient.patch.mockResolvedValueOnce(expected);

      const result = await agentsModule.update('agent_abc123', update);

      expect(result.role).toBe('new-role');
    });
  });

  describe('agents.delete', () => {
    it('should DELETE /agents/:id', async () => {
      mockClient.delete.mockResolvedValueOnce({ success: true });

      await agentsModule.delete('agent_abc123');

      expect(mockClient.delete).toHaveBeenCalledWith('/agents/agent_abc123');
    });
  });

  // ─── Task Management ───────────────────────────────────────────────────────

  describe('tasks.create', () => {
    it('should POST to /tasks with config', async () => {
      const config: TaskConfig = { description: 'Analyze data', agent_types: ['analyst'] };
      const expected = makeTask({ description: 'Analyze data', agent_types: ['analyst'] });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await agentsModule.tasks.create(config);

      expect(mockClient.post).toHaveBeenCalledWith('/tasks', config);
      expect(result).toEqual(expected);
    });

    it('should return the created task with an id', async () => {
      const config: TaskConfig = { description: 'Write report' };
      const expected = makeTask({ id: 'task_new001', description: 'Write report' });
      mockClient.post.mockResolvedValueOnce(expected);

      const result = await agentsModule.tasks.create(config);

      expect(result.id).toBe('task_new001');
    });

    it('should include optional config fields in the request', async () => {
      const config: TaskConfig = {
        description: 'Run analysis',
        agent_types: ['analyst'],
        config: { timeout: 60 },
      };
      mockClient.post.mockResolvedValueOnce(makeTask());

      await agentsModule.tasks.create(config);

      expect(mockClient.post).toHaveBeenCalledWith('/tasks', expect.objectContaining({
        config: { timeout: 60 },
      }));
    });
  });

  describe('tasks.get', () => {
    it('should GET /tasks/:taskId', async () => {
      const expected = makeTask({ id: 'task_xyz' });
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await agentsModule.tasks.get('task_xyz');

      expect(mockClient.get).toHaveBeenCalledWith('/tasks/task_xyz');
      expect(result).toEqual(expected);
    });

    it('should return the task matching the given id', async () => {
      const expected = makeTask({ id: 'task_abc' });
      mockClient.get.mockResolvedValueOnce(expected);

      const result = await agentsModule.tasks.get('task_abc');

      expect(result.id).toBe('task_abc');
    });
  });

  describe('tasks.list', () => {
    it('should GET /tasks without filters', async () => {
      const response = { tasks: [makeTask()], total: 1, limit: 100, offset: 0 };
      mockClient.get.mockResolvedValueOnce(response);

      const result = await agentsModule.tasks.list();

      expect(mockClient.get).toHaveBeenCalledWith('/tasks');
      expect(result).toEqual(response);
    });

    it('should append status query parameter when provided', async () => {
      const response = { tasks: [], total: 0, limit: 100, offset: 0 };
      mockClient.get.mockResolvedValueOnce(response);

      await agentsModule.tasks.list({ status: 'completed' });

      expect(mockClient.get).toHaveBeenCalledWith('/tasks?status=completed');
    });

    it('should append multiple query parameters', async () => {
      const response = { tasks: [], total: 0, limit: 100, offset: 0 };
      mockClient.get.mockResolvedValueOnce(response);

      const options: TaskListOptions = { status: 'running', limit: 50, offset: 10 };
      await agentsModule.tasks.list(options);

      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('status=running')
      );
    });
  });
});
