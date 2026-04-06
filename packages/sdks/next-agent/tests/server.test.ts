import { createServerSDK, withAgentAuth, createAgentAPIHandler } from '../src/index';

describe('createServerSDK', () => {
  it('creates SDK with api key and default base URL', () => {
    const sdk = createServerSDK({ apiKey: 'test-key' });
    expect(sdk.config.apiKey).toBe('test-key');
    expect(sdk.config.baseUrl).toBe('https://api.ainative.studio/v1');
  });

  it('creates SDK with custom base URL', () => {
    const sdk = createServerSDK({ apiKey: 'k', baseUrl: 'http://localhost:8000' });
    expect(sdk.config.baseUrl).toBe('http://localhost:8000');
  });

  it('provides agents module with list, get, create', async () => {
    const sdk = createServerSDK({ apiKey: 'k' });
    const list = await sdk.agents.list();
    expect(list).toHaveProperty('agents');
    const agent = await sdk.agents.create({ name: 'test' });
    expect(agent).toHaveProperty('id');
    const got = await sdk.agents.get('123');
    expect(got.id).toBe('123');
  });

  it('provides memory module with remember and recall', async () => {
    const sdk = createServerSDK({ apiKey: 'k' });
    const mem = await sdk.memory.remember('hello');
    expect(mem).toHaveProperty('id');
    const results = await sdk.memory.recall('hello');
    expect(results).toHaveProperty('results');
  });

  it('provides tasks module with create and get', async () => {
    const sdk = createServerSDK({ apiKey: 'k' });
    const task = await sdk.tasks.create('do something');
    expect(task.status).toBe('pending');
    const got = await sdk.tasks.get(task.id);
    expect(got.id).toBe(task.id);
  });
});

describe('withAgentAuth', () => {
  it('rejects requests without authentication', async () => {
    const handler = withAgentAuth(async () => ({ ok: true }));
    const mockRes = { status: jest.fn().mockReturnThis(), json: jest.fn() };
    await handler({ headers: {} }, mockRes);
    expect(mockRes.status).toHaveBeenCalledWith(401);
  });

  it('passes through requests with X-API-Key header', async () => {
    const inner = jest.fn().mockResolvedValue({ ok: true });
    const handler = withAgentAuth(inner);
    const req = { headers: { 'x-api-key': 'test-key' } };
    await handler(req, {});
    expect(inner).toHaveBeenCalled();
    expect((req as any).agentApiKey).toBe('test-key');
  });

  it('extracts API key from Bearer authorization', async () => {
    const inner = jest.fn().mockResolvedValue({ ok: true });
    const handler = withAgentAuth(inner);
    const req = { headers: { authorization: 'Bearer my-jwt' } };
    await handler(req, {});
    expect((req as any).agentApiKey).toBe('my-jwt');
  });
});

describe('createAgentAPIHandler', () => {
  it('rejects unknown operations', async () => {
    const handler = createAgentAPIHandler({ apiKey: 'k' });
    const mockRes = { status: jest.fn().mockReturnThis(), json: jest.fn() };
    await handler({ query: { operation: 'unknown.op' }, body: {} }, mockRes);
    expect(mockRes.status).toHaveBeenCalledWith(400);
  });

  it('executes allowed operations', async () => {
    const handler = createAgentAPIHandler({ apiKey: 'k' });
    const mockRes = { status: jest.fn().mockReturnThis(), json: jest.fn() };
    await handler({ query: { operation: 'agents.list' }, body: {} }, mockRes);
    expect(mockRes.status).toHaveBeenCalledWith(200);
  });
});
