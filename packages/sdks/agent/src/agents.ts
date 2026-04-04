/**
 * @ainative/agent-sdk — Agent CRUD and Task Management
 * Built by AINative Dev Team
 * Refs #178
 */

import type { HttpClient } from './client';
import type {
  Agent,
  AgentConfig,
  AgentUpdateConfig,
  AgentListResponse,
  Task,
  TaskConfig,
  TaskListOptions,
  TaskListResponse,
} from './types';

class TasksSubModule {
  constructor(private readonly client: HttpClient) {}

  /**
   * Create a new task.
   */
  async create(config: TaskConfig): Promise<Task> {
    return this.client.post<Task>('/tasks', config);
  }

  /**
   * Get a task by ID.
   */
  async get(taskId: string): Promise<Task> {
    return this.client.get<Task>(`/tasks/${taskId}`);
  }

  /**
   * List tasks with optional filters.
   */
  async list(options?: TaskListOptions): Promise<TaskListResponse> {
    const params = new URLSearchParams();

    if (options?.status) params.set('status', options.status);
    if (options?.projectId) params.set('project_id', options.projectId);
    if (options?.limit !== undefined) params.set('limit', String(options.limit));
    if (options?.offset !== undefined) params.set('offset', String(options.offset));

    const qs = params.toString();
    const path = qs ? `/tasks?${qs}` : '/tasks';
    return this.client.get<TaskListResponse>(path);
  }
}

export class AgentsModule {
  /** Task management sub-module */
  readonly tasks: TasksSubModule;

  constructor(private readonly client: HttpClient) {
    this.tasks = new TasksSubModule(client);
  }

  /**
   * Create a new agent.
   */
  async create(config: AgentConfig): Promise<Agent> {
    return this.client.post<Agent>('/agents', config);
  }

  /**
   * Get an agent by ID.
   */
  async get(id: string): Promise<Agent> {
    return this.client.get<Agent>(`/agents/${id}`);
  }

  /**
   * List all agents.
   */
  async list(): Promise<AgentListResponse> {
    return this.client.get<AgentListResponse>('/agents');
  }

  /**
   * Update an existing agent.
   */
  async update(id: string, config: AgentUpdateConfig): Promise<Agent> {
    return this.client.patch<Agent>(`/agents/${id}`, config);
  }

  /**
   * Delete an agent by ID.
   */
  async delete(id: string): Promise<void> {
    await this.client.delete(`/agents/${id}`);
  }
}
