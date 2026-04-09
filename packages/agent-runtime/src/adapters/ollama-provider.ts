/**
 * @ainative/agent-runtime — OllamaProvider
 * Built by AINative Dev Team
 * Refs #248
 *
 * Wraps the Ollama /api/chat endpoint to match the LLMProvider interface.
 */

import { v4 as uuidv4 } from 'uuid';
import type {
  LLMProvider,
  LLMMessage,
  LLMToolDefinition,
  LLMChatOptions,
  LLMResponse,
  ToolCall,
} from '../types';

// ─── Config ───────────────────────────────────────────────────────────────────

export interface OllamaProviderConfig {
  baseUrl?: string;
  model?: string;
}

// ─── Ollama wire types ────────────────────────────────────────────────────────

interface OllamaToolFunction {
  name: string;
  arguments: Record<string, unknown>;
}

interface OllamaToolCall {
  function: OllamaToolFunction;
}

interface OllamaMessage {
  role: string;
  content: string;
  tool_calls?: OllamaToolCall[];
}

interface OllamaChatResponse {
  model: string;
  message: OllamaMessage;
  done: boolean;
}

interface OllamaToolDefinition {
  type: 'function';
  function: {
    name: string;
    description: string;
    parameters?: Record<string, unknown>;
  };
}

// ─── OllamaProvider ──────────────────────────────────────────────────────────

export class OllamaProvider implements LLMProvider {
  readonly baseUrl: string;
  readonly model: string;
  /** Human-readable name for use in model selection */
  readonly name: string;

  constructor(config: OllamaProviderConfig) {
    this.baseUrl = config.baseUrl ?? 'http://localhost:11434';
    this.model = config.model ?? 'llama3.2';
    this.name = `ollama:${this.model}`;
  }

  // ─── chat() ───────────────────────────────────────────────────────────────

  async chat(messages: LLMMessage[], options?: LLMChatOptions): Promise<LLMResponse> {
    const body: Record<string, unknown> = {
      model: this.model,
      messages,
      stream: false,
    };

    if (options?.temperature !== undefined) {
      body.options = { temperature: options.temperature };
    }

    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Ollama error ${response.status}: ${text}`);
    }

    const data = (await response.json()) as OllamaChatResponse;
    return {
      content: data.message.content ?? '',
      toolCalls: [],
    };
  }

  // ─── chatWithTools() ──────────────────────────────────────────────────────

  async chatWithTools(
    messages: LLMMessage[],
    tools: LLMToolDefinition[],
    options?: LLMChatOptions,
  ): Promise<LLMResponse> {
    const ollamaTools: OllamaToolDefinition[] = tools.map((t) => ({
      type: 'function',
      function: {
        name: t.name,
        description: t.description,
        parameters: t.parameters,
      },
    }));

    const body: Record<string, unknown> = {
      model: this.model,
      messages,
      tools: ollamaTools,
      stream: false,
    };

    if (options?.temperature !== undefined) {
      body.options = { temperature: options.temperature };
    }

    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Ollama error ${response.status}: ${text}`);
    }

    const data = (await response.json()) as OllamaChatResponse;

    const toolCalls: ToolCall[] = (data.message.tool_calls ?? []).map((tc) => ({
      id: uuidv4(),
      name: tc.function.name,
      args: tc.function.arguments,
    }));

    return {
      content: data.message.content ?? '',
      toolCalls,
    };
  }
}
