# 🟦 One-Day Sprint Plan — ZeroDB Public API + Dev Docs Alignment

**Sprint Length:** 1 Day (8 hours)
**Sprint Goal:**

> *Every copy-paste example in the ZeroDB Developer Guide executes successfully against production/staging APIs with predictable behavior and errors.*

---

## 🕘 09:00–09:30 — Sprint Kickoff & Scope Lock (30 min)

### Objectives

* Lock **what is in scope**
* Freeze the Developer Guide as the **source of truth**
* Assign owners

### Tasks

* ✅ Confirm **no new features**
* ✅ Confirm **384-dim default, multi-model optional**
* ✅ Confirm required endpoints:

  * `/projects`
  * `/embeddings/*`
  * `/database/vectors/*`
  * `/database/tables/*`
  * `/database/events`
* ✅ Decide staging vs prod test target

**Deliverable**

* Sprint checklist pinned in repo / Notion

---

## 🕘 09:30–10:45 — API Contract Validation & Gaps (75 min)

### Objectives

* Verify endpoints behave exactly as docs claim
* Identify mismatches **before coding**

### Tasks

* Run **every curl example** in the guide
* Log failures by category:

  * ❌ wrong path
  * ❌ wrong param name
  * ❌ missing defaults
  * ❌ inconsistent error shape
* Validate:

  * `row_data` enforcement
  * `/database/` prefix enforcement
  * default embedding model behavior
  * dimension mismatch errors

**Deliverable**

* Short “API Gap List” (max 10 items)

---

## 🕙 10:45–12:00 — API Fixes & Enforcement (75 min)

### Objectives

* Fix only what breaks the guide
* Enforce guardrails, not flexibility

### Tasks

* Enforce **default embedding model**
* Enforce **dimension validation**
* Normalize error responses:

  ```json
  { "detail": "...", "error_code": "..." }
  ```
* Ensure:

  * `/vectors/upsert` without `/database/` = 404
  * missing `row_data` = 422
  * bad model = 500 MODEL_NOT_FOUND

**Deliverable**

* All guide examples now succeed or fail *correctly*

---

## 🕛 12:00–12:30 — Lunch / Async Review (30 min)

* Let tests run
* Fix anything obvious

---

## 🕧 12:30–13:45 — Smoke Test Harness (75 min)

### Objectives

* Guarantee docs never drift again

### Tasks

Create a single script that executes:

1. Create project
2. Embed + store document
3. Semantic search
4. Create table
5. Insert row
6. Track event
7. Fail test cases:

   * wrong model
   * wrong vector dimension
   * missing row_data

**Deliverable**

* `zerodb_smoke_test.py` or `smoke.sh`
* Runnable with env vars:

  ```bash
  API_KEY=... PROJECT_ID=...
  ```

---

## 🕑 13:45–15:00 — Docs Final Alignment Pass (75 min)

### Objectives

* Make the guide **bulletproof**
* Remove ambiguity and future foot-guns

### Tasks

* Normalize variables everywhere:

  * `API_KEY`
  * `PROJECT_ID`
  * `BASE_URL`
* Add **CRITICAL** callouts where enforcement exists
* Remove:

  * vague claims (“40+ endpoints”)
  * anything not test-verified
* Confirm:

  * every snippet copy-pastes clean
  * every error example matches reality

**Deliverable**

* Final v2.0 Developer Guide (locked)

---

## 🕒 15:00–16:00 — CI Hook + Final Verification (60 min)

### Objectives

* Prevent regressions
* Declare sprint success

### Tasks

* Add smoke test to CI (or manual gate)
* Run full test suite once more
* Tag release:

  * `zerodb-api-docs-v2.0`

**Deliverables**

* ✅ Green CI / green smoke run
* ✅ Docs published
* ✅ Sprint marked complete

---

## 🟩 Sprint Exit Criteria (Non-Negotiable)

You **do not close this sprint unless**:

* ✅ Every curl snippet works exactly as written
* ✅ Every documented error happens exactly as documented
* ✅ Default embedding behavior is enforced
* ✅ Dimension mismatch cannot silently pass
* ✅ Docs == reality == CI

---

