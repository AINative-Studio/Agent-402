# 📘 Frontend Product Requirements Document (PRD – Demo UI)

**Product Name**
**Autonomous Fintech Agent Crew — Demo UI**
*(AINative / CrewAI × X402 × ZeroDB × AIKit)*

**Framework**
Next.js (App Router) + AIKit Next.js Components

**PRD Type**
**Frontend-only** (read-only, demo UI)

---

## 1. Objective

Build a **read-only demo UI** that makes the backend system **visually provable**:

* Multi-agent workflow (CrewAI)
* Signed X402 requests (cryptographic proof)
* Persistent ZeroDB memory & compliance logs
* Deterministic replay of agent runs

This UI exists to **explain, not control** the system.

---

## 2. Explicit Non-Goals (Hard Boundaries)

The UI will **NOT**:

* Execute agents
* Sign requests
* Write to ZeroDB
* Replace CLI demo execution
* Add authentication or permissions
* Introduce new backend behavior

**Source of truth remains:** backend services + ZeroDB.

---

## 3. Design System (AINative Demo UI)

### 3.1 Color Tokens (CSS Variables)

```css
--bg: #0B0F1A;
--surface: #111A2E;
--surface-2: #0F1628;
--border: rgba(255,255,255,0.08);

--text: rgba(255,255,255,0.92);
--muted: rgba(255,255,255,0.65);
--subtle: rgba(255,255,255,0.45);

--primary: #4F8CFF;
--primary-2: #2E6BFF;
--primary-glow: rgba(79,140,255,0.25);

--success: #2FE39B;
--warning: #FFB020;
--danger: #FF4D5E;
--info: #7C5CFF;
```

**Semantic usage**

* Verified → `success`
* Running / Pending → `primary`
* Warning → `warning`
* Failed → `danger`

---

### 3.2 Typography

**Fonts**

* UI: **Inter**
* Code / hashes: **JetBrains Mono**

**Scale**

* Page title: 28–32px / 700
* Section title: 18–20px / 600
* Body: 14–16px / 400–500
* Code: 12–13px / mono

---

### 3.3 Layout & Shape

* Max width: `1200px`
* Base spacing: `8px`
* Card padding: `16–20px`
* Radius:

  * Cards: `16px`
  * Buttons: `12px`
* Shadows: subtle only

---

## 4. Navigation & IA

```
/                     → Overview
/runs                 → Run list
/runs/[runId]         → Timeline (default)
/runs/[runId]/x402    → X402 ledger
/runs/[runId]/memory  → Agent memory
/runs/[runId]/audit   → Compliance
```

Desktop: left sidebar
Mobile: top tabs

---

## 5. Core Screens (MVP)

### 5.1 Overview

Purpose: **Instant context**

* Title + tagline
* KPI strip (latest run status, #ledger entries, #memory items)
* CTA: **View Latest Run**
* Empty state if no runs exist

---

### 5.2 Runs List

Purpose: **Replay selection**

Each run card:

* Run ID (short)
* Timestamp
* Status badge
* Counts: X402 / Compliance / Memory
* CTA: Open

---

### 5.3 Run Timeline (Primary Screen)

Purpose: **Explain the agent workflow**

Nodes:

1. Analyst decision
2. Compliance evaluation
3. Transaction signing
4. Server verification
5. ZeroDB persistence

Each node:

* Status badge
* Timestamp
* Expandable details
* Links to related tabs

---

### 5.4 X402 Request Inspector

Purpose: **Cryptographic proof**

Displays:

* DID
* Payload hash
* Signature (truncate + expand)
* Verification result
* Timestamp

Expandable drawer:

* Full payload JSON
* Full signature (mono)

---

### 5.5 Agent Memory Viewer

Purpose: **Persistence & learning**

* Filter by agent
* Memory cards with summary, confidence, timestamp
* Read-only

---

### 5.6 Compliance Audit View

Purpose: **Regulated-domain credibility**

* Risk score
* Pass / Fail
* Reason codes
* Timestamp
* Optional mini trend visualization

---

### 5.7 Replay Mode

Purpose: **Deterministic replay**

* Select run
* UI re-renders entirely from stored ZeroDB data
* No execution, no writes

---

## 6. AIKit Component Inventory (Required)

| Screen            | AIKit Primitive                |
| ----------------- | ------------------------------ |
| Layout            | `AICard`, `AIButton`           |
| Status            | `AIBadge`                      |
| Timeline          | `AITimeline`, `AITimelineItem` |
| Tabs              | `AITabs`                       |
| Data display      | `AIKeyValue`                   |
| JSON / signatures | `AICodeBlock`                  |
| Loading           | `AISkeleton`                   |
| Empty state       | `AIEmptyState`                 |
| Errors            | `AIToast`                      |

**Rule:**
If a component does not exist yet, create a **wrapper stub** in `/components/aikit/` so it is drop-in replaceable later.

---

## 7. Frontend Data Rules

* **Read-only** API access
* Never mutate backend state
* Never sign or submit requests
* Only consume `/v1/public/...` endpoints

Data sources:

* `x402_requests`
* `agent_memory`
* `compliance_events`
* `agents`

Runs may be derived by grouping on `run_id`.

---

## 8. Next.js Folder Structure

```
app/
  layout.tsx
  page.tsx                # Overview
  runs/
    page.tsx              # Runs list
    [runId]/
      page.tsx            # Timeline
      x402/page.tsx
      memory/page.tsx
      audit/page.tsx

components/
  aikit/                  # AIKit wrappers
    AICard.tsx
    AIBadge.tsx
    AITimeline.tsx
    ...
  layout/
    Sidebar.tsx
    Header.tsx
  runs/
    RunCard.tsx
    RunTimeline.tsx

lib/
  api.ts                  # read-only API helpers
  types.ts                # Run, Ledger, Memory, Audit

styles/
  globals.css             # tokens + tailwind config
```

---

## 9. One-Day Frontend Sprint Plan

### Hour 0–1

* Scaffold Next.js app
* Install Tailwind
* Add fonts + design tokens

### Hour 1–2

* Implement layout + navigation
* Stub AIKit wrapper components

### Hour 2–4

* Overview screen
* Runs list screen
* API read helpers

### Hour 4–6

* Timeline view
* X402 inspector
* Memory & audit views

### Hour 6–7

* Replay logic (run selection)
* Error & empty states

### Hour 7–8

* Polish
* Demo rehearsal
* Dark-mode QA
* Final sanity check

---

## 10. Success Criteria

The frontend is successful if:

* A judge understands the system in <2 minutes
* Verified signatures and persistence are obvious
* Replay works without executing agents
* No backend changes were required

---

## Final Clarifier (Important)

**This UI is a proof surface, not a control surface.**

> *“The system already ran. This UI proves it.”*

---


