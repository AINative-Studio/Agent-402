/**
 * @ainative/agent-runtime — AgentRuntime
 * Built by AINative Dev Team
 * Refs #246
 */

import type {
  RuntimeConfig,
  AgentTask,
  TurnResult,
  RunResult,
  RunStatus,
  StepContext,
  LLMMessage,
  ToolCall,
  Tool,
} from './types';

// ─── Event Types ─────────────────────────────────────────────────────────────

export type RuntimeEvent =
  | 'turn_start'
  | 'turn_end'
  | 'tool_call'
  | 'tool_result'
  | 'complete'
  | 'error';

export type EventCallback = (data: unknown) => void;

// ─── AgentRuntime ────────────────────────────────────────────────────────────

/**
 * Embeddable agent runtime that executes multi-turn agent loops.
 * Works in Node.js, Electron, Tauri, or any environment with async/await.
 */
export class AgentRuntime {
  readonly maxTurns: number;

  private readonly config: RuntimeConfig;
  private readonly listeners: Map<RuntimeEvent, EventCallback[]> = new Map();
  private readonly globalTools: Tool[];

  constructor(config: RuntimeConfig) {
    this.config = config;
    this.maxTurns = config.maxTurns ?? 10;
    this.globalTools = config.tools ?? [];
  }

  // ─── Event Emitter ────────────────────────────────────────────────────────

  on(event: RuntimeEvent, callback: EventCallback): void {
    const existing = this.listeners.get(event) ?? [];
    this.listeners.set(event, [...existing, callback]);
  }

  private emit(event: RuntimeEvent, data: unknown): void {
    const callbacks = this.listeners.get(event) ?? [];
    for (const cb of callbacks) {
      cb(data);
    }
  }

  // ─── step() ───────────────────────────────────────────────────────────────

  /**
   * Execute a single agent turn: think → select tool → execute → record.
   */
  async step(context: StepContext): Promise<TurnResult> {
    const { messages, tools, options } = context;

    const llmToolDefs = tools.map((t) => ({
      name: t.name,
      description: t.description,
      parameters: t.parameters,
    }));

    const llmResponse = await this.config.llmProvider.chatWithTools(
      messages,
      llmToolDefs,
      options,
    );

    const toolCalls: ToolCall[] = [];

    for (const tc of llmResponse.toolCalls) {
      this.emit('tool_call', tc);

      const tool = tools.find((t) => t.name === tc.name);
      const executed: ToolCall = { ...tc };

      if (tool) {
        try {
          executed.result = await tool.execute(tc.args);
        } catch (err) {
          executed.error = err instanceof Error ? err.message : String(err);
        }
      } else {
        executed.error = `Tool "${tc.name}" not found`;
      }

      this.emit('tool_result', executed);
      toolCalls.push(executed);
    }

    return {
      turnNumber: 0, // caller fills in the turn number
      thought: llmResponse.content,
      toolCalls,
      messages,
    };
  }

  // ─── run() ────────────────────────────────────────────────────────────────

  /**
   * Execute the full agent loop for a task, up to maxTurns.
   */
  async run(task: AgentTask): Promise<RunResult> {
    const allTools = [...this.globalTools, ...task.tools];
    const turns: TurnResult[] = [];

    const systemMessage: LLMMessage = {
      role: 'system',
      content: task.systemPrompt ?? 'You are a helpful AI assistant. Complete the given task.',
    };
    const userMessage: LLMMessage = { role: 'user', content: task.description };

    const messages: LLMMessage[] = [systemMessage, userMessage];

    let status: RunStatus = 'complete';
    let finalAnswer: string | undefined;
    let errorMessage: string | undefined;

    try {
      for (let turn = 0; turn < this.maxTurns; turn++) {
        this.emit('turn_start', { turn, taskId: task.id });

        const turnResult = await this.step({ messages, tools: allTools });
        turnResult.turnNumber = turn + 1;

        turns.push(turnResult);
        this.emit('turn_end', turnResult);

        // Append assistant thought to conversation
        if (turnResult.thought) {
          messages.push({ role: 'assistant', content: turnResult.thought });
        }

        // Append tool results to conversation
        for (const tc of turnResult.toolCalls) {
          messages.push({
            role: 'tool',
            content: tc.error
              ? `Error: ${tc.error}`
              : String(tc.result ?? ''),
            toolCallId: tc.id,
          });
        }

        // If LLM returned no tool calls and has content, the agent is done
        if (turnResult.toolCalls.length === 0 && turnResult.thought) {
          finalAnswer = turnResult.thought;
          status = 'complete';
          break;
        }

        // If this is the last allowed turn and we still have tool calls, mark limit
        if (turn === this.maxTurns - 1) {
          status = 'max_turns_reached';
        }
      }
    } catch (err) {
      status = 'error';
      errorMessage = err instanceof Error ? err.message : String(err);
      this.emit('error', { taskId: task.id, error: errorMessage });
    }

    const result: RunResult = {
      taskId: task.id,
      status,
      turns,
      finalAnswer,
      error: errorMessage,
    };

    // Persist to storage
    try {
      await this.config.storage.storeRecord('agent_runs', {
        taskId: task.id,
        status,
        turnsCount: turns.length,
        finalAnswer,
        error: errorMessage,
        completedAt: new Date().toISOString(),
      });
    } catch {
      // Storage errors do not fail the run
    }

    if (status !== 'error') {
      this.emit('complete', result);
    }

    return result;
  }
}
