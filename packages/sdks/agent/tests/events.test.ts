/**
 * RED tests for SDK Event Subscription Helpers — Issue #213.
 *
 * Tests EventsModule: subscribe (WebSocket), subscribeTask (SSE),
 * and unsubscribe / cleanup.
 *
 * Built by AINative Dev Team
 * Refs #213
 */

import { EventsModule } from '../src/events';
import { HttpClient } from '../src/client';

// ─── Mock WebSocket ──────────────────────────────────────────────────────────

class MockWebSocket {
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((e: Error) => void) | null = null;
  readonly OPEN = 1;
  readyState: number;
  closeCallCount = 0;

  constructor(url: string) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    // Simulate async open
    setImmediate(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) this.onopen();
    });
  }

  close() {
    this.closeCallCount++;
    this.readyState = 3;
    if (this.onclose) this.onclose();
  }

  simulateMessage(data: object) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }
}

// ─── Mock EventSource ────────────────────────────────────────────────────────

class MockEventSource {
  url: string;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: ((e: Error) => void) | null = null;
  closeCallCount = 0;

  constructor(url: string) {
    this.url = url;
  }

  close() {
    this.closeCallCount++;
  }

  simulateMessage(data: object) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }
}

// ─── Globals injected into module scope ─────────────────────────────────────

let lastWebSocket: MockWebSocket | null = null;
let lastEventSource: MockEventSource | null = null;

const WebSocketFactory = jest.fn((url: string) => {
  lastWebSocket = new MockWebSocket(url);
  return lastWebSocket;
});

const EventSourceFactory = jest.fn((url: string) => {
  lastEventSource = new MockEventSource(url);
  return lastEventSource;
});

jest.mock('../src/client');

// ─── Helpers ────────────────────────────────────────────────────────────────

function makeModule(): EventsModule {
  const mockClient = {
    baseUrl: 'https://api.ainative.studio/v1',
    timeout: 30000,
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  } as unknown as jest.Mocked<HttpClient>;

  return new EventsModule(mockClient, WebSocketFactory as any, EventSourceFactory as any);
}

// ============================================================================
// describe EventsModule
// ============================================================================

