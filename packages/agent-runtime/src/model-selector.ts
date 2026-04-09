/**
 * @ainative/agent-runtime — ModelSelector
 * Built by AINative Dev Team
 * Refs #248
 *
 * Selects the best LLM provider based on:
 *   1. Local availability (health check result)
 *   2. Task complexity (metadata.complexity vs threshold)
 *   3. Fallback to next available provider
 */

import type { LLMProvider, AgentTask, ProviderHealth } from './types';

// ─── Config ───────────────────────────────────────────────────────────────────

export interface ModelSelectorConfig {
  providers: Array<LLMProvider & { name: string }>;
  /**
   * Tasks with metadata.complexity above this value are routed to the
   * last registered provider (assumed to be cloud). Default: none.
   */
  complexityThreshold?: number;
}

// ─── ModelSelector ───────────────────────────────────────────────────────────

export class ModelSelector {
  private readonly providers: Array<LLMProvider & { name: string }>;
  private readonly complexityThreshold: number | undefined;
  private healthMap: Map<string, boolean> = new Map();

  constructor(config: ModelSelectorConfig) {
    this.providers = config.providers;
    this.complexityThreshold = config.complexityThreshold;
    // Initially mark all providers as healthy (unknown)
    for (const p of this.providers) {
      this.healthMap.set(p.name, true);
    }
  }

  // ─── select() ─────────────────────────────────────────────────────────────

  /**
   * Choose the appropriate provider for a given task.
   *
   * Selection order:
   *   1. If complexityThreshold is set and task complexity exceeds it,
   *      prefer the last provider (cloud fallback).
   *   2. Otherwise prefer the first healthy provider (local).
   *   3. If no healthy provider found, throw.
   */
  async select(task: AgentTask): Promise<LLMProvider & { name: string }> {
    if (this.providers.length === 0) {
      throw new Error('No providers registered in ModelSelector');
    }

    const complexity = typeof task.metadata?.complexity === 'number'
      ? (task.metadata.complexity as number)
      : 0;

    const isHighComplexity =
      this.complexityThreshold !== undefined && complexity > this.complexityThreshold;

    if (isHighComplexity) {
      // Prefer the last registered (cloud) provider if it's healthy
      const cloud = this.providers[this.providers.length - 1];
      if (this.healthMap.get(cloud.name) !== false) return cloud;
    }

    // Find first healthy provider
    for (const provider of this.providers) {
      if (this.healthMap.get(provider.name) !== false) {
        return provider;
      }
    }

    throw new Error('No healthy providers available');
  }

  // ─── healthCheck() ────────────────────────────────────────────────────────

  /**
   * Ping all providers with a minimal request and record their health status.
   */
  async healthCheck(): Promise<ProviderHealth[]> {
    const results: ProviderHealth[] = [];

    for (const provider of this.providers) {
      const start = Date.now();
      let healthy = true;
      let error: string | undefined;

      try {
        await provider.chat([{ role: 'user', content: 'ping' }]);
      } catch (err) {
        healthy = false;
        error = err instanceof Error ? err.message : String(err);
      }

      const latencyMs = Date.now() - start;

      this.healthMap.set(provider.name, healthy);

      results.push({
        name: provider.name,
        healthy,
        latencyMs,
        error,
      });
    }

    return results;
  }
}
