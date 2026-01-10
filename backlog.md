## Epic 1 — Public Projects API (Create/List) ✅

**Goal:** Developers can create a project and list projects reliably using `X-API-Key`.

### User Stories

1. **(2 pts)** As a developer, I can **create a project** via `POST /v1/public/projects` with `name, description, tier, database_enabled`.
2. **(2 pts)** As a developer, I can **list my projects** via `GET /v1/public/projects` and see `id/name/status/tier`.
3. **(2 pts)** As a developer, I receive **tier validation errors** (`INVALID_TIER`) with clear messages.
4. **(2 pts)** As a developer, I receive **project limit errors** (`PROJECT_LIMIT_EXCEEDED`) with clear messages.
5. **(1 pt)** As a developer, I can see **status ACTIVE** in project responses consistently.

---

## Epic 2 — Auth & Request Consistency (API Key + Optional JWT)

**Goal:** Requests consistently authenticate and failures are uniform.

### User Stories

1. **(2 pts)** As a developer, I can authenticate all public endpoints using **`X-API-Key`**.
2. **(2 pts)** As a developer, invalid API keys return **401 with `INVALID_API_KEY`** consistently.
3. **(1 pt)** As a developer, errors include **`detail`** consistently across endpoints.
4. **(2 pts)** As a developer, I can optionally login via `POST /v1/public/auth/login` and use **Bearer JWT**.
5. **(1 pt)** As a developer, docs clearly warn **never use API keys client-side**.

---

## Epic 3 — Embeddings: Generate (Multi-dimension)

**Goal:** Generate embeddings reliably with a default model and optional model selection.

### User Stories

1. **(2 pts)** As a developer, I can generate embeddings using `POST /v1/public/{project_id}/embeddings/generate` with `texts[]`.
2. **(2 pts)** As a developer, the API defaults to **384-dim** embeddings when `model` is omitted.
3. **(2 pts)** As a developer, I can set `model` to `bge-small/base/large` and receive correct `dimensions`.
4. **(2 pts)** As a developer, I receive **MODEL_NOT_FOUND** when I pass an unsupported model.
5. **(1 pt)** As a developer, I can see `processing_time_ms` in responses for debugging.

---

## Epic 4 — Embeddings: Embed and Store

**Goal:** Store documents + vectors with namespaces and upsert behavior.

### User Stories

1. **(2 pts)** As a developer, I can embed+store documents using `POST /v1/public/{project_id}/embeddings/embed-and-store`.
2. **(2 pts)** As a developer, I can specify `namespace` and it scopes retrieval properly.
3. **(2 pts)** As a developer, `upsert: true` updates existing IDs without creating duplicates.
4. **(2 pts)** As a developer, responses always include `vectors_stored`, `embeddings_generated`, `model`, `dimensions`.
5. **(1 pt)** As a developer, docs and examples enforce **model consistency** across store and search.

---

## Epic 5 — Embeddings: Semantic Search

**Goal:** Search with top_k, namespace, filters, and thresholds.

### User Stories

1. **(2 pts)** As a developer, I can search via `POST /v1/public/{project_id}/embeddings/search` with `query`.
2. **(2 pts)** As a developer, I can set `top_k` and receive that many results (up to max).
3. **(2 pts)** As a developer, I can search within a `namespace` only.
4. **(2 pts)** As a developer, I can apply `filter` over metadata fields.
5. **(2 pts)** As a developer, I can set `similarity_threshold` to filter low-score results.
6. **(1 pt)** As a developer, I can toggle `include_embeddings` and `include_metadata`.

---

## Epic 6 — Vector Operations API (`/database/vectors/...`)

**Goal:** Provide direct vector upsert for advanced users and ensure `/database/` prefix correctness.

### User Stories

1. **(2 pts)** As a developer, I can upsert a vector via `POST /v1/public/{project_id}/database/vectors/upsert`.
2. **(2 pts)** As a developer, vector upsert enforces correct **dimension length** for the chosen model/namespace.
3. **(2 pts)** As a developer, I receive `DIMENSION_MISMATCH` with expected vs received dimensions.
4. **(1 pt)** As a developer, docs clearly warn that missing `/database/` causes 404.
5. **(2 pts)** As a developer, vector upsert supports `metadata` + `namespace`.

