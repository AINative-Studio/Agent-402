# Autonomous Fintech Agent Crew

**AINative Edition: CrewAI × X402 × ZeroDB × AIKit**

> **Status:** MVP / Hackathon-ready
> **Goal:** Demonstrate an auditable, replayable, agent-native fintech workflow

---

## 🧠 What This Is

This project is a **minimal but real** implementation of an **agent-native fintech system**.

It proves that autonomous AI agents can:

* Discover and call financial services
* Cryptographically sign requests (X402)
* Persist decisions and memory
* Produce audit-ready ledgers
* Replay workflows deterministically

This is **not a toy demo**.
It is the smallest possible foundation for **regulated, agent-driven finance**.

---

## 🎯 Why This Exists

Most AI agent demos today are:

* Stateless
* Non-verifiable
* Impossible to audit or replay
* Unsafe for regulated domains

This project shows what changes when you add:

* **Signed requests**
* **Persistent agent memory**
* **Immutable ledgers**
* **Deterministic replay**

---

## 🏗️ Architecture Overview

```
+------------------------------+
|        CrewAI Agents         |
|------------------------------|
| analyst                      |
| compliance_agent             |
| transaction_agent            |
|------------------------------|
| Tools                        |
| - AIKit x402.request         |
| - Market Data (mock)         |
+--------------+---------------+
               |
               v
+------------------------------+
|      X402 FastAPI Server     |
|------------------------------|
| /.well-known/x402            |
| /x402 (signed POST)          |
| Signature verification      |
| Payload validation           |
+--------------+---------------+
               |
               v
+------------------------------+
|           ZeroDB             |
|------------------------------|
| agents                       |
| agent_memory                 |
| compliance_events            |
| x402_requests (ledger)       |
| events                       |
+------------------------------+
```

---

## 🤖 Agent Roles (MVP)

| Agent                 | Responsibility                   |
| --------------------- | -------------------------------- |
| **Analyst Agent**     | Evaluates mock market data       |
| **Compliance Agent**  | Simulates KYC/KYT + risk scoring |
| **Transaction Agent** | Signs and submits X402 requests  |

Each agent has:

* A DID
* A defined scope
* Access to shared AIKit tools
* Persistent memory in ZeroDB

---

## 🔐 Core Technologies

* **CrewAI** — Multi-agent orchestration
* **FastAPI** — X402 protocol server
* **X402** — Cryptographically signed request protocol
* **ZeroDB** — Persistent memory, vectors, ledgers, audit
* **AIKit** — Tool abstraction + execution tracing

---

## 📦 Repo Structure

```
.
├── agents/
│   ├── analyst.py
│   ├── compliance.py
│   └── transaction.py
│
├── server/
│   ├── main.py              # FastAPI X402 server
│   ├── x402.py              # Signing + verification
│   └── routes.py
│
├── tools/
│   └── x402_request.py      # AIKit tool wrapper
│
├── zerodb/
│   ├── client.py
│   └── schemas.py
│
├── tests/
│   └── smoke_test.py        # End-to-end validation
│
├── scripts/
│   └── run_demo.py          # One-command demo
│
├── .env.example
├── README.md
└── pyproject.toml
```

---

## 🚀 Quick Start (5 Minutes)

### 1. Clone & install

```bash
git clone https://github.com/ainative/autonomous-fintech-agent-crew.git
cd autonomous-fintech-agent-crew
pip install -r requirements.txt
```

---

### 2. Configure environment

Create `.env`:

```bash
API_KEY=your_zerodb_api_key
BASE_URL=https://api.ainative.studio/v1/public
PROJECT_ID=your_project_id
```

---

### 3. Start the X402 server

```bash
uvicorn server.main:app --reload
```

---

### 4. Run the full agent workflow

```bash
python scripts/run_demo.py
```

✅ In under 5 minutes you should see:

* Signed X402 request verified
* Agent memory written to ZeroDB
* Compliance event stored
* Ledger entry created
* Replayable workflow completed

---

## 🧪 Smoke Test

Run the full system validation:

```bash
python tests/smoke_test.py
```

The smoke test verifies:

1. Project exists
2. Embeddings work
3. Agent memory persists
4. X402 requests are signed + verified
5. Ledger entries are immutable
6. Workflow is replayable

If this passes, **the system is real**.

---

## 🔁 Deterministic Replay

Every agent action writes to ZeroDB with:

* `agent_id`
* `run_id`
* `inputs`
* `outputs`
* `timestamp`

You can replay a run **without re-executing agents**, proving:

* Auditability
* Non-repudiation
* Compliance traceability

---

## 📜 ZeroDB DX Contract

This project follows the **ZeroDB DX Contract**, which guarantees:

* Stable endpoints
* Default 384-dim embeddings
* Deterministic errors
* Immutable ledgers
* Copy-paste-safe docs

If the contract changes, it requires versioning.

---

## 🧠 What This Project Is *Not*

* ❌ A production fintech system
* ❌ A full compliance implementation
* ❌ A UI product

This is **infrastructure**, not an app.

---

## 🏆 Hackathon Framing

> “We didn’t build a demo.
> We built the minimum viable foundation for agent-native finance.”

Judges should focus on:

* Auditability
* Determinism
* Real cryptography
* Replayability
* Clear extensibility

---

## 🔮 What Comes Next

* Replace mock fintech endpoints with real APIs
* Expand compliance logic
* Add multi-party signing
* Introduce agent marketplaces
* Enforce regulatory workflows

---

## 📫 Support & Contact

* **AINative Studio** — [https://ainative.studio](https://ainative.studio)
* **Issues / PRs** — welcome
* **Hackathon questions** — find us onsite

---
