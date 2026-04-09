/**
 * @ainative/agent-runtime — Type definitions
 * Built by AINative Dev Team
 * Refs #246 #247 #248
 */

// ─── Messages ─────────────────────────────────────────────────────────────────

export interface Message {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  toolCallId?: string;
}

// ─── Tool ─────────────────────────────────────────────────────────────────────

export interface Tool {
  name: string;
  description: string;
  parameters?: Record<string, unknown>;
  execute: (args: Record<string, unknown>) => Promise<unknown>;
}

// ─── Tool Call ────────────────────────────────────────────────────────────────

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  error?: string;
}

// ─── Turn Result ──────────────────────────────────────────────────────────────

export interface TurnResult {
  turnNumber: number;
  thought: string;
  toolCalls: ToolCall[];
  messages: Message[];
}

// ─── Agent Task ───────────────────────────────────────────────────────────────

export interface AgentTask {
  id: string;
  description: string;
  tools: Tool[];
  metadata: Record<string, unknown>;
  systemPrompt?: string;
}

// ─── Run Result ───────────────────────────────────────────────────────────────

export type RunStatus = 'complete' | 'max_turns_reached' | 'error';

export interface RunResult {
  taskId: string;
  status: RunStatus;
  turns: TurnResult[];
  finalAnswer?: string;
  error?: string;
}

// ─── Storage Adapter ──────────────────────────────────────────────────────────

export interface MemoryEntry {
  id: string;
  content: string;
  metadata: Record<string, unknown>;
  score: number;
  createdAt: string;
}

export interface RecordEntry {
  id: string;
  data: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface StorageAdapter {
  storeMemory(content: string, metadata: Record<string, unknown>): Promise<{ id: string }>;
  recallMemory(query: string, limit: number): Promise<MemoryEntry[]>;
  storeRecord(table: string, data: Record<string, unknown>): Promise<{ id: string }>;
  queryRecords(table: string, filter: Record<string, unknown>): Promise<RecordEntry[]>;
}

// ─── LLM Provider ────────────────────────────────────────────────────────────

export interface LLMMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  toolCallId?: string;
}

export interface LLMToolDefinition {
  name: string;
  description: string;
  parameters?: Record<string, unknown>;
}

export interface LLMChatOptions {
  temperature?: number;
  maxTokens?: number;
  stopSequences?: string[];
}

export interface LLMResponse {
  content: string;
  toolCalls: ToolCall[];
}

export interface LLMProvider {
  chat(messages: LLMMessage[], options?: LLMChatOptions): Promise<LLMResponse>;
  chatWithTools(
    messages: LLMMessage[],
    tools: LLMToolDefinition[],
    options?: LLMChatOptions,
  ): Promise<LLMResponse>;
}

// ─── Runtime Config ───────────────────────────────────────────────────────────

export interface RuntimeConfig {
  storage: StorageAdapter;
  llmProvider: LLMProvider;
  tools?: Tool[];
  maxTurns?: number;
}

// ─── Step Context ─────────────────────────────────────────────────────────────

export interface StepContext {
  messages: LLMMessage[];
  tools: Tool[];
  options?: LLMChatOptions;
}

// ─── Sync Change ──────────────────────────────────────────────────────────────

export interface SyncChange {
  id: string;
  type: 'memory' | 'record';
  content?: string;
  table?: string;
  data?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  createdAt: string;
}

// ─── Provider Health ─────────────────────────────────────────────────────────

export interface ProviderHealth {
  name: string;
  healthy: boolean;
  latencyMs: number;
  error?: string;
}