describe('EventsModule', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    lastWebSocket = null;
    lastEventSource = null;
  });

  // ─── subscribe ────────────────────────────────────────────────────────────

  describe('subscribe', () => {
    it('should open a WebSocket connection to the agent events endpoint', async () => {
      const module = makeModule();
      const callback = jest.fn();

      module.subscribe('agent-abc', ['task_started'], callback);

      // Allow setImmediate to run (simulates WS open)
      await new Promise((r) => setImmediate(r));

      expect(WebSocketFactory).toHaveBeenCalledWith(
        expect.stringContaining('/ws/events/agent-abc')
      );
    });

    it('should return a subscription id string', () => {
      const module = makeModule();
      const id = module.subscribe('agent-1', ['task_started'], jest.fn());
      expect(typeof id).toBe('string');
      expect(id.length).toBeGreaterThan(0);
    });

    it('should invoke callback when a matching event message arrives', async () => {
      const module = makeModule();
      const callback = jest.fn();

      module.subscribe('agent-2', ['task_started'], callback);
      await new Promise((r) => setImmediate(r));

      const event = { event_type: 'task_started', payload: { task_id: 't1' }, agent_id: 'agent-2', timestamp: 'now' };
      lastWebSocket!.simulateMessage(event);

      expect(callback).toHaveBeenCalledWith(event);
    });

    it('should not invoke callback for non-JSON messages', async () => {
      const module = makeModule();
      const callback = jest.fn();

      module.subscribe('agent-3', ['task_started'], callback);
      await new Promise((r) => setImmediate(r));

      // Simulate bad message
      if (lastWebSocket!.onmessage) {
        lastWebSocket!.onmessage({ data: 'not json' });
      }

      expect(callback).not.toHaveBeenCalled();
    });

    it('should include event_types in the WebSocket URL query string', () => {
      const module = makeModule();
      module.subscribe('agent-4', ['task_completed', 'task_failed'], jest.fn());

      expect(WebSocketFactory).toHaveBeenCalledWith(
        expect.stringContaining('event_types=')
      );
    });

    it('should return a unique subscription id each time', () => {
      const module = makeModule();
      const id1 = module.subscribe('agent-5', ['task_started'], jest.fn());
      const id2 = module.subscribe('agent-5', ['task_started'], jest.fn());
      expect(id1).not.toBe(id2);
    });
  });

  // ─── subscribeTask ────────────────────────────────────────────────────────

  describe('subscribeTask', () => {
    it('should open an EventSource to the task stream endpoint', () => {
      const module = makeModule();
      module.subscribeTask('task-xyz', jest.fn(), jest.fn());

      expect(EventSourceFactory).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/events/tasks/task-xyz/stream')
      );
    });

    it('should return a subscription id string', () => {
      const module = makeModule();
      const id = module.subscribeTask('task-1', jest.fn(), jest.fn());
      expect(typeof id).toBe('string');
    });

    it('should call onProgress when a progress event arrives', () => {
      const module = makeModule();
      const onProgress = jest.fn();
      const onComplete = jest.fn();

      module.subscribeTask('task-2', onProgress, onComplete);

      const progressEvent = { task_id: 'task-2', step: 1, total_steps: 3, message: 'Step 1', timestamp: 'now' };
      lastEventSource!.simulateMessage(progressEvent);

      expect(onProgress).toHaveBeenCalledWith(progressEvent);
    });

    it('should call onComplete when a completion event arrives', () => {
      const module = makeModule();
      const onProgress = jest.fn();
      const onComplete = jest.fn();

      module.subscribeTask('task-3', onProgress, onComplete);

      const completeEvent = { task_id: 'task-3', status: 'completed', result: { x: 1 }, timestamp: 'now' };
      lastEventSource!.simulateMessage(completeEvent);

      expect(onComplete).toHaveBeenCalledWith(completeEvent);
    });

    it('should not call onProgress for completion events', () => {
      const module = makeModule();
      const onProgress = jest.fn();
      const onComplete = jest.fn();

      module.subscribeTask('task-4', onProgress, onComplete);

      const completeEvent = { task_id: 'task-4', status: 'completed', result: {} };
      lastEventSource!.simulateMessage(completeEvent);

      expect(onProgress).not.toHaveBeenCalled();
    });
  });

  // ─── unsubscribe ──────────────────────────────────────────────────────────

  describe('unsubscribe', () => {
    it('should close the WebSocket when unsubscribing a ws subscription', async () => {
      const module = makeModule();
      const id = module.subscribe('agent-6', ['task_started'], jest.fn());
      await new Promise((r) => setImmediate(r));

      module.unsubscribe(id);

      expect(lastWebSocket!.closeCallCount).toBeGreaterThan(0);
    });

    it('should close the EventSource when unsubscribing a task subscription', () => {
      const module = makeModule();
      const id = module.subscribeTask('task-5', jest.fn(), jest.fn());

      module.unsubscribe(id);

      expect(lastEventSource!.closeCallCount).toBeGreaterThan(0);
    });

    it('should not throw when unsubscribing an unknown id', () => {
      const module = makeModule();
      expect(() => module.unsubscribe('unknown-id')).not.toThrow();
    });

    it('should stop delivering messages after unsubscribe', async () => {
      const module = makeModule();
      const callback = jest.fn();
      const id = module.subscribe('agent-7', ['task_started'], callback);
      await new Promise((r) => setImmediate(r));

      module.unsubscribe(id);

      lastWebSocket!.simulateMessage({ event_type: 'task_started', payload: {}, agent_id: 'agent-7' });
      expect(callback).not.toHaveBeenCalled();
    });
  });
});
