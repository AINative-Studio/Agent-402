# @ainative/hedera-agent-kit-plugin

AINative tools plugin for [Hedera Agent Kit v3](https://github.com/hashgraph/hedera-agent-kit).

Provides persistent memory, multi-provider chat completions, and vector search capabilities to Hedera-based AI agents through LangChain-compatible tools.

Built by AINative Dev Team — Refs #183, #184, #185, #186

---

## Installation

```bash
npm install @ainative/hedera-agent-kit-plugin
```

---

## Configuration

Set your AINative API key as an environment variable:

```bash
export AINATIVE_API_KEY=your-api-key-here
```

Or pass it directly in code (see usage examples below).

---

## Quick Start

```typescript
import { getAINativeTools } from '@ainative/hedera-agent-kit-plugin';

const tools = getAINativeTools({
  apiKey: process.env.AINATIVE_API_KEY,
});

// All 8 tools are now ready to use with your Hedera agent
console.log(tools.map(t => t.name));
// [
//   'ainative_remember', 'ainative_recall', 'ainative_forget', 'ainative_reflect',
//   'ainative_chat',
//   'ainative_vector_upsert', 'ainative_vector_search', 'ainative_vector_delete'
// ]
```

---

## API Reference

### `getAINativeTools(config)` / `registerAINativeTools(config)`

Returns an array of 8 LangChain `DynamicStructuredTool` instances compatible with Hedera Agent Kit v3.

```typescript
interface AINativePluginConfig {
  apiKey: string;          // AINative API key (falls back to AINATIVE_API_KEY env var)
  baseUrl?: string;        // Custom API base URL (default: https://api.ainative.studio)
  agentId?: string;        // Optional default agent ID for memory scoping
}
```

---

## Memory Tools (Issue #183)

### `ainative_remember`

Store information in persistent agent memory.

```typescript
await rememberTool.invoke({
  content: 'User prefers Hedera mainnet over testnet.',
  agent_id: 'my-agent',                  // optional
  metadata: { network: 'mainnet' },      // optional
});
// Returns: "Memory stored successfully. ID: mem-abc123"
```

### `ainative_recall`

Search memories by semantic similarity.

```typescript
await recallTool.invoke({
  query: 'Which Hedera network does the user prefer?',
  agent_id: 'my-agent',   // optional filter
  limit: 5,               // optional
});
// Returns: "Found 1 memories:\n1. [mem-abc123] (score: 0.954) User prefers Hedera mainnet..."
```

### `ainative_forget`

Delete a specific memory by ID.

```typescript
await forgetTool.invoke({ id: 'mem-abc123' });
// Returns: "Memory mem-abc123 deleted successfully."
```

### `ainative_reflect`

Generate a contextual summary of agent knowledge.

```typescript
await reflectTool.invoke({
  agent_id: 'my-agent',
  topic: 'network preferences',   // optional
});
// Returns: "Summary for my-agent:\n<synthesized summary>\nKey entities: mainnet, HBAR"
```

---

## Chat Completion Tools (Issue #184)

### `ainative_chat`

Route chat requests to any of 7 LLM providers.

Supported providers: `anthropic`, `openai`, `meta`, `google`, `mistral`, `nouscoder`, `cohere`

```typescript
await chatTool.invoke({
  messages: [
    { role: 'system', content: 'You are a Hedera blockchain assistant.' },
    { role: 'user', content: 'What is HBAR?' },
  ],
  provider: 'anthropic',    // optional, defaults to 'anthropic'
  model: 'claude-3-5-sonnet-20241022',  // optional, uses provider default
  temperature: 0.7,         // optional
  max_tokens: 1024,         // optional
});
// Returns: "[anthropic/claude-3-5-sonnet-20241022] HBAR is the native cryptocurrency..."
```

#### Provider Default Models

| Provider    | Default Model                            |
|-------------|------------------------------------------|
| anthropic   | claude-3-5-sonnet-20241022               |
| openai      | gpt-4o                                   |
| meta        | meta-llama/Llama-3.1-70B-Instruct       |
| google      | gemini-1.5-pro                           |
| mistral     | mistral-large-latest                     |
| nouscoder   | NousResearch/Nous-Hermes-2-Yi-34B       |
| cohere      | command-r-plus                           |

---

## Vector Tools (Issue #185)

Supported dimensions: **384**, **768**, **1024**, **1536**

Use Hedera account IDs as namespaces for per-account vector isolation.

### `ainative_vector_upsert`

Store a vector embedding with metadata.

```typescript
await upsertTool.invoke({
  vector: embeddingArray,          // 384/768/1024/1536 floats
  metadata: { source: 'doc-1' },  // optional
  namespace: '0.0.1234567',        // optional Hedera account ID
  id: 'my-custom-id',             // optional
});
// Returns: "Vector stored successfully. ID: vec-abc123"
```

### `ainative_vector_search`

Find similar vectors by cosine similarity.

```typescript
await searchTool.invoke({
  vector: queryEmbedding,    // same dimension as stored vectors
  top_k: 5,                  // optional, number of results
  namespace: '0.0.1234567',  // optional filter by namespace
});
// Returns: "Found 3 match(es):\n1. [vec-001] score: 0.98\n..."
```

### `ainative_vector_delete`

Remove a vector by ID.

```typescript
await deleteTool.invoke({
  id: 'vec-abc123',
  namespace: '0.0.1234567',  // optional
});
// Returns: "Vector vec-abc123 deleted successfully."
```

---

## Integration with Hedera Agent Kit

```typescript
import { HederaAgentKit } from '@hashgraph/hedera-agent-kit';
import { getAINativeTools } from '@ainative/hedera-agent-kit-plugin';

const hederaKit = new HederaAgentKit(/* ... */);
const ainativeTools = getAINativeTools({
  apiKey: process.env.AINATIVE_API_KEY,
});

// Combine with Hedera tools
const allTools = [
  ...hederaKit.getTools(),
  ...ainativeTools,
];
```

---

## Authentication

All API calls use the `X-API-Key` header with your AINative API key.

- Get your API key at [ainative.studio](https://ainative.studio)
- Key is read from `config.apiKey` or the `AINATIVE_API_KEY` environment variable

---

## API Endpoints

| Feature | Endpoint |
|---------|----------|
| Remember | `POST /api/v1/public/memory/v2/remember` |
| Recall   | `POST /api/v1/public/memory/v2/recall`   |
| Forget   | `POST /api/v1/public/memory/v2/forget`   |
| Reflect  | `POST /api/v1/public/memory/v2/reflect`  |
| Chat     | `POST /api/v1/public/chat/completions`   |
| Vector Upsert | `POST /api/v1/public/vectors/upsert` |
| Vector Search | `POST /api/v1/public/vectors/search` |
| Vector Delete | `DELETE /api/v1/public/vectors/{id}`  |

---

## Development

```bash
npm install
npm test           # Run tests with coverage
npm run build      # Compile TypeScript
```

---

## License

MIT
