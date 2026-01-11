# API Endpoint Inventory

**Last Updated:** 2026-01-11
**Total Endpoints:** 24 public endpoints
**Documentation Status:** ✅ All endpoints have copy-paste examples

---

## Quick Reference

| # | Method | Endpoint | Description | Docs |
|---|--------|----------|-------------|------|
| 1 | GET | `/v1/public/projects` | List user projects | ✅ |
| 2 | POST | `/v1/public/{project_id}/agents` | Create agent profile | ✅ |
| 3 | GET | `/v1/public/{project_id}/agents` | List agents in project | ✅ |
| 4 | GET | `/v1/public/{project_id}/agents/{agent_id}` | Get agent by ID | ✅ |
| 5 | POST | `/v1/public/{project_id}/agent-memory` | Create agent memory | ✅ |
| 6 | GET | `/v1/public/{project_id}/agent-memory` | List agent memories | ✅ |
| 7 | GET | `/v1/public/{project_id}/agent-memory/{memory_id}` | Get memory by ID | ✅ |
| 8 | POST | `/v1/public/{project_id}/database/events` | Create event | ✅ |
| 9 | POST | `/v1/public/{project_id}/embeddings/generate` | Generate embedding | ✅ |
| 10 | POST | `/v1/public/{project_id}/embeddings/embed-and-store` | Embed and store | ✅ |
| 11 | POST | `/v1/public/{project_id}/embeddings/search` | Search vectors | ✅ |
| 12 | GET | `/v1/public/embeddings/models` | List embedding models | ✅ |
| 13 | POST | `/v1/public/{project_id}/database/vectors/upsert` | Upsert vector | ✅ |
| 14 | POST | `/v1/public/{project_id}/compliance-events` | Create compliance event | ✅ |
| 15 | GET | `/v1/public/{project_id}/compliance-events` | List compliance events | ✅ |
| 16 | GET | `/v1/public/{project_id}/compliance-events/{event_id}` | Get compliance event | ✅ |
| 17 | POST | `/v1/public/{project_id}/x402-requests` | Create X402 request | ✅ |
| 18 | GET | `/v1/public/{project_id}/x402-requests` | List X402 requests | ✅ |
| 19 | GET | `/v1/public/{project_id}/x402-requests/{request_id}` | Get X402 request | ✅ |
| 20 | GET | `/v1/public/{project_id}/runs` | List agent runs | ✅ |
| 21 | GET | `/v1/public/{project_id}/runs/{run_id}` | Get run details | ✅ |
| 22 | GET | `/v1/public/{project_id}/runs/{run_id}/replay` | Get run replay data | ✅ |

---

## Endpoints by Category

### Projects API (1 endpoint)
- `GET /v1/public/projects` - List all projects

### Agents API (3 endpoints)
- `POST /v1/public/{project_id}/agents` - Create agent
- `GET /v1/public/{project_id}/agents` - List agents
- `GET /v1/public/{project_id}/agents/{agent_id}` - Get agent

### Agent Memory API (3 endpoints)
- `POST /v1/public/{project_id}/agent-memory` - Create memory
- `GET /v1/public/{project_id}/agent-memory` - List memories
- `GET /v1/public/{project_id}/agent-memory/{memory_id}` - Get memory

### Events API (1 endpoint)
- `POST /v1/public/{project_id}/database/events` - Create event

### Embeddings API (4 endpoints)
- `POST /v1/public/{project_id}/embeddings/generate` - Generate embedding
- `POST /v1/public/{project_id}/embeddings/embed-and-store` - Embed and store
- `POST /v1/public/{project_id}/embeddings/search` - Search vectors
- `GET /v1/public/embeddings/models` - List models

### Vector Operations API (1 endpoint)
- `POST /v1/public/{project_id}/database/vectors/upsert` - Upsert vector

### Compliance Events API (3 endpoints)
- `POST /v1/public/{project_id}/compliance-events` - Create event
- `GET /v1/public/{project_id}/compliance-events` - List events
- `GET /v1/public/{project_id}/compliance-events/{event_id}` - Get event

### X402 Requests API (3 endpoints)
- `POST /v1/public/{project_id}/x402-requests` - Create request
- `GET /v1/public/{project_id}/x402-requests` - List requests
- `GET /v1/public/{project_id}/x402-requests/{request_id}` - Get request

### Runs API (3 endpoints)
- `GET /v1/public/{project_id}/runs` - List runs
- `GET /v1/public/{project_id}/runs/{run_id}` - Get run
- `GET /v1/public/{project_id}/runs/{run_id}/replay` - Get replay data

---

## Authentication Requirements

| Endpoint Type | Auth Required | Header |
|---------------|---------------|--------|
| All endpoints (except GET /embeddings/models) | ✅ Yes | `X-API-Key: $API_KEY` |
| GET /v1/public/embeddings/models | ❌ No | Public endpoint |

---

## Prefix Requirements

| Endpoint Pattern | Requires /database/ Prefix |
|------------------|---------------------------|
| `/v1/public/{project_id}/database/events` | ✅ Yes |
| `/v1/public/{project_id}/database/vectors/upsert` | ✅ Yes |
| `/v1/public/{project_id}/embeddings/*` | ❌ No |
| All other endpoints | ❌ No |

---

## Implementation Files

| API Category | Router File |
|--------------|-------------|
| Projects | `/Users/aideveloper/Agent-402/backend/app/api/projects.py` |
| Agents | `/Users/aideveloper/Agent-402/backend/app/api/agents.py` |
| Agent Memory | `/Users/aideveloper/Agent-402/backend/app/api/agent_memory.py` |
| Events | `/Users/aideveloper/Agent-402/backend/app/api/events.py` |
| Embeddings | `/Users/aideveloper/Agent-402/backend/app/api/embeddings.py` |
| Vectors | `/Users/aideveloper/Agent-402/backend/app/api/vectors.py` |
| Compliance | `/Users/aideveloper/Agent-402/backend/app/api/compliance_events.py` |
| X402 | `/Users/aideveloper/Agent-402/backend/app/api/x402_requests.py` |
| Runs | `/Users/aideveloper/Agent-402/backend/app/api/runs.py` |

---

## Documentation Files

- **[API_EXAMPLES.md](./API_EXAMPLES.md)** - Complete copy-paste examples for all endpoints
- **[api-spec.md](./api-spec.md)** - Full API specification
- **[QUICKSTART.md](../quick-reference/QUICKSTART.md)** - Quick start guide
- **[EPIC10_STORY3_REPORT.md](./EPIC10_STORY3_REPORT.md)** - Implementation report

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-11 | 1.0 | Initial inventory with 24 endpoints documented |

---

## Related GitHub Issues

- **Issue #12:** Default model behavior for embeddings
- **Issue #17:** Namespace scoping for search
- **Issue #18:** Upsert behavior for embed-and-store
- **Issue #19:** Response fields for embed-and-store
- **Issue #27:** Direct vector upsert operations
- **Issue #28:** Strict dimension validation
- **Issue #31:** Metadata and namespace support
- **Issue #40:** Stable response format for events

---

## Quick Links

- 📖 [All Endpoint Examples](./API_EXAMPLES.md)
- 🚀 [Quick Start Guide](../quick-reference/QUICKSTART.md)
- 🔒 [Security Guide](./API_KEY_SECURITY.md)
- ⚠️ [Database Prefix Warning](./DATABASE_PREFIX_WARNING.md)
