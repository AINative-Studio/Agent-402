/**
 * @ainative/agent-sdk — HTTP client
 * Built by AINative Dev Team
 * Refs #178
 *
 * Fetch-based HTTP client with no heavy dependencies.
 * Handles authentication, base URL, and error mapping.
 */

import type { AINativeSDKConfig } from './types';
import {
  AINativeSDKError,
  AuthenticationError,
  NotFoundError,
  RateLimitError,
  NetworkError,
} from './errors';

const DEFAULT_BASE_URL = 'https://api.ainative.studio/v1';
const DEFAULT_TIMEOUT_MS = 30000;

export class HttpClient {
  readonly baseUrl: string;
  readonly timeout: number;
  private readonly authHeader: string;

  constructor(config: AINativeSDKConfig) {
    if (!config.apiKey && !config.jwt) {
      throw new AINativeSDKError(
        'AINativeSDK requires either apiKey or jwt',
        400,
        'CONFIG_ERROR'
      );
    }

    this.baseUrl = config.baseUrl ?? DEFAULT_BASE_URL;
    this.timeout = config.timeout ?? DEFAULT_TIMEOUT_MS;
    // Both apiKey and jwt are sent as Bearer tokens per the API convention
    this.authHeader = `Bearer ${config.apiKey ?? config.jwt}`;
  }

  private buildUrl(path: string): string {
    // Prevent double-slashes
    const base = this.baseUrl.replace(/\/$/, '');
    const suffix = path.startsWith('/') ? path : `/${path}`;
    return `${base}${suffix}`;
  }

  private defaultHeaders(): Record<string, string> {
    return {
      'Authorization': this.authHeader,
      'Content-Type': 'application/json',
    };
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = {};
    }

    if (!response.ok) {
      const errorBody = body as Record<string, unknown>;
      const message = (errorBody.error ?? errorBody.message ?? 'Request failed') as string;
      const code = (errorBody.code ?? 'SDK_ERROR') as string;

      switch (response.status) {
        case 401:
          throw new AuthenticationError(message, errorBody);
        case 404:
          throw new NotFoundError(message, errorBody);
        case 429:
          throw new RateLimitError(message, errorBody);
        default:
          throw new AINativeSDKError(message, response.status, code, errorBody);
      }
    }

    return body as T;
  }

  async get<T = unknown>(path: string): Promise<T> {
    try {
      const response = await fetch(this.buildUrl(path), {
        method: 'GET',
        headers: this.defaultHeaders(),
      });
      return this.handleResponse<T>(response);
    } catch (err) {
      if (err instanceof AINativeSDKError) throw err;
      throw new NetworkError(`Network error: ${(err as Error).message}`, err);
    }
  }

  async post<T = unknown>(path: string, body?: unknown): Promise<T> {
    try {
      const response = await fetch(this.buildUrl(path), {
        method: 'POST',
        headers: this.defaultHeaders(),
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      return this.handleResponse<T>(response);
    } catch (err) {
      if (err instanceof AINativeSDKError) throw err;
      throw new NetworkError(`Network error: ${(err as Error).message}`, err);
    }
  }

  async patch<T = unknown>(path: string, body?: unknown): Promise<T> {
    try {
      const response = await fetch(this.buildUrl(path), {
        method: 'PATCH',
        headers: this.defaultHeaders(),
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      return this.handleResponse<T>(response);
    } catch (err) {
      if (err instanceof AINativeSDKError) throw err;
      throw new NetworkError(`Network error: ${(err as Error).message}`, err);
    }
  }

  async delete<T = unknown>(path: string): Promise<T> {
    try {
      const response = await fetch(this.buildUrl(path), {
        method: 'DELETE',
        headers: this.defaultHeaders(),
      });
      return this.handleResponse<T>(response);
    } catch (err) {
      if (err instanceof AINativeSDKError) throw err;
      throw new NetworkError(`Network error: ${(err as Error).message}`, err);
    }
  }

  async postFormData<T = unknown>(path: string, formData: FormData): Promise<T> {
    try {
      // Omit Content-Type so fetch sets multipart/form-data with boundary automatically
      const headers: Record<string, string> = {
        'Authorization': this.authHeader,
      };
      const response = await fetch(this.buildUrl(path), {
        method: 'POST',
        headers,
        body: formData,
      });
      return this.handleResponse<T>(response);
    } catch (err) {
      if (err instanceof AINativeSDKError) throw err;
      throw new NetworkError(`Network error: ${(err as Error).message}`, err);
    }
  }
}
