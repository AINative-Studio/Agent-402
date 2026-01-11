# 🔒 ZeroDB DX Contract (v1)

**Status:** Stable
**Applies To:** `https://api.ainative.studio/v1/public`
**Audience:** Developers, Agent Frameworks (CrewAI, AIKit), Platform Integrators

---

## 🎯 Purpose

The ZeroDB DX Contract defines the **behaviors, defaults, and invariants** that ZeroDB guarantees will **not change without explicit versioning**.

This contract exists to ensure:

* Deterministic behavior
* Safe agent execution
* Auditability and replay
* Long-term developer trust

If your code follows this contract, **ZeroDB will not silently break it**.

---

## ✅ Guaranteed Behaviors (Hard Invariants)

### 1. API Stability

* All endpoints documented under `/v1/public` maintain:

  * Request shapes
  * Response shapes
  * Error codes
* Breaking changes require **a new version** (`/v2/...`)

---

### 2. Authentication

* All public endpoints accept:

  * `X-API-Key` (server-side, recommended)
  * JWT Bearer token (optional)
* Invalid keys always return:

  * `401 INVALID_API_KEY`

---

### 3. Embeddings & Vectors

* **Default embedding model:**
  `BAAI/bge-small-en-v1.5` → **384 dimensions**
* If `model` is omitted, **384-dim is guaranteed**
* **Model Consistency Requirement (CRITICAL):**
  * The **SAME model MUST be used** for both:
    * `embed-and-store` (storing documents)
    * `search` (querying documents)
  * Within a namespace, mixing models causes:
    * Poor search results
    * Semantic drift
    * Low similarity scores
  * **See [Model Consistency Guide](/docs/api/MODEL_CONSISTENCY_GUIDE.md) for details**
* Dimension mismatches always return:
  * `DIMENSION_MISMATCH` error with clear message
* **Best Practice:** Define model as configuration constant
* **Best Practice:** Use separate namespaces for different models

---

### 4. Endpoint Prefixing

* **CRITICAL:** All vector and database operations **require** the `/database/` prefix

  ```
  ✅ CORRECT:   /v1/public/database/vectors/upsert
  ❌ INCORRECT: /v1/public/vectors/upsert  (returns 404)
  ```

* **Operations requiring `/database/` prefix:**
  * Vector operations: `/database/vectors/*`
  * Table operations: `/database/tables/*`
  * File operations: `/database/files/*`
  * Event operations: `/database/events/*`

* **Operations NOT requiring `/database/` prefix:**
  * Projects API: `/v1/public/projects`
  * Embeddings generation: `/v1/public/{project_id}/embeddings/generate`
  * Embed and store: `/v1/public/{project_id}/embeddings/embed-and-store`
  * Semantic search: `/v1/public/{project_id}/embeddings/search`

* Missing `/database/` will always return:
  * `404 Not Found`

* This behavior is permanent and guaranteed

* **See:** [DATABASE_PREFIX_WARNING.md](/docs/api/DATABASE_PREFIX_WARNING.md) for comprehensive guide

---

### 5. Tables API

* Table row inserts **must** use:

  ```json
  { "row_data": { ... } }
  ```
* Using `rows` or `data` will always return:

  * `422 Unprocessable Entity`
* Error payloads include:

  * `loc`, `msg`, `type`

---

### 6. Projects API

* **All project responses MUST include `status` field**
* Supported statuses: `ACTIVE`, `SUSPENDED`, `DELETED`
* Newly created projects **always** have:

  ```json
  { "status": "ACTIVE" }
  ```
* The `status` field will **never** be null, undefined, or omitted
* This applies to:

  * `POST /v1/public/projects` (create)
  * `GET /v1/public/projects` (list - all items)
  * `GET /v1/public/projects/{id}` (get details)

---

### 7. Error Semantics

* All errors return a deterministic shape:

  ```json
  {
    "detail": "...",
    "error_code": "..."
  }
  ```
* Error codes are stable and documented
* Validation errors always use HTTP 422

---

## 🤖 Agent-Native Guarantees

ZeroDB is safe for autonomous agents.

### Agent-Specific Invariants

* Agent-written data is **append-only by convention**
* Historical records are never silently mutated
* Events, memory, and ledgers are replayable
* Identical inputs produce identical outcomes

This enables:

* Auditing
* Compliance workflows
* Deterministic replay
* Non-repudiation

---

## 📚 Documentation Guarantees

* All examples in the Developer Guide are:

  * Copy-paste safe
  * Executable
  * Tested via smoke tests
* Only **verified endpoints** appear in docs
* Defaults and hard rules are enforced consistently

Docs are treated as **executable specifications**, not marketing.

---

## 🔁 Versioning Policy

* Backward-incompatible changes:

  * Require a new major version (`/v2`)
* Additive changes:

  * May be introduced in-place
* Deprecated behavior:

  * Will be documented before removal

---

## 🛡️ What This Contract Does *Not* Guarantee

* Performance SLAs (covered separately)
* Feature availability across tiers
* Business logic correctness in your application

This contract governs **behavior**, not outcomes.

---

## 📌 In One Sentence

> **The ZeroDB DX Contract guarantees that agent systems and developer integrations remain stable, deterministic, and auditable — even as the platform evolves.**

---