---

## Epic 7 — Tables API (NoSQL Tables)

**Goal:** Support table creation and row insertion + listing with strict request shapes.

### User Stories

1. **(2 pts)** As a developer, I can create a table via `POST /v1/public/{project_id}/database/tables` with `name/description/schema`.
2. **(2 pts)** As a developer, I can insert a row via `POST /v1/public/{project_id}/database/tables/{table}/rows` using **`row_data`**.
3. **(2 pts)** As a developer, invalid row payloads return **422** with a helpful missing-field error for `row_data`.
4. **(2 pts)** As a developer, I can list rows via `GET /v1/public/{project_id}/database/tables/{table}/rows?limit=...`.
5. **(1 pt)** As a developer, docs clearly warn **NOT** to use `rows` or `data`.

---

## Epic 8 — Events API (`/database/events`)

**Goal:** Developers can post analytics-style events with consistent schema.

### User Stories

1. **(2 pts)** As a developer, I can send events via `POST /v1/public/{project_id}/database/events`.
2. **(2 pts)** As a developer, events accept `event_type`, `data`, and `timestamp`.
3. **(2 pts)** As a developer, timestamp validation errors are clear and actionable.
4. **(1 pt)** As a developer, event writes return a stable success response.

---

## Epic 9 — Error Codes, Response Shapes, and Consistency Layer

**Goal:** One predictable API experience across all endpoints.

### User Stories

1. **(2 pts)** As a developer, all errors return `{ detail, error_code }` when applicable.
2. **(2 pts)** As a developer, 404s are clearly distinguishable between wrong path vs missing resource.
3. **(2 pts)** As a developer, validation errors (422) always show `loc/msg/type`.
4. **(1 pt)** As a developer, docs list the **top 10 most common errors** with fixes.

---

## Epic 10 — Docs System: Copy/Paste Safety + Single Source of Truth

**Goal:** The guide is always correct, consistent, and matches production.

### User Stories

1. **(2 pts)** As a developer, every snippet uses the same variables: `API_KEY`, `PROJECT_ID`, `BASE_URL`.
2. **(2 pts)** As a developer, the guide includes a **canonical endpoint list** (only endpoints verified).
3. **(2 pts)** As a developer, every endpoint includes **method + path + minimal example**.
4. **(2 pts)** As a developer, “Critical Requirements” are enforced throughout examples (384 default, /database/, row_data).
5. **(2 pts)** As a developer, docs remove claims like “40+ endpoints” unless the endpoints are enumerated.

---

## Epic 11 — Integration Tests + Smoke Harness (Docs Verification)

**Goal:** Every example in the guide is executable in CI against staging/prod.

### User Stories

1. **(3 pts)** As a maintainer, I have a **smoke test script** that runs: create project → embed+store → search → create table → insert row → post event.
2. **(2 pts)** As a maintainer, tests validate **dimension consistency** for embedding models.
3. **(2 pts)** As a maintainer, tests verify `/database/` vector paths and fail loudly if missing.
4. **(2 pts)** As a maintainer, tests verify 422 behavior for missing `row_data`.
5. **(2 pts)** As a maintainer, tests run in CI with secrets stored safely (no keys committed).

---

## Epic 12 — “AINative Aligned” SDK Helpers (Optional but huge DX win)

**Goal:** Reduce integration friction by providing thin helpers that match the docs.

### User Stories

1. **(2 pts)** As a developer, I can use a minimal client wrapper that sets base URL + headers once.
2. **(2 pts)** As a developer, I have helper methods: `create_project`, `embed_and_store`, `search`, `create_table`, `insert_row`, `track_event`.
3. **(2 pts)** As a developer, wrappers surface friendly errors for common gotchas (row_data, /database/).
4. **(1 pt)** As a developer, SDK examples match docs line-for-line.

---

