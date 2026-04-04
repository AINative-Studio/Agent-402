/**
 * @ainative/hedera-agent-kit-plugin — AINative HTTP client
 * Built by AINative Dev Team
 * Refs #183, #184, #185, #186
 */

import {
  AINativeAPIError,
  RememberInput,
  RememberResult,
  RecallInput,
  RecallResult,
  ForgetInput,
  ForgetResult,
  ReflectInput,
  ReflectResult,
  ChatInput,
  ChatResult,
  VectorUpsertInput,
  VectorUpsertResult,
  VectorSearchInput,
  VectorSearchResult,
  VectorDeleteInput,
  VectorDeleteResult,
} from './types';

export const DEFAULT_BASE_URL = 'https://api.ainative.studio';

export class AINativeClient {
  private readonly apiKey: string;
  private readonly baseUrl: string;

  constructor(apiKey: string, baseUrl: string = DEFAULT_BASE_URL) {
    if (!apiKey || apiKey.trim() === '') {
      throw new Error('API key is required');
    }
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-API-Key': this.apiKey,
    };

    const options: RequestInit = {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    };

    const response = await fetch(url, options);

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorBody = await response.json() as { message?: string; error?: string };
        errorMessage = errorBody.message ?? errorBody.error ?? errorMessage;
      } catch {
        // ignore JSON parse errors; keep default message
      }
      const apiError: AINativeAPIError = {
        status: response.status,
        message: errorMessage,
      };
      throw apiError;
    }

    if (response.status === 204) {
      return undefined as unknown as T;
    }

    return response.json() as Promise<T>;
  }

  // ─── Memory ─────────────────────────────────────────────────────────────────

  async remember(input: RememberInput): Promise<RememberResult> {
    return this.request<RememberResult>(
      'POST',
      '/api/v1/public/memory/v2/remember',
      input,
    );
  }

  async recall(input: RecallInput): Promise<RecallResult> {
    return this.request<RecallResult>(
      'POST',
      '/api/v1/public/memory/v2/recall',
      input,
    );
  }

  async forget(input: ForgetInput): Promise<ForgetResult> {
    return this.request<ForgetResult>(
      'POST',
      '/api/v1/public/memory/v2/forget',
      input,
    );
  }

  async reflect(input: ReflectInput): Promise<ReflectResult> {
    return this.request<ReflectResult>(
      'POST',
      '/api/v1/public/memory/v2/reflect',
      input,
    );
  }

  // ─── Chat ────────────────────────────────────────────────────────────────────

  async chatCompletion(input: ChatInput): Promise<ChatResult> {
    return this.request<ChatResult>(
      'POST',
      '/api/v1/public/chat/completions',
      input,
    );
  }

  // ─── Vectors ─────────────────────────────────────────────────────────────────

  async vectorUpsert(input: VectorUpsertInput): Promise<VectorUpsertResult> {
    return this.request<VectorUpsertResult>(
      'POST',
      '/api/v1/public/vectors/upsert',
      input,
    );
  }

  async vectorSearch(input: VectorSearchInput): Promise<VectorSearchResult> {
    return this.request<VectorSearchResult>(
      'POST',
      '/api/v1/public/vectors/search',
      input,
    );
  }

  async vectorDelete(input: VectorDeleteInput): Promise<VectorDeleteResult> {
    return this.request<VectorDeleteResult>(
      'DELETE',
      `/api/v1/public/vectors/${encodeURIComponent(input.id)}`,
      input.namespace !== undefined ? { namespace: input.namespace } : undefined,
    );
  }
}
