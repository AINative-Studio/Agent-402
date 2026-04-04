# AINative SDK Documentation

This directory contains developer documentation for the AINative Agent-402 SDK.

Built by AINative Dev Team | Refs #182

---

## Guides in This Directory

| File | Description |
|---|---|
| [typescript-quickstart.md](./typescript-quickstart.md) | Get started with the TypeScript SDK in 5 minutes |
| [python-quickstart.md](./python-quickstart.md) | Get started with the Python SDK in 5 minutes |
| [api-reference.md](./api-reference.md) | Complete API reference for both SDKs |
| [examples.md](./examples.md) | Code examples: agents, tasks, memory, vectors, files |
| [hedera-plugin-guide.md](./hedera-plugin-guide.md) | Hedera Agent Kit plugin integration guide |

---

## What Is Agent-402?

Agent-402 is an autonomous fintech agent platform built on AINative. It provides:

- **Agent lifecycle management** — create, configure, and run AI agents
- **USDC payments via X402** — agents can pay and receive payment
- **Hedera HTS integration** — native USDC transfers on Hedera Hashgraph
- **ZeroDB persistence** — vectors, memory, tables, and events
- **Compliance and audit trail** — append-only records for all agent actions

---

## Quick Navigation

### I want to...

**Run my first agent:**
- TypeScript: [typescript-quickstart.md](./typescript-quickstart.md)
- Python: [python-quickstart.md](./python-quickstart.md)

**Understand the API:**
- Full reference: [api-reference.md](./api-reference.md)

**See working code:**
- All examples: [examples.md](./examples.md)

**Add Hedera payments:**
- Hedera plugin: [hedera-plugin-guide.md](./hedera-plugin-guide.md)

---

## Authentication

All API endpoints require an `X-API-Key` header:

```http
X-API-Key: your_api_key_here
```

Base URL: `https://api.ainative.studio/v1/public/{project_id}`

---

## SDK Installation

### TypeScript / JavaScript

```bash
npm install @ainative/sdk
# or
yarn add @ainative/sdk
```

### Python

```bash
pip install ainative-sdk
```

---

## Support

- Issues: [GitHub Issues](https://github.com/AINative-Studio/Agent-402/issues)
- Documentation: This directory
- API Docs: `/docs` on your deployed instance

Built by AINative Dev Team
