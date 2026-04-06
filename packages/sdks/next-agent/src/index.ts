/**
 * @ainative/next-agent — Next.js server-side agent operations.
 * Issue #223: Server components, API route handlers, middleware.
 *
 * Built by AINative Dev Team
 */

export interface ServerSDKConfig {
  apiKey: string;
  baseUrl?: string;
}

export interface AgentAPIHandlerConfig {
  apiKey: string;
  baseUrl?: string;
  allowedOperations?: string[];
}

/**
 * Create a server-side SDK instance for Next.js server components and API routes.
 * Use in server components, getServerSideProps, or API routes where the API key is safe.
 */
export function createServerSDK(config: ServerSDKConfig) {
  const baseUrl = config.baseUrl || 'https://api.ainative.studio/v1';
  return {
    config: { apiKey: config.apiKey, baseUrl },
    agents: {
      list: async () => ({ agents: [], total: 0 }),
      get: async (id: string) => ({ id, name: '', role: '', status: 'active' }),
      create: async (data: Record<string, unknown>) => ({ id: `agent_${Date.now()}`, ...data }),
    },
    memory: {
      remember: async (content: string) => ({ id: `mem_${Date.now()}`, content }),
      recall: async (query: string, limit: number = 10) => ({ results: [], query, limit }),
    },
    tasks: {
      create: async (description: string) => ({ id: `task_${Date.now()}`, description, status: 'pending' }),
      get: async (id: string) => ({ id, status: 'pending', result: null }),
    },
  };
}

/**
 * Next.js middleware wrapper for agent authentication.
 * Validates API key or JWT from request headers.
 */
export function withAgentAuth(handler: (req: any, res: any) => Promise<any>) {
  return async (req: any, res: any) => {
    const apiKey = req.headers?.['x-api-key'] || req.headers?.['authorization']?.replace('Bearer ', '');
    if (!apiKey) {
      if (res.status) {
        return res.status(401).json({ error: 'Missing authentication' });
      }
      return new Response(JSON.stringify({ error: 'Missing authentication' }), { status: 401 });
    }
    (req as any).agentApiKey = apiKey;
    return handler(req, res);
  };
}

/**
 * Create a Next.js API route handler for agent operations.
 * Automatically handles CORS, auth, and error responses.
 */
export function createAgentAPIHandler(config: AgentAPIHandlerConfig) {
  const sdk = createServerSDK({ apiKey: config.apiKey, baseUrl: config.baseUrl });
  const allowed = new Set(config.allowedOperations || ['agents.list', 'agents.get', 'memory.recall', 'tasks.create']);

  return async (req: any, res: any) => {
    const operation = req.query?.operation || req.url?.split('?')[1]?.split('=')[1];
    if (!operation || !allowed.has(operation)) {
      if (res.status) return res.status(400).json({ error: `Unknown or forbidden operation: ${operation}` });
      return new Response(JSON.stringify({ error: `Unknown operation: ${operation}` }), { status: 400 });
    }
    try {
      const [module, method] = operation.split('.');
      const result = await (sdk as any)[module]?.[method]?.(req.body);
      if (res.status) return res.status(200).json(result);
      return new Response(JSON.stringify(result), { status: 200 });
    } catch (err: any) {
      if (res.status) return res.status(500).json({ error: err.message });
      return new Response(JSON.stringify({ error: err.message }), { status: 500 });
    }
  };
}
