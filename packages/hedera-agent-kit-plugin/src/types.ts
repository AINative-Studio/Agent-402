/**
 * @ainative/hedera-agent-kit-plugin — Shared types
 * Built by AINative Dev Team
 * Refs #183, #184, #185, #186
 */

export interface AINativePluginConfig {
  apiKey: string;
  baseUrl?: string;
  agentId?: string;
}

// ─── Memory Types ─────────────────────────────────────────────────────────────

export interface MemoryMetadata {
  [key: string]: string | number | boolean | null;
}

export interface RememberInput {
  content: string;
  agent_id?: string;
  metadata?: MemoryMetadata;
}

export interface RememberResult {
  id: string;
  content: string;
  agent_id?: string;
  metadata?: MemoryMetadata;
  created_at: string;
}

export interface RecallInput {
  query: string;
  limit?: number;
  agent_id?: string;
  filters?: MemoryMetadata;
}

export interface RecallResult {
  memories: Array<{
    id: string;
    content: string;
    score: number;
    metadata?: MemoryMetadata;
  }>;
}

export interface ForgetInput {
  id: string;
}

export interface ForgetResult {
  success: boolean;
  id: string;
}

export interface ReflectInput {
  agent_id: string;
  topic?: string;
}

export interface ReflectResult {
  summary: string;
  entities: string[];
  agent_id: string;
}

// ─── Chat Types ────────────────────────────────────────────────────────────────

export type ChatProvider =
  | 'anthropic'
  | 'openai'
  | 'meta'
  | 'google'
  | 'mistral'
  | 'nouscoder'
  | 'cohere';

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatInput {
  messages: ChatMessage[];
  provider?: ChatProvider;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface ChatResult {
  id: string;
  provider: ChatProvider;
  model: string;
  content: string;
  finish_reason: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

// ─── Vector Types ──────────────────────────────────────────────────────────────

export type VectorDimension = 384 | 768 | 1024 | 1536;

export interface VectorMetadata {
  [key: string]: string | number | boolean | null;
}

export interface VectorUpsertInput {
  id?: string;
  vector: number[];
  metadata?: VectorMetadata;
  namespace?: string;
}

export interface VectorUpsertResult {
  id: string;
  namespace?: string;
  upserted: boolean;
}

export interface VectorSearchInput {
  vector: number[];
  top_k?: number;
  namespace?: string;
  filter?: VectorMetadata;
}

export interface VectorSearchResult {
  matches: Array<{
    id: string;
    score: number;
    metadata?: VectorMetadata;
  }>;
}

export interface VectorDeleteInput {
  id: string;
  namespace?: string;
}

export interface VectorDeleteResult {
  success: boolean;
  id: string;
}

// ─── API Error ─────────────────────────────────────────────────────────────────

export interface AINativeAPIError {
  status: number;
  message: string;
  code?: string;
}
