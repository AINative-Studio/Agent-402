/**
 * @ainative/agent-runtime — ModelSelector tests
 * Built by AINative Dev Team
 * Refs #248
 *
 * RED phase: All tests written before implementation.
 */

import { ModelSelector } from '../src/model-selector';
import type { LLMProvider, AgentTask } from '../src/types';

// ─── Test Doubles ─────────────────────────────────────────────────────────────

function makeProvider(name: string, healthy = true): jest.Mocked<LLMProvider> & { name: string } {
  return {
    name,
    chat: jest.fn().mockResolvedValue({ content: 'ok', toolCalls: [] }),
    chatWithTools: jest.fn().mockResolvedValue({ content: 'ok', toolCalls: [] }),
  };
}

function makeTask(overrides: Partial<AgentTask> = {}): AgentTask {
  return {
    id: 'task-1',
    description: 'Simple task',
    tools: [],
    metadata: {},
    ...overrides,
  };
}

describe('ModelSelector', () => {
  // ─── Constructor ────────────────────────────────────────────────────────

  describe('constructor', () => {
    it('creates selector with a list of providers', () => {
      const selector = new ModelSelector({ providers: [makeProvider('local')] });
      expect(selector).toBeInstanceOf(ModelSelector);
    });

    it('accepts empty providers list', () => {
      expect(() => new ModelSelector({ providers: [] })).not.toThrow();
    });
  });

  // ─── select() ───────────────────────────────────────────────────────────

  describe('select()', () => {
    it('returns the first available provider for a simple task', async () => {
      const local = makeProvider('local');
      const cloud = makeProvider('cloud');
      const selector = new ModelSelector({ providers: [local, cloud] });

      const chosen = await selector.select(makeTask());
      expect(chosen).toBe(local);
    });

    it('falls back to cloud provider when local is unavailable', async () => {
      const local = makeProvider('local');
      const cloud = makeProvider('cloud');

      // Simulate local being down: chat throws
      local.chat.mockRejectedValue(new Error('connection refused'));
      local.chatWithTools.mockRejectedValue(new Error('connection refused'));

      const selector = new ModelSelector({ providers: [local, cloud] });
      // mark local as unhealthy by running healthCheck first
      await selector.healthCheck();

      const chosen = await selector.select(makeTask());
      expect(chosen).toBe(cloud);
    });

    it('throws when no providers are available', async () => {
      const selector = new ModelSelector({ providers: [] });
      await expect(selector.select(makeTask())).rejects.toThrow();
    });

    it('returns cloud provider for high-complexity tasks when configured', async () => {
      const local = makeProvider('local');
      const cloud = makeProvider('cloud');
      const selector = new ModelSelector({
        providers: [local, cloud],
        complexityThreshold: 5,
      });

      // High complexity task
      const complexTask = makeTask({ metadata: { complexity: 8 } });
      const chosen = await selector.select(complexTask);
      // For complex tasks, should prefer cloud (non-first) provider
      expect(chosen).toBe(cloud);
    });

    it('returns first provider for low-complexity tasks', async () => {
      const local = makeProvider('local');
      const cloud = makeProvider('cloud');
      const selector = new ModelSelector({
        providers: [local, cloud],
        complexityThreshold: 5,
      });

      const simpleTask = makeTask({ metadata: { complexity: 2 } });
      const chosen = await selector.select(simpleTask);
      expect(chosen).toBe(local);
    });
  });

  // ─── healthCheck() ──────────────────────────────────────────────────────

  describe('healthCheck()', () => {
    it('returns status for each provider', async () => {
      const local = makeProvider('local');
      const cloud = makeProvider('cloud');
      const selector = new ModelSelector({ providers: [local, cloud] });

      const status = await selector.healthCheck();
      expect(status).toHaveLength(2);
    });

    it('marks a provider healthy when chat succeeds', async () => {
      const local = makeProvider('local');
      const selector = new ModelSelector({ providers: [local] });

      const status = await selector.healthCheck();
      expect(status[0].healthy).toBe(true);
    });

    it('marks a provider unhealthy when chat throws', async () => {
      const local = makeProvider('local');
      local.chat.mockRejectedValue(new Error('timeout'));
      const selector = new ModelSelector({ providers: [local] });

      const status = await selector.healthCheck();
      expect(status[0].healthy).toBe(false);
    });

    it('includes provider name in health status', async () => {
      const provider = makeProvider('ollama-local');
      const selector = new ModelSelector({ providers: [provider] });

      const status = await selector.healthCheck();
      expect(status[0].name).toBe('ollama-local');
    });

    it('includes latency in health status when provider responds', async () => {
      const provider = makeProvider('local');
      const selector = new ModelSelector({ providers: [provider] });

      const status = await selector.healthCheck();
      expect(typeof status[0].latencyMs).toBe('number');
      expect(status[0].latencyMs).toBeGreaterThanOrEqual(0);
    });

    it('updates internal health state used by select()', async () => {
      const local = makeProvider('local');
      local.chat.mockRejectedValue(new Error('down'));
      const cloud = makeProvider('cloud');

      const selector = new ModelSelector({ providers: [local, cloud] });
      await selector.healthCheck();

      // local is now marked unhealthy; select should return cloud
      const chosen = await selector.select(makeTask());
      expect(chosen).toBe(cloud);
    });
  });
});
