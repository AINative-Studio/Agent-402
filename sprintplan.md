# 🗓️ One-Day Sprint Plan (8–10 Hours)

**Sprint Goal:**
Deliver a **fully runnable, auditable, replayable CrewAI × X402 × ZeroDB MVP** that matches the PRD exactly and can be demoed in under 5 minutes.

---

## 🧭 Sprint Principles (Non-Negotiable)

* Local-first execution (CrewAI runs locally)
* One command demo (`python main.py`)
* Zero mocks in the happy path
* Docs = behavior
* Smoke test == gate to done

---

## ⏱️ Hour-by-Hour Plan

---

## **Hour 0–0.5 — Sprint Setup & Lock Scope**

**PRD Sections:** 1–4, 14

### Tasks

* Create repo structure
* Add `.env.example`
* Lock dependency versions

### Deliverables

* Repo initialized
* `.env.example` includes:

  * `ZERODB_API_KEY`
  * `ZERODB_PROJECT_ID`
  * `X402_SERVER_URL`
* README stub with **Sprint Goal**

### Definition of Done

* Repo runs `python --version`
* No missing env vars unclear

---

## **Hour 0.5–1.5 — ZeroDB Schema & Connectivity**

**PRD Sections:** 6, 10

### Tasks

* Define ZeroDB collections:

  * `agents`
  * `agent_memory`
  * `compliance_events`
  * `x402_requests`
* Write minimal ZeroDB client wrapper

### Deliverables

* `zerodb/client.py`
* `zerodb/schema.md`
* Connectivity test script

### Definition of Done

* Can write + read a record from each collection
* No vectors unless explicitly required

---

## **Hour 1.5–2.5 — X402 FastAPI Server**

**PRD Sections:** 3, 4, 8

### Tasks

* Build FastAPI app
* Implement:

  * `/.well-known/x402`
  * `/x402` POST
* Signature verification
* Persist request to `x402_requests`

### Deliverables

* `server/main.py`
* Deterministic mock responses:

  * quote
  * compliance
  * transaction

### Definition of Done

* Signed request accepted
* Invalid signature rejected
* Ledger entry written

---

## **Hour 2.5–3.5 — AIKit Tool: `x402.request`**

**PRD Sections:** 7, 8

### Tasks

* Wrap X402 client as AIKit tool
* Standardize schema
* Add logging hooks

### Deliverables

* `aikit/tools/x402_request.py`
* Tool schema documented

### Definition of Done

* Tool callable outside CrewAI
* Tool logs request + response
* Tool failure is explicit

---

## **Hour 3.5–5.0 — CrewAI Local Runtime Integration**

**PRD Sections:** 5, 6, 8

### Tasks

* Install CrewAI locally
* Define agents:

  * Analyst
  * Compliance
  * Transaction
* Wire AIKit tool into CrewAI
* Define tasks + sequencing

### Deliverables

* `crew/agents.py`
* `crew/tasks.py`
* `crew/run.py`

### Definition of Done

* Crew runs locally
* Tools invoked correctly
* Output visible in console

---

## **Hour 5.0–6.0 — ZeroDB-Backed Agent Memory**

**PRD Sections:** 6, 11

### Tasks

* Persist agent decisions
* Persist compliance results
* Persist task outputs

### Deliverables

* `memory/adapter.py`
* Memory write hooks

### Definition of Done

* Agent output persists across runs
* Second run sees previous memory
* Memory query works

---

## **Hour 6.0–7.0 — Workflow Replay**

**PRD Sections:** 6, 11

### Tasks

* Read agent history from ZeroDB
* Reconstruct execution order
* Output replay trace

### Deliverables

* `replay/replay.py`

### Definition of Done

* Replay reproduces prior run
* Outputs match stored values
* No agent re-execution required

---

## **Hour 7.0–8.0 — Exact Smoke Test**

**PRD Sections:** 11

### Tasks

Create **one script** that:

1. Runs the crew
2. Verifies X402 signature
3. Writes ledger entry
4. Writes agent memory
5. Writes compliance result
6. Replays workflow
7. Intentionally fails on:

   * wrong model
   * missing `/database/`
   * missing `row_data`

### Deliverables

* `tests/smoke_test.py`

### Definition of Done

* Test passes cleanly
* Any contract drift fails loudly

---

## **Hour 8.0–9.0 — Demo Hardening**

**PRD Sections:** 9, 12

### Tasks

* Create single demo command
* Clean logs
* Add timestamps + IDs

### Deliverables

* `main.py`
* Clean console output
* Optional screenshot

### Definition of Done

* `python main.py` runs end-to-end
* Demo completes < 5 minutes

---

## **Hour 9.0–10.0 — Final Polish**

**PRD Sections:** All

### Tasks

* Update README
* Add architecture diagram (optional)
* Verify PRD alignment

### Deliverables

* README.md (How it works, How to run)
* Final PRD reference link

### Definition of Done

* Anyone can clone and run
* Judges understand in 60 seconds

---

## ✅ Sprint Exit Criteria (Hard Gate)

You are **done** only if:

* CrewAI runs locally
* X402 signatures verified
* ZeroDB persists:

  * agent memory
  * compliance events
  * request ledger
* Workflow is replayable
* Smoke test passes
* Demo is deterministic

---

## 🎯 Final Outcome

At the end of this sprint you will have:

> **The minimum viable, auditable, agent-native fintech system — built correctly.**

No fluff. No fake infra.
Just **agents, signatures, memory, and proof**.

