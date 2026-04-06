/**
 * @ainative/agent-sdk — Event Subscription Helpers
 * Built by AINative Dev Team
 * Refs #213
 *
 * Provides WebSocket and SSE subscriptions for real-time agent events.
 */

import type { HttpClient } from './client';

// ─── Types ────────────────────────────────────────────────────────────────────

export type EventType =
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'memory_stored'
  | 'payment_settled';

export interface AgentEvent {
  agent_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface TaskProgressEvent {
  task_id: string;
  step: number;
  total_steps: number;
  message: string;
  timestamp: string;
}

export interface TaskCompletionEvent {
  task_id: string;
  status: 'completed';
  result: Record<string, unknown>;
  timestamp: string;
}

// Factory types so we can inject mocks in tests
type WebSocketFactory = (url: string) => WebSocketLike;
type EventSourceFactory = (url: string) => EventSourceLike;

interface WebSocketLike {
  readonly OPEN: number;
  readyState: number;
  onopen: (() => void) | null;
  onmessage: ((e: { data: string }) => void) | null;
  onclose: (() => void) | null;
  onerror: ((e: Error) => void) | null;
  close(): void;
}

interface EventSourceLike {
  onmessage: ((e: { data: string }) => void) | null;
  onerror: ((e: Error) => void) | null;
  close(): void;
}

// ─── Subscription registry ────────────────────────────────────────────────────

interface Subscription {
  type: 'websocket' | 'eventsource';
  connection: WebSocketLike | EventSourceLike;
  active: boolean;
  callback?: (event: AgentEvent) => void;
}

// ─── Module ───────────────────────────────────────────────────────────────────

/**
 * EventsModule provides real-time subscription helpers for agent events.
 *
 * WebSocket subscriptions receive agent-level events (task lifecycle, payments…).
 * SSE subscriptions receive fine-grained task progress updates.
 */
export class EventsModule {
  private readonly subscriptions = new Map<string, Subscription>();
  private idCounter = 0;

  constructor(
    private readonly client: HttpClient,
    private readonly wsFactory: WebSocketFactory = (url) => new WebSocket(url) as unknown as WebSocketLike,
    private readonly esFactory: EventSourceFactory = (url) => new EventSource(url) as unknown as EventSourceLike,
  ) {}

  private nextId(): string {
    return `sub_${++this.idCounter}_${Date.now()}`;
  }

  // ─── subscribe ─────────────────────────────────────────────────────────────

  /**
   * Open a WebSocket connection to receive agent events in real time.
   *
   * @param agentId     - Agent whose events to subscribe to.
   * @param eventTypes  - List of event type strings to receive.
   * @param callback    - Called with each received event object.
   * @returns Subscription ID that can be passed to unsubscribe().
   */
  subscribe(
    agentId: string,
    eventTypes: string[],
    callback: (event: AgentEvent) => void,
  ): string {
    const baseUrl = this.client.baseUrl.replace(/\/v1$/, '');
    const query = `event_types=${eventTypes.join(',')}`;
    const wsUrl = `${baseUrl}/ws/events/${agentId}?${query}`;

    const ws = this.wsFactory(wsUrl);
    const id = this.nextId();
    const sub: Subscription = { type: 'websocket', connection: ws, active: true, callback };
    this.subscriptions.set(id, sub);

    ws.onmessage = (e) => {
      if (!sub.active) return;
      try {
        const data = JSON.parse(e.data) as AgentEvent;
        callback(data);
      } catch {
        // Silently ignore non-JSON frames
      }
    };

    ws.onerror = () => {
      // No-op; let the caller handle via callback absence
    };

    return id;
  }

  // ─── subscribeTask ─────────────────────────────────────────────────────────

  /**
   * Subscribe to SSE task progress events.
   *
   * @param taskId      - Task to monitor.
   * @param onProgress  - Called for progress events (step/total_steps/message).
   * @param onComplete  - Called once when the task reaches 'completed' status.
   * @returns Subscription ID that can be passed to unsubscribe().
   */
  subscribeTask(
    taskId: string,
    onProgress: (event: TaskProgressEvent) => void,
    onComplete: (event: TaskCompletionEvent) => void,
  ): string {
    const baseUrl = this.client.baseUrl.replace(/\/v1$/, '');
    const url = `${baseUrl}/api/v1/events/tasks/${taskId}/stream`;

    const es = this.esFactory(url);
    const id = this.nextId();
    const sub: Subscription = { type: 'eventsource', connection: es, active: true };
    this.subscriptions.set(id, sub);

    es.onmessage = (e) => {
      if (!sub.active) return;
      try {
        const data = JSON.parse(e.data) as Record<string, unknown>;
        if (data.status === 'completed') {
          onComplete(data as unknown as TaskCompletionEvent);
        } else {
          onProgress(data as unknown as TaskProgressEvent);
        }
      } catch {
        // Silently ignore parse errors
      }
    };

    es.onerror = () => {
      // No-op
    };

    return id;
  }

  // ─── unsubscribe ───────────────────────────────────────────────────────────

  /**
   * Close and clean up a subscription by ID.
   *
   * Safe to call with an unknown ID (no-op).
   *
   * @param subscriptionId - ID returned from subscribe() or subscribeTask().
   */
  unsubscribe(subscriptionId: string): void {
    const sub = this.subscriptions.get(subscriptionId);
    if (!sub) return;

    sub.active = false;
    sub.connection.close();
    this.subscriptions.delete(subscriptionId);
  }
}
