# 📚 Final Backlog — PRD-Aligned (Source of Truth)

---

## Epic 1 — Public Projects API (Create & List)

**PRD Alignment:** §6 ZeroDB Integration, §9 Deliverables

**Goal:** Developers can create and list projects reliably using `X-API-Key`.

### User Stories

1. **(2 pts)** As a developer, I can create a project via `POST /v1/public/projects` with `name, description, tier, database_enabled`.
   → PRD §6 (ZeroDB collections require project scoping)

2. **(2 pts)** As a developer, I can list my projects via `GET /v1/public/projects` and see `id, name, status, tier`.
   → PRD §9 (Demo setup must be deterministic)

3. **(2 pts)** As a developer, I receive tier validation errors (`INVALID_TIER`) with clear messages.
   → PRD §10 (Demo must fail loudly and clearly)

4. **(2 pts)** As a developer, I receive project limit errors (`PROJECT_LIMIT_EXCEEDED`) with clear messages.
   → PRD §12 (Infrastructure credibility)

5. **(1 pt)** As a developer, project responses consistently show `status: ACTIVE`.
   → PRD §9 (Stable demo expectations)

---

## Epic 2 — Auth & Request Consistency

**PRD Alignment:** §10 Success Criteria, §12 Strategic Positioning

**Goal:** All requests authenticate consistently and predictably.

### User Stories

1. **(2 pts)** As a developer, I can authenticate all public endpoints using `X-API-Key`.
   → PRD §10 (Signed requests + auditability)

2. **(2 pts)** As a developer, invalid API keys return `401 INVALID_API_KEY`.
   → PRD §10 (Clear failure modes)

3. **(1 pt)** As a developer, all errors include a `detail` field.
   → PRD §10 (Replay + explainability)

4. **(2 pts)** As a developer, I can optionally authenticate via JWT using `POST /v1/public/auth/login`.
   → PRD §12 (Future extensibility, not required for MVP)

5. **(1 pt)** As a developer, docs clearly warn not to use API keys client-side.
   → PRD §12 (Fintech credibility)

---

## Epic 3 — Embeddings: Generate

**PRD Alignment:** §6 ZeroDB Integration

**Goal:** Generate embeddings reliably with deterministic defaults.

### User Stories

1. **(2 pts)** As a developer, I can generate embeddings via `POST /embeddings/generate`.
   → PRD §6 (Agent memory + search)

2. **(2 pts)** As a developer, the API defaults to 384-dim embeddings when `model` is omitted.
   → PRD §10 (Determinism)

3. **(2 pts)** As a developer, I can specify supported models and receive correct dimensions.
   → PRD §12 (Extensibility)

4. **(2 pts)** As a developer, unsupported models return `MODEL_NOT_FOUND`.
   → PRD §10 (Clear failure modes)

5. **(1 pt)** As a developer, responses include `processing_time_ms`.
   → PRD §9 (Demo observability)

---

## Epic 4 — Embeddings: Embed & Store

**PRD Alignment:** §6 ZeroDB Integration

**Goal:** Store documents and vectors with namespaces and upsert behavior.

### User Stories

1. **(2 pts)** As a developer, I can embed and store documents via `embed-and-store`.
   → PRD §6 (Agent memory foundation)

2. **(2 pts)** As a developer, `namespace` scopes retrieval correctly.
   → PRD §6 (Agent-scoped memory)

3. **(2 pts)** As a developer, `upsert: true` updates existing IDs without duplication.
   → PRD §10 (Replayability)

4. **(2 pts)** As a developer, responses include vectors stored, model, and dimensions.
   → PRD §9 (Demo proof)

5. **(1 pt)** As a developer, docs enforce model consistency across store and search.
   → PRD §10 (Determinism)

---

## Epic 5 — Embeddings: Semantic Search

**PRD Alignment:** §6 ZeroDB Integration

**Goal:** Search memory with filters and thresholds.

### User Stories

1. **(2 pts)** As a developer, I can search via `/embeddings/search`.
   → PRD §6 (Agent recall)

2. **(2 pts)** As a developer, I can limit results via `top_k`.
   → PRD §10 (Predictable replay)

3. **(2 pts)** As a developer, I can scope search by namespace.
   → PRD §6 (Agent isolation)

4. **(2 pts)** As a developer, I can filter over metadata.
   → PRD §6 (Compliance & audit)

5. **(2 pts)** As a developer, I can enforce `similarity_threshold`.
   → PRD §10 (Explainability)

6. **(1 pt)** As a developer, I can toggle metadata and embeddings in results.
   → PRD §9 (Demo visibility)

---

## Epic 6 — Vector Operations API

**PRD Alignment:** §6 ZeroDB Integration

**Goal:** Enable direct vector operations for advanced use cases.

### User Stories

1. **(2 pts)** As a developer, I can upsert vectors via `/database/vectors/upsert`.
   → PRD §6 (Low-level control)

