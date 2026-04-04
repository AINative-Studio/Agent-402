# TypeScript SDK Quickstart

Get your first AINative agent running in 5 minutes.

Built by AINative Dev Team | Refs #182

---

## Prerequisites

- Node.js 18+
- An AINative API key
- A project ID from the AINative dashboard

---

## Step 1: Install the SDK

```bash
npm install @ainative/sdk
```

---

## Step 2: Configure Authentication

Create a `.env` file:

```env
AINATIVE_API_KEY=your_api_key_here
AINATIVE_PROJECT_ID=proj_your_project_id
AINATIVE_BASE_URL=https://api.ainative.studio/v1/public
```

---

## Step 3: Create Your First Agent

```typescript
import { AINativeClient } from '@ainative/sdk';

const client = new AINativeClient({
  apiKey: process.env.AINATIVE_API_KEY!,
  projectId: process.env.AINATIVE_PROJECT_ID!,
  baseUrl: process.env.AINATIVE_BASE_URL,
});

async function main() {
  // Create an agent
  const agent = await client.agents.create({
    name: 'my-first-agent',
    did: 'did:key:z6MkExample123',
    metadata: {
      role: 'analyst',
      capabilities: ['data-analysis', 'report-generation'],
    },
  });

  console.log('Agent created:', agent.agent_id);
  console.log('Agent DID:', agent.did);
}

main().catch(console.error);
```

---

## Step 4: Submit a Task

```typescript
// Submit work for the agent
const task = await client.tasks.create({
  agentId: agent.agent_id,
  description: 'Analyze quarterly revenue data',
  inputs: {
    dataset: 'q4_2025_revenue.csv',
    outputFormat: 'summary',
  },
});

console.log('Task ID:', task.task_id);
console.log('Task status:', task.status);
```

---

## Step 5: Store Agent Memory

```typescript
// Store a memory for the agent
const memory = await client.memory.store({
  agentId: agent.agent_id,
  content: 'User prefers concise summaries with bullet points.',
  memoryType: 'preference',
  metadata: {
    source: 'user_interaction',
    confidence: 0.95,
  },
});

console.log('Memory stored:', memory.memory_id);

// Search memory later
const results = await client.memory.search({
  agentId: agent.agent_id,
  query: 'output format preferences',
  topK: 5,
});

results.forEach(r => {
  console.log(`[${r.score.toFixed(2)}] ${r.content}`);
});
```

---

## Step 6: Work with Vectors

```typescript
// Store a vector embedding
await client.vectors.upsert({
  id: 'doc-001',
  text: 'Quarterly revenue increased 23% year-over-year.',
  namespace: 'financial-docs',
  metadata: {
    quarter: 'Q4-2025',
    type: 'revenue',
  },
});

// Semantic search
const similar = await client.vectors.search({
  query: 'revenue growth',
  namespace: 'financial-docs',
  topK: 3,
  filters: { quarter: 'Q4-2025' },
});

similar.results.forEach(r => {
  console.log(`Match: ${r.id} (score: ${r.score.toFixed(3)})`);
  console.log(`  Content: ${r.metadata.content}`);
});
```

---

## Complete Example

```typescript
import { AINativeClient } from '@ainative/sdk';

const client = new AINativeClient({
  apiKey: process.env.AINATIVE_API_KEY!,
  projectId: process.env.AINATIVE_PROJECT_ID!,
});

async function runAgent() {
  // 1. Create agent
  const agent = await client.agents.create({
    name: 'financial-analyst',
    did: 'did:key:z6MkFinAgent',
    metadata: { role: 'analyst' },
  });

  // 2. Submit task
  const task = await client.tasks.create({
    agentId: agent.agent_id,
    description: 'Analyze portfolio performance',
    inputs: { portfolioId: 'port-001' },
  });

  // 3. Store decision context
  await client.memory.store({
    agentId: agent.agent_id,
    content: 'Portfolio analysis completed. Risk level: medium.',
    metadata: { taskId: task.task_id },
  });

  // 4. Embed analysis results
  await client.vectors.upsert({
    id: `analysis-${task.task_id}`,
    text: 'Portfolio performance: +12.3% YTD, Sharpe ratio 1.8',
    namespace: 'analyses',
    metadata: { taskId: task.task_id },
  });

  console.log('Agent run complete!');
  console.log('Agent:', agent.agent_id);
  console.log('Task:', task.task_id);
}

runAgent().catch(console.error);
```

---

## Next Steps

- [Python Quickstart](./python-quickstart.md) — same concepts in Python
- [API Reference](./api-reference.md) — complete method signatures
- [Examples](./examples.md) — more code examples
- [Hedera Plugin Guide](./hedera-plugin-guide.md) — add USDC payments

Built by AINative Dev Team
