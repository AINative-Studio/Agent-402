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
* If `model` is specified:

  * The same model **must** be used for store + search
* Dimension mismatches always return:

  * `DIMENSION_MISMATCH`

---

### 4. Endpoint Prefixing

* All vector and database operations **require** the `/database/` prefix
* Missing `/database/` will always return:

  * `404 Not Found`
* This behavior is permanent

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