2. **(2 pts)** As a developer, dimension length is enforced strictly.
   → PRD §10 (Determinism)

3. **(2 pts)** As a developer, mismatches return `DIMENSION_MISMATCH`.
   → PRD §10 (Clear failures)

4. **(1 pt)** As a developer, docs clearly warn about missing `/database/`.
   → PRD §10 (DX contract)

5. **(2 pts)** As a developer, vector upsert supports metadata and namespace.
   → PRD §6 (Auditability)

---

## Epic 7 — Tables API (NoSQL)

**PRD Alignment:** §6 ZeroDB Integration

**Goal:** Support structured, auditable data storage.

### User Stories

1. **(2 pts)** As a developer, I can create tables with schema definitions.
   → PRD §6 (Compliance records)

2. **(2 pts)** As a developer, I can insert rows using `row_data`.
   → PRD §10 (Contract stability)

3. **(2 pts)** As a developer, missing `row_data` returns a clear 422 error.
   → PRD §10 (Deterministic errors)

4. **(2 pts)** As a developer, I can list rows with pagination.
   → PRD §9 (Demo verification)

5. **(1 pt)** As a developer, docs warn against using `rows` or `data`.
   → PRD §10 (DX contract)

---

## Epic 8 — Events API

**PRD Alignment:** §6 ZeroDB Integration, §10 Success Criteria

**Goal:** Track system and agent events consistently.

### User Stories

1. **(2 pts)** As a developer, I can post events via `/database/events`.
   → PRD §6 (Audit trail)

2. **(2 pts)** As a developer, events accept `event_type, data, timestamp`.
   → PRD §10 (Replayability)

3. **(2 pts)** As a developer, invalid timestamps return clear errors.
   → PRD §10 (Determinism)

4. **(1 pt)** As a developer, event writes return a stable success response.
   → PRD §9 (Demo clarity)

5. **(1 pt)** As an agent system, I can emit agent lifecycle events (`agent_decision`, `agent_tool_call`).
   → PRD §5 (Agent personas)

---

## Epic 9 — Error & Response Consistency

**PRD Alignment:** §10 Success Criteria

**Goal:** One predictable API surface.

### User Stories

1. **(2 pts)** As a developer, errors return `{ detail, error_code }`.
   → PRD §10

2. **(2 pts)** As a developer, 404s distinguish path vs resource errors.
   → PRD §10

3. **(2 pts)** As a developer, validation errors include `loc/msg/type`.
   → PRD §10

4. **(1 pt)** As a developer, docs list top 10 common errors with fixes.
   → PRD §9

---

## Epic 10 — Docs System & DX Contract

**PRD Alignment:** §9 Deliverables, §12 Strategic Positioning

**Goal:** Docs are executable and authoritative.

### User Stories

1. **(2 pts)** As a developer, all examples use `API_KEY`, `PROJECT_ID`, `BASE_URL`.
   → PRD §9

2. **(2 pts)** As a developer, only verified endpoints appear in docs.
   → PRD §12

3. **(2 pts)** As a developer, every endpoint has a minimal copy-paste example.
   → PRD §9

4. **(2 pts)** As a developer, critical requirements are enforced everywhere.
   → PRD §10

5. **(2 pts)** As a maintainer, a public **ZeroDB DX Contract** documents all invariants.
   → PRD §10, §12

---

## Epic 11 — Integration Tests & Smoke Harness

**PRD Alignment:** §10 Success Criteria, §9 Deliverables

**Goal:** Behavior is continuously verified.

### User Stories

1. **(3 pts)** As a maintainer, a smoke test runs: project → embed → search → table → row → event.
   → PRD §10

2. **(2 pts)** As a maintainer, tests validate embedding dimension consistency.
   → PRD §10

3. **(2 pts)** As a maintainer, tests fail loudly on missing `/database/`.
   → PRD §10

4. **(2 pts)** As a maintainer, tests validate 422 for missing `row_data`.
   → PRD §10

5. **(2 pts)** As a maintainer, smoke tests verify agent memory write + replay.
   → PRD §10

---

## Epic 12 — Agent-Native & CrewAI Integration (MVP-Critical)

**PRD Alignment:** §5, §6, §8, §10, §11

**Goal:** Make PRD claims about agents *provably true*.

### User Stories

1. **(2 pts)** As a CrewAI system, I can write agent profiles (`did, role`) to `agents`.
   → PRD §5

2. **(2 pts)** As an agent, I can persist decisions to `agent_memory`.
   → PRD §6

3. **(2 pts)** As a compliance agent, I can write outcomes to `compliance_events`.
   → PRD §6

4. **(3 pts)** As a system, X402 requests are linked to the agent + task that produced them.
   → PRD §6, §8

5. **(2 pts)** As a developer, I can replay an agent run using only ZeroDB records.
   → PRD §10, §11

6. **(1 pt)** As a system, all agent records are append-only.
   → PRD §10 (Non-repudiation)

---

